"""
DAO Pattern fuer Job-Tracking und Observability.

Kapselt Job-Updates, Kostenlogs, Assets und Event-Timeline.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import uuid

from sqlalchemy.orm import Session

from api.models.database_models import Job, JobAsset, CostLog, JobEvent


class JobTrackingDao(ABC):
    """Abstraktes Interface fuer Job-Tracking-Storage."""

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[Job]:
        pass

    @abstractmethod
    def update_job(self, job_id: str, **kwargs) -> None:
        pass

    @abstractmethod
    def add_cost(
        self,
        job_id: str,
        llm_cost: float = 0,
        tts_cost: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        characters: int = 0
    ) -> None:
        pass

    @abstractmethod
    def log_cost(
        self,
        job_id: str,
        user_id: str,
        operation: str,
        provider: str,
        cost_usd: float,
        **kwargs
    ) -> None:
        pass

    @abstractmethod
    def add_asset(
        self,
        job_id: str,
        asset_type: str,
        file_path: str,
        file_name: str,
        file_size: int = 0,
        duration: float = 0,
        chapter_index: Optional[int] = None,
        chapter_title: Optional[str] = None
    ) -> str:
        pass

    @abstractmethod
    def create_event(
        self,
        job_id: str,
        user_id: str,
        event_type: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        pass

    @abstractmethod
    def list_events(self, job_id: str) -> List[JobEvent]:
        pass


class SQLiteJobTrackingDao(JobTrackingDao):
    """SQLite/SQLAlchemy Implementation des JobTrackingDao."""

    def __init__(self, db: Session):
        self.db = db

    def get_job(self, job_id: str) -> Optional[Job]:
        return self.db.query(Job).filter(Job.job_id == job_id).first()

    def update_job(self, job_id: str, **kwargs) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        for key, value in kwargs.items():
            if hasattr(job, key) and value is not None:
                setattr(job, key, value)
        self.db.commit()

    def add_cost(
        self,
        job_id: str,
        llm_cost: float = 0,
        tts_cost: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        characters: int = 0
    ) -> None:
        job = self.get_job(job_id)
        if not job:
            return
        job.llm_cost_usd += llm_cost
        job.tts_cost_usd += tts_cost
        job.total_cost_usd = job.llm_cost_usd + job.tts_cost_usd
        job.input_tokens += input_tokens
        job.output_tokens += output_tokens
        job.total_tokens = job.input_tokens + job.output_tokens
        job.total_characters += characters
        self.db.commit()

    def log_cost(
        self,
        job_id: str,
        user_id: str,
        operation: str,
        provider: str,
        cost_usd: float,
        **kwargs
    ) -> None:
        log = CostLog(
            job_id=job_id,
            user_id=user_id,
            operation=operation,
            provider=provider,
            cost_usd=cost_usd,
            **{k: v for k, v in kwargs.items() if v is not None}
        )
        self.db.add(log)
        self.db.commit()

    def add_asset(
        self,
        job_id: str,
        asset_type: str,
        file_path: str,
        file_name: str,
        file_size: int = 0,
        duration: float = 0,
        chapter_index: Optional[int] = None,
        chapter_title: Optional[str] = None
    ) -> str:
        asset_id = str(uuid.uuid4())
        asset = JobAsset(
            asset_id=asset_id,
            job_id=job_id,
            asset_type=asset_type,
            file_path=file_path,
            file_name=file_name,
            file_size_bytes=file_size,
            duration_seconds=duration,
            chapter_index=chapter_index,
            chapter_title=chapter_title,
            storage_provider="local"
        )
        self.db.add(asset)
        self.db.commit()
        return asset_id

    def create_event(
        self,
        job_id: str,
        user_id: str,
        event_type: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        event = JobEvent(
            job_id=job_id,
            user_id=user_id,
            event_type=event_type,
            status=status,
            progress=progress,
            step=step,
            details=json.dumps(details) if details is not None else None,
            timestamp=datetime.utcnow()
        )
        self.db.add(event)
        self.db.commit()

    def list_events(self, job_id: str) -> List[JobEvent]:
        return (
            self.db.query(JobEvent)
            .filter(JobEvent.job_id == job_id)
            .order_by(JobEvent.timestamp.asc())
            .all()
        )


def get_job_tracking_dao(db: Session, provider: str = "sqlite") -> JobTrackingDao:
    """Factory fuer JobTrackingDao."""
    if provider == "sqlite":
        return SQLiteJobTrackingDao(db)
    raise ValueError(f"Unbekannter Job-Tracking-Provider: {provider}")
