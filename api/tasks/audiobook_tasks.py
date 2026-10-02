"""
Huey Tasks für Audiobook-Generierung

Diese Tasks werden im Huey Consumer (Worker) ausgeführt.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydub import AudioSegment
from slugify import slugify

from api.config.huey_config import huey
from api.database.connection import SessionLocal
from api.models.database_models import Job
from api.models.schemas import Chapter, ChapterType
from api.services.epub_service import EPUBService
from api.daos.tts_dao import get_tts_dao
from api.daos.llm_dao import get_llm_dao
from api.daos.job_tracking_dao import get_job_tracking_dao
from api.config.settings import settings

import logging
logger = logging.getLogger("api.tasks")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_job(db, job_id: str) -> Optional[Job]:
    """Hole Job aus DB"""
    dao = get_job_tracking_dao(db)
    return dao.get_job(job_id)


def update_job(db, job_id: str, **kwargs):
    """Aktualisiere Job"""
    dao = get_job_tracking_dao(db)
    if dao.get_job(job_id):
        dao.update_job(job_id, **kwargs)


def add_cost(db, job_id: str, llm_cost: float = 0, tts_cost: float = 0,
             input_tokens: int = 0, output_tokens: int = 0, characters: int = 0):
    """Addiere Kosten zum Job"""
    dao = get_job_tracking_dao(db)
    dao.add_cost(
        job_id=job_id,
        llm_cost=llm_cost,
        tts_cost=tts_cost,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        characters=characters
    )


def log_cost(db, job_id: str, user_id: str, operation: str, provider: str,
             cost_usd: float, **kwargs):
    """Erstelle Cost-Log Eintrag"""
    dao = get_job_tracking_dao(db)
    dao.log_cost(
        job_id=job_id,
        user_id=user_id,
        operation=operation,
        provider=provider,
        cost_usd=cost_usd,
        **kwargs
    )


def add_asset(db, job_id: str, asset_type: str, file_path: str, file_name: str,
              file_size: int = 0, duration: float = 0, chapter_index: int = None,
              chapter_title: str = None) -> str:
    """Füge Asset hinzu"""
    dao = get_job_tracking_dao(db)
    return dao.add_asset(
        job_id=job_id,
        asset_type=asset_type,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        duration=duration,
        chapter_index=chapter_index,
        chapter_title=chapter_title
    )


def log_event(db, job_id: str, user_id: str, event_type: str, **kwargs):
    """Erstelle Event-Eintrag für Job-Timeline."""
    dao = get_job_tracking_dao(db)
    dao.create_event(job_id=job_id, user_id=user_id, event_type=event_type, **kwargs)


def combine_audio_files(chapter_audios: List[Dict], book_title: str, job_id: str = "") -> str:
    """Kombiniere alle Kapitel-Audios zu einer Datei"""
    audio_files = [ch["audio_file"] for ch in chapter_audios if os.path.exists(ch["audio_file"])]
    
    if not audio_files:
        raise ValueError("Keine Audio-Dateien zum Kombinieren")
    
    combined = AudioSegment.empty()
    for file in audio_files:
        segment = AudioSegment.from_mp3(file)
        combined += segment
    
    output_file = os.path.join(
        settings.audiofiles_dir,
        f"{job_id}_{slugify(book_title)}_complete.mp3"
    )
    combined.export(output_file, format="mp3", bitrate="128k")
    
    return output_file


# =============================================================================
# HUEY TASKS
# =============================================================================

@huey.task(retries=2, retry_delay=60)
def process_chapter_analysis(job_id: str):
    """
    Task: Kapitelanalyse mit KI
    
    Analysiert alle Kapitel und klassifiziert sie als content/supplement.
    Speichert Ergebnis auch am Book-Objekt wenn book_id vorhanden.
    """
    from api.models.database_models import Book
    
    db = SessionLocal()
    epub_service = EPUBService()
    
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} nicht gefunden")
            return
        
        config = json.loads(job.config) if job.config else {}
        llm_provider = config.get("llm_provider")
        book_id = config.get("book_id") or job.book_id
        
        # Lade Book wenn vorhanden
        book = None
        if book_id:
            book = db.query(Book).filter(Book.book_id == book_id).first()
            if book:
                logger.info(f"📚 Book gefunden: {book.title}")
        
        # Start
        update_job(db, job_id,
            status="processing",
            progress=5,
            current_step="Validiere EPUB...",
            started_at=datetime.utcnow()
        )
        log_event(
            db, job_id, job.user_id, "job_started",
            status="processing", progress=5, step="Validiere EPUB..."
        )
        
        # Validiere
        validation = epub_service.validate_epub(job.file_path)
        if not validation["is_valid"]:
            raise ValueError(f"EPUB ungültig: {validation['message']}")
        
        update_job(db, job_id,
            book_title=validation["title"],
            book_author=validation.get("author"),
            progress=10,
            current_step="Extrahiere Kapitel..."
        )
        log_event(
            db, job_id, job.user_id, "epub_validated",
            status="processing", progress=10, step="Extrahiere Kapitel..."
        )
        
        # Kapitel extrahieren
        all_chapters = epub_service.extract_chapters(job.file_path)
        total_chapters = len(all_chapters)
        
        # KI-Analyse
        llm_dao = get_llm_dao(llm_provider)
        content_chapters = []
        supplement_chapters = []
        total_cost = 0.0
        total_input_tokens = 0
        total_output_tokens = 0
        
        for idx, chapter in enumerate(all_chapters):
            progress = 10 + int((idx / total_chapters) * 80)
            update_job(db, job_id,
                progress=progress,
                current_step=f"Analysiere {idx + 1}/{total_chapters}: {chapter.title[:40]}...",
                processed_chapters=idx + 1,
                total_chapters=total_chapters
            )
            
            # Excerpt extrahieren
            try:
                content = epub_service.extract_chapter_content(
                    job.file_path, chapter.href, all_chapters
                )
                excerpt = content[:500]
            except:
                excerpt = ""
            
            # KI-Klassifizierung
            result = llm_dao.detect_chapter_type(chapter.title, excerpt)
            chapter.chapter_type = ChapterType(result["type"])
            
            # Kosten tracken
            total_cost += result["cost"]
            total_input_tokens += result["tokens"]["input"]
            total_output_tokens += result["tokens"]["output"]
            
            add_cost(db, job_id,
                llm_cost=result["cost"],
                input_tokens=result["tokens"]["input"],
                output_tokens=result["tokens"]["output"]
            )
            
            log_cost(db, job_id, job.user_id,
                operation="chapter_detection",
                provider=result["provider"],
                model=result.get("model"),
                cost_usd=result["cost"],
                input_tokens=result["tokens"]["input"],
                output_tokens=result["tokens"]["output"],
                step_name=chapter.title
            )
            
            if chapter.chapter_type == ChapterType.CONTENT:
                content_chapters.append(chapter)
            else:
                supplement_chapters.append(chapter)
        
        # Ergebnis speichern
        result_data = {
            "all_chapters": [ch.dict() for ch in all_chapters],
            "content_chapters": [ch.dict() for ch in content_chapters],
            "supplement_chapters": [ch.dict() for ch in supplement_chapters],
            "total_chapters": total_chapters,
            "content_count": len(content_chapters),
            "supplement_count": len(supplement_chapters)
        }
        
        # Am Book speichern wenn vorhanden
        if book:
            book.chapters_analyzed = json.dumps({
                "all_chapters": result_data["all_chapters"],
                "content_chapters": result_data["content_chapters"],
                "supplement_chapters": result_data["supplement_chapters"],
                "total_chapters": total_chapters,
                "content_count": len(content_chapters),
                "supplement_count": len(supplement_chapters)
            })
            book.chapters_analyzed_at = datetime.utcnow()
            book.analysis_llm_provider = llm_provider or "openai"
            book.analysis_cost_usd = total_cost
            book.analysis_tokens = total_input_tokens + total_output_tokens
            book.total_llm_cost_usd += total_cost
            book.total_cost_usd += total_cost
            db.commit()
            logger.info(f"💾 Analyse am Book gespeichert: {book.title}")
        
        update_job(db, job_id,
            status="completed",
            progress=100,
            current_step="Analyse abgeschlossen",
            completed_at=datetime.utcnow(),
            result_data=json.dumps(result_data, default=str)
        )
        log_event(
            db, job_id, job.user_id, "job_completed",
            status="completed", progress=100, step="Analyse abgeschlossen",
            details={
                "content_count": len(content_chapters),
                "supplement_count": len(supplement_chapters)
            }
        )
        
        logger.info(f"✅ Analyse {job_id} abgeschlossen: {len(content_chapters)} content, {len(supplement_chapters)} supplement")
        
    except Exception as e:
        logger.error(f"❌ Analyse {job_id} fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        update_job(db, job_id,
            status="failed",
            current_step="Fehlgeschlagen",
            completed_at=datetime.utcnow(),
            error_message=str(e)
        )
        if job:
            log_event(
                db, job_id, job.user_id, "job_failed",
                status="failed", step="Fehlgeschlagen",
                details={"error": str(e)}
            )
    finally:
        db.close()


@huey.task(retries=1, retry_delay=120)
def process_audiobook_basic(job_id: str):
    """
    Task: Basic Audiobook-Generierung
    
    Generiert Audiobook aus allen Content-Kapiteln.
    """
    db = SessionLocal()
    epub_service = EPUBService()
    
    try:
        from api.models.database_models import Book

        job = get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} nicht gefunden")
            return
        
        config = json.loads(job.config) if job.config else {}
        tts_provider = config.get("tts_provider", "openai")
        voice = config.get("voice", "alloy")
        auto_detect = config.get("auto_detect_content", True)
        llm_provider = config.get("llm_provider")
        book_id = config.get("book_id") or job.book_id
        
        # Start
        update_job(db, job_id,
            status="processing",
            progress=5,
            current_step="Validiere EPUB...",
            started_at=datetime.utcnow()
        )
        log_event(
            db, job_id, job.user_id, "job_started",
            status="processing", progress=5, step="Validiere EPUB..."
        )

        # Validiere
        validation = epub_service.validate_epub(job.file_path)
        if not validation["is_valid"]:
            raise ValueError(f"EPUB ungültig: {validation['message']}")
        
        book_title = validation["title"]
        update_job(db, job_id,
            book_title=book_title,
            book_author=validation.get("author"),
            progress=10,
            current_step="Extrahiere Kapitel..."
        )
        log_event(
            db, job_id, job.user_id, "epub_validated",
            status="processing", progress=10, step="Extrahiere Kapitel..."
        )
        
        # Kapitel
        all_chapters = epub_service.extract_chapters(job.file_path)
        
        # Filter wenn auto_detect
        if auto_detect:
            update_job(db, job_id, progress=15, current_step="Analysiere Kapiteltypen...")
            chapters_to_process = []

            book = None
            if book_id:
                book = db.query(Book).filter(Book.book_id == book_id).first()

            # 1) Cache-Hit: bereits analysierte Kapitel am Book verwenden (keine neue KI-Kosten)
            if book and book.chapters_analyzed:
                try:
                    analyzed = json.loads(book.chapters_analyzed)
                    content_hrefs = {ch["href"] for ch in analyzed.get("content_chapters", [])}
                    chapters_to_process = [ch for ch in all_chapters if ch.href in content_hrefs]
                    log_event(
                        db, job_id, job.user_id, "chapter_analysis_cache_hit",
                        status="processing",
                        progress=15,
                        step="Verwende gecachte Kapitelanalyse",
                        details={"source": "book.chapters_analyzed", "content_count": len(chapters_to_process)}
                    )
                except Exception:
                    chapters_to_process = []

            # 2) Cache-Miss: KI-Analyse durchführen und am Book cachen
            if not chapters_to_process:
                if book:
                    result = epub_service.analyze_chapters_with_ai(
                        file_path=job.file_path,
                        llm_provider=llm_provider,
                        db_book=book
                    )
                    db.commit()
                    content_hrefs = {ch["href"] for ch in result.get("content_chapters", [])}
                    chapters_to_process = [ch for ch in all_chapters if ch.href in content_hrefs]
                    add_cost(
                        db, job_id,
                        llm_cost=result.get("total_cost", 0.0),
                        input_tokens=result.get("input_tokens", 0),
                        output_tokens=result.get("output_tokens", 0)
                    )
                    log_cost(
                        db, job_id, job.user_id,
                        operation="chapter_detection_cached_to_book",
                        provider=llm_provider or "openai",
                        cost_usd=result.get("total_cost", 0.0),
                        input_tokens=result.get("input_tokens", 0),
                        output_tokens=result.get("output_tokens", 0)
                    )
                else:
                    llm_dao = get_llm_dao(llm_provider)
                    for ch in all_chapters:
                        try:
                            content = epub_service.extract_chapter_content(job.file_path, ch.href, all_chapters)
                            excerpt = content[:500]
                        except:
                            excerpt = ""

                        detection = llm_dao.detect_chapter_type(ch.title, excerpt)
                        add_cost(
                            db, job_id,
                            llm_cost=detection["cost"],
                            input_tokens=detection["tokens"]["input"],
                            output_tokens=detection["tokens"]["output"]
                        )
                        if detection["type"] == "content":
                            chapters_to_process.append(ch)
        else:
            chapters_to_process = all_chapters
        
        # Audiobook generieren
        _generate_audiobook_from_chapters(
            db, job_id, job.user_id, job.file_path, book_title,
            chapters_to_process, all_chapters, tts_provider, voice
        )
        
    except Exception as e:
        logger.error(f"❌ Audiobook {job_id} fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        update_job(db, job_id,
            status="failed",
            current_step="Fehlgeschlagen",
            completed_at=datetime.utcnow(),
            error_message=str(e)
        )
        if job:
            log_event(
                db, job_id, job.user_id, "job_failed",
                status="failed", step="Fehlgeschlagen",
                details={"error": str(e)}
            )
    finally:
        db.close()


@huey.task(retries=1, retry_delay=120)
def process_audiobook_chapters(job_id: str):
    """
    Task: Audiobook aus spezifischen Kapiteln
    """
    db = SessionLocal()
    epub_service = EPUBService()
    
    try:
        job = get_job(db, job_id)
        if not job:
            logger.error(f"Job {job_id} nicht gefunden")
            return
        
        config = json.loads(job.config) if job.config else {}
        tts_provider = config.get("tts_provider", "openai")
        voice = config.get("voice", "alloy")
        chapter_hrefs = config.get("chapters", [])
        
        if not chapter_hrefs:
            raise ValueError("Keine Kapitel angegeben")
        
        # Start
        update_job(db, job_id,
            status="processing",
            progress=5,
            current_step="Validiere EPUB...",
            started_at=datetime.utcnow()
        )
        log_event(
            db, job_id, job.user_id, "job_started",
            status="processing", progress=5, step="Validiere EPUB..."
        )
        
        # Validiere
        validation = epub_service.validate_epub(job.file_path)
        if not validation["is_valid"]:
            raise ValueError(f"EPUB ungültig: {validation['message']}")
        
        book_title = validation["title"]
        update_job(db, job_id,
            book_title=book_title,
            book_author=validation.get("author"),
            progress=10,
            current_step="Extrahiere Kapitel..."
        )
        log_event(
            db, job_id, job.user_id, "epub_validated",
            status="processing", progress=10, step="Extrahiere Kapitel..."
        )
        
        # Kapitel filtern
        all_chapters = epub_service.extract_chapters(job.file_path)
        chapters_to_process = [ch for ch in all_chapters if ch.href in chapter_hrefs]
        
        if not chapters_to_process:
            raise ValueError("Keine der angegebenen Kapitel gefunden")
        
        # Audiobook generieren
        _generate_audiobook_from_chapters(
            db, job_id, job.user_id, job.file_path, book_title,
            chapters_to_process, all_chapters, tts_provider, voice
        )
        
    except Exception as e:
        logger.error(f"❌ Audiobook {job_id} fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        update_job(db, job_id,
            status="failed",
            current_step="Fehlgeschlagen",
            completed_at=datetime.utcnow(),
            error_message=str(e)
        )
        if job:
            log_event(
                db, job_id, job.user_id, "job_failed",
                status="failed", step="Fehlgeschlagen",
                details={"error": str(e)}
            )
    finally:
        db.close()


def _generate_audiobook_from_chapters(
    db, job_id: str, user_id: str, file_path: str, book_title: str,
    chapters_to_process: List[Chapter], all_chapters: List[Chapter],
    tts_provider: str, voice: str
):
    """Generiere Audio fuer gegebene Kapitel mit fein granularen TTS-Progressdaten."""
    epub_service = EPUBService()
    if not chapters_to_process:
        raise ValueError("Keine Kapitel zum Verarbeiten")

    tts_dao = get_tts_dao(tts_provider)

    prepared_chapters: List[Dict[str, Any]] = []
    total_text_length = 0
    total_tts_chunks = 0
    job_config = json.loads(get_job(db, job_id).config)
    edition_texts = None
    if job_config.get("edition_job_id"):
        edition = get_job(db, job_config["edition_job_id"])
        if not edition or edition.user_id != user_id or edition.status != "completed":
            raise ValueError("Lesefassung nicht verfügbar")
        edition_data = json.loads(edition.result_data)
        if edition_data.get("quality_status") not in ("automated_review_passed", "length_warning"):
            raise ValueError("Lesefassung hat offene Prüfpunkte")
        edition_texts = {}
        for section in edition_data["sections"]:
            edition_texts.setdefault(section["href"], []).append(section["text"])

    for chapter in chapters_to_process:
        try:
            if edition_texts is not None:
                content = "\n\n".join(edition_texts[chapter.href])
            else:
                content = epub_service.extract_chapter_content(file_path, chapter.href, all_chapters)
        except Exception as e:
            logger.warning(f"Kapitel {chapter.title} konnte nicht extrahiert werden: {e}")
            raise ValueError(f"Kapitel {chapter.title} konnte nicht gelesen werden") from e

        if not content.strip():
            logger.warning(f"Kapitel {chapter.title} zu kurz, ueberspringe")
            continue

        full_text = f"{chapter.title}\n\n{content}"
        chapter_chars = len(full_text)

        if hasattr(tts_dao, "split_text_into_segments"):
            try:
                chapter_chunks = len(tts_dao.split_text_into_segments(full_text))
            except Exception:
                chapter_chunks = 1
        else:
            chapter_chunks = 1

        chapter_chunks = max(chapter_chunks, 1)
        total_text_length += chapter_chars
        total_tts_chunks += chapter_chunks

        prepared_chapters.append({
            "chapter": chapter,
            "full_text": full_text,
            "chars": chapter_chars,
            "chunks": chapter_chunks
        })

    if not prepared_chapters:
        raise ValueError("Keine verwertbaren Kapitel nach Extraktion gefunden")

    total_chapters = len(prepared_chapters)
    update_job(
        db, job_id,
        total_chapters=total_chapters,
        progress=20,
        current_step=f"Generiere Audio fuer {total_chapters} Kapitel...",
        total_text_length=total_text_length,
        processed_text_length=0,
        total_tts_chunks=total_tts_chunks,
        processed_tts_chunks=0
    )
    log_event(
        db, job_id, user_id, "tts_generation_started",
        status="processing", progress=20,
        step=f"Generiere Audio fuer {total_chapters} Kapitel...",
        details={
            "total_chapters": total_chapters,
            "tts_provider": tts_provider,
            "voice": voice,
            "total_text_length": total_text_length,
            "total_tts_chunks": total_tts_chunks
        }
    )

    chapter_audios = []
    total_duration = 0.0
    processed_chunks_done = 0
    processed_chars_done = 0

    for idx, item in enumerate(prepared_chapters):
        chapter: Chapter = item["chapter"]
        full_text: str = item["full_text"]
        chapter_chars: int = item["chars"]
        chapter_chunks: int = item["chunks"]

        chapter_progress = 20 + int((idx / max(total_chapters, 1)) * 70)
        update_job(
            db, job_id,
            progress=chapter_progress,
            current_step=f"Audio {idx + 1}/{total_chapters}: {chapter.title[:40]}...",
            processed_chapters=idx,
            current_chapter_name=chapter.title
        )

        output_file = os.path.join(
            settings.audiofiles_dir,
            f"{job_id}_{slugify(book_title)}_{idx:03d}_{slugify(chapter.title[:30])}.mp3"
        )

        last_chunk_seen = 0

        def _progress_callback(current_chunk: int, total_chunk_count: int):
            nonlocal last_chunk_seen
            if current_chunk <= last_chunk_seen:
                return
            last_chunk_seen = current_chunk

            overall_chunks = processed_chunks_done + current_chunk
            overall_chars = processed_chars_done + int(
                chapter_chars * (current_chunk / max(total_chunk_count, 1))
            )
            live_progress = 20 + int((overall_chunks / max(total_tts_chunks, 1)) * 70)

            update_job(
                db, job_id,
                progress=min(live_progress, 95),
                current_step=f"TTS-Chunk {overall_chunks}/{total_tts_chunks}: {chapter.title[:30]}...",
                processed_tts_chunks=overall_chunks,
                total_tts_chunks=total_tts_chunks,
                processed_text_length=overall_chars,
                total_text_length=total_text_length,
                current_chapter_name=chapter.title
            )

        audio_file, duration, cost_details = tts_dao.generate_speech(
            text=full_text,
            voice=voice,
            output_file=output_file,
            progress_callback=_progress_callback
        )

        processed_chunks_done += chapter_chunks
        processed_chars_done += chapter_chars

        file_size = os.path.getsize(audio_file) if os.path.exists(audio_file) else 0
        add_asset(
            db, job_id,
            asset_type="audio_chapter",
            file_path=audio_file,
            file_name=os.path.basename(audio_file),
            file_size=file_size,
            duration=duration,
            chapter_index=idx,
            chapter_title=chapter.title
        )

        add_cost(
            db, job_id,
            tts_cost=cost_details["total_cost_usd"],
            characters=cost_details["characters"]
        )

        log_cost(
            db, job_id, user_id,
            operation="tts",
            provider=cost_details["provider"],
            model=cost_details.get("model"),
            cost_usd=cost_details["total_cost_usd"],
            characters=cost_details["characters"],
            audio_seconds=duration,
            step_name=chapter.title
        )

        chapter_audios.append({
            "chapter_title": chapter.title,
            "audio_file": audio_file,
            "duration_seconds": duration,
            "characters_count": cost_details["characters"],
            "was_translated": False,
            "was_summarized": edition_texts is not None,
            "cost_usd": cost_details["total_cost_usd"]
        })

        log_event(
            db, job_id, user_id, "chapter_audio_generated",
            status="processing",
            progress=chapter_progress,
            step=f"Audio {idx + 1}/{total_chapters}",
            details={
                "chapter_index": idx,
                "chapter_title": chapter.title,
                "duration_seconds": duration,
                "cost_usd": cost_details["total_cost_usd"],
                "processed_tts_chunks": processed_chunks_done,
                "total_tts_chunks": total_tts_chunks
            }
        )

        total_duration += duration

    update_job(db, job_id, progress=95, current_step="Kombiniere Audio-Dateien...")

    combined_file = combine_audio_files(chapter_audios, book_title, job_id)
    combined_size = os.path.getsize(combined_file) if os.path.exists(combined_file) else 0

    add_asset(
        db, job_id,
        asset_type="audio_combined",
        file_path=combined_file,
        file_name=os.path.basename(combined_file),
        file_size=combined_size,
        duration=total_duration
    )

    result_data = {
        "chapters_audio": chapter_audios,
        "combined_audio_file": combined_file,
        "total_duration_seconds": total_duration
    }

    update_job(
        db, job_id,
        status="completed",
        progress=100,
        current_step="Audiobook fertig!",
        completed_at=datetime.utcnow(),
        result_data=json.dumps(result_data, default=str),
        audio_duration_seconds=total_duration,
        processed_tts_chunks=total_tts_chunks,
        processed_text_length=total_text_length
    )
    log_event(
        db, job_id, user_id, "job_completed",
        status="completed",
        progress=100,
        step="Audiobook fertig!",
        details={
            "processed_chapters": len(chapter_audios),
            "total_duration_seconds": total_duration
        }
    )

    logger.info(f"Audiobook {job_id} fertig: {total_duration:.1f}s, {len(chapter_audios)} Kapitel")

