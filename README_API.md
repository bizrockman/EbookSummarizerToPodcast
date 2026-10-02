# eBook to Audiobook API

Eine FastAPI-basierte API zur Konvertierung von eBooks (EPUB) in Audiobooks mit automatischer Kapitelerkennung und Übersetzungsfunktion.

## 🚀 Features

- ✅ **EPUB-Validierung**: Prüfung ob EPUB-Dateien valide sind
- 📚 **Kapitelextraktion**: Automatische Extraktion der Kapitelstruktur
- 🤖 **KI-basierte Kapitelerkennung**: Automatische Unterscheidung zwischen Inhalt und Zusatzmaterial (Vorwörter, Anhänge, etc.)
- ⚡ **Asynchrone Jobs**: Background-Processing für lange Tasks ohne Timeouts
- 🌍 **Automatische Übersetzung**: Erkennung der Quellsprache und Übersetzung in Zielsprache
- 🎙️ **Text-to-Speech**: Generierung von hochwertigen Audiobooks
- 💰 **Kostenverfolgung**: Automatisches Tracking von Token- und TTS-Kosten
- 🔒 **API-Key Authentifizierung**: Sichere API mit User-Management
- 📊 **Admin-Dashboard**: Vollständige Nutzungsstatistiken und Reports
- 📝 **Request Logging**: Umfassendes Logging aller API-Requests mit Request-IDs

## 🏗️ Architektur

Die API folgt einem sauberen DAO (Data Access Object) Pattern:

```
api/
├── config/          # Konfiguration und Settings
├── models/          # Pydantic Schemas und SQLAlchemy Models
├── daos/            # Data Access Objects (austauschbar)
│   ├── tts_dao.py       # TTS Provider (OpenAI, ElevenLabs, Lokal)
│   ├── llm_dao.py       # LLM Provider (OpenAI, Groq)
│   └── database_dao.py  # Datenbank (SQLite, später Supabase)
├── services/        # Business Logic
│   ├── epub_service.py
│   └── audiobook_service.py
├── routers/         # FastAPI Endpunkte
├── middleware/      # Auth und andere Middleware
└── database/        # Datenbank-Setup
```

## 📋 Voraussetzungen

- Python 3.9+
- OpenAI API Key
- FFmpeg (für Audio-Verarbeitung)

## 🔧 Installation

1. **Repository klonen und Dependencies installieren:**

```bash
pip install -r requirements_api.txt
```

2. **.env Datei erstellen:**

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_DEFAULT_MODEL=gpt-4o

# Optional: Andere Provider
GROQ_API_KEY=your_groq_key
ELEVENLABS_API_KEY=your_elevenlabs_key

# LLM Provider (openai oder groq)
LLM_MODEL_PROVIDER=openai
```

3. **API starten:**

```bash
python -m api.main
```

Oder mit uvicorn direkt:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Die API ist dann verfügbar unter: `http://localhost:8000`

## 📖 API Dokumentation

Nach dem Start ist die automatische Dokumentation verfügbar unter:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Authentifizierung

Die API verwendet API-Key Authentifizierung über den Header `X-API-Key`.

### Standard-Credentials:

**Dummy User** (für Testing, unbegrenzte Credits):
```
X-API-Key: dummy-api-key-12345
```

**Admin User** (für Admin-Endpunkte):
```
X-API-Key: admin-api-key-67890
```

## 🎯 API Endpunkte

### EPUB Endpunkte

#### `POST /epub/validate`
Validiert eine EPUB-Datei und extrahiert Metadaten.

**Request:**
```json
{
  "file_path": "uploads/meinbuch.epub"
}
```

**Response:**
```json
{
  "is_valid": true,
  "title": "Mein Buch",
  "author": "Max Mustermann",
  "message": "EPUB-Datei ist valide"
}
```

#### `POST /epub/chapters`
Gibt Liste aller Kapitel zurück.

**Request:**
```json
{
  "file_path": "uploads/meinbuch.epub"
}
```

**Response:**
```json
{
  "chapters": [
    {
      "title": "Kapitel 1",
      "href": "chapter1.xhtml",
      "chapter_type": null,
      "order": 0
    }
  ],
  "total_chapters": 15
}
```

### Audiobook Endpunkte

#### `POST /audiobook/generate`
Generiert ein Audiobook aus einer EPUB-Datei.

**Request:**
```json
{
  "file_path": "uploads/meinbuch.epub",
  "chapters": [],
  "target_language": "de",
  "auto_detect_content": true,
  "tts_provider": "openai",
  "voice": "alloy",
  "llm_provider": "openai"
}
```

**Parameter:**
- `file_path`: Pfad zur EPUB-Datei (erforderlich)
- `chapters`: Liste spezifischer Kapitel-hrefs (optional, leer = alle oder auto-detect)
- `target_language`: Zielsprache für Übersetzung (optional, z.B. "de", "en")
- `auto_detect_content`: KI-basierte Erkennung von Inhalts-Kapiteln (default: true)
- `tts_provider`: TTS Provider - "openai", "elevenlabs", "local" (default: "openai")
- `voice`: Stimme für TTS (default: "alloy")
- `llm_provider`: LLM Provider - "openai", "groq" (optional)

**Response:**
```json
{
  "job_id": "job-12345",
  "status": "completed",
  "chapters_audio": [
    {
      "chapter_title": "Kapitel 1",
      "audio_file": "audiofiles/meinbuch_001_kapitel-1.mp3",
      "duration_seconds": 245.5,
      "characters_count": 5000,
      "was_translated": true,
      "cost_usd": 0.15
    }
  ],
  "combined_audio_url": "audiofiles/meinbuch_complete.mp3",
  "total_duration_seconds": 3600.0,
  "total_cost_usd": 2.45,
  "usage_details": {
    "chapters_processed": 12,
    "translation_cost_usd": 0.50,
    "chapter_detection_cost_usd": 0.05,
    "tts_cost_usd": 1.90,
    "total_tokens": 50000,
    "total_characters": 60000
  }
}
```

### Admin Endpunkte

#### `GET /admin/usage`
Vollständiger Usage-Report (Admin only).

**Response:**
```json
{
  "users": [
    {
      "user_id": "dummy-user-001",
      "user_name": "Dummy User",
      "total_credits": "Infinity",
      "used_credits": 10.50,
      "remaining_credits": "Infinity",
      "total_jobs": 5,
      "total_cost_usd": 10.50
    }
  ],
  "jobs": [...],
  "total_system_cost_usd": 10.50,
  "generated_at": "2025-11-04T14:30:00"
}
```

#### `GET /admin/users/{user_id}/stats`
Statistiken für einen bestimmten User (Admin only).

#### `GET /admin/jobs/{job_id}`
Details zu einem bestimmten Job (Admin only).

## 💡 Beispiel-Workflow

```python
import requests

API_URL = "http://localhost:8000"
API_KEY = "dummy-api-key-12345"
headers = {"X-API-Key": API_KEY}

# 1. EPUB validieren
response = requests.post(
    f"{API_URL}/epub/validate",
    json={"file_path": "uploads/Blitzscaling.epub"},
    headers=headers
)
print(response.json())

# 2. Kapitel anzeigen
response = requests.post(
    f"{API_URL}/epub/chapters",
    json={"file_path": "uploads/Blitzscaling.epub"},
    headers=headers
)
chapters = response.json()
print(f"Gefunden: {chapters['total_chapters']} Kapitel")

# 3. Audiobook generieren (mit Auto-Detect und Übersetzung)
response = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/Blitzscaling.epub",
        "target_language": "de",
        "auto_detect_content": True,
        "tts_provider": "openai",
        "voice": "alloy"
    },
    headers=headers
)
result = response.json()
print(f"Audiobook generiert: {result['combined_audio_url']}")
print(f"Gesamtkosten: ${result['total_cost_usd']:.2f}")
```

## 🔄 Provider austauschen

Dank DAO Pattern können Sie einfach zwischen verschiedenen Providern wechseln:

### TTS Provider:
- **OpenAI** (Standard): Hochwertige Stimmen, $0.030 per 1K Zeichen
- **ElevenLabs**: Noch natürlichere Stimmen (in Entwicklung)
- **Lokal**: Kostenfrei, offline (in Entwicklung)

### LLM Provider:
- **OpenAI** (Standard): GPT-4o für beste Qualität
- **Groq**: Schneller und oft kostenlos

### Datenbank:
- **SQLite** (Standard): Einfach, keine externe DB nötig
- **Supabase/Appwrite**: Für Produktion (vorbereitet)

## 📊 Kostenmodell

Die API trackt automatisch alle Kosten:

- **OpenAI GPT-4o**: $0.005 / 1K Input Tokens, $0.015 / 1K Output Tokens
- **OpenAI TTS (tts-1-hd)**: $0.030 / 1K Zeichen
- **Groq**: Oft kostenlos

Alle Kosten werden pro Job erfasst und können über Admin-Endpunkte abgerufen werden.

## 🛠️ Entwicklung

### Datenbank zurücksetzen:
```bash
rm audiobook_tracker.db
python -m api.database.init_db
```

### Tests ausführen:
```bash
pytest tests/
```

## 📝 TODOs / Roadmap

- [ ] ElevenLabs TTS Implementation
- [ ] Lokales TTS Modell Integration
- [ ] Supabase/Appwrite Integration
- [ ] Background Jobs mit Celery
- [ ] WebSocket für Progress-Updates
- [ ] File Upload Endpunkt
- [ ] Audio-Streaming
- [ ] Rate Limiting
- [ ] User Registration
- [ ] Payment Integration

## 📚 Weitere Dokumentation

- **[ASYNC_JOBS.md](ASYNC_JOBS.md)** - Dokumentation des asynchronen Job-Systems
- **[LOGGING.md](LOGGING.md)** - Umfassende Logging-Dokumentation und Best Practices
- **[WORKFLOW_BEISPIEL.md](WORKFLOW_BEISPIEL.md)** - Beispiel-Workflows
- **API Docs**: http://localhost:8000/docs (interaktive OpenAPI Docs)
- **ReDoc**: http://localhost:8000/redoc (alternative API Dokumentation)

## 📄 Lizenz

MIT License

## 🤝 Beitragen

Contributions sind willkommen! Bitte erstellen Sie einen Pull Request.

## 📧 Support

Bei Fragen oder Problemen bitte ein Issue erstellen.

