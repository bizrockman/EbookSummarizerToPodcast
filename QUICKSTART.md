# 🚀 Schnellstart - eBook to Audiobook API

Eine Schritt-für-Schritt-Anleitung zum Starten der API.

## ⚡ Schnellstart in 5 Minuten

### 1. Dependencies installieren

```bash
pip install -r requirements_api.txt
```

### 2. Umgebungsvariablen setzen

Erstellen Sie eine `.env` Datei:

```env
OPENAI_API_KEY=sk-your-key-here
OPENAI_DEFAULT_MODEL=gpt-4o
LLM_MODEL_PROVIDER=openai
```

### 3. API starten

```bash
python start_api.py
```

Die API läuft jetzt auf: **http://localhost:8000**

### 4. API testen

Öffnen Sie in einem neuen Terminal:

```bash
python test_api.py
```

## 📚 Verwendung

### Mit der Swagger UI (im Browser):

1. Öffnen Sie: http://localhost:8000/docs
2. Klicken Sie auf "Authorize"
3. Geben Sie ein: `dummy-api-key-12345`
4. Testen Sie die Endpunkte!

### Mit Python:

```python
import requests

API_URL = "http://localhost:8000"
headers = {"X-API-Key": "dummy-api-key-12345"}

# EPUB validieren
response = requests.post(
    f"{API_URL}/epub/validate",
    json={"file_path": "uploads/meinbuch.epub"},
    headers=headers
)
print(response.json())

# Audiobook generieren
response = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/meinbuch.epub",
        "target_language": "de",
        "auto_detect_content": True,
        "tts_provider": "openai",
        "voice": "alloy"
    },
    headers=headers
)
result = response.json()
print(f"Audiobook: {result['combined_audio_url']}")
print(f"Kosten: ${result['total_cost_usd']:.2f}")
```

### Mit curl:

```bash
# EPUB validieren
curl -X POST "http://localhost:8000/epub/validate" \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "uploads/meinbuch.epub"}'

# Kapitel anzeigen
curl -X POST "http://localhost:8000/epub/chapters" \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"file_path": "uploads/meinbuch.epub"}'

# Audiobook generieren
curl -X POST "http://localhost:8000/audiobook/generate" \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "uploads/meinbuch.epub",
    "target_language": "de",
    "auto_detect_content": true,
    "tts_provider": "openai",
    "voice": "alloy"
  }'
```

## 🔑 API Keys

**Dummy User** (Testing):
```
X-API-Key: dummy-api-key-12345
```

**Admin User** (Reports):
```
X-API-Key: admin-api-key-67890
```

## 💡 Tipps

### 1. EPUB-Dateien hochladen

Legen Sie Ihre EPUB-Dateien in den `uploads/` Ordner:

```
uploads/
  └── meinbuch.epub
```

### 2. Generierte Audiobooks finden

Alle generierten Audio-Dateien werden hier gespeichert:

```
audiofiles/
  ├── meinbuch_001_kapitel-1.mp3
  ├── meinbuch_002_kapitel-2.mp3
  └── meinbuch_complete.mp3  ← Komplettes Audiobook
```

### 3. Kosten überwachen

Admin-Report abrufen:

```bash
curl -X GET "http://localhost:8000/admin/usage" \
  -H "X-API-Key: admin-api-key-67890"
```

### 4. Nur bestimmte Kapitel

```python
# Kapitel-Liste holen
response = requests.post(
    f"{API_URL}/epub/chapters",
    json={"file_path": "uploads/meinbuch.epub"},
    headers=headers
)
chapters = response.json()['chapters']

# Nur Kapitel 1 und 3
selected_hrefs = [chapters[0]['href'], chapters[2]['href']]

# Audiobook für ausgewählte Kapitel
response = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/meinbuch.epub",
        "chapters": selected_hrefs,
        "tts_provider": "openai",
        "voice": "alloy"
    },
    headers=headers
)
```

## 🎯 Beispiel-Workflow

```python
import requests
import time

API_URL = "http://localhost:8000"
headers = {"X-API-Key": "dummy-api-key-12345"}

# Schritt 1: Validieren
print("📖 Validiere EPUB...")
valid = requests.post(
    f"{API_URL}/epub/validate",
    json={"file_path": "uploads/Blitzscaling.epub"},
    headers=headers
).json()

if valid['is_valid']:
    print(f"✅ {valid['title']} von {valid['author']}")
    
    # Schritt 2: Kapitel anzeigen
    print("\n📚 Lade Kapitel...")
    chapters = requests.post(
        f"{API_URL}/epub/chapters",
        json={"file_path": "uploads/Blitzscaling.epub"},
        headers=headers
    ).json()
    print(f"✅ {chapters['total_chapters']} Kapitel gefunden")
    
    # Schritt 3: Audiobook generieren
    print("\n🎙️ Generiere Audiobook...")
    print("   (Dies kann einige Minuten dauern)")
    
    start = time.time()
    result = requests.post(
        f"{API_URL}/audiobook/generate",
        json={
            "file_path": "uploads/Blitzscaling.epub",
            "target_language": "de",
            "auto_detect_content": True,
            "tts_provider": "openai",
            "voice": "alloy"
        },
        headers=headers,
        timeout=600
    ).json()
    
    elapsed = time.time() - start
    
    print(f"\n✅ Fertig in {elapsed/60:.1f} Minuten!")
    print(f"   📊 {len(result['chapters_audio'])} Kapitel")
    print(f"   ⏱️  {result['total_duration_seconds']/60:.1f} Minuten Audio")
    print(f"   💰 ${result['total_cost_usd']:.2f} Kosten")
    print(f"   🎵 {result['combined_audio_url']}")
```

## ❓ Häufige Probleme

### "API ist nicht erreichbar"

Stellen Sie sicher, dass die API läuft:
```bash
python start_api.py
```

### "Ungültiger API Key"

Verwenden Sie einen der Test-API-Keys:
- User: `dummy-api-key-12345`
- Admin: `admin-api-key-67890`

### "EPUB-Datei nicht gefunden"

Legen Sie die EPUB-Datei in den `uploads/` Ordner und verwenden Sie den relativen Pfad:
```
"file_path": "uploads/meinbuch.epub"
```

### "OpenAI API Error"

Prüfen Sie Ihren OpenAI API Key in der `.env` Datei:
```env
OPENAI_API_KEY=sk-your-actual-key
```

## 📖 Weitere Informationen

- **Vollständige Dokumentation**: [README_API.md](README_API.md)
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎉 Viel Erfolg!

Bei Fragen oder Problemen bitte ein Issue erstellen.

