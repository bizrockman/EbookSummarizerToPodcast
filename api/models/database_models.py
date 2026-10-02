"""
SQLAlchemy Database Models

Einheitliches Job-System für alle Aufgabentypen:
- audiobook_basic: Direktes Audiobook aus EPUB
- audiobook_chapters: Audiobook aus spezifischen Kapiteln
- audiobook_translated: Übersetztes Audiobook
- audiobook_summary: Zusammengefasstes Audiobook
- chapter_analysis: Kapitelanalyse
"""
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


class JobType(enum.Enum):
    """Typen von Jobs"""
    CHAPTER_ANALYSIS = "chapter_analysis"
    AUDIOBOOK_BASIC = "audiobook_basic"
    AUDIOBOOK_CHAPTERS = "audiobook_chapters"
    AUDIOBOOK_TRANSLATED = "audiobook_translated"
    AUDIOBOOK_SUMMARY = "audiobook_summary"
    AUDIOBOOK_SUMMARY_TRANSLATED = "audiobook_summary_translated"


class JobStatus(enum.Enum):
    """Status eines Jobs"""
    QUEUED = "queued"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(Base):
    """User Tabelle"""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    api_key = Column(String, unique=True, index=True, nullable=False)
    
    # RapidAPI Support
    rapidapi_user = Column(String, unique=True, nullable=True, index=True)
    
    # Credits & Billing
    total_credits = Column(Float, default=0.0)
    used_credits = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    # Flags
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    jobs = relationship("Job", back_populates="user")
    books = relationship("Book", back_populates="user", cascade="all, delete-orphan")


class Book(Base):
    """Hochgeladenes Buch eines Users"""
    __tablename__ = "books"
    
    # Identifikation
    book_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Datei-Info
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    file_hash = Column(String, index=True)  # MD5 für Duplikat-Check
    
    # Metadaten (aus EPUB extrahiert)
    title = Column(String, nullable=True)
    author = Column(String, nullable=True)
    language = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    # Kapitel (in DB statt LRU-Cache!)
    chapter_count = Column(Integer, default=0)
    chapters_raw = Column(Text, nullable=True)       # JSON: Rohe Kapitel aus TOC
    chapters_analyzed = Column(Text, nullable=True)  # JSON: KI-analysierte Kapitel
    chapters_analyzed_at = Column(DateTime, nullable=True)
    analysis_llm_provider = Column(String, nullable=True)
    analysis_cost_usd = Column(Float, default=0.0)
    analysis_tokens = Column(Integer, default=0)
    
    # Aggregierte Kosten für dieses Buch
    total_llm_cost_usd = Column(Float, default=0.0)
    total_tts_cost_usd = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Audiobook-Statistiken
    audiobooks_generated = Column(Integer, default=0)
    total_audio_duration_seconds = Column(Float, default=0.0)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_accessed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="books")
    jobs = relationship("Job", back_populates="book", cascade="all, delete-orphan")


class Job(Base):
    """Einheitliches Job-Modell für alle Aufgabentypen."""
    __tablename__ = "jobs"
    
    # Identifikation
    job_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=True, index=True)
    
    # Job-Typ und Status
    job_type = Column(String, nullable=False, index=True)
    status = Column(String, default="queued", index=True)
    priority = Column(Integer, default=0)
    
    # Eingabe-Daten (file_path kann leer sein wenn book_id gesetzt)
    file_path = Column(String, nullable=True)
    book_title = Column(String, nullable=True)
    book_author = Column(String, nullable=True)
    
    # Job-Konfiguration (JSON)
    config = Column(Text, nullable=True)
    
    # Progress-Tracking
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    
    # Detaillierter Progress
    total_chapters = Column(Integer, default=0)
    processed_chapters = Column(Integer, default=0)
    current_chapter_name = Column(String, nullable=True)
    total_text_length = Column(Integer, default=0)
    processed_text_length = Column(Integer, default=0)
    
    # TTS-spezifisch
    total_tts_chunks = Column(Integer, default=0)
    processed_tts_chunks = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    queued_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Ergebnis
    result_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Kosten-Tracking
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_characters = Column(Integer, default=0)
    audio_duration_seconds = Column(Float, default=0.0)
    
    # Kosten pro Kategorie (USD)
    llm_cost_usd = Column(Float, default=0.0)
    tts_cost_usd = Column(Float, default=0.0)
    total_cost_usd = Column(Float, default=0.0)
    
    # Provider-Info
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)
    tts_provider = Column(String, nullable=True)
    tts_model = Column(String, nullable=True)
    voice = Column(String, default="alloy")
    
    # Cache
    content_hash = Column(String, nullable=True, index=True)
    from_cache = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="jobs")
    book = relationship("Book", back_populates="jobs")
    assets = relationship("JobAsset", back_populates="job", cascade="all, delete-orphan")
    cost_logs = relationship("CostLog", back_populates="job", cascade="all, delete-orphan")
    events = relationship("JobEvent", back_populates="job", cascade="all, delete-orphan")


class JobAsset(Base):
    """Assets (Audio-Dateien) die zu einem Job gehören."""
    __tablename__ = "job_assets"
    
    asset_id = Column(String, primary_key=True, index=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False, index=True)
    
    # Asset-Info
    asset_type = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String, default="audio/mpeg")
    
    # Metadaten
    chapter_index = Column(Integer, nullable=True)
    chapter_title = Column(String, nullable=True)
    duration_seconds = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Storage-Info (für Cloud-Migration)
    storage_provider = Column(String, default="local")
    storage_url = Column(String, nullable=True)
    
    # Relationship
    job = relationship("Job", back_populates="assets")


class CostLog(Base):
    """Detailliertes Kosten-Log pro Operation."""
    __tablename__ = "cost_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=True, index=True)
    book_id = Column(String, ForeignKey("books.book_id"), nullable=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Operation
    operation = Column(String, nullable=False)
    step_name = Column(String, nullable=True)
    
    # Provider & Modell
    provider = Column(String, nullable=False)
    model = Column(String, nullable=True)
    
    # Token-Nutzung (LLM)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    
    # Zeichen-Nutzung (TTS)
    characters = Column(Integer, default=0)
    audio_seconds = Column(Float, default=0.0)
    
    # Kosten
    cost_usd = Column(Float, default=0.0)
    
    # Zusätzliche Details (JSON)
    details = Column(Text, nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="cost_logs")


class JobEvent(Base):
    """Zeitliche Event-Historie pro Job fuer observability und debugging."""
    __tablename__ = "job_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("jobs.job_id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=True)
    progress = Column(Integer, nullable=True)
    step = Column(String, nullable=True)
    details = Column(Text, nullable=True)

    # Relationship
    job = relationship("Job", back_populates="events")
