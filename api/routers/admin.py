"""
Admin Endpunkte
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from api.models.schemas import AdminUsageReport
from api.models.database_models import User
from api.daos.database_dao import SQLiteDatabaseDao
from api.middleware.auth import get_current_admin_user, get_db


router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/usage", response_model=AdminUsageReport)
def get_usage_report(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Hole vollständigen Usage-Report (Admin only)
    
    Zeigt:
    - Alle User mit ihren Credits und Nutzungsstatistiken
    - Alle Jobs mit detaillierten Kosten
    - Gesamtkosten des Systems
    
    **Benötigt Admin-Rechte**
    """
    try:
        db_dao = SQLiteDatabaseDao(db)
        
        # Hole User-Statistiken
        users_stats = db_dao.get_all_users_stats()
        
        # Hole Job-Details
        jobs = db_dao.get_all_jobs()
        
        # Berechne Gesamtkosten
        total_system_cost = sum(job.total_cost_usd for job in jobs)
        
        return AdminUsageReport(
            users=users_stats,
            jobs=jobs,
            total_system_cost_usd=total_system_cost,
            generated_at=datetime.utcnow()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/stats")
def get_user_stats(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Hole Statistiken für einen bestimmten User (Admin only)
    
    **Benötigt Admin-Rechte**
    """
    try:
        db_dao = SQLiteDatabaseDao(db)
        stats = db_dao.get_user_stats(user_id)
        
        if not stats:
            raise HTTPException(status_code=404, detail="User nicht gefunden")
        
        return stats
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
def get_job_details(
    job_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Hole Details zu einem bestimmten Job (Admin only)
    
    **Benötigt Admin-Rechte**
    """
    try:
        db_dao = SQLiteDatabaseDao(db)
        job = db_dao.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job nicht gefunden")
        
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

