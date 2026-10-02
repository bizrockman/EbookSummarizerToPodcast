"""
Konfigurationseinstellungen für die FastAPI-Anwendung
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Anwendungseinstellungen"""
    
    # API Einstellungen
    api_title: str = "eBook to Audiobook API"
    api_version: str = "1.0.0"
    api_description: str = "API zur Konvertierung von eBooks in Audiobooks mit Übersetzungsfunktion"
    
    # OpenAI Einstellungen
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY")
    openai_default_model: str = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o")
    openai_tts_model: str = "tts-1-hd"
    
    # ElevenLabs Einstellungen (optional)
    elevenlabs_api_key: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    
    # Groq Einstellungen (optional)
    groq_api_key: Optional[str] = os.getenv("GROQ_API_KEY")
    groq_api_base: Optional[str] = os.getenv("GROQ_API_BASE")
    groq_default_model: Optional[str] = os.getenv("GROQ_DEFAULT_MODEL")
    
    # LLM Provider
    llm_model_provider: str = os.getenv("LLM_MODEL_PROVIDER", "openai")
    
    # Datenbank Einstellungen
    database_url: str = "sqlite:///./audiobook_tracker.db"
    
    # Datei-Pfade
    upload_dir: str = "uploads"
    audiofiles_dir: str = "audiofiles"
    production_prices: dict = {}  # Optional JSON map, keyed by provider:model.
    worker_threads: int = 3
    recover_jobs_on_start: bool = False
    
    # Dummy User für Testing
    dummy_user_id: str = "dummy-user-001"
    dummy_user_name: str = "Dummy User"
    dummy_user_api_key: str = "dummy-api-key-12345"
    dummy_user_credits: float = float('inf')  # Unbegrenzte Credits
    
    # Admin User
    admin_user_id: str = "admin-001"
    admin_user_name: str = "Admin User"
    admin_api_key: str = "admin-api-key-67890"
    
    # Kostenmodell (USD)
    # OpenAI TTS Kosten: $0.000030 pro Zeichen (tts-1-hd)
    openai_tts_cost_per_char: float = 0.000030
    
    # OpenAI GPT-4o Token Kosten
    openai_gpt4o_input_cost_per_1k: float = 0.005  # $5 per 1M tokens
    openai_gpt4o_output_cost_per_1k: float = 0.015  # $15 per 1M tokens
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()


# Erstelle erforderliche Verzeichnisse
os.makedirs(settings.upload_dir, exist_ok=True)
os.makedirs(settings.audiofiles_dir, exist_ok=True)

