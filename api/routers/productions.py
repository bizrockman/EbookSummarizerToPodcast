"""One persisted job for reduction, translation and optional speech."""
import json
import uuid
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from api.middleware.auth import get_current_user, get_db
from api.models.database_models import Book, Job, User
from api.services.queue_service import get_queue_service
from api.services.production.providers import get_providers, get_strategies, ProviderValidationError
from api.services.production.pipeline import VERSION, FFmpegAssembler
from api.services.production.library import load_chapters
from api.services.production.usage import usage_report
from api.config.settings import settings

router = APIRouter(prefix="/productions", tags=["Book studio"])


class ProductionRequest(BaseModel):
    book_id: str
    chapters: list[str] = Field(..., min_length=1, max_length=1000)
    strategy: str = Field("reading", max_length=60)
    ratio: float = Field(.4, ge=.1, le=.9)
    core_words: int = Field(1200, ge=150, le=5000)
    language: Literal["original", "de", "en", "fr", "es", "it"] = "original"
    audio: bool = False
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy"
    text_provider: str = Field("openai", max_length=60)
    audio_provider: str = Field("openai", max_length=60)
    text_model: str | None = Field(None, min_length=1, max_length=100)


class RetryRequest(BaseModel):
    text_model: str | None = Field(None, min_length=1, max_length=100)


def validate_text_model(config, providers):
    if config["strategy"] == "original" and config["language"] == "original":
        return
    try:
        providers.text(config["text_provider"], config["text_model"]).validate_model()
    except ProviderValidationError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc


def owned(db, user, job_id):
    job = db.query(Job).filter(Job.job_id == job_id, Job.job_type == "book_processing",
                              Job.user_id == user.user_id).first()
    if not job:
        raise HTTPException(404, "Auftrag nicht gefunden")
    return job


@router.get("/options")
def options(user: User = Depends(get_current_user)):
    providers = get_providers()
    return {"strategies": get_strategies().describe(), "text_providers": list(providers.text_factories),
        "audio_providers": list(providers.audio_factories), "text_model": settings.openai_default_model,
        "suggested_text_models": list(dict.fromkeys([settings.openai_default_model, "gpt-5", "gpt-6.1-sol"])),
        "audio_model": settings.openai_tts_model, "audio_available": FFmpegAssembler.available(),
        "worker_threads": settings.worker_threads,
        "voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]}


@router.get("/books/{book_id}/chapters")
def chapters(book_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.book_id == book_id, Book.user_id == user.user_id).first()
    if not book:
        raise HTTPException(404, "Buch nicht gefunden")
    try:
        values = load_chapters(book.file_path)
    except Exception as exc:
        raise HTTPException(422, "Kapitel konnten nicht gelesen werden: " + str(exc))
    return {"book_id": book_id, "chapters": [{k: v for k, v in c.items() if k != "text"} for c in values],
            "total_words": sum(c["word_count"] for c in values), "analysis": "deterministic", "input_tokens": 0}


@router.post("")
def create(request: ProductionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.book_id == request.book_id, Book.user_id == user.user_id).first()
    if not book:
        raise HTTPException(404, "Buch nicht gefunden")
    strategies, providers = get_strategies(), get_providers()
    if request.strategy != "original" and request.strategy not in strategies.strategies:
        raise HTTPException(422, "Unbekannte Strategie")
    if request.text_provider not in providers.text_factories or request.audio_provider not in providers.audio_factories:
        raise HTTPException(422, "Anbieter ist noch nicht implementiert")
    if request.audio and not FFmpegAssembler.available():
        raise HTTPException(422, "Für Audio werden ffmpeg und ffprobe benötigt")
    from api.services.epub_service import EPUBService
    valid = {c.href for c in EPUBService().extract_chapters(book.file_path)}
    if not set(request.chapters).issubset(valid):
        raise HTTPException(422, "Unbekannte Kapitel ausgewählt")
    config = request.model_dump()
    config.update(chapters=sorted(set(request.chapters)), text_model=request.text_model or settings.openai_default_model,
                  audio_model=settings.openai_tts_model, file_hash=book.file_hash, version=VERSION)
    if config["strategy"] != "reading":
        config["ratio"] = .4
    if config["strategy"] != "core":
        config["core_words"] = 1200
    candidates = db.query(Job).filter(Job.book_id == book.book_id, Job.user_id == user.user_id,
        Job.job_type == "book_processing", Job.status.in_(["queued", "processing", "completed"])).all()
    for candidate in candidates:
        prior = json.loads(candidate.config)
        if {k: v for k, v in prior.items() if k not in ("workspace_id", "retry_of")} == config:
            return {"job_id": candidate.job_id, "status": candidate.status, "reused": True}
    validate_text_model(config, providers)
    config["workspace_id"] = str(uuid.uuid4())
    job_id = get_queue_service().create_job(db, user.user_id, "book_processing", book.file_path,
        config, book.title, book.author, book.book_id)
    return {"job_id": job_id, "status": "queued", "reused": False}


@router.get("/{job_id}")
def read(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = owned(db, user, job_id)
    return {"job_id": job_id, "book_id": job.book_id, "book_title": job.book_title, "status": job.status,
            "progress": job.progress, "current_step": job.current_step, "error_message": job.error_message,
            "config": json.loads(job.config), "result": json.loads(job.result_data) if job.result_data else None,
            "usage": usage_report(db, job_id)}


@router.post("/{job_id}/retry")
def retry(job_id: str, request: RetryRequest | None = None,
          user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = owned(db, user, job_id)
    if job.status not in ("failed", "cancelled"):
        raise HTTPException(409, "Dieser Auftrag kann noch nicht neu gestartet werden")
    active = db.query(Job).filter(Job.user_id == user.user_id, Job.job_type == "book_processing",
                                  Job.status.in_(["queued", "processing"])).all()
    config = json.loads(job.config)
    for candidate in active:
        if json.loads(candidate.config).get("workspace_id") == config["workspace_id"]:
            return {"job_id": candidate.job_id, "reused": True}
    if request and request.text_model:
        config["text_model"] = request.text_model.strip()
    validate_text_model(config, get_providers())
    config["retry_of"] = job_id
    new_id = get_queue_service().create_job(db, user.user_id, "book_processing", job.file_path,
        config, job.book_title, job.book_author, job.book_id)
    return {"job_id": new_id, "reused": False}
