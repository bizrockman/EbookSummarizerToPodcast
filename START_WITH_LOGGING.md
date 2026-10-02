# 🚀 Quick Start: API mit Logging

## Schritt-für-Schritt Anleitung

### 1. API starten

```bash
python start_api.py
```

**Erwartete Ausgabe:**
```
============================================================
🚀 Starte eBook to Audiobook API
============================================================
✓ Datenbank-Tabellen erstellt
✓ Dummy User bereits vorhanden: Dummy User
✓ Admin User bereits vorhanden: Admin User

============================================================
✓ API bereit!
============================================================

📝 Dummy User API Key: dummy-api-key-12345
🔑 Admin User API Key: admin-api-key-67890
📊 Logging: Aktiviert (Console)

============================================================

2025-11-04 10:15:30 | INFO     | API erfolgreich gestartet
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 2. Test-Script ausführen (in neuem Terminal)

```bash
python test_logging.py
```

**Ihre Ausgabe:**
```
============================================================
  Test: API Logging Demo
============================================================

👀 Schauen Sie in der API-Console, um die Logs zu sehen!

1️⃣  Teste erfolgreichen Request (Health Check)...
   → Status: 200
   → Request-ID: a1b2c3d4

2️⃣  Teste Request mit API Key (EPUB Validation)...
   → Status: 200
   → Request-ID: b2c3d4e5

3️⃣  Teste 404 Error (nicht existierender Endpoint)...
   → Status: 404
   → Request-ID: c3d4e5f6

...
```

**API-Console (parallel):**
```
2025-11-04 10:16:45 | INFO     | [a1b2c3d4] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:45 | INFO     | [a1b2c3d4] ✅  200 GET    /health | 12ms

2025-11-04 10:16:46 | INFO     | [b2c3d4e5] ➡️  POST   /epub/validate | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:16:46 | INFO     | [b2c3d4e5] ✅  200 POST   /epub/validate | 45ms

2025-11-04 10:16:47 | INFO     | [c3d4e5f6] ➡️  GET    /does-not-exist | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:16:47 | WARNING  | [c3d4e5f6] ⚠️  404 GET    /does-not-exist | 8ms

2025-11-04 10:16:48 | INFO     | [d4e5f6g7] ➡️  POST   /epub/validate | IP: 127.0.0.1 | API Key: invalid-...
2025-11-04 10:16:48 | WARNING  | [d4e5f6g7] ⚠️  401 POST   /epub/validate | 12ms

2025-11-04 10:16:49 | INFO     | [e5f6g7h8] ➡️  POST   /epub/validate | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:16:49 | WARNING  | [e5f6g7h8] ⚠️  400 POST   /epub/validate | 23ms

2025-11-04 10:16:50 | INFO     | [f6g7h8i9] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:50 | INFO     | [f6g7h8i9] ✅  200 GET    /health | 8ms

2025-11-04 10:16:50 | INFO     | [g7h8i9j0] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:50 | INFO     | [g7h8i9j0] ✅  200 GET    /health | 7ms

2025-11-04 10:16:51 | INFO     | [h8i9j0k1] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:51 | INFO     | [h8i9j0k1] ✅  200 GET    /health | 9ms

2025-11-04 10:16:51 | INFO     | [i9j0k1l2] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:51 | INFO     | [i9j0k1l2] ✅  200 GET    /health | 6ms

2025-11-04 10:16:51 | INFO     | [j0k1l2m3] ➡️  GET    /health | IP: 127.0.0.1 | API Key: none
2025-11-04 10:16:51 | INFO     | [j0k1l2m3] ✅  200 GET    /health | 8ms
```

### 3. Test mit echtem Workflow (Chapter Analysis)

```bash
python test_api.py
```

**Wähle "ja" bei der Kapitelanalyse-Frage**

**API-Console zeigt:**
```
2025-11-04 10:17:00 | INFO     | [job00001] ➡️  POST   /epub/analyze-chapters | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:17:00 | INFO     | [job00001] ✅  200 POST   /epub/analyze-chapters | 234ms

2025-11-04 10:17:02 | INFO     | [job00002] ➡️  GET    /epub/analyze-chapters/status/abc-123-def | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:17:02 | INFO     | [job00002] ✅  200 GET    /epub/analyze-chapters/status/abc-123-def | 8ms

2025-11-04 10:17:04 | INFO     | [job00003] ➡️  GET    /epub/analyze-chapters/status/abc-123-def | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:17:04 | INFO     | [job00003] ✅  200 GET    /epub/analyze-chapters/status/abc-123-def | 7ms

2025-11-04 10:17:06 | INFO     | [job00004] ➡️  GET    /epub/analyze-chapters/status/abc-123-def | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:17:06 | INFO     | [job00004] ✅  200 GET    /epub/analyze-chapters/status/abc-123-def | 9ms

... (weitere Status-Polls alle 2 Sekunden)

2025-11-04 10:18:45 | INFO     | [job00025] ➡️  GET    /epub/analyze-chapters/result/abc-123-def | IP: 127.0.0.1 | API Key: dummy-ap...
2025-11-04 10:18:45 | INFO     | [job00025] ✅  200 GET    /epub/analyze-chapters/result/abc-123-def | 42ms
```

## 📊 Was Sie sehen sollten

### ✅ Erfolgreiche Requests
```
[request-id] ✅  200 METHOD /path | XXms
```

### ⚠️ Client Errors
```
[request-id] ⚠️  400 METHOD /path | XXms  (Bad Request)
[request-id] ⚠️  401 METHOD /path | XXms  (Unauthorized)
[request-id] ⚠️  404 METHOD /path | XXms  (Not Found)
```

### ❌ Server Errors
```
[request-id] ❌  500 METHOD /path | XXms
```

### 💥 Exceptions
```
[request-id] 💥  500 METHOD /path | XXms | Error: Some error message
Traceback (most recent call last):
  File "...", line ..., in ...
    ...
```

## 🔍 Request-ID Tracking

Jede Response enthält die Request-ID im Header:

```bash
curl -i http://localhost:8000/health

# Response Headers:
HTTP/1.1 200 OK
...
x-request-id: a1b2c3d4
...
```

Nutzen Sie diese ID um den Request in den Logs zu finden:
```bash
# Suche in Console-Output
grep "a1b2c3d4"

# Oder falls File-Logging aktiviert:
grep "a1b2c3d4" logs/api.log
```

## 🎨 Symbole Bedeutung

| Symbol | Bedeutung | Log Level |
|--------|-----------|-----------|
| ➡️ | Eingehender Request | INFO |
| ✅ | Erfolg (2xx) | INFO |
| ↩️ | Redirect (3xx) | INFO |
| ⚠️ | Client Error (4xx) | WARNING |
| ❌ | Server Error (5xx) | ERROR |
| 💥 | Exception | ERROR |

## 💡 Tipps

### 1. Logs in Echtzeit folgen

Wenn File-Logging aktiviert:
```bash
tail -f logs/api.log
```

### 2. Nur Errors anzeigen

```bash
tail -f logs/api.log | grep -E "(⚠️|❌|💥)"
```

### 3. Performance analysieren

```bash
# Finde langsame Requests (> 1000ms)
grep -E "[0-9]{4,}ms" logs/api.log
```

### 4. Requests pro Endpoint zählen

```bash
grep "➡️" logs/api.log | awk '{print $6}' | sort | uniq -c | sort -rn
```

## 🐛 Troubleshooting

### Keine Logs sichtbar?

1. **Prüfe Log-Level:**
   ```python
   import logging
   print(logging.getLogger("api").level)  # Sollte 20 (INFO) sein
   ```

2. **Setze explizit:**
   ```python
   # In api/main.py
   logging.getLogger("api").setLevel(logging.INFO)
   ```

### Zu viele Logs?

```python
# Reduziere auf WARNING (nur Errors)
logging.getLogger("api").setLevel(logging.WARNING)
```

### Logs in Datei speichern?

```python
# In api/main.py lifespan Funktion:
setup_file_logging("logs/api.log")
```

Erstelle vorher das Verzeichnis:
```bash
mkdir logs
```

## 📚 Weitere Informationen

- **[LOGGING.md](LOGGING.md)** - Vollständige Dokumentation
- **[ASYNC_JOBS.md](ASYNC_JOBS.md)** - Async Job System
- **[README_API.md](README_API.md)** - API Hauptdokumentation
- **API Docs**: http://localhost:8000/docs

## ✨ Das war's!

Die Logging-Middleware ist jetzt aktiv und trackt alle Ihre API-Requests automatisch! 🎉

