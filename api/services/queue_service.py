"""
Queue Service für Job-Management

Nutzt Huey für Task Queue.
- SQLite für lokale Entwicklung
- Redis für Produktion (QUEUE_BACKEND=redis)
"""
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from api.models.database_models import Job, JobAsset
from api.models.schemas import (
    JobStatusResponse, JobResultResponse, JobListItem,
    CostBreakdown, AssetInfo, Chapter, ChapterAudioInfo
)
from api.config.huey_config import huey
from api.daos.job_tracking_dao import get_job_tracking_dao

import logging
logger = logging.getLogger("api.queue")


class QueueService:
    """
    Queue Service mit Huey Backend.
    
    Erstellt Jobs in der DB und queued sie für den Huey Consumer.
    """
    
    def _enqueue_task(self, job_type: str, job_id: str):
        """Queue passenden Huey-Task fuer job_type."""
        from api.tasks.audiobook_tasks import (
            process_chapter_analysis,
            process_audiobook_basic,
            process_audiobook_chapters
        )

        if job_type == "book_processing":
            from api.tasks.production_tasks import process_book
            process_book(job_id)
        elif job_type == "book_summary":
            from api.tasks.summary_tasks import process_book_summary
            process_book_summary(job_id)
        elif job_type == "chapter_analysis":
            process_chapter_analysis(job_id)
        elif job_type == "audiobook_basic":
            process_audiobook_basic(job_id)
        elif job_type == "audiobook_chapters":
            process_audiobook_chapters(job_id)
        else:
            logger.warning(f"Unbekannter Job-Typ: {job_type}")

    def create_job(
        self,
        db: Session,
        user_id: str,
        job_type: str,
        file_path: str,
        config: Dict[str, Any],
        book_title: Optional[str] = None,
        book_author: Optional[str] = None,
        book_id: Optional[str] = None,
        priority: int = 0
    ) -> str:
        """
        Erstelle Job und queue ihn für Verarbeitung.
        
        Args:
            book_id: Optional - Referenz auf ein Book für Kosten-Tracking
        
        Returns:
            job_id
        """
        job_id = str(uuid.uuid4())
        
        # Job in DB erstellen
        job = Job(
            job_id=job_id,
            user_id=user_id,
            book_id=book_id,
            job_type=job_type,
            status="queued",
            priority=priority,
            file_path=file_path,
            book_title=book_title,
            book_author=book_author,
            config=json.dumps(config),
            llm_provider=config.get("llm_provider"),
            tts_provider=config.get("tts_provider", "openai"),
            voice=config.get("voice", "alloy"),
            queued_at=datetime.utcnow(),
            current_step="In Queue, warte auf Worker..."
        )
        
        db.add(job)
        db.commit()

        # Initiales Event fuer Observability
        tracking_dao = get_job_tracking_dao(db)
        tracking_dao.create_event(
            job_id=job_id,
            user_id=user_id,
            event_type="job_queued",
            status="queued",
            progress=0,
            step="In Queue, warte auf Worker...",
            details={"job_type": job_type}
        )
        
        # Task in Huey Queue einreihen
        self._enqueue_task(job_type, job_id)
        
        logger.info(f"📦 Job {job_id} erstellt und gequeued (Typ: {job_type})")
        
        return job_id

    def recover_interrupted_jobs(self, db: Session, max_age_minutes: int = 1) -> int:
        """
        Re-queue Jobs die beim letzten Shutdown in processing/pending haengen blieben.
        """
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        interrupted_jobs = (
            db.query(Job)
            .filter(Job.status.in_(["processing", "pending"]))
            .filter((Job.started_at == None) | (Job.started_at <= cutoff))  # noqa: E711
            .all()
        )

        if not interrupted_jobs:
            return 0

        tracking_dao = get_job_tracking_dao(db)
        recovered = 0

        for job in interrupted_jobs:
            job.status = "queued"
            job.current_step = "Nach Neustart erneut eingeplant"
            job.error_message = None
            job.queued_at = datetime.utcnow()
            db.commit()

            tracking_dao.create_event(
                job_id=job.job_id,
                user_id=job.user_id,
                event_type="job_requeued_after_restart",
                status="queued",
                progress=job.progress,
                step="Nach Neustart erneut eingeplant",
                details={"previous_status": "processing_or_pending"}
            )

            self._enqueue_task(job.job_type, job.job_id)
            recovered += 1

        logger.warning(f"{recovered} unterbrochene Jobs wurden re-queued.")
        return recovered
    
    def get_job(self, db: Session, job_id: str) -> Optional[Job]:
        """Hole Job aus DB"""
        return db.query(Job).filter(Job.job_id == job_id).first()
    
    def get_job_status(self, db: Session, job_id: str) -> Optional[JobStatusResponse]:
        """Hole Job-Status als Response"""
        job = self.get_job(db, job_id)
        if not job:
            return None
        
        return JobStatusResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            current_step=job.current_step,
            total_chapters=job.total_chapters,
            processed_chapters=job.processed_chapters,
            current_chapter_name=job.current_chapter_name,
            total_text_length=job.total_text_length,
            processed_text_length=job.processed_text_length,
            total_tts_chunks=job.total_tts_chunks,
            processed_tts_chunks=job.processed_tts_chunks,
            created_at=job.created_at,
            queued_at=job.queued_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            costs=CostBreakdown(
                llm_cost_usd=job.llm_cost_usd,
                tts_cost_usd=job.tts_cost_usd,
                total_cost_usd=job.total_cost_usd,
                input_tokens=job.input_tokens,
                output_tokens=job.output_tokens,
                total_tokens=job.total_tokens,
                total_characters=job.total_characters
            ),
            error_message=job.error_message,
            from_cache=job.from_cache
        )
    
    def get_job_result(self, db: Session, job_id: str) -> Optional[JobResultResponse]:
        """Hole Job-Ergebnis"""
        job = self.get_job(db, job_id)
        if not job or job.status != "completed":
            return None
        
        # Assets
        assets = db.query(JobAsset).filter(JobAsset.job_id == job_id).all()
        asset_infos = [
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
        ]
        
        # Result parsen
        chapters_audio = []
        content_chapters = None
        supplement_chapters = None
        combined_audio_file = None
        
        if job.result_data:
            try:
                result = json.loads(job.result_data)
                chapters_audio = [ChapterAudioInfo(**ch) for ch in result.get("chapters_audio", [])]
                combined_audio_file = result.get("combined_audio_file")
                
                if "content_chapters" in result:
                    content_chapters = [Chapter(**ch) for ch in result["content_chapters"]]
                if "supplement_chapters" in result:
                    supplement_chapters = [Chapter(**ch) for ch in result["supplement_chapters"]]
            except Exception as e:
                logger.error(f"Fehler beim Parsen von result_data: {e}")
        
        return JobResultResponse(
            job_id=job.job_id,
            job_type=job.job_type,
            status=job.status,
            book_title=job.book_title,
            book_author=job.book_author,
            chapters_audio=chapters_audio,
            combined_audio_file=combined_audio_file,
            total_duration_seconds=job.audio_duration_seconds,
            assets=asset_infos,
            costs=CostBreakdown(
                llm_cost_usd=job.llm_cost_usd,
                tts_cost_usd=job.tts_cost_usd,
                total_cost_usd=job.total_cost_usd,
                input_tokens=job.input_tokens,
                output_tokens=job.output_tokens,
                total_tokens=job.total_tokens,
                total_characters=job.total_characters
            ),
            content_chapters=content_chapters,
            supplement_chapters=supplement_chapters,
            error_message=job.error_message
        )
    
    def cancel_job(self, db: Session, job_id: str, user_id: str) -> bool:
        """Breche Job ab"""
        job = self.get_job(db, job_id)
        if not job or job.user_id != user_id:
            return False
        
        if job.status not in ["queued", "pending", "processing"]:
            return False
        
        # Huey Task revoken (wenn möglich)
        try:
            huey.revoke_by_id(job_id)
        except:
            pass
        
        job.status = "cancelled"
        job.completed_at = datetime.utcnow()
        job.current_step = "Vom User abgebrochen"
        db.commit()
        
        logger.info(f"Job {job_id} abgebrochen")
        return True
    
    def get_user_jobs(
        self,
        db: Session,
        user_id: str,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[JobListItem]:
        """Hole Jobs eines Users"""
        query = db.query(Job).filter(Job.user_id == user_id)
        
        if status:
            query = query.filter(Job.status == status)
        if job_type:
            query = query.filter(Job.job_type == job_type)
        
        jobs = query.order_by(Job.created_at.desc()).offset(offset).limit(limit).all()
        
        from api.services.production.usage import usage_report
        return [
            JobListItem(
                job_id=j.job_id,
                job_type=j.job_type,
                status=j.status,
                book_title=j.book_title,
                progress=j.progress,
                created_at=j.created_at,
                completed_at=j.completed_at,
                total_cost_usd=j.total_cost_usd,
                input_tokens=j.input_tokens or 0,
                output_tokens=j.output_tokens or 0,
                strategy=json.loads(j.config or "{}").get("strategy"),
                language=json.loads(j.config or "{}").get("language"),
                audio=json.loads(j.config or "{}").get("audio", False),
                cost_is_complete=not usage_report(db, j.job_id)["totals"]["unknown_calls"]
                    if j.job_type == "book_processing" else True
            )
            for j in jobs
        ]
    
    def get_user_job_count(self, db: Session, user_id: str) -> int:
        """Zähle Jobs eines Users"""
        return db.query(Job).filter(Job.user_id == user_id).count()
    
    def get_queue_length(self) -> int:
        """Hole Queue-Länge von Huey"""
        try:
            return len(huey.pending())
        except:
            return 0
    
    def get_processing_count(self, db: Session) -> int:
        """Zähle aktiv verarbeitete Jobs"""
        return db.query(Job).filter(Job.status == "processing").count()
    
    def get_job_assets(self, db: Session, job_id: str) -> List[JobAsset]:
        """Hole Assets eines Jobs"""
        return db.query(JobAsset).filter(JobAsset.job_id == job_id).all()


# Singleton
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Hole Queue Service"""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
