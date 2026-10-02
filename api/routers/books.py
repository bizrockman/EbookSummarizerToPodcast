"""
Books Endpunkte

Verwaltung von hochgeladenen Büchern:
- POST /books/upload - Buch hochladen (multipart/form-data)
- POST /books        - Buch von Pfad/URL registrieren
- GET  /books        - Liste aller Bücher
- GET  /books/{id}   - Buch-Details
- DELETE /books/{id} - Buch löschen
"""
import os
import uuid
import hashlib
import shutil
import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from api.models.database_models import Book, User
from api.models.schemas import (
    BookCreateRequest, BookResponse, BookListResponse, BookDetailResponse
)
from api.services.epub_service import EPUBService
from api.middleware.auth import get_current_user, get_db
from api.config.settings import settings

import logging
logger = logging.getLogger("api.books")


router = APIRouter(prefix="/books", tags=["Books"])
epub_service = EPUBService()


def _calculate_file_hash(file_path: str) -> str:
    """Berechne MD5-Hash einer Datei"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _get_user_upload_dir(user_id: str) -> str:
    """Hole Upload-Verzeichnis für User"""
    user_dir = os.path.join(settings.upload_dir, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


@router.post("/upload", response_model=BookResponse)
def upload_book(
    file: UploadFile = File(..., description="EPUB-Datei"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📤 Buch hochladen (multipart/form-data)
    
    Lädt eine EPUB-Datei hoch und erstellt einen Buch-Eintrag.
    
    **Duplikat-Erkennung**: Wenn die gleiche Datei (per Hash) bereits 
    existiert, wird die ID des existierenden Buchs zurückgegeben.
    
    **Returns**: BookResponse mit book_id für weitere Operationen
    
    **Beispiel (curl)**:
    ```bash
    curl -X POST "http://localhost:8000/books/upload" \\
         -H "X-API-Key: your-key" \\
         -F "file=@mein-buch.epub"
    ```
    """
    # Prüfe Dateiendung
    if not file.filename or not file.filename.lower().endswith('.epub'):
        raise HTTPException(status_code=400, detail="Nur EPUB-Dateien erlaubt")
    
    # Generiere book_id
    book_id = str(uuid.uuid4())
    
    # Speichere temporär um Hash zu berechnen
    user_dir = _get_user_upload_dir(current_user.user_id)
    temp_path = os.path.join(user_dir, f"temp_{book_id}.epub")
    
    try:
        # Speichere Datei
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(temp_path)
        file_hash = _calculate_file_hash(temp_path)
        
        # Prüfe auf Duplikat
        existing_book = db.query(Book).filter(
            Book.user_id == current_user.user_id,
            Book.file_hash == file_hash
        ).first()
        
        if existing_book:
            # Lösche temporäre Datei
            os.remove(temp_path)
            logger.info(f"📚 Duplikat erkannt: {existing_book.book_id}")
            
            return BookResponse(
                book_id=existing_book.book_id,
                title=existing_book.title,
                author=existing_book.author,
                filename=existing_book.original_filename,
                chapter_count=existing_book.chapter_count,
                is_analyzed=existing_book.chapters_analyzed is not None,
                total_cost_usd=existing_book.total_cost_usd,
                uploaded_at=existing_book.uploaded_at,
                is_duplicate=True,
                message="Buch bereits vorhanden"
            )
        
        # Finaler Pfad
        final_path = os.path.join(user_dir, f"{book_id}.epub")
        os.rename(temp_path, final_path)
        
        # Validiere und extrahiere Metadaten
        validation = epub_service.validate_epub(final_path)
        if not validation["is_valid"]:
            os.remove(final_path)
            raise HTTPException(status_code=400, detail=validation["message"])
        
        # Extrahiere Kapitel
        chapters = epub_service.extract_chapters(final_path, use_cache=False)
        chapters_json = json.dumps([
            {"title": ch.title, "href": ch.href, "order": ch.order}
            for ch in chapters
        ])
        
        # Erstelle Book-Eintrag
        book = Book(
            book_id=book_id,
            user_id=current_user.user_id,
            original_filename=file.filename,
            file_path=final_path,
            file_size_bytes=file_size,
            file_hash=file_hash,
            title=validation["title"],
            author=validation.get("author"),
            chapter_count=len(chapters),
            chapters_raw=chapters_json,
            uploaded_at=datetime.utcnow(),
            last_accessed_at=datetime.utcnow()
        )
        
        db.add(book)
        db.commit()
        db.refresh(book)
        
        logger.info(f"📚 Buch hochgeladen: {book.title} ({book_id})")
        
        return BookResponse(
            book_id=book.book_id,
            title=book.title,
            author=book.author,
            filename=book.original_filename,
            chapter_count=book.chapter_count,
            is_analyzed=False,
            total_cost_usd=0.0,
            uploaded_at=book.uploaded_at,
            is_duplicate=False,
            message="Buch erfolgreich hochgeladen"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup bei Fehler
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"Upload fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail=f"Upload fehlgeschlagen: {str(e)}")


@router.post("", response_model=BookResponse)
def register_book(
    request: BookCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📁 Buch von lokalem Pfad registrieren
    
    Registriert eine bereits vorhandene EPUB-Datei als Buch.
    Die Datei wird NICHT kopiert, nur referenziert.
    
    **Duplikat-Erkennung**: Per Hash, gibt existierendes Buch zurück.
    
    **Beispiel**:
    ```python
    response = register_book(file_path="uploads/mein-buch.epub")
    book_id = response.book_id
    ```
    """
    file_path = request.file_path
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Datei nicht gefunden: {file_path}")
    
    if not file_path.lower().endswith('.epub'):
        raise HTTPException(status_code=400, detail="Nur EPUB-Dateien erlaubt")
    
    # Validiere EPUB
    validation = epub_service.validate_epub(file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    # Hash berechnen
    file_hash = _calculate_file_hash(file_path)
    file_size = os.path.getsize(file_path)
    
    # Prüfe auf Duplikat
    existing_book = db.query(Book).filter(
        Book.user_id == current_user.user_id,
        Book.file_hash == file_hash
    ).first()
    
    if existing_book:
        logger.info(f"📚 Duplikat erkannt: {existing_book.book_id}")
        return BookResponse(
            book_id=existing_book.book_id,
            title=existing_book.title,
            author=existing_book.author,
            filename=existing_book.original_filename,
            chapter_count=existing_book.chapter_count,
            is_analyzed=existing_book.chapters_analyzed is not None,
            total_cost_usd=existing_book.total_cost_usd,
            uploaded_at=existing_book.uploaded_at,
            is_duplicate=True,
            message="Buch bereits vorhanden"
        )
    
    # Kapitel extrahieren
    chapters = epub_service.extract_chapters(file_path, use_cache=False)
    chapters_json = json.dumps([
        {"title": ch.title, "href": ch.href, "order": ch.order}
        for ch in chapters
    ])
    
    # Erstelle Book-Eintrag
    book_id = str(uuid.uuid4())
    book = Book(
        book_id=book_id,
        user_id=current_user.user_id,
        original_filename=os.path.basename(file_path),
        file_path=file_path,
        file_size_bytes=file_size,
        file_hash=file_hash,
        title=validation["title"],
        author=validation.get("author"),
        chapter_count=len(chapters),
        chapters_raw=chapters_json,
        uploaded_at=datetime.utcnow(),
        last_accessed_at=datetime.utcnow()
    )
    
    db.add(book)
    db.commit()
    db.refresh(book)
    
    logger.info(f"📚 Buch registriert: {book.title} ({book_id})")
    
    return BookResponse(
        book_id=book.book_id,
        title=book.title,
        author=book.author,
        filename=book.original_filename,
        chapter_count=book.chapter_count,
        is_analyzed=False,
        total_cost_usd=0.0,
        uploaded_at=book.uploaded_at,
        is_duplicate=False,
        message="Buch erfolgreich registriert"
    )


@router.get("", response_model=BookListResponse)
def list_books(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📚 Liste aller Bücher des Users
    
    Admins sehen alle Bücher aller User.
    """
    if current_user.is_admin:
        books = db.query(Book).order_by(Book.uploaded_at.desc()).all()
    else:
        books = db.query(Book).filter(
            Book.user_id == current_user.user_id
        ).order_by(Book.uploaded_at.desc()).all()
    
    return BookListResponse(
        books=[
            BookResponse(
                book_id=book.book_id,
                title=book.title,
                author=book.author,
                filename=book.original_filename,
                chapter_count=book.chapter_count,
                is_analyzed=book.chapters_analyzed is not None,
                total_cost_usd=book.total_cost_usd,
                uploaded_at=book.uploaded_at
            )
            for book in books
        ],
        total_count=len(books)
    )


@router.get("/{book_id}", response_model=BookDetailResponse)
def get_book(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📖 Buch-Details abrufen
    
    Gibt vollständige Informationen über ein Buch zurück,
    inkl. Kapitel, Kosten-Aufschlüsselung und Analyse-Status.
    """
    book = db.query(Book).filter(Book.book_id == book_id).first()
    
    if not book:
        raise HTTPException(status_code=404, detail="Buch nicht gefunden")
    
    # Zugriffscheck
    if book.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    # Update last_accessed_at
    book.last_accessed_at = datetime.utcnow()
    db.commit()
    
    # Parse Kapitel
    chapters_raw = json.loads(book.chapters_raw) if book.chapters_raw else []
    chapters_analyzed = json.loads(book.chapters_analyzed) if book.chapters_analyzed else None
    
    return BookDetailResponse(
        book_id=book.book_id,
        user_id=book.user_id,
        title=book.title,
        author=book.author,
        filename=book.original_filename,
        file_path=book.file_path,
        file_size_bytes=book.file_size_bytes,
        chapter_count=book.chapter_count,
        
        # Kapitel
        chapters_raw=chapters_raw,
        chapters_analyzed=chapters_analyzed,
        is_analyzed=chapters_analyzed is not None,
        analyzed_at=book.chapters_analyzed_at,
        
        # Kosten
        analysis_cost_usd=book.analysis_cost_usd,
        total_llm_cost_usd=book.total_llm_cost_usd,
        total_tts_cost_usd=book.total_tts_cost_usd,
        total_cost_usd=book.total_cost_usd,
        
        # Statistiken
        audiobooks_generated=book.audiobooks_generated,
        total_audio_duration_seconds=book.total_audio_duration_seconds,
        
        # Timestamps
        uploaded_at=book.uploaded_at,
        last_accessed_at=book.last_accessed_at
    )


@router.delete("/{book_id}")
def delete_book(
    book_id: str,
    delete_file: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🗑️ Buch löschen
    
    Löscht den Buch-Eintrag und optional die Datei.
    
    **Parameter**:
    - `delete_file`: Datei auch vom Dateisystem löschen (Standard: True)
    
    **Achtung**: Löscht auch alle zugehörigen Jobs und Assets!
    """
    book = db.query(Book).filter(Book.book_id == book_id).first()
    
    if not book:
        raise HTTPException(status_code=404, detail="Buch nicht gefunden")
    
    # Zugriffscheck
    if book.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    file_path = book.file_path
    title = book.title
    
    # Lösche aus DB (cascade löscht Jobs)
    db.delete(book)
    db.commit()
    
    # Lösche Datei
    if delete_file and file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"🗑️ Datei gelöscht: {file_path}")
        except Exception as e:
            logger.warning(f"Datei konnte nicht gelöscht werden: {e}")
    
    logger.info(f"🗑️ Buch gelöscht: {title} ({book_id})")
    
    return {
        "message": f"Buch '{title}' wurde gelöscht",
        "book_id": book_id,
        "file_deleted": delete_file
    }

