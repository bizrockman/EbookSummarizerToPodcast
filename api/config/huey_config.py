"""
Huey Queue Konfiguration

- SQLite für Entwicklung (Standard)
- Redis für Produktion
"""
import os
from huey import SqliteHuey, RedisHuey

# Queue-Backend: sqlite (Standard) oder redis
QUEUE_BACKEND = os.getenv("QUEUE_BACKEND", "sqlite")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Huey DB Pfad
HUEY_DB_PATH = os.getenv("HUEY_DB_PATH", "./huey_queue.db")


def create_huey():
    """Erstelle Huey-Instanz"""
    if QUEUE_BACKEND == "redis":
        return RedisHuey(
            name="audiobook_queue",
            url=REDIS_URL,
            immediate=False,
            results=True,
            store_none=False,
            utc=True
        )
    else:
        # SQLite für Entwicklung
        return SqliteHuey(
            name="audiobook_queue",
            filename=HUEY_DB_PATH,
            immediate=False,
            results=True,
            store_none=False,
            utc=True
        )


# Globale Huey-Instanz
huey = create_huey()

# Tasks importieren damit sie beim Consumer registriert werden
# (muss NACH huey = create_huey() stehen!)
from api.tasks import audiobook_tasks  # noqa
from api.tasks import summary_tasks  # noqa
from api.tasks import production_tasks  # noqa
