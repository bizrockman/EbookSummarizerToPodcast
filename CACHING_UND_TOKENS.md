# Caching & Token-Metriken für Kapitelanalyse

## 📦 Caching-System

Die Kapitelanalyse nutzt jetzt ein intelligentes Caching-System, um bereits durchgeführte Analysen wiederzuverwenden und Kosten zu sparen.

### Wie funktioniert das Caching?

1. **Cache-Hash-Generierung**: 
   - Für jede Analyse wird ein eindeutiger Hash erstellt basierend auf:
     - Dateipfad
     - Datei-Modifikationszeit
     - LLM Provider
   
2. **Cache-Lookup**:
   - Vor jeder Analyse prüft das System, ob bereits ein abgeschlossener Job mit dem gleichen Hash existiert
   - Bei einem **Cache Hit** wird das gespeicherte Ergebnis sofort zurückgegeben
   - Bei einem **Cache Miss** wird eine neue Analyse durchgeführt

3. **Vorteile**:
   - ⚡ **Sofortige Ergebnisse** bei wiederholten Analysen
   - 💰 **Keine LLM-Kosten** bei gecachten Analysen
   - 🔄 **Automatische Invalidierung** bei Dateiänderungen

### Beispiel: Cache Hit

```bash
# Erste Analyse (Cache Miss)
POST /epub/analyze-chapters
→ Dauert ~141s, kostet $0.0234

# Zweite Analyse der gleichen Datei (Cache Hit)
POST /epub/analyze-chapters
→ Dauert <1s, kostet $0.0000
```

### Cache-Invalidierung

Der Cache wird automatisch invalidiert, wenn:
- Die EPUB-Datei geändert wird (neue Modifikationszeit)
- Ein anderer LLM Provider verwendet wird
- Die Datei verschoben wird (neuer Pfad)

## 📊 Token-Metriken

Die API gibt jetzt detaillierte Token-Metriken für jede Kapitelanalyse zurück.

### Verfügbare Metriken

```json
{
  "input_tokens": 12450,     // Anzahl Input-Tokens (Prompt)
  "output_tokens": 235,      // Anzahl Output-Tokens (Response)
  "total_tokens": 12685,     // Gesamtzahl Tokens
  "analysis_cost_usd": 0.0234, // Kosten in USD
  "from_cache": false        // Ob aus Cache geladen
}
```

### Token-Kosten

Die Kosten werden basierend auf dem verwendeten LLM Provider berechnet:

| Provider | Model | Input (pro 1K) | Output (pro 1K) |
|----------|-------|----------------|-----------------|
| OpenAI   | GPT-4o | $0.0025 | $0.010 |
| Groq     | Llama-3 | $0.0000 | $0.0000 |

**Beispielrechnung** (OpenAI GPT-4o):
```
Input:  12,450 tokens × $0.0025 / 1,000 = $0.0311
Output:    235 tokens × $0.010  / 1,000 = $0.0024
Total:  $0.0335
```

## 🔍 API-Responses

### Status-Endpoint mit Token-Metriken

```http
GET /epub/analyze-chapters/status/{job_id}
```

**Response (Cache Miss - neue Analyse)**:
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "progress": 100,
  "current_step": "Analyse abgeschlossen",
  "input_tokens": 12450,
  "output_tokens": 235,
  "total_tokens": 12685,
  "analysis_cost_usd": 0.0234,
  "from_cache": false,
  "created_at": "2025-11-04T10:00:00",
  "started_at": "2025-11-04T10:00:01",
  "completed_at": "2025-11-04T10:02:22"
}
```

**Response (Cache Hit)**:
```json
{
  "job_id": "def-456",
  "status": "completed",
  "progress": 100,
  "current_step": "Aus Cache geladen (keine Analyse nötig)",
  "input_tokens": 0,
  "output_tokens": 0,
  "total_tokens": 0,
  "analysis_cost_usd": 0.0,
  "from_cache": true,
  "created_at": "2025-11-04T10:05:00",
  "started_at": "2025-11-04T10:05:00",
  "completed_at": "2025-11-04T10:05:00"
}
```

## 📈 Test-Client Ausgabe

Der `test_api.py` Client zeigt jetzt Cache- und Token-Informationen an:

### Cache Miss (neue Analyse)
```
⏳ Warte auf Abschluss...

  [2s] 10% - Analysiere Kapitel 1/47: Cover...
  [6s] 11% - Analysiere Kapitel 2/47: Title Page...
  ...

✅ Analyse abgeschlossen nach 141s!
   📊 Token-Metriken:
      - Input:  12,450 Tokens
      - Output: 235 Tokens
      - Total:  12,685 Tokens
      - Kosten: $0.0234
```

### Cache Hit
```
⏳ Warte auf Abschluss...

  [0s] 100% [📦 CACHE] - Aus Cache geladen (keine Analyse nötig)

✅ Analyse abgeschlossen nach 0s!
   📦 Aus Cache geladen - keine LLM-Kosten!
```

## 🛠️ Migration

Die Datenbankschema-Änderungen werden automatisch durch das Migrationsskript angewendet:

```bash
python api/database/migrate_add_cache_and_tokens.py
```

**Neue Felder in `analysis_jobs` Tabelle**:
- `content_hash` (TEXT, indexed) - Hash für Cache-Deduplizierung
- `input_tokens` (INTEGER) - Anzahl Input-Tokens
- `output_tokens` (INTEGER) - Anzahl Output-Tokens
- `total_tokens` (INTEGER) - Gesamtzahl Tokens

## 💡 Best Practices

### Kosten optimieren

1. **Nutzen Sie den Cache**: 
   - Führen Sie Testanalysen durch, bevor Sie große Batches starten
   - Das System cached automatisch, keine manuelle Konfiguration nötig

2. **Wählen Sie den richtigen Provider**:
   - **Groq**: Kostenlos, gut für Tests und Entwicklung
   - **OpenAI**: Höhere Qualität, besser für Produktionsumgebungen

3. **Überwachen Sie die Metriken**:
   - Prüfen Sie `total_tokens` und `analysis_cost_usd` regelmäßig
   - Bei hohen Kosten: Überprüfen Sie die Anzahl der Kapitel

### Cache-Verwaltung

- **Automatische Invalidierung**: Der Cache wird automatisch ungültig, wenn sich die Datei ändert
- **Manuelle Invalidierung**: Derzeit nicht implementiert, aber geplant für zukünftige Versionen
- **Cache-Dauer**: Jobs werden nach 7 Tagen automatisch gelöscht (konfigurierbar)

## 🔧 Technische Details

### Cache-Hash-Algorithmus

```python
def generate_content_hash(file_path: str, llm_provider: Optional[str]) -> str:
    mtime = os.path.getmtime(file_path)
    provider = llm_provider or "default"
    hash_input = f"{file_path}|{mtime}|{provider}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
```

### Token-Sammlung

Token-Informationen werden aus den LLM-Responses extrahiert:

```python
detection_result = llm_dao.detect_chapter_type(
    chapter_title=chapter.title,
    chapter_excerpt=excerpt
)

# Sammle Token-Metriken
tokens = detection_result.get("tokens", {})
total_input_tokens += tokens.get("input", 0)
total_output_tokens += tokens.get("output", 0)
```

## 📚 Siehe auch

- [README_API.md](README_API.md) - API-Dokumentation
- [ASYNC_JOBS.md](ASYNC_JOBS.md) - Asynchrone Job-Verarbeitung
- [LOGGING.md](LOGGING.md) - Logging-Middleware

