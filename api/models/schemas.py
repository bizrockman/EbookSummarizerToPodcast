"""
Pydantic Schemas für API Request/Response

Saubere API-Definition mit klaren Schemas für:
- Basic: Audiobook aus komplettem EPUB
- Basic Extended: Audiobook aus spezifischen Kapiteln
- Addon 1: Mit Übersetzung
- Addon 2: Mit Zusammenfassung
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


# =============================================================================
# ENUMS
# =============================================================================

class JobType(str, Enum):
    """Typen von Jobs"""
    CHAPTER_ANALYSIS = "chapter_analysis"
    BOOK_SUMMARY = "book_summary"
    BOOK_PROCESSING = "book_processing"
    AUDIOBOOK_BASIC = "audiobook_basic"
    AUDIOBOOK_CHAPTERS = "audiobook_chapters"
    AUDIOBOOK_TRANSLATED = "audiobook_translated"
    AUDIOBOOK_SUMMARY = "audiobook_summary"
    AUDIOBOOK_SUMMARY_TRANSLATED = "audiobook_summary_translated"


class JobStatus(str, Enum):
    """Status eines Jobs"""
    QUEUED = "queued"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChapterType(str, Enum):
    """Kapiteltyp"""
    CONTENT = "content"
    SUPPLEMENT = "supplement"


class TTSProvider(str, Enum):
    """TTS Provider"""
    OPENAI = "openai"
    ELEVENLABS = "elevenlabs"
    LOCAL = "local"


class LLMProvider(str, Enum):
    """LLM Provider"""
    OPENAI = "openai"
    GROQ = "groq"


# =============================================================================
# BOOK SCHEMAS
# =============================================================================

class BookCreateRequest(BaseModel):
    """Request um ein Buch von Pfad zu registrieren"""
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")


class BookResponse(BaseModel):
    """Basis-Response für ein Buch"""
    book_id: str = Field(..., description="Eindeutige Buch-ID")
    title: Optional[str] = Field(None, description="Buchtitel")
    author: Optional[str] = Field(None, description="Autor")
    filename: str = Field(..., description="Original-Dateiname")
    chapter_count: int = Field(0, description="Anzahl Kapitel")
    is_analyzed: bool = Field(False, description="KI-Analyse durchgeführt")
    total_cost_usd: float = Field(0.0, description="Gesamtkosten für dieses Buch")
    uploaded_at: datetime = Field(..., description="Upload-Zeitpunkt")
    is_duplicate: bool = Field(False, description="Buch war bereits vorhanden")
    message: Optional[str] = Field(None, description="Status-Nachricht")


class BookListResponse(BaseModel):
    """Response für Buchliste"""
    books: List[BookResponse]
    total_count: int


class BookDetailResponse(BaseModel):
    """Detaillierte Response für ein Buch"""
    book_id: str
    user_id: str
    title: Optional[str] = None
    author: Optional[str] = None
    filename: str
    file_path: str
    file_size_bytes: int
    chapter_count: int
    
    # Kapitel
    chapters_raw: List[Dict[str, Any]] = Field(default_factory=list)
    chapters_analyzed: Optional[Dict[str, Any]] = None
    is_analyzed: bool = False
    analyzed_at: Optional[datetime] = None
    
    # Kosten
    analysis_cost_usd: float = 0.0
    total_llm_cost_usd: float = 0.0
    total_tts_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    
    # Statistiken
    audiobooks_generated: int = 0
    total_audio_duration_seconds: float = 0.0
    
    # Timestamps
    uploaded_at: datetime
    last_accessed_at: datetime


# =============================================================================
# COMMON SCHEMAS
# =============================================================================

class Chapter(BaseModel):
    """Kapitel aus einem eBook"""
    title: str = Field(..., description="Kapiteltitel")
    href: str = Field(..., description="Referenz im EPUB")
    chapter_type: Optional[ChapterType] = Field(None, description="Typ des Kapitels")
    order: Optional[int] = Field(None, description="Reihenfolge im Buch")


class ChapterAudioInfo(BaseModel):
    """Information über ein generiertes Kapitel-Audio"""
    chapter_title: str
    audio_file: str
    duration_seconds: float
    characters_count: int
    was_translated: bool = False
    was_summarized: bool = False
    cost_usd: float


class AssetInfo(BaseModel):
    """Information über ein Asset (Audio-Datei)"""
    asset_id: str
    asset_type: str
    file_name: str
    file_path: str
    file_size_bytes: int
    duration_seconds: float
    chapter_title: Optional[str] = None
    download_url: Optional[str] = None


class CostBreakdown(BaseModel):
    """Kostenaufschlüsselung"""
    llm_cost_usd: float = Field(0.0, description="LLM-Kosten (Analyse, Übersetzung, Summary)")
    tts_cost_usd: float = Field(0.0, description="TTS-Kosten")
    total_cost_usd: float = Field(0.0, description="Gesamtkosten")
    
    # Details
    input_tokens: int = Field(0, description="LLM Input-Tokens")
    output_tokens: int = Field(0, description="LLM Output-Tokens")
    total_tokens: int = Field(0, description="LLM Gesamt-Tokens")
    total_characters: int = Field(0, description="TTS-Zeichen")


# =============================================================================
# EPUB SCHEMAS
# =============================================================================

class EPUBValidationRequest(BaseModel):
    """Request für EPUB-Validierung"""
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")


class EPUBValidationResponse(BaseModel):
    """Response der EPUB-Validierung"""
    is_valid: bool
    title: Optional[str] = None
    author: Optional[str] = None
    message: Optional[str] = None


class ChaptersListRequest(BaseModel):
    """Request für Kapitelliste"""
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")


class ChaptersListResponse(BaseModel):
    """Response mit Kapitelliste"""
    chapters: List[Chapter]
    total_chapters: int


class ChapterAnalysisRequest(BaseModel):
    """Request für Kapitelanalyse"""
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider")


class ChapterAnalysisResponse(BaseModel):
    """Response mit analysierten Kapiteln"""
    book_title: Optional[str] = Field(None, description="Buchtitel")
    book_author: Optional[str] = Field(None, description="Autor")
    all_chapters: List[Dict[str, Any]] = Field(..., description="Alle Kapitel")
    content_chapters: List[Dict[str, Any]] = Field(..., description="Inhalts-Kapitel")
    supplement_chapters: List[Dict[str, Any]] = Field(..., description="Zusatzmaterial")
    total_chapters: int = Field(..., description="Anzahl aller Kapitel")
    content_count: int = Field(..., description="Anzahl Inhalts-Kapitel")
    supplement_count: int = Field(..., description="Anzahl Zusatzmaterial")
    analysis_cost_usd: float = Field(0.0, description="Kosten für die Analyse (0 bei Cache-Hit)")
    from_cache: bool = Field(False, description="True wenn Ergebnis aus Cache")
    input_tokens: int = Field(0, description="LLM Input-Tokens (0 bei Cache)")
    output_tokens: int = Field(0, description="LLM Output-Tokens (0 bei Cache)")
    total_tokens: int = Field(0, description="LLM Gesamt-Tokens (0 bei Cache)")


# =============================================================================
# AUDIOBOOK GENERATION SCHEMAS
# =============================================================================

class AudiobookBasicRequest(BaseModel):
    """
    Request für Basic Audiobook-Generierung.
    Generiert ein Audiobook aus dem kompletten EPUB.
    
    Akzeptiert entweder book_id ODER file_path.
    """
    book_id: Optional[str] = Field(None, description="ID eines hochgeladenen Buchs (empfohlen)")
    file_path: Optional[str] = Field(None, description="Pfad zur EPUB-Datei (stateless)")
    tts_provider: TTSProvider = Field(TTSProvider.OPENAI, description="TTS Provider")
    voice: str = Field("alloy", description="Stimme für TTS")
    auto_detect_content: bool = Field(
        True, 
        description="KI-basierte Erkennung von Inhalt vs. Zusatzmaterial"
    )
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider für Kapitelanalyse")


class AudiobookChaptersRequest(BaseModel):
    """
    Request für Basic Extended Audiobook-Generierung.
    Generiert ein Audiobook aus spezifischen Kapiteln.
    
    Akzeptiert entweder book_id ODER file_path.
    """
    book_id: Optional[str] = Field(None, description="ID eines hochgeladenen Buchs (empfohlen)")
    file_path: Optional[str] = Field(None, description="Pfad zur EPUB-Datei (stateless)")
    chapters: List[str] = Field(..., description="Liste der Kapitel-hrefs die verarbeitet werden sollen")
    tts_provider: TTSProvider = Field(TTSProvider.OPENAI, description="TTS Provider")
    voice: str = Field("alloy", description="Stimme für TTS")


class AudiobookTranslatedRequest(BaseModel):
    """
    Request für Addon 1: Übersetztes Audiobook.
    Übersetzt und generiert Audiobook.
    """
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")
    target_language: str = Field(..., description="Zielsprache (z.B. 'de', 'en', 'fr')")
    chapters: Optional[List[str]] = Field(None, description="Optional: Spezifische Kapitel")
    tts_provider: TTSProvider = Field(TTSProvider.OPENAI, description="TTS Provider")
    voice: str = Field("alloy", description="Stimme für TTS")
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider für Übersetzung")
    auto_detect_content: bool = Field(True, description="KI-basierte Kapitelfilterung")


class AudiobookSummaryRequest(BaseModel):
    """
    Request für Addon 2: Zusammengefasstes Audiobook.
    Fasst zusammen und generiert Audiobook.
    """
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")
    summary_length: int = Field(250, description="Wörter pro Zusammenfassung")
    chapters: Optional[List[str]] = Field(None, description="Optional: Spezifische Kapitel")
    tts_provider: TTSProvider = Field(TTSProvider.OPENAI, description="TTS Provider")
    voice: str = Field("alloy", description="Stimme für TTS")
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider")
    auto_detect_content: bool = Field(True, description="KI-basierte Kapitelfilterung")


class AudiobookSummaryTranslatedRequest(BaseModel):
    """
    Request für Addon 2 Extended: Zusammengefasst + Übersetzt.
    """
    file_path: str = Field(..., description="Pfad zur EPUB-Datei")
    target_language: str = Field(..., description="Zielsprache")
    summary_length: int = Field(250, description="Wörter pro Zusammenfassung")
    chapters: Optional[List[str]] = Field(None, description="Optional: Spezifische Kapitel")
    tts_provider: TTSProvider = Field(TTSProvider.OPENAI, description="TTS Provider")
    voice: str = Field("alloy", description="Stimme für TTS")
    llm_provider: Optional[LLMProvider] = Field(None, description="LLM Provider")
    auto_detect_content: bool = Field(True, description="KI-basierte Kapitelfilterung")


# Legacy Request für Abwärtskompatibilität
class AudiobookGenerationRequest(BaseModel):
    """Legacy Request - verwendet AudiobookBasicRequest oder AudiobookChaptersRequest"""
    file_path: str
    chapters: Optional[List[str]] = None
    target_language: Optional[str] = None
    auto_detect_content: bool = True
    tts_provider: TTSProvider = TTSProvider.OPENAI
    voice: Optional[str] = "alloy"
    llm_provider: Optional[LLMProvider] = None


# =============================================================================
# JOB RESPONSE SCHEMAS
# =============================================================================

class JobCreatedResponse(BaseModel):
    """Response beim Erstellen eines Jobs"""
    job_id: str = Field(..., description="Eindeutige Job-ID (UUID)")
    job_type: JobType = Field(..., description="Typ des Jobs")
    status: JobStatus = Field(..., description="Initialer Status")
    message: str = Field(..., description="Info-Nachricht")
    estimated_time_seconds: Optional[int] = Field(None, description="Geschätzte Dauer")
    queue_position: Optional[int] = Field(None, description="Position in der Queue")


class JobStatusResponse(BaseModel):
    """Response für Job-Status-Abfrage"""
    job_id: str
    job_type: JobType
    status: JobStatus
    
    # Progress
    progress: int = Field(0, description="Fortschritt 0-100%")
    current_step: Optional[str] = None
    
    # Kapitel-Progress
    total_chapters: int = 0
    processed_chapters: int = 0
    current_chapter_name: Optional[str] = None
    
    # Text-Progress
    total_text_length: int = 0
    processed_text_length: int = 0
    
    # TTS-Progress
    total_tts_chunks: int = 0
    processed_tts_chunks: int = 0
    
    # Timestamps
    created_at: datetime
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Kosten (Zwischenstand)
    costs: CostBreakdown = Field(default_factory=CostBreakdown)
    
    # Error
    error_message: Optional[str] = None
    
    # Cache
    from_cache: bool = False


class JobEventResponse(BaseModel):
    """Ein Event in der Job-Historie."""
    event_id: int
    timestamp: datetime
    event_type: str
    status: Optional[JobStatus] = None
    progress: Optional[int] = None
    step: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class JobEventsListResponse(BaseModel):
    """Response fuer Job-Event-Timeline."""
    job_id: str
    events: List[JobEventResponse]
    total_count: int


class JobResultResponse(BaseModel):
    """Response mit Job-Ergebnis"""
    job_id: str
    job_type: JobType
    status: JobStatus
    
    # Buch-Info
    book_title: Optional[str] = None
    book_author: Optional[str] = None
    
    # Audio-Info
    chapters_audio: List[ChapterAudioInfo] = Field(default_factory=list)
    combined_audio_file: Optional[str] = None
    total_duration_seconds: float = 0.0
    
    # Assets
    assets: List[AssetInfo] = Field(default_factory=list)
    
    # Kosten
    costs: CostBreakdown = Field(default_factory=CostBreakdown)
    
    # Für Analyse-Jobs
    content_chapters: Optional[List[Chapter]] = None
    supplement_chapters: Optional[List[Chapter]] = None
    
    # Error
    error_message: Optional[str] = None


class JobListItem(BaseModel):
    """Job in einer Liste"""
    job_id: str
    job_type: JobType
    status: JobStatus
    book_title: Optional[str] = None
    progress: int = 0
    created_at: datetime
    completed_at: Optional[datetime] = None
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    strategy: Optional[str] = None
    language: Optional[str] = None
    audio: bool = False
    cost_is_complete: bool = True


class JobListResponse(BaseModel):
    """Response mit Job-Liste"""
    jobs: List[JobListItem]
    total_count: int
    page: int = 1
    page_size: int = 20


# =============================================================================
# USER SCHEMAS
# =============================================================================

class UserStatsResponse(BaseModel):
    """User-Statistiken"""
    user_id: str
    user_name: str
    
    # Credits
    total_credits: Optional[float] = Field(None, description="Total Credits (None = Unbegrenzt)")
    used_credits: float
    remaining_credits: Optional[float] = Field(None, description="Verbleibend (None = Unbegrenzt)")
    
    # Nutzung
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    
    # Kosten
    total_cost_usd: float
    
    # Letzte Aktivität
    last_job_at: Optional[datetime] = None


class UserJobsResponse(BaseModel):
    """Alle Jobs eines Users"""
    user_id: str
    jobs: List[JobListItem]
    total_count: int
    
    # Zusammenfassung
    total_cost_usd: float
    total_duration_seconds: float


# =============================================================================
# ADMIN SCHEMAS
# =============================================================================

class AdminStatsResponse(BaseModel):
    """Admin-Statistiken"""
    total_users: int
    total_jobs: int
    jobs_by_status: Dict[str, int]
    jobs_by_type: Dict[str, int]
    total_cost_usd: float
    total_audio_duration_seconds: float
    
    # Queue-Info
    queue_length: int
    processing_jobs: int


class QueueStatusResponse(BaseModel):
    """Queue-Status"""
    queue_length: int
    processing_jobs: int
    workers_active: int
    jobs_in_queue: List[JobListItem]


# =============================================================================
# LEGACY SCHEMAS (für Abwärtskompatibilität)
# =============================================================================

class AnalysisJobStatus(str, Enum):
    """Legacy - wird durch JobStatus ersetzt"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudiobookJobStatus(str, Enum):
    """Legacy - wird durch JobStatus ersetzt"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisJobResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AnalysisJobStatus
    message: str
    estimated_time_seconds: Optional[int] = None


class AnalysisJobStatusResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AnalysisJobStatus
    progress: int
    current_step: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    analysis_cost_usd: float = 0.0
    from_cache: bool = False


class AnalysisJobResultResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AnalysisJobStatus
    result: Optional[ChapterAnalysisResponse] = None
    error_message: Optional[str] = None


class AudiobookJobResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AudiobookJobStatus
    message: str
    estimated_time_seconds: Optional[int] = None


class AudiobookJobStatusResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AudiobookJobStatus
    progress: int
    current_step: Optional[str] = None
    total_chapters: int = 0
    processed_chapters: int = 0
    total_text_length: int = 0
    processed_text_length: int = 0
    current_chapter_name: Optional[str] = None
    total_tts_chunks: int = 0
    processed_tts_chunks: int = 0
    current_tts_chunk: int = 0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    translation_cost_usd: float = 0.0
    chapter_detection_cost_usd: float = 0.0
    tts_cost_usd: float = 0.0
    total_cost_usd: float = 0.0
    error_message: Optional[str] = None


class AudiobookJobResultResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: AudiobookJobStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None


class AudiobookGenerationResponse(BaseModel):
    """Legacy Response"""
    job_id: str
    status: str
    chapters_audio: List[ChapterAudioInfo]
    combined_audio_url: Optional[str] = None
    total_duration_seconds: float
    total_cost_usd: float
    usage_details: Dict[str, Any]


# Legacy Schemas
class UsageStats(BaseModel):
    """Legacy - wird durch UserStatsResponse ersetzt"""
    user_id: str
    user_name: str
    total_credits: Optional[float] = None
    used_credits: float
    remaining_credits: Optional[float] = None
    total_jobs: int
    total_cost_usd: float


class JobDetail(BaseModel):
    """Legacy - wird durch JobListItem ersetzt"""
    job_id: str
    user_id: str
    book_title: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    chapters_processed: int
    total_tokens: int
    total_characters: int
    audio_duration_seconds: float
    translation_cost_usd: float
    chapter_detection_cost_usd: float
    tts_cost_usd: float
    total_cost_usd: float


class AdminUsageReport(BaseModel):
    """Legacy Admin Report"""
    users: List[UsageStats]
    jobs: List[JobDetail]
    total_system_cost_usd: float
    generated_at: datetime
