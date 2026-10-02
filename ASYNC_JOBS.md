# Asynchrones Job-System für Kapitelanalyse

## 📋 Übersicht

Das neue asynchrone Job-System ermöglicht es, zeitintensive Kapitelanalysen im Hintergrund auszuführen, ohne dass der Client auf eine Antwort warten muss.

## 🚀 Vorteile

- ✅ **Keine Timeouts**: Jobs können beliebig lange laufen
- ✅ **Fortschritts-Tracking**: Echtzeit-Updates über den Job-Status
- ✅ **Skalierbar**: Mehrere Jobs können parallel laufen
- ✅ **Zuverlässig**: Status wird in Datenbank persistiert
- ✅ **Fehlerbehandlung**: Detaillierte Fehlerinformationen bei Fehlschlägen

## 🔄 Workflow

### 1. Job starten

```python
import requests

response = requests.post(
    "http://localhost:8000/epub/analyze-chapters",
    json={"file_path": "uploads/buch.epub"},
    headers={"X-API-Key": "your-api-key"}
)

job_data = response.json()
job_id = job_data['job_id']
print(f"Job gestartet: {job_id}")
print(f"Geschätzte Dauer: {job_data['estimated_time_seconds']}s")
```

**Response:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "pending",
  "message": "Analyse-Job wurde gestartet...",
  "estimated_time_seconds": 90
}
```

### 2. Status abfragen (Polling)

```python
import time

while True:
    status_response = requests.get(
        f"http://localhost:8000/epub/analyze-chapters/status/{job_id}",
        headers={"X-API-Key": "your-api-key"}
    )
    
    status_data = status_response.json()
    print(f"{status_data['progress']}% - {status_data['current_step']}")
    
    if status_data['status'] in ['completed', 'failed']:
        break
    
    time.sleep(2)  # Alle 2 Sekunden prüfen
```

**Response während Verarbeitung:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "processing",
  "progress": 45,
  "current_step": "Analysiere Kapitel 12/27: Introduction to AI...",
  "created_at": "2025-11-04T10:00:00",
  "started_at": "2025-11-04T10:00:01",
  "completed_at": null,
  "error_message": null,
  "analysis_cost_usd": 0.0
}
```

### 3. Ergebnis abrufen

```python
result_response = requests.get(
    f"http://localhost:8000/epub/analyze-chapters/result/{job_id}",
    headers={"X-API-Key": "your-api-key"}
)

result_data = result_response.json()

if result_data['status'] == 'completed':
    result = result_data['result']
    print(f"Gefunden: {result['content_count']} Inhalts-Kapitel")
    
    # Verwende content_chapters für weitere Verarbeitung
    content_hrefs = [ch['href'] for ch in result['content_chapters']]
```

**Response bei Erfolg:**
```json
{
  "job_id": "abc-123-def-456",
  "status": "completed",
  "result": {
    "all_chapters": [...],
    "content_chapters": [...],
    "supplement_chapters": [...],
    "total_chapters": 27,
    "content_count": 22,
    "supplement_count": 5,
    "analysis_cost_usd": 0.0523
  },
  "error_message": null
}
```

## 📊 Job-Status-Werte

| Status | Beschreibung |
|--------|--------------|
| `pending` | Job wartet auf Verarbeitung |
| `processing` | Job wird gerade verarbeitet |
| `completed` | Job erfolgreich abgeschlossen |
| `failed` | Job ist fehlgeschlagen |

## 🔧 API-Endpunkte

### POST `/epub/analyze-chapters`
Startet einen neuen Analyse-Job.

**Request:**
```json
{
  "file_path": "uploads/buch.epub",
  "llm_provider": "openai"  // optional
}
```

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "pending",
  "message": "...",
  "estimated_time_seconds": 90
}
```

### GET `/epub/analyze-chapters/status/{job_id}`
Hole aktuellen Status eines Jobs.

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "processing",
  "progress": 45,
  "current_step": "...",
  "created_at": "...",
  "started_at": "...",
  "completed_at": null,
  "error_message": null,
  "analysis_cost_usd": 0.0
}
```

### GET `/epub/analyze-chapters/result/{job_id}`
Hole Ergebnis eines abgeschlossenen Jobs.

**Response:**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "result": {
    "all_chapters": [...],
    "content_chapters": [...],
    ...
  },
  "error_message": null
}
```

## 💡 Best Practices

### 1. Polling-Intervall
- Empfohlen: **2-5 Sekunden**
- Zu kurz (<1s): Unnötige Server-Last
- Zu lang (>10s): Schlechte UX

### 2. Timeout-Handling
```python
import time

max_wait = 300  # 5 Minuten
start = time.time()

while time.time() - start < max_wait:
    status = get_status(job_id)
    if status['status'] in ['completed', 'failed']:
        break
    time.sleep(2)
else:
    print("Timeout: Job dauert zu lange")
```

### 3. Fehlerbehandlung
```python
result = get_result(job_id)

if result['status'] == 'failed':
    print(f"Fehler: {result['error_message']}")
elif result['status'] == 'completed':
    if result['result']:
        # Verarbeite Ergebnis
        process_chapters(result['result']['content_chapters'])
    else:
        print("Ergebnis nicht verfügbar")
```

### 4. UI/UX
- Zeige **Progress-Bar** mit `progress` Wert
- Zeige **aktuellen Schritt** mit `current_step`
- Ermögliche **Abbruch** (Job läuft trotzdem im Hintergrund)
- Speichere **job_id** für späteren Abruf

## 🗄️ Datenbank

Die Jobs werden in der `analysis_jobs` Tabelle gespeichert:

```sql
CREATE TABLE analysis_jobs (
    job_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    llm_provider TEXT,
    status TEXT DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    current_step TEXT,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result_data TEXT,  -- JSON
    error_message TEXT,
    analysis_cost_usd REAL DEFAULT 0.0
);
```

## 🧹 Cleanup

Alte Jobs werden nicht automatisch gelöscht. Implementieren Sie ein Cleanup-Script:

```python
from api.services.job_service import get_job_service
from api.database.connection import get_db

with get_db() as db:
    job_service = get_job_service()
    job_service.cleanup_old_jobs(db, days=7)  # Lösche Jobs älter als 7 Tage
```

## 🔐 Sicherheit

- Jobs sind **user-spezifisch**: User können nur eigene Jobs abrufen
- **Admin-User** können alle Jobs sehen
- Job-IDs sind **UUIDs**: Nicht rate-bar

## 📝 Beispiel: Vollständiger Workflow

```python
import requests
import time

API_URL = "http://localhost:8000"
API_KEY = "your-api-key"
headers = {"X-API-Key": API_KEY}

# 1. Starte Job
response = requests.post(
    f"{API_URL}/epub/analyze-chapters",
    json={"file_path": "uploads/book.epub"},
    headers=headers
)
job_id = response.json()['job_id']
print(f"Job gestartet: {job_id}")

# 2. Warte auf Abschluss mit Progress-Anzeige
while True:
    status = requests.get(
        f"{API_URL}/epub/analyze-chapters/status/{job_id}",
        headers=headers
    ).json()
    
    print(f"[{status['progress']}%] {status['current_step']}")
    
    if status['status'] == 'completed':
        print("✅ Fertig!")
        break
    elif status['status'] == 'failed':
        print(f"❌ Fehler: {status['error_message']}")
        exit(1)
    
    time.sleep(2)

# 3. Hole Ergebnis
result = requests.get(
    f"{API_URL}/epub/analyze-chapters/result/{job_id}",
    headers=headers
).json()

chapters = result['result']['content_chapters']
print(f"Gefunden: {len(chapters)} Kapitel")

# 4. Verwende für Audiobook-Generierung
content_hrefs = [ch['href'] for ch in chapters]
requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/book.epub",
        "chapters": content_hrefs,
        "auto_detect_content": False  # Nicht nochmal analysieren!
    },
    headers=headers
)
```

## 🔄 Migration vom alten Sync-Endpoint

**Alt (Sync mit Timeout-Risiko):**
```python
response = requests.post(
    "/epub/analyze-chapters",
    json={"file_path": "..."},
    timeout=120  # ⚠️ Kann timeout bei vielen Kapiteln
)
result = response.json()  # Direkt Ergebnis
```

**Neu (Async ohne Timeout):**
```python
# 1. Starte Job
response = requests.post("/epub/analyze-chapters", ...)
job_id = response.json()['job_id']

# 2. Warte auf Abschluss
while get_status(job_id)['status'] not in ['completed', 'failed']:
    time.sleep(2)

# 3. Hole Ergebnis
result = get_result(job_id)['result']
```

## 📚 Weitere Informationen

- **API Docs**: http://localhost:8000/docs
- **README**: README_API.md
- **Test-Script**: test_api.py

