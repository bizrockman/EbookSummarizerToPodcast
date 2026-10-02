# 📊 API Logging System

## Übersicht

Die API verfügt über eine umfassende Logging-Middleware, die alle Requests und Responses trackt.

## ✨ Features

- ✅ **Request Tracking**: Loggt alle eingehenden Requests mit Details
- ✅ **Response Tracking**: Loggt Status Codes und Antwortzeiten
- ✅ **Request IDs**: Jeder Request erhält eine eindeutige ID für Tracking
- ✅ **Farbige Ausgabe**: Verschiedene Symbole für verschiedene Status Codes
- ✅ **Performance Monitoring**: Zeigt Dauer jedes Requests in Millisekunden
- ✅ **Error Logging**: Detailliertes Logging bei Exceptions
- ✅ **API Key Tracking**: Zeigt welcher User den Request macht (anonymisiert)
- ✅ **Optional: File Logging**: Zusätzlich zur Console auch in Datei loggen

## 📝 Log-Format

### Eingehender Request
```
2025-11-04 10:15:32 | INFO     | [abc123ef] ➡️  POST   /epub/analyze-chapters | IP: 127.0.0.1 | API Key: dummy-ap...
```

### Erfolgreiche Response
```
2025-11-04 10:15:35 | INFO     | [abc123ef] ✅  200 POST   /epub/analyze-chapters | 3240ms
```

### Fehler Response
```
2025-11-04 10:15:35 | WARNING  | [abc123ef] ⚠️  404 GET    /epub/unknown | 12ms
2025-11-04 10:15:35 | ERROR    | [abc123ef] ❌  500 POST   /epub/analyze-chapters | 1523ms
```

### Exception mit Stack Trace
```
2025-11-04 10:15:35 | ERROR    | [abc123ef] 💥  500 POST   /epub/analyze-chapters | 1523ms | Error: File not found
Traceback (most recent call last):
  ...
```

## 📊 Status-Symbole

| Symbol | Status Codes | Bedeutung |
|--------|-------------|-----------|
| ✅ | 200-299 | Erfolgreiche Requests |
| ↩️ | 300-399 | Redirects |
| ⚠️ | 400-499 | Client Errors (Bad Request, etc.) |
| ❌ | 500-599 | Server Errors |
| 💥 | Exception | Unbehandelte Exceptions |
| ➡️ | - | Eingehender Request |

## 🔧 Konfiguration

### Standard-Logging (Console)

Die Logging-Middleware ist bereits aktiviert. Keine zusätzliche Konfiguration nötig!

```python
# api/main.py
from api.middleware.logging_middleware import LoggingMiddleware

app.add_middleware(LoggingMiddleware)
```

### File Logging aktivieren

Um zusätzlich in eine Datei zu loggen:

```python
# api/main.py
from api.middleware.logging_middleware import setup_file_logging

# In der lifespan Funktion:
setup_file_logging("logs/api.log")
```

**Erstelle vorher das Verzeichnis:**
```bash
mkdir logs
```

### Log-Level anpassen

```python
import logging

# Für weniger Logs (nur Warnings und Errors)
logging.getLogger("api").setLevel(logging.WARNING)

# Für mehr Details (inkl. Debug-Infos)
logging.getLogger("api").setLevel(logging.DEBUG)

# Standard ist INFO
logging.getLogger("api").setLevel(logging.INFO)
```

## 🔍 Detailliertes Logging (Optional)

Für noch mehr Details (z.B. beim Debugging):

```python
from api.middleware.logging_middleware import DetailedLoggingMiddleware

# Ersetze LoggingMiddleware mit:
app.add_middleware(
    DetailedLoggingMiddleware,
    log_headers=True,        # Loggt Request/Response Headers
    log_response_body=False  # Loggt Response Body (Vorsicht bei großen Responses!)
)
```

**Ausgabe mit detailliertem Logging:**
```
2025-11-04 10:15:32 | INFO  | [abc123ef] ➡️  POST /epub/analyze-chapters
2025-11-04 10:15:32 | DEBUG | [abc123ef]     Client: 127.0.0.1:54321
2025-11-04 10:15:32 | DEBUG | [abc123ef]     User-Agent: python-requests/2.31.0
2025-11-04 10:15:32 | DEBUG | [abc123ef]     Headers: {
  "host": "localhost:8000",
  "x-api-key": "dummy-ap...",
  "content-type": "application/json",
  ...
}
2025-11-04 10:15:32 | DEBUG | [abc123ef]     Body: {"file_path": "uploads/book.epub"}
2025-11-04 10:15:35 | INFO  | [abc123ef] ✅  200 | 3240ms
```

## 📋 Beispiele

### Normaler Request Flow

**Client:**
```bash
curl -X POST http://localhost:8000/epub/validate \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "uploads/book.epub"}'
```

**Server Logs:**
```
2025-11-04 10:15:32 | INFO | [a1b2c3d4] ➡️  POST   /epub/validate | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:15:32 | INFO | [a1b2c3d4] ✅  200 POST   /epub/validate | 45ms
```

### Async Job mit Polling

**Client:**
```python
# 1. Starte Job
response = requests.post("/epub/analyze-chapters", ...)
job_id = response.json()['job_id']

# 2. Prüfe Status mehrfach
for i in range(10):
    status = requests.get(f"/analyze-chapters/status/{job_id}", ...)
    time.sleep(2)

# 3. Hole Ergebnis
result = requests.get(f"/analyze-chapters/result/{job_id}", ...)
```

**Server Logs:**
```
2025-11-04 10:15:32 | INFO | [req001] ➡️  POST   /epub/analyze-chapters | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:15:32 | INFO | [req001] ✅  200 POST   /epub/analyze-chapters | 123ms

2025-11-04 10:15:34 | INFO | [req002] ➡️  GET    /epub/analyze-chapters/status/abc-123 | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:15:34 | INFO | [req002] ✅  200 GET    /epub/analyze-chapters/status/abc-123 | 8ms

2025-11-04 10:15:36 | INFO | [req003] ➡️  GET    /epub/analyze-chapters/status/abc-123 | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:15:36 | INFO | [req003] ✅  200 GET    /epub/analyze-chapters/status/abc-123 | 7ms

...

2025-11-04 10:16:12 | INFO | [req015] ➡️  GET    /epub/analyze-chapters/result/abc-123 | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:16:12 | INFO | [req015] ✅  200 GET    /epub/analyze-chapters/result/abc-123 | 42ms
```

### Fehlerfall

**Client:**
```python
requests.post("/epub/analyze-chapters", 
              json={"file_path": "/non/existent/file.epub"})
```

**Server Logs:**
```
2025-11-04 10:15:32 | INFO    | [err001] ➡️  POST   /epub/analyze-chapters | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:15:32 | WARNING | [err001] ⚠️  400 POST   /epub/analyze-chapters | 23ms
```

### Unauthorized Request

**Client:**
```python
requests.post("/epub/analyze-chapters", 
              headers={"X-API-Key": "invalid-key"})
```

**Server Logs:**
```
2025-11-04 10:15:32 | INFO    | [unauth1] ➡️  POST   /epub/analyze-chapters | IP: 127.0.0.1 | API Key: invalid-...
2025-11-04 10:15:32 | WARNING | [unauth1] ⚠️  401 POST   /epub/analyze-chapters | 12ms
```

## 🔎 Log-Analyse

### Request-ID für Debugging

Jede Response enthält die Request-ID im Header:

```bash
curl -i http://localhost:8000/health

HTTP/1.1 200 OK
...
x-request-id: a1b2c3d4
...
```

So können Sie einen spezifischen Request in den Logs finden:

```bash
# Suche nach Request-ID in Logs
grep "a1b2c3d4" logs/api.log
```

### Performance-Analyse

Finde langsame Requests:

```bash
# Requests > 1000ms
grep -E "[0-9]{4,}ms" logs/api.log

# Top 10 langsamste Requests
grep -oE "[0-9]+ms" logs/api.log | sort -nr | head -10
```

### Error-Analyse

Finde Fehler:

```bash
# Alle 4xx und 5xx Errors
grep -E "(⚠️|❌)" logs/api.log

# Nur 5xx Errors
grep "❌" logs/api.log

# Exceptions mit Stack Trace
grep -A 10 "💥" logs/api.log
```

## 📈 Monitoring

### Real-Time Monitoring

```bash
# Folge Logs in Echtzeit
tail -f logs/api.log

# Nur Errors anzeigen
tail -f logs/api.log | grep -E "(⚠️|❌|💥)"

# Mit Farben (Linux/Mac)
tail -f logs/api.log | grep --color=always -E "ERROR|WARNING|✅|⚠️|❌|💥|$"
```

### Log-Rotation (Produktion)

Für Produktion, verwende `logrotate` oder Python's `RotatingFileHandler`:

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=10_000_000,  # 10 MB
    backupCount=5         # Behalte 5 Backup-Dateien
)
logger.addHandler(handler)
```

## 🎨 Anpassung

### Custom Log-Format

```python
# In logging_middleware.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
```

### Verschiedene Log-Level für verschiedene Module

```python
# Root Logger auf WARNING
logging.getLogger().setLevel(logging.WARNING)

# Nur API Logger auf INFO
logging.getLogger("api").setLevel(logging.INFO)

# Database Logger auf DEBUG
logging.getLogger("sqlalchemy").setLevel(logging.DEBUG)
```

## 🚀 Best Practices

1. **Request-IDs nutzen**: Verwenden Sie die `X-Request-ID` zum Debuggen
2. **Log-Level angemessen wählen**: 
   - Entwicklung: `DEBUG`
   - Produktion: `INFO` oder `WARNING`
3. **File Logging in Produktion**: Speichern Sie Logs für Analyse
4. **Log Rotation**: Verhindern Sie volle Festplatten
5. **Sensitive Daten**: API Keys werden automatisch anonymisiert
6. **Monitoring**: Nutzen Sie Tools wie Grafana/Prometheus für Visualisierung

## 🐛 Troubleshooting

### Logs erscheinen nicht

```python
# Prüfe Log-Level
import logging
print(logging.getLogger("api").level)  # Sollte 20 (INFO) sein

# Setze explizit
logging.getLogger("api").setLevel(logging.DEBUG)
```

### Zu viele Logs

```python
# Reduziere Log-Level
logging.getLogger("api").setLevel(logging.WARNING)

# Oder deaktiviere DetailedLoggingMiddleware
```

### Performance-Probleme durch Logging

- Verwenden Sie nicht `DetailedLoggingMiddleware` in Produktion
- Deaktivieren Sie `log_response_body`
- Verwenden Sie asynchrones Logging

## 📚 Weiterführende Informationen

- **FastAPI Middleware**: https://fastapi.tiangolo.com/tutorial/middleware/
- **Python Logging**: https://docs.python.org/3/library/logging.html
- **Structured Logging**: Für JSON-Logs (z.B. mit `python-json-logger`)

