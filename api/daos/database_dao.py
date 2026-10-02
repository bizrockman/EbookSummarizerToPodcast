"""
DAO Pattern für Datenbankzugriff
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from sqlalchemy.orm import Session
import math

from api.models.database_models import User, Job, CostLog
from api.models.schemas import UsageStats, JobListItem


class DatabaseDao(ABC):
    """Abstrakte Basis-Klasse für Datenbank DAOs"""
    
    @abstractmethod
    def create_user(self, user_id: str, user_name: str, api_key: str, 
                    total_credits: float, is_admin: bool = False) -> User:
        pass
    
    @abstractmethod
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        pass
    
    @abstractmethod
    def update_user_credits(self, user_id: str, used_credits: float) -> User:
        pass
    
    @abstractmethod
    def get_user_stats(self, user_id: str) -> UsageStats:
        pass
    
    @abstractmethod
    def get_all_users_stats(self) -> List[UsageStats]:
        pass
    
    @abstractmethod
    def get_all_jobs(self, user_id: Optional[str] = None) -> List[JobListItem]:
        pass


class SQLiteDatabaseDao(DatabaseDao):
    """SQLite Implementation des Database DAO"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_id: str, user_name: str, api_key: str,
                    total_credits: float, is_admin: bool = False) -> User:
        """Erstelle einen neuen User"""
        user = User(
            user_id=user_id,
            user_name=user_name,
            api_key=api_key,
            total_credits=total_credits,
            is_admin=is_admin,
            used_credits=0.0
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Hole User anhand des API Keys"""
        return self.db.query(User).filter(User.api_key == api_key).first()
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Hole User anhand der ID"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def update_user_credits(self, user_id: str, used_credits: float) -> User:
        """Aktualisiere verwendete Credits"""
        user = self.get_user_by_id(user_id)
        if user:
            user.used_credits += used_credits
            self.db.commit()
            self.db.refresh(user)
        return user
    
    def get_user_stats(self, user_id: str) -> UsageStats:
        """Hole Statistiken für einen User"""
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        jobs = self.db.query(Job).filter(Job.user_id == user_id).all()
        total_cost = sum(job.total_cost_usd for job in jobs)
        
        # Konvertiere float('inf') zu None
        total_credits = None if math.isinf(user.total_credits) else user.total_credits
        used_credits = user.used_credits
        remaining_credits = None if total_credits is None else (total_credits - used_credits)
        
        return UsageStats(
            user_id=user.user_id,
            user_name=user.user_name,
            total_credits=total_credits,
            used_credits=used_credits,
            remaining_credits=remaining_credits,
            total_jobs=len(jobs),
            total_cost_usd=total_cost
        )
    
    def get_all_users_stats(self) -> List[UsageStats]:
        """Hole Statistiken für alle User"""
        users = self.db.query(User).all()
        stats = []
        for user in users:
            user_stats = self.get_user_stats(user.user_id)
            if user_stats:
                stats.append(user_stats)
        return stats
    
    def get_all_jobs(self, user_id: Optional[str] = None) -> List[JobListItem]:
        """Hole alle Jobs"""
        query = self.db.query(Job)
        if user_id:
            query = query.filter(Job.user_id == user_id)
        
        jobs = query.order_by(Job.created_at.desc()).all()
        
        return [
            JobListItem(
                job_id=job.job_id,
                job_type=job.job_type,
                status=job.status,
                book_title=job.book_title,
                progress=job.progress,
                created_at=job.created_at,
                completed_at=job.completed_at,
                total_cost_usd=job.total_cost_usd
            )
            for job in jobs
        ]


def get_database_dao(db: Session, provider: str = "sqlite") -> DatabaseDao:
    """Factory-Funktion für Database DAO"""
    if provider == "sqlite":
        return SQLiteDatabaseDao(db)
    else:
        raise ValueError(f"Unbekannter Database Provider: {provider}")
