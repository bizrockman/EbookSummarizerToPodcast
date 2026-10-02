"""
EPUB Endpunkte

- /epub/validate - Validiere EPUB
- /epub/chapters - Rohe Kapitel (book_id oder file_path)
- /epub/analyze-chapters - KI-Analyse (book_id oder file_path)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import json

from api.models.schemas import (
    EPUBValidationRequest,
    EPUBValidationResponse,
    ChaptersListResponse,
    ChapterAnalysisResponse,
    JobCreatedResponse,
    JobType,
    JobStatus,
    LLMProvider,
    Chapter
)
from api.models.database_models import User, Book
from api.services.epub_service import EPUBService
from api.services.queue_service import get_queue_service
from api.middleware.auth import get_current_user, get_db
from pydantic import BaseModel, Field


router = APIRouter(prefix="/epub", tags=["EPUB"])
epub_service = EPUBService()


# =============================================================================
# REQUEST SCHEMAS (mit book_id ODER file_path)
# =============================================================================

class ChaptersRequest(BaseModel):
    """Request für Kapitel - book_id ODER file_path"""
    book_id: Optional[str] = Field(None, description="ID eines hochgeladenen Buchs")
    file_path: Optional[str] = Field(None, description="Pfad zur EPUB-Datei (stateless)")


class ChapterAnalysisRequest(BaseModel):
    """Request für Kapitelanalyse - book_id ODER file_path"""
    book_id: Optional[str] = Field(None, description="ID eines hochgeladenen Buchs")
    file_path: Optional[str] = Field(None, description="Pfad zur EPUB-Datei (stateless)")
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider")


# =============================================================================
# HELPER
# =============================================================================

def _resolve_book_or_path(
    book_id: Optional[str],
    file_path: Optional[str],
    user: User,
    db: Session,
    require_access: bool = True
) -> tuple[Optional[Book], str]:
    """
    Löst book_id oder file_path auf.
    
    Returns:
        Tuple von (Book oder None, file_path)
    """
    if not book_id and not file_path:
        raise HTTPException(
            status_code=400, 
            detail="Entweder book_id oder file_path erforderlich"
        )
    
    if book_id:
        book = db.query(Book).filter(Book.book_id == book_id).first()
        if not book:
            raise HTTPException(status_code=404, detail="Buch nicht gefunden")
        
        if require_access and book.user_id != user.user_id and not user.is_admin:
            raise HTTPException(status_code=403, detail="Zugriff verweigert")
        
        return book, book.file_path
    
    # file_path Modus (stateless)
    return None, file_path


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/validate", response_model=EPUBValidationResponse)
def validate_epub(
    request: EPUBValidationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    ✓ Validiere eine EPUB-Datei
    
    Prüft ob die EPUB-Datei valide ist und extrahiert Metadaten.
    """
    try:
        result = epub_service.validate_epub(request.file_path)
        return EPUBValidationResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chapters", response_model=ChaptersListResponse)
def get_chapters(
    request: ChaptersRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📚 Hole rohe Kapitelliste
    
    Akzeptiert **entweder**:
    - `book_id`: ID eines hochgeladenen Buchs
    - `file_path`: Direkter Pfad zur EPUB-Datei
    
    Bei `book_id` werden die Kapitel aus der DB geladen (schneller).
    Bei `file_path` werden die Kapitel direkt aus der Datei extrahiert.
    """
    book, file_path = _resolve_book_or_path(
        request.book_id, request.file_path, current_user, db
    )
    
    # Bei Book aus DB laden
    if book and book.chapters_raw:
        chapters_data = json.loads(book.chapters_raw)
        chapters = [
            Chapter(
                title=ch["title"],
                href=ch["href"],
                order=ch.get("order", idx)
            )
            for idx, ch in enumerate(chapters_data)
        ]
    else:
        # Aus Datei extrahieren
        chapters = epub_service.extract_chapters(file_path)
    
    return ChaptersListResponse(
        chapters=chapters,
        total_chapters=len(chapters)
    )


@router.post("/analyze-chapters", response_model=ChapterAnalysisResponse)
def analyze_chapters(
    request: ChapterAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔍 KI-basierte Kapitel-Analyse
    
    Akzeptiert **entweder**:
    - `book_id`: Ergebnis wird am Buch gespeichert (empfohlen!)
    - `file_path`: Stateless, keine Speicherung
    
    **Mit book_id**:
    - Erster Aufruf: KI-Analyse (kostet Tokens)
    - Weitere Aufrufe: Aus DB (kostenlos!)
    - Kosten werden am Buch getrackt
    
    **Mit file_path**:
    - Jeder Aufruf kostet Tokens
    - Keine Speicherung
    """
    book, file_path = _resolve_book_or_path(
        request.book_id, request.file_path, current_user, db
    )
    
    # Validiere EPUB
    validation = epub_service.validate_epub(file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    try:
        llm_provider = request.llm_provider.value if request.llm_provider else None
        
        result = epub_service.analyze_chapters_with_ai(
            file_path=file_path,
            llm_provider=llm_provider,
            db_book=book  # None bei file_path Modus
        )
        
        # Bei book: DB committen
        if book:
            db.commit()
        
        return ChapterAnalysisResponse(
            book_title=validation["title"],
            book_author=validation.get("author"),
            all_chapters=result["all_chapters"],
            content_chapters=result["content_chapters"],
            supplement_chapters=result["supplement_chapters"],
            total_chapters=result["total_chapters"],
            content_count=result["content_count"],
            supplement_count=result["supplement_count"],
            analysis_cost_usd=result["total_cost"],
            from_cache=result["from_cache"],
            input_tokens=result.get("input_tokens", 0),
            output_tokens=result.get("output_tokens", 0),
            total_tokens=result.get("total_tokens", 0)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analyse fehlgeschlagen: {str(e)}")


@router.post("/analyze-chapters/async", response_model=JobCreatedResponse)
def analyze_chapters_async(
    request: ChapterAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🔍 KI-basierte Kapitel-Analyse (asynchron als Job)
    
    Startet die Analyse als Hintergrund-Job.
    Für die meisten Bücher ist der synchrone Endpunkt 
    `/epub/analyze-chapters` schneller!
    """
    book, file_path = _resolve_book_or_path(
        request.book_id, request.file_path, current_user, db
    )
    
    # Validiere EPUB
    validation = epub_service.validate_epub(file_path)
    if not validation["is_valid"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    
    queue_service = get_queue_service()
    
    config = {
        "llm_provider": request.llm_provider.value if request.llm_provider else None,
        "book_id": book.book_id if book else None
    }
    
    job_id = queue_service.create_job(
        db=db,
        user_id=current_user.user_id,
        job_type=JobType.CHAPTER_ANALYSIS.value,
        file_path=file_path,
        config=config,
        book_title=validation["title"],
        book_author=validation.get("author"),
        book_id=book.book_id if book else None
    )
    
    # Schätze Zeit
    try:
        chapters = epub_service.extract_chapters(file_path)
        estimated_time = len(chapters) * 3
    except:
        estimated_time = 60
    
    return JobCreatedResponse(
        job_id=job_id,
        job_type=JobType.CHAPTER_ANALYSIS,
        status=JobStatus.QUEUED,
        message="Analyse-Job erstellt. Verwenden Sie GET /jobs/{job_id} für Status.",
        estimated_time_seconds=estimated_time,
        queue_position=queue_service.get_queue_length()
    )
