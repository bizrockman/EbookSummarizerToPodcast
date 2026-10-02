"""
Audiobook Generierung Endpunkte

Endpunkte für alle Audiobook-Varianten:
- Basic: Komplettes Buch als Audiobook
- Basic Extended: Spezifische Kapitel
- Addon 1: Mit Übersetzung (geplant)
- Addon 2: Mit Zusammenfassung (geplant)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.models.schemas import (
    AudiobookBasicRequest, AudiobookChaptersRequest,
    AudiobookTranslatedRequest, AudiobookSummaryRequest,
    JobCreatedResponse, JobStatus, JobType,
    # Legacy Support
    AudiobookGenerationRequest, AudiobookJobResponse,
    AudiobookJobStatus, AudiobookJobStatusResponse, AudiobookJobResultResponse
)
from api.models.database_models import User, Book
from api.services.queue_service import get_queue_service
from api.services.epub_service import EPUBService
from api.middleware.auth import get_current_user, get_db
from typing import Optional, Tuple

router = APIRouter(prefix="/audiobook", tags=["Audiobook"])
epub_service = EPUBService()


def _resolve_book_or_path(
    book_id: Optional[str],
    file_path: Optional[str],
    user: User,
    db: Session
) -> Tuple[Optional[Book], str]:
    """Löst book_id oder file_path auf."""
    if not book_id and not file_path:
        raise HTTPException(
            status_code=400, 
            detail="Entweder book_id oder file_path erforderlich"
        )
    
    if book_id:
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Buch nicht gefunden")
        
        if book.user_id != user.user_id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Zugriff verweigert")
        
        return book, book.file_path
    
    return None, file_path


# =============================================================================
# NEW API - Saubere Endpunkte
# =============================================================================

@router.post("/basic", response_model=JobCreatedResponse)
def create_audiobook_basic(
    request: AudiobookBasicRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎧 Basic: Erstelle Audiobook aus komplettem EPUB
    
    Akzeptiert **entweder**:
    - `book_id`: Referenz auf ein hochgeladenes Buch (empfohlen!)
    - `file_path`: Direkter Pfad zur EPUB-Datei
    
    Bei `book_id` werden Kosten am Buch getrackt und analysierte 
    Kapitel wiederverwendet!
    
    **Parameter**:
    - `tts_provider`: openai (Standard), elevenlabs, local
    - `voice`: Stimme (alloy, echo, fable, onyx, nova, shimmer)
    - `auto_detect_content`: KI-basierte Filterung (Standard: true)
    
    **Kosten**: Abhängig von Buchlänge, typisch $1-10
    """
    book, file_path = _resolve_book_or_path(
        request.book_id, request.file_path, current_user, db
    )
    
    # Validiere EPUB
    validation = epub_service.validate_epub(file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    queue_service = get_queue_service()
    
    # Erstelle Job
    config = {
        "tts_provider": request.tts_provider.value,
        "voice": request.voice,
        "auto_detect_content": request.auto_detect_content,
        "llm_provider": request.llm_provider.value if request.llm_provider else None,
        "book_id": book.book_id if book else None
    }
    
    job_id = queue_service.create_job(
        db=db,
        user_id=current_user.user_id,
        job_type=JobType.AUDIOBOOK_BASIC.value,
        file_path=file_path,
        config=config,
        book_title=book.title if book else validation["title"],
        book_author=book.author if book else validation.get("author"),
        book_id=book.book_id if book else None
    )
    
    # Schätze Zeit
    try:
        chapters = epub_service.extract_chapters(file_path)
        estimated_time = len(chapters) * 30
    except:
        estimated_time = 300
    
    return JobCreatedResponse(
        job_id=job_id,
        job_type=JobType.AUDIOBOOK_BASIC,
        status=JobStatus.QUEUED,
        message="Audiobook-Job wurde erstellt. Verwenden Sie GET /jobs/{job_id} für Status.",
        estimated_time_seconds=estimated_time,
        queue_position=queue_service.get_queue_length()
    )


@router.post("/chapters", response_model=JobCreatedResponse)
def create_audiobook_chapters(
    request: AudiobookChaptersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🎧 Basic Extended: Erstelle Audiobook aus spezifischen Kapiteln
    
    Akzeptiert **entweder**:
    - `book_id`: Referenz auf ein hochgeladenes Buch (empfohlen!)
    - `file_path`: Direkter Pfad zur EPUB-Datei
    
    **Parameter**:
    - `chapters`: Liste der Kapitel-hrefs (z.B. ["chapter1.xhtml", "chapter2.xhtml"])
    - `tts_provider`: openai, elevenlabs, local
    - `voice`: Stimme für TTS
    
    **Tipp**: Hole Kapitel-HREFs mit `GET /books/{book_id}` oder 
    `POST /epub/analyze-chapters`.
    """
    if not request.chapters or len(request.chapters) == 0:
        raise HTTPException(status_code=400, detail="Mindestens ein Kapitel erforderlich")
    
    book, file_path = _resolve_book_or_path(
        request.book_id, request.file_path, current_user, db
    )
    
    validation = epub_service.validate_epub(file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    queue_service = get_queue_service()
    
    config = {
        "chapters": request.chapters,
        "tts_provider": request.tts_provider.value,
        "voice": request.voice,
        "book_id": book.book_id if book else None
    }
    
    job_id = queue_service.create_job(
        db=db,
        user_id=current_user.user_id,
        job_type=JobType.AUDIOBOOK_CHAPTERS.value,
        file_path=file_path,
        config=config,
        book_title=book.title if book else validation["title"],
        book_author=book.author if book else validation.get("author"),
        book_id=book.book_id if book else None
    )
    
    estimated_time = len(request.chapters) * 30
    
    return JobCreatedResponse(
        job_id=job_id,
        job_type=JobType.AUDIOBOOK_CHAPTERS,
        status=JobStatus.QUEUED,
        message=f"Audiobook-Job mit {len(request.chapters)} Kapiteln erstellt.",
        estimated_time_seconds=estimated_time,
        queue_position=queue_service.get_queue_length()
    )


@router.post("/translated", response_model=JobCreatedResponse)
def create_audiobook_translated(
    request: AudiobookTranslatedRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🌍 Addon 1: Erstelle übersetztes Audiobook
    
    Übersetzt das EPUB in die Zielsprache und generiert dann das Audiobook.
    Die Übersetzung erfolgt kapitelweise um Kontextfehler zu vermeiden.
    
    **Parameter**:
    - `file_path`: Pfad zur EPUB-Datei
    - `target_language`: Zielsprache (de, en, fr, es, it, pt)
    - `chapters`: Optional - spezifische Kapitel
    - `tts_provider`: openai, elevenlabs, local
    - `voice`: Stimme für TTS
    
    **Hinweis**: Noch nicht implementiert!
    """
    raise HTTPException(
        status_code=501, 
        detail="Addon 1 (Übersetzung) ist noch nicht implementiert"
    )


@router.post("/summary", response_model=JobCreatedResponse)
def create_audiobook_summary(
    request: AudiobookSummaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📝 Addon 2: Erstelle Zusammenfassungs-Audiobook
    
    Fasst das Buch zusammen und generiert ein kompaktes Audiobook.
    Verwendet Clustering um Redundanzen zu vermeiden.
    
    **Parameter**:
    - `file_path`: Pfad zur EPUB-Datei
    - `summary_length`: Wörter pro Zusammenfassung (Standard: 250)
    - `chapters`: Optional - spezifische Kapitel
    
    **Hinweis**: Noch nicht implementiert!
    """
    raise HTTPException(
        status_code=501, 
        detail="Addon 2 (Zusammenfassung) ist noch nicht implementiert"
    )


# =============================================================================
# LEGACY API - Abwärtskompatibilität
# =============================================================================

@router.post("/generate", response_model=AudiobookJobResponse)
def generate_audiobook(
    request: AudiobookGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🚀 [LEGACY] Starte Audiobook-Generierung
    
    **Hinweis**: Dieser Endpunkt ist veraltet. 
    Verwenden Sie stattdessen:
    - POST /audiobook/basic für komplettes Buch
    - POST /audiobook/chapters für spezifische Kapitel
    
    Dieser Endpunkt bleibt für Abwärtskompatibilität erhalten.
    """
    validation = epub_service.validate_epub(request.file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    queue_service = get_queue_service()
    
    # Bestimme Job-Typ
    if request.chapters:
        job_type = JobType.AUDIOBOOK_CHAPTERS.value
    elif request.target_language:
        job_type = JobType.AUDIOBOOK_TRANSLATED.value
    else:
        job_type = JobType.AUDIOBOOK_BASIC.value
    
    config = {
        "chapters": request.chapters,
        "target_language": request.target_language,
        "auto_detect_content": request.auto_detect_content,
        "tts_provider": request.tts_provider.value,
        "voice": request.voice,
        "llm_provider": request.llm_provider.value if request.llm_provider else None
    }
    
    job_id = queue_service.create_job(
        db=db,
        user_id=current_user.user_id,
        job_type=job_type,
        file_path=request.file_path,
        config=config,
        book_title=validation["title"]
    )
    
    try:
        chapters = epub_service.extract_chapters(request.file_path)
        estimated_time = len(chapters) * 30
    except:
        estimated_time = 300
    
    return AudiobookJobResponse(
        job_id=job_id,
        status=AudiobookJobStatus.PENDING,
        message="Audiobook-Job wurde gestartet. Verwenden Sie /audiobook/status/{job_id} um den Fortschritt zu prüfen.",
        estimated_time_seconds=estimated_time
    )


@router.get("/status/{job_id}", response_model=AudiobookJobStatusResponse)
def get_audiobook_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 [LEGACY] Hole Status eines Audiobook-Jobs
    
    **Hinweis**: Verwenden Sie stattdessen GET /jobs/{job_id}
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    # Map zu Legacy-Status
    status_map = {
        "queued": AudiobookJobStatus.PENDING,
        "pending": AudiobookJobStatus.PENDING,
        "processing": AudiobookJobStatus.PROCESSING,
        "completed": AudiobookJobStatus.COMPLETED,
        "failed": AudiobookJobStatus.FAILED,
        "cancelled": AudiobookJobStatus.FAILED
    }
    
    return AudiobookJobStatusResponse(
        job_id=job.job_id,
        status=status_map.get(job.status, AudiobookJobStatus.PENDING),
        progress=job.progress,
        current_step=job.current_step,
        total_chapters=job.total_chapters,
        processed_chapters=job.processed_chapters,
        total_text_length=job.total_text_length,
        processed_text_length=job.processed_text_length,
        current_chapter_name=job.current_chapter_name,
        total_tts_chunks=job.total_tts_chunks,
        processed_tts_chunks=job.processed_tts_chunks,
        current_tts_chunk=0,  # Nicht mehr separat getrackt
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        translation_cost_usd=0.0,  # Wird jetzt anders getrackt
        chapter_detection_cost_usd=job.llm_cost_usd,
        tts_cost_usd=job.tts_cost_usd,
        total_cost_usd=job.total_cost_usd,
        error_message=job.error_message
    )


@router.get("/result/{job_id}", response_model=AudiobookJobResultResponse)
def get_audiobook_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📥 [LEGACY] Hole Ergebnis eines Audiobook-Jobs
    
    **Hinweis**: Verwenden Sie stattdessen GET /jobs/{job_id}/result
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    result = queue_service.get_job_result(db, job_id)
    
    status_map = {
        "queued": AudiobookJobStatus.PENDING,
        "pending": AudiobookJobStatus.PENDING,
        "processing": AudiobookJobStatus.PROCESSING,
        "completed": AudiobookJobStatus.COMPLETED,
        "failed": AudiobookJobStatus.FAILED,
        "cancelled": AudiobookJobStatus.FAILED
    }
    
    # Konvertiere zu Legacy-Format
    legacy_result = None
    if result and result.status == JobStatus.COMPLETED:
        from api.models.schemas import AudiobookGenerationResponse
        legacy_result = AudiobookGenerationResponse(
            job_id=job_id,
            status="completed",
            chapters_audio=result.chapters_audio,
            combined_audio_url=result.combined_audio_file,
            total_duration_seconds=result.total_duration_seconds,
            total_cost_usd=result.costs.total_cost_usd,
            usage_details={
                "tts_cost_usd": result.costs.tts_cost_usd,
                "llm_cost_usd": result.costs.llm_cost_usd,
                "total_characters": result.costs.total_characters
            }
        )
    
    return AudiobookJobResultResponse(
        job_id=job_id,
        status=status_map.get(job.status, AudiobookJobStatus.PENDING),
        result=legacy_result,
        error_message=job.error_message
    )
