"""
Job Management Endpunkte

Zentrale API für alle Job-Operationen:
- Job-Liste abrufen
- Job-Status abfragen
- Job-Ergebnisse holen
- Jobs abbrechen
- Assets abrufen
"""
import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import Request
from fastapi.responses import StreamingResponse, FileResponse
from pathlib import Path
from api.models.database_models import JobAsset
from api.config.settings import settings
from sqlalchemy.orm import Session
from typing import Optional

from api.models.schemas import (
    JobStatusResponse, JobResultResponse, JobListResponse,
    JobListItem, AssetInfo, JobStatus, JobEventResponse, JobEventsListResponse
)
from api.models.database_models import User
from api.services.queue_service import get_queue_service
from api.middleware.auth import get_current_user, get_db
from api.daos.job_tracking_dao import get_job_tracking_dao
from api.daos.database_dao import SQLiteDatabaseDao

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}/assets/{asset_id}/download")
def download_asset(job_id: str, asset_id: str, current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    job = get_queue_service().get_job(db, job_id)
    if not job or (job.user_id != current_user.user_id and not current_user.is_admin):
        raise HTTPException(404, "Datei nicht gefunden")
    asset = db.query(JobAsset).filter(JobAsset.job_id == job_id, JobAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(404, "Datei nicht gefunden")
    path = Path(asset.file_path).resolve()
    if not path.is_relative_to(Path(settings.audiofiles_dir).resolve()) or not path.is_file():
        raise HTTPException(404, "Audiodatei nicht verfügbar")
    return FileResponse(path, media_type="audio/mpeg", filename=asset.file_name)


def _resolve_user_from_request(request: Request, db: Session, api_key_query: Optional[str]) -> User:
    """
    Auth fuer SSE: akzeptiert X-API-Key Header oder api_key Query (fuer EventSource).
    """
    api_key = api_key_query or request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key fehlt")

    dao = SQLiteDatabaseDao(db)
    user = dao.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(status_code=401, detail="Ungültiger API Key")
    return user


@router.get("", response_model=JobListResponse)
def list_jobs(
    status: Optional[str] = Query(None, description="Filter nach Status"),
    job_type: Optional[str] = Query(None, description="Filter nach Job-Typ"),
    page: int = Query(1, ge=1, description="Seite"),
    page_size: int = Query(20, ge=1, le=100, description="Einträge pro Seite"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📋 Liste alle eigenen Jobs
    
    Gibt eine paginierte Liste aller Jobs des aktuellen Users zurück.
    
    **Filter-Optionen**:
    - `status`: queued, pending, processing, completed, failed, cancelled
    - `job_type`: chapter_analysis, audiobook_basic, audiobook_chapters, etc.
    
    **Beispiel**:
    ```python
    # Alle Jobs
    jobs = list_jobs()
    
    # Nur abgeschlossene
    jobs = list_jobs(status="completed")
    
    # Nur Audiobook-Jobs
    jobs = list_jobs(job_type="audiobook_basic")
    ```
    """
    queue_service = get_queue_service()
    
    offset = (page - 1) * page_size
    jobs = queue_service.get_user_jobs(
        db, 
        current_user.user_id,
        status=status,
        job_type=job_type,
        limit=page_size,
        offset=offset
    )
    
    total_count = queue_service.get_user_job_count(db, current_user.user_id)
    
    return JobListResponse(
        jobs=jobs,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📊 Hole Status eines Jobs
    
    Gibt detaillierte Status-Informationen zurück:
    - Progress (0-100%)
    - Aktueller Schritt
    - Verarbeitete Kapitel / TTS-Chunks
    - Bisherige Kosten
    
    **Beispiel**:
    ```python
    status = get_job_status("abc-123")
    print(f"Status: {status.status}")
    print(f"Progress: {status.progress}%")
    print(f"Schritt: {status.current_step}")
    print(f"Kapitel: {status.processed_chapters}/{status.total_chapters}")
    print(f"Kosten: ${status.costs.total_cost_usd:.2f}")
    ```
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    # Prüfe Berechtigung
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    status = queue_service.get_job_status(db, job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    return status


@router.get("/{job_id}/result", response_model=JobResultResponse)
def get_job_result(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📥 Hole Ergebnis eines abgeschlossenen Jobs
    
    Gibt das vollständige Ergebnis zurück inkl.:
    - Generierte Audio-Dateien
    - Kombinierte Audio-Datei
    - Asset-Liste zum Download
    - Kostenaufstellung
    
    **Hinweis**: Nur für Jobs mit Status "completed".
    
    **Beispiel**:
    ```python
    result = get_job_result("abc-123")
    
    if result.status == "completed":
        print(f"Audio: {result.combined_audio_file}")
        print(f"Dauer: {result.total_duration_seconds}s")
        
        for asset in result.assets:
            print(f"- {asset.file_name}: {asset.file_path}")
    ```
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    result = queue_service.get_job_result(db, job_id)
    
    if not result:
        # Job noch nicht fertig - gib Status zurück
        status = queue_service.get_job_status(db, job_id)
        return JobResultResponse(
            job_id=job_id,
            job_type=status.job_type,
            status=status.status,
            error_message=status.error_message if status.status == JobStatus.FAILED else "Job noch nicht abgeschlossen"
        )
    
    return result


@router.delete("/{job_id}")
def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ❌ Breche einen Job ab
    
    Bricht einen laufenden oder wartenden Job ab.
    Funktioniert nur für Jobs mit Status: queued, pending, processing
    
    **Hinweis**: Bereits generierte Audio-Dateien werden NICHT gelöscht.
    
    **Beispiel**:
    ```python
    # Job abbrechen
    result = cancel_job("abc-123")
    print(result["message"])
    ```
    """
    queue_service = get_queue_service()
    
    success = queue_service.cancel_job(db, job_id, current_user.user_id)
    
    if not success:
        job = queue_service.get_job(db, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job nicht gefunden")
        if job.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Zugriff verweigert")
        raise HTTPException(
            status_code=400, 
            detail=f"Job kann nicht abgebrochen werden (Status: {job.status})"
        )
    
    return {"message": "Job wurde abgebrochen", "job_id": job_id}


@router.get("/{job_id}/assets")
def get_job_assets(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    📂 Hole alle Assets (Audio-Dateien) eines Jobs
    
    Gibt Liste aller generierten Dateien zurück mit:
    - Dateiname und Pfad
    - Dateigröße
    - Dauer (bei Audio)
    - Kapitel-Info
    
    **Beispiel**:
    ```python
    assets = get_job_assets("abc-123")
    
    for asset in assets["assets"]:
        print(f"{asset.file_name}: {asset.duration_seconds}s")
    ```
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")
    
    assets = queue_service.get_job_assets(db, job_id)
    
    return {
        "job_id": job_id,
        "assets": [
            AssetInfo(
                asset_id=a.asset_id,
                asset_type=a.asset_type,
                file_name=a.file_name,
                file_path=a.file_path,
                file_size_bytes=a.file_size_bytes,
                duration_seconds=a.duration_seconds,
                chapter_title=a.chapter_title,
                download_url=a.storage_url
            )
            for a in assets
        ],
        "total_count": len(assets)
    }


@router.get("/{job_id}/events", response_model=JobEventsListResponse)
def get_job_events(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    🧭 Hole Event-Timeline eines Jobs.

    Liefert den chronologischen Verlauf der wichtigsten Pipeline-Events:
    queued, started, stage updates, completed/failed.
    """
    queue_service = get_queue_service()
    job = queue_service.get_job(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")

    tracking_dao = get_job_tracking_dao(db)
    events = tracking_dao.list_events(job_id)

    serialized = []
    for event in events:
        details = None
        if event.details:
            import json
            try:
                details = json.loads(event.details)
            except Exception:
                details = {"raw": event.details}

        normalized_status = event.status if event.status in {s.value for s in JobStatus} else None
        serialized.append(
            JobEventResponse(
                event_id=event.event_id,
                timestamp=event.timestamp,
                event_type=event.event_type,
                status=normalized_status,
                progress=event.progress,
                step=event.step,
                details=details
            )
        )

    return {
        "job_id": job_id,
        "events": serialized,
        "total_count": len(serialized)
    }


@router.get("/{job_id}/stream")
async def stream_job_updates(
    job_id: str,
    request: Request,
    api_key: Optional[str] = Query(None, description="API Key für SSE/EventSource"),
    db: Session = Depends(get_db)
):
    """
    SSE Stream fuer Live-Status + neue Job-Events.

    Event-Typen:
    - status_update
    - job_event
    - done
    - heartbeat
    """
    current_user = _resolve_user_from_request(request, db, api_key)
    queue_service = get_queue_service()
    tracking_dao = get_job_tracking_dao(db)

    job = queue_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    if job.user_id != current_user.user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Zugriff verweigert")

    async def event_generator():
        last_event_id = 0
        last_status_fingerprint = ""

        while True:
            if await request.is_disconnected():
                break

            # Status-Update senden wenn sich relevante Felder geaendert haben
            current_job = queue_service.get_job(db, job_id)
            if not current_job:
                payload = {"job_id": job_id, "status": "not_found"}
                yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break

            status_payload = {
                "job_id": current_job.job_id,
                "status": current_job.status,
                "progress": current_job.progress,
                "current_step": current_job.current_step,
                "processed_tts_chunks": current_job.processed_tts_chunks,
                "total_tts_chunks": current_job.total_tts_chunks,
                "processed_text_length": current_job.processed_text_length,
                "total_text_length": current_job.total_text_length,
                "started_at": current_job.started_at.isoformat() if current_job.started_at else None,
                "completed_at": current_job.completed_at.isoformat() if current_job.completed_at else None,
                "error_message": current_job.error_message
            }
            fingerprint = json.dumps(status_payload, sort_keys=True)
            if fingerprint != last_status_fingerprint:
                last_status_fingerprint = fingerprint
                yield f"event: status_update\ndata: {fingerprint}\n\n"

            # Neue Events senden
            all_events = tracking_dao.list_events(job_id)
            new_events = [ev for ev in all_events if ev.event_id > last_event_id]
            for ev in new_events:
                details = None
                if ev.details:
                    try:
                        details = json.loads(ev.details)
                    except Exception:
                        details = {"raw": ev.details}

                ev_payload = {
                    "event_id": ev.event_id,
                    "timestamp": ev.timestamp.isoformat() if ev.timestamp else None,
                    "event_type": ev.event_type,
                    "status": ev.status,
                    "progress": ev.progress,
                    "step": ev.step,
                    "details": details
                }
                last_event_id = max(last_event_id, ev.event_id)
                yield f"id: {ev.event_id}\nevent: job_event\ndata: {json.dumps(ev_payload)}\n\n"

            if current_job.status in ["completed", "failed", "cancelled"]:
                done_payload = {"job_id": job_id, "status": current_job.status}
                yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"
                break

            yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(1.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

