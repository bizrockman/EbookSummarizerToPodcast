"""
FastAPI Hauptanwendung für eBook to Audiobook Konvertierung

Queue: Huey (SQLite lokal, Redis für Produktion)
Consumer läuft als separater Prozess - siehe start_dev.py
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.config.settings import settings
from api.config.huey_config import QUEUE_BACKEND
from api.database.init_db import initialize_database
from api.database.connection import SessionLocal
from api.middleware.logging_middleware import LoggingMiddleware

# Router imports
from api.routers.books import router as books_router
from api.routers.epub import router as epub_router
from api.routers.audiobook import router as audiobook_router
from api.routers.jobs import router as jobs_router
from api.routers.admin import router as admin_router
from api.routers.summaries import router as summaries_router
from api.routers.productions import router as productions_router

# Importiere Tasks damit sie registriert werden
from api.tasks import audiobook_tasks  # noqa

# Logger
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan Events"""
    # Initialisiere Datenbank
    initialize_database()

    # Re-queue unterbrochene Jobs (Server-Neustart / Worker-Abbruch)
    from api.services.queue_service import get_queue_service
    queue_service = get_queue_service()
    db = SessionLocal()
    try:
        recovered = queue_service.recover_interrupted_jobs(db) if settings.recover_jobs_on_start else 0
        if recovered:
            logger.warning(f"{recovered} Jobs wurden beim Start wieder eingeplant.")
    finally:
        db.close()
    
    logger.info("API gestartet")
    
    yield
    
    logger.info("API beendet")


# FastAPI App
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="""
## eBook to Audiobook API

Konvertiere eBooks in Audiobooks mit KI-Unterstützung.

### Workflow

1. **Buch hochladen** → `POST /books/upload` oder `POST /books`
2. **Kapitel analysieren** → `POST /epub/analyze-chapters` (mit book_id)
3. **Audiobook generieren** → `POST /audiobook/basic` oder `/chapters`
4. **Status prüfen** → `GET /jobs/{job_id}`
5. **Ergebnis holen** → `GET /jobs/{job_id}/result`

### Flexibilität

Alle Endpoints akzeptieren **entweder**:
- `book_id`: Referenz auf ein hochgeladenes Buch
- `file_path`: Direkter Pfad (für RapidAPI/stateless Nutzung)

### RapidAPI Support

Bei Nutzung über RapidAPI wird der User automatisch anhand des 
`X-RapidAPI-User` Headers identifiziert.
    """,
    lifespan=lifespan
)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router
app.include_router(books_router)
app.include_router(epub_router)
app.include_router(audiobook_router)
app.include_router(jobs_router)
app.include_router(admin_router)
app.include_router(summaries_router)
app.include_router(productions_router)


@app.get("/", tags=["System"])
def root():
    """Root Endpunkt"""
    from api.services.queue_service import get_queue_service
    queue_service = get_queue_service()
    
    return {
        "message": "eBook to Audiobook API",
        "version": settings.api_version,
        "docs": "/docs",
        "queue": {
            "backend": QUEUE_BACKEND,
            "pending": queue_service.get_queue_length()
        }
    }


@app.get("/health", tags=["System"])
def health_check():
    """Health Check"""
    from api.services.queue_service import get_queue_service
    from api.database.connection import SessionLocal
    
    queue_service = get_queue_service()
    db = SessionLocal()
    try:
        processing = queue_service.get_processing_count(db)
    finally:
        db.close()
    
    return {
        "status": "healthy",
        "queue_backend": QUEUE_BACKEND,
        "queue_pending": queue_service.get_queue_length(),
        "jobs_processing": processing
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
