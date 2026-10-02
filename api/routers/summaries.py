"""Persistent reading editions, separate from the optional audio generation."""
import json
from typing import Literal, List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from api.middleware.auth import get_current_user, get_db
from api.models.database_models import Book, Job, User
from api.services.queue_service import get_queue_service
from api.services.epub_service import EPUBService

router = APIRouter(prefix="/summaries", tags=["Reading editions"])


class EditionRequest(BaseModel):
    book_id: str
    chapters: List[str] = Field(..., min_length=1, max_length=1000)
    level: Literal["light", "standard", "compact", "essence"] = "standard"
    language: Literal["original", "de", "en", "fr"] = "original"
    revision: int = Field(0, ge=0)


class AudioRequest(BaseModel):
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy"


def owned_edition(db, user, job_id):
    job = db.query(Job).filter(Job.job_id == job_id, Job.job_type == "book_summary").first()
    if not job or (job.user_id != user.user_id and not user.is_admin):
        raise HTTPException(404, "Lesefassung nicht gefunden")
    return job


@router.post("")
def create_edition(request: EditionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    book = db.query(Book).filter(Book.book_id == request.book_id, Book.user_id == user.user_id).first()
    if not book:
        raise HTTPException(404, "Buch nicht gefunden")
    valid = {ch.href for ch in EPUBService().extract_chapters(book.file_path)}
    if not set(request.chapters).issubset(valid):
        raise HTTPException(422, "Unbekannte Kapitel ausgewählt")
    config = request.model_dump()
    config["chapters"] = sorted(set(config["chapters"]))
    # Reuse an existing edition/job for exactly this selection and source version.
    from api.config.settings import settings
    from api.services.abridgement import VERSION
    config.update(version=VERSION, file_hash=book.file_hash, model=settings.openai_default_model)
    candidates = db.query(Job).filter(Job.book_id == book.book_id, Job.user_id == user.user_id,
                                      Job.job_type == "book_summary",
                                      Job.status.in_(["queued", "processing", "completed"])).all()
    for job in candidates:
        if json.loads(job.config) == config:
            return {"job_id": job.job_id, "status": job.status, "reused": True}
    job_id = get_queue_service().create_job(db, user.user_id, "book_summary", book.file_path,
                                           config, book.title, book.author, book.book_id)
    return {"job_id": job_id, "status": "queued", "reused": False}


@router.get("/{job_id}")
def read_edition(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = owned_edition(db, user, job_id)
    if job.status != "completed":
        raise HTTPException(409, "Lesefassung ist noch nicht fertig")
    return {"job_id": job_id, "book_id": job.book_id, "book_title": job.book_title, **json.loads(job.result_data)}


@router.post("/{job_id}/retry")
def retry_edition(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = owned_edition(db, user, job_id)
    needs_review = job.status == "completed" and json.loads(job.result_data).get("quality_status") == "length_warning"
    if job.status not in ("failed", "cancelled") and not needs_review:
        raise HTTPException(409, "Nur fehlgeschlagene oder abgebrochene Fassungen können neu gestartet werden")
    config = json.loads(job.config)
    config["revision"] = config.get("revision", 0) + 1
    return create_edition(EditionRequest(**config), user, db)


@router.post("/{job_id}/audio")
def read_aloud(job_id: str, request: AudioRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    edition = owned_edition(db, user, job_id)
    if edition.status != "completed":
        raise HTTPException(409, "Zuerst die Lesefassung fertigstellen")
    data = json.loads(edition.result_data)
    if data.get("quality_status") not in ("automated_review_passed", "length_warning"):
        raise HTTPException(409, "Die Lesefassung enthält noch offene Prüfpunkte und wird nicht automatisch vertont")
    config = {"edition_job_id": job_id, "chapters": sorted({s["href"] for s in data["sections"]}),
              "voice": request.voice, "tts_provider": "openai"}
    audio_id = get_queue_service().create_job(db, user.user_id, "audiobook_chapters", edition.file_path,
                                             config, edition.book_title, edition.book_author, edition.book_id)
    return {"job_id": audio_id}
