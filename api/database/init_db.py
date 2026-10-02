"""
Datenbankinitialisierung und Seed-Daten
"""
import os
import logging
from api.database.connection import engine, Base, get_db
from api.daos.database_dao import SQLiteDatabaseDao
from api.config.settings import settings

logger = logging.getLogger("api")

# Marker-Datei für erstmalige Initialisierung
_DB_INITIALIZED_MARKER = ".db_initialized"


def _is_first_run() -> bool:
    """Prüft ob es der erste Start ist"""
    db_path = settings.database_url.replace("sqlite:///", "")
    marker_path = os.path.join(os.path.dirname(db_path) or ".", _DB_INITIALIZED_MARKER)
    return not os.path.exists(marker_path)


def _mark_initialized():
    """Markiert DB als initialisiert"""
    db_path = settings.database_url.replace("sqlite:///", "")
    marker_path = os.path.join(os.path.dirname(db_path) or ".", _DB_INITIALIZED_MARKER)
    with open(marker_path, "w") as f:
        f.write("initialized")


def initialize_database():
    """
    Initialisiere Datenbank und erstelle Seed-Daten.
    Gibt nur bei erstmaliger Initialisierung Meldungen aus.
    """
    first_run = _is_first_run()
    
    # Erstelle Tabellen (SQLAlchemy macht das idempotent)
    Base.metadata.create_all(bind=engine)
    
    if first_run:
        print("🗃️  Datenbank initialisiert")
    
    # Erstelle Seed-User falls nicht vorhanden
    with get_db() as db:
        dao = SQLiteDatabaseDao(db)
        created_users = []
        
        # Dummy User
        if not dao.get_user_by_id(settings.dummy_user_id):
            dao.create_user(
                user_id=settings.dummy_user_id,
                user_name=settings.dummy_user_name,
                api_key=settings.dummy_user_api_key,
                total_credits=settings.dummy_user_credits,
                is_admin=False
            )
            created_users.append("Dummy User")
        
        # Admin User
        if not dao.get_user_by_id(settings.admin_user_id):
            dao.create_user(
                user_id=settings.admin_user_id,
                user_name=settings.admin_user_name,
                api_key=settings.admin_api_key,
                total_credits=float('inf'),
                is_admin=True
            )
            created_users.append("Admin User")
        
        if created_users:
            print(f"👤 User erstellt: {', '.join(created_users)}")
    
    if first_run:
        _mark_initialized()
        logger.info("Datenbank erstmalig initialisiert")


if __name__ == "__main__":
    initialize_database()
