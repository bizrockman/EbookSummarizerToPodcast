"""
Datenbankverbindung und Session Management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator

from api.config.settings import settings
from api.models.database_models import Base

# Engine erstellen
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

# SessionLocal erstellen
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialisiere die Datenbank und erstelle alle Tabellen"""
    Base.metadata.create_all(bind=engine)
    print("Datenbank initialisiert")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Context Manager für Datenbank-Sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """Dependency für FastAPI"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # wird von FastAPI geschlossen

