"""
FastAPI Router
"""
from api.routers.epub import router as epub_router
from api.routers.audiobook import router as audiobook_router
from api.routers.jobs import router as jobs_router
from api.routers.admin import router as admin_router

__all__ = [
    "epub_router",
    "audiobook_router", 
    "jobs_router",
    "admin_router"
]
