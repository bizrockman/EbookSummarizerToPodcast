"""
Service für EPUB-Verarbeitung

Kapitel werden am Book-Objekt in der DB gespeichert.
"""
import os
import hashlib
import json
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from api.models.schemas import Chapter, ChapterType
from api.daos.llm_dao import get_llm_dao

import logging
logger = logging.getLogger("api.epub")


class EPUBService:
    """Service für EPUB-Operationen"""
    
    def validate_epub(self, file_path: str) -> Dict[str, Any]:
        """
        Validiere EPUB-Datei
        
        Returns:
            Dict mit: {"is_valid": bool, "title": str, "author": str, "message": str}
        """
        if not os.path.exists(file_path):
            return {
                "is_valid": False,
                "title": None,
                "author": None,
                "message": f"Datei nicht gefunden: {file_path}"
            }
        
        try:
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
            
            # Extrahiere Metadaten
            title = book.get_metadata('DC', 'title')
            title = title[0][0] if title else "Unbekannt"
            
            author = book.get_metadata('DC', 'creator')
            author = author[0][0] if author else "Unbekannt"
            
            return {
                "is_valid": True,
                "title": title,
                "author": author,
                "message": "EPUB-Datei ist valide"
            }
        except Exception as e:
            return {
                "is_valid": False,
                "title": None,
                "author": None,
                "message": f"Fehler beim Lesen der EPUB-Datei: {str(e)}"
            }
    
    def extract_chapters(self, file_path: str, use_cache: bool = True) -> List[Chapter]:
        """
        Extrahiere Kapitelliste aus EPUB
        
        Args:
            file_path: Pfad zur EPUB-Datei
            use_cache: Ignoriert (für Kompatibilität)
        
        Returns:
            Liste von Chapter-Objekten
        """
        try:
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
            toc = self._extract_toc(book)
            
            chapters = []
            for idx, (title, href) in enumerate(toc):
                chapters.append(Chapter(
                    title=title,
                    href=href,
                    chapter_type=None,
                    order=idx
                ))
            
            return chapters
        except Exception as e:
            raise ValueError(f"Fehler beim Extrahieren der Kapitel: {str(e)}")
    
    def analyze_chapters_with_ai(
        self,
        file_path: str,
        llm_provider: Optional[str] = None,
        db_book=None  # Optional: Book-Objekt aus DB
    ) -> Dict[str, Any]:
        """
        Analysiere alle Kapitel mit KI.
        
        Wenn db_book übergeben wird, werden die Ergebnisse im Book gespeichert
        und bei wiederholtem Aufruf aus dem Book gelesen.
        
        Args:
            file_path: Pfad zur EPUB-Datei
            llm_provider: LLM-Provider (openai, groq)
            db_book: Optional - Book-Objekt aus der Datenbank
        
        Returns:
            Dict mit content_chapters, supplement_chapters, Kosten, etc.
        """
        # Prüfe ob bereits analysiert (aus DB)
        if db_book and db_book.chapters_analyzed:
            logger.info(f"📦 Analyse aus DB geladen: {db_book.title}")
            analyzed = json.loads(db_book.chapters_analyzed)
            return {
                **analyzed,
                "from_cache": True,
                "total_cost": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0
            }
        
        # Neue Analyse durchführen
        logger.info(f"🔍 KI-Analyse wird durchgeführt: {file_path}")
        
        all_chapters = self.extract_chapters(file_path)
        llm_dao = get_llm_dao(llm_provider)
        
        content_chapters = []
        supplement_chapters = []
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        
        for chapter in all_chapters:
            try:
                content = self.extract_chapter_content(
                    file_path, chapter.href, all_chapters
                )
                excerpt = content[:500] if len(content) > 500 else content
            except Exception as e:
                logger.warning(f"Konnte Inhalt für '{chapter.title}' nicht extrahieren: {e}")
                excerpt = ""
            
            detection_result = llm_dao.detect_chapter_type(
                chapter_title=chapter.title,
                chapter_excerpt=excerpt
            )
            
            chapter.chapter_type = ChapterType(detection_result["type"])
            total_cost += detection_result["cost"]
            total_input_tokens += detection_result["tokens"]["input"]
            total_output_tokens += detection_result["tokens"]["output"]
            
            if chapter.chapter_type == ChapterType.CONTENT:
                content_chapters.append(chapter)
            else:
                supplement_chapters.append(chapter)
        
        result = {
            "all_chapters": [ch.dict() for ch in all_chapters],
            "content_chapters": [ch.dict() for ch in content_chapters],
            "supplement_chapters": [ch.dict() for ch in supplement_chapters],
            "total_chapters": len(all_chapters),
            "content_count": len(content_chapters),
            "supplement_count": len(supplement_chapters),
            "total_cost": total_cost,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
            "from_cache": False
        }
        
        # Speichere in DB wenn Book vorhanden
        if db_book:
            db_book.chapters_analyzed = json.dumps({
                "all_chapters": result["all_chapters"],
                "content_chapters": result["content_chapters"],
                "supplement_chapters": result["supplement_chapters"],
                "total_chapters": result["total_chapters"],
                "content_count": result["content_count"],
                "supplement_count": result["supplement_count"]
            })
            db_book.chapters_analyzed_at = datetime.utcnow()
            db_book.analysis_llm_provider = llm_provider or "openai"
            db_book.analysis_cost_usd = total_cost
            db_book.analysis_tokens = total_input_tokens + total_output_tokens
            db_book.total_llm_cost_usd += total_cost
            db_book.total_cost_usd += total_cost
            # DB commit wird vom Aufrufer gemacht
            logger.info(f"💾 Analyse in DB gespeichert: {db_book.title}")
        
        return result
    
    def get_chapters_for_book(self, db_book) -> List[Dict[str, Any]]:
        """
        Hole rohe Kapitel aus einem Book-Objekt.
        """
        if db_book.chapters_raw:
            return json.loads(db_book.chapters_raw)
        return []
    
    def get_analyzed_chapters_for_book(self, db_book) -> Optional[Dict[str, Any]]:
        """
        Hole analysierte Kapitel aus einem Book-Objekt.
        """
        if db_book.chapters_analyzed:
            return json.loads(db_book.chapters_analyzed)
        return None
    
    def extract_chapter_content(
        self,
        file_path: str,
        chapter_href: str,
        all_chapters: Optional[List[Chapter]] = None
    ) -> str:
        """
        Extrahiere Inhalt eines Kapitels
        
        Returns:
            Text-Inhalt des Kapitels
        """
        try:
            book = epub.read_epub(file_path, options={'ignore_ncx': True})
            
            if all_chapters is None:
                all_chapters = self.extract_chapters(file_path)
            
            toc = [(ch.title, ch.href) for ch in all_chapters]
            
            content = self._extract_chapter_content_from_book(
                book, chapter_href, toc
            )
            
            return content
        except Exception as e:
            raise ValueError(f"Fehler beim Extrahieren des Kapitelinhalts: {str(e)}")
    
    def _extract_toc(self, book: epub.EpubBook) -> List[Tuple[str, str]]:
        """Extrahiere Table of Contents"""
        from api.services.epub_structure import table_of_contents
        return table_of_contents(book)
    
    def _extract_toc_from_ncx(self, book: epub.EpubBook) -> List[Tuple[str, str]]:
        """Extrahiere TOC aus NCX-Datei"""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_NAVIGATION:
                soup = BeautifulSoup(item.get_content(), 'xml')
                nav_points = soup.find_all('navPoint')
                toc = [
                    (nav_point.navLabel.text, nav_point.content['src'])
                    for nav_point in nav_points
                ]
                return toc
        return []
    
    def _extract_toc_from_nav(self, book: epub.EpubBook) -> List[Tuple[str, str]]:
        """Extrahiere TOC aus NAV-Datei"""
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_NAVIGATION:
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                toc = [
                    (a.text, a['href'])
                    for a in soup.select('nav[epub|type="toc"] ol li a')
                ]
                return toc
        return []
    
    def _get_spine_order(self, book: epub.EpubBook) -> List[str]:
        """Hole Spine-Reihenfolge"""
        from api.services.epub_structure import spine_items
        return [item.get_name() for item in spine_items(book)]
    
    def _extract_chapter_content_from_book(
        self,
        book: epub.EpubBook,
        href: str,
        toc: List[Tuple[str, str]]
    ) -> str:
        """Extrahiere Kapitelinhalt aus Buch"""
        from api.services.epub_structure import chapter_text
        return chapter_text(book, href, toc)
