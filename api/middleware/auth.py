"""
Authentifizierungs-Middleware
"""
from fastapi import HTTPException, Security, status, Depends
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.orm import Session

from api.database.connection import SessionLocal
from api.daos.database_dao import SQLiteDatabaseDao
from api.models.database_models import User


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def get_db():
    """Dependency für Datenbank-Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Authentifiziere User anhand des API Keys
    
    Raises:
        HTTPException: Wenn API Key ungültig ist
    """
    dao = SQLiteDatabaseDao(db)
    user = dao.get_user_by_api_key(api_key)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger API Key"
        )
    
    return user


def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Prüfe ob User Admin ist
    
    Raises:
        HTTPException: Wenn User kein Admin ist
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Rechte erforderlich"
        )
    
    return current_user

