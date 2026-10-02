# 🎯 Workflow-Beispiel: Intelligente Kapitelauswahl

## Problem gelöst!

**Vorher**: Das Test-Script hat immer das erste Kapitel genommen (oft "Cover" oder "Title Page")  
**Jetzt**: Neuer Endpunkt analysiert alle Kapitel mit KI und wählt nur relevante aus!

## Neuer Workflow

### Option 1: Automatische Analyse während Generierung

```python
import requests

API_URL = "http://localhost:8000"
headers = {"X-API-Key": "dummy-api-key-12345"}

# Generiere Audiobook mit automatischer Kapitelerkennung
response = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/Blitzscaling.epub",
        "auto_detect_content": True,  # ← KI filtert automatisch
        "target_language": "de",
        "tts_provider": "openai",
        "voice": "alloy"
    },
    headers=headers
)
```

**Ergebnis**: Generiert nur Audio für echte Kapitel, überspringt Cover, Vorwort, etc.

---

### Option 2: Vorab-Analyse mit neuem Endpunkt (EMPFOHLEN!)

```python
import requests

API_URL = "http://localhost:8000"
headers = {"X-API-Key": "dummy-api-key-12345"}

# Schritt 1: Analysiere Kapitel VORAB
print("🤖 Analysiere Kapitel...")
analysis_response = requests.post(
    f"{API_URL}/epub/analyze-chapters",
    json={
        "file_path": "uploads/Blitzscaling.epub",
        "llm_provider": "openai"
    },
    headers=headers
)

analysis = analysis_response.json()

print(f"✅ Gefunden:")
print(f"  - {analysis['content_count']} Inhalts-Kapitel")
print(f"  - {analysis['supplement_count']} Zusatzmaterial")
print(f"  - Kosten: ${analysis['analysis_cost_usd']:.4f}")

# Schritt 2: Zeige dem User, was verarbeitet wird
print("\n📚 Diese Kapitel werden zu Audio:")
for chapter in analysis['content_chapters']:
    print(f"  ✅ {chapter['title']}")

print("\n🗑️ Diese werden übersprungen:")
for chapter in analysis['supplement_chapters']:
    print(f"  ❌ {chapter['title']}")

# Schritt 3: User kann bestätigen oder anpassen
# (Optional: User kann Kapitel manuell hinzufügen/entfernen)

# Schritt 4: Generiere Audio nur für ausgewählte Kapitel
content_hrefs = [ch['href'] for ch in analysis['content_chapters']]

print("\n🎙️ Generiere Audiobook...")
audiobook_response = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/Blitzscaling.epub",
        "chapters": content_hrefs,  # ← Nutze analysierte Kapitel
        "auto_detect_content": False,  # ← Nicht nochmal analysieren!
        "target_language": "de",
        "tts_provider": "openai",
        "voice": "alloy"
    },
    headers=headers
)

result = audiobook_response.json()
print(f"✅ Fertig! Audio: {result['combined_audio_url']}")
print(f"💰 Gesamtkosten: ${result['total_cost_usd']:.2f}")
```

---

## Vorteile des neuen Endpunkts

### ✅ Transparenz
- User sieht VORAB, welche Kapitel verarbeitet werden
- Kann Auswahl überprüfen und anpassen

### ✅ Kontrolle
- User kann einzelne Kapitel hinzufügen/entfernen
- Keine Überraschungen bei der Abrechnung

### ✅ Effizienz
- Analyse erfolgt nur einmal
- Ergebnis kann wiederverwendet werden

### ✅ Kostenersparnis
- Vermeidet Audio-Generierung für irrelevante Kapitel
- Analysis kostet $0.01-0.10, spart aber oft $1-5 bei TTS

---

## Beispiel: Typische Buchstruktur

```
📖 Blitzscaling.epub (47 Kapitel)

🗑️ Übersprungen (KI erkannt):
  ❌ Cover
  ❌ Title Page
  ❌ Copyright
  ❌ Contents
  ❌ Foreword by Bill Gates
  ❌ About the Author
  ❌ Index

✅ Verarbeitet (echte Kapitel):
  ✅ Introduction
  ✅ Chapter 1: What Is Blitzscaling?
  ✅ Chapter 2: Business Model Innovation
  ✅ Chapter 3: Strategy Innovation
  ...
  ✅ Conclusion

Ergebnis: 39 statt 47 Kapitel → 17% Kostenersparnis!
```

---

## API Endpunkte

### POST `/epub/analyze-chapters`

Analysiert alle Kapitel mit KI und klassifiziert sie.

**Request:**
```json
{
  "file_path": "uploads/buch.epub",
  "llm_provider": "openai"
}
```

**Response:**
```json
{
  "all_chapters": [...],
  "content_chapters": [...],
  "supplement_chapters": [...],
  "total_chapters": 47,
  "content_count": 39,
  "supplement_count": 8,
  "analysis_cost_usd": 0.05
}
```

---

## Curl Beispiel

```bash
# 1. Analysiere Kapitel
curl -X POST "http://localhost:8000/epub/analyze-chapters" \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "uploads/Blitzscaling.epub"
  }'

# 2. Nutze Ergebnis für Audiobook-Generierung
# (content_hrefs aus Schritt 1 extrahieren)

curl -X POST "http://localhost:8000/audiobook/generate" \
  -H "X-API-Key: dummy-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "uploads/Blitzscaling.epub",
    "chapters": ["chapter1.xhtml", "chapter2.xhtml", ...],
    "auto_detect_content": false,
    "tts_provider": "openai",
    "voice": "alloy"
  }'
```

---

## Matching nach Kapitelnamen

Sie können auch Kapitel nach Namen filtern:

```python
# Alle Kapitel holen
all_chapters = requests.post(
    f"{API_URL}/epub/chapters",
    json={"file_path": "uploads/buch.epub"},
    headers=headers
).json()['chapters']

# Filtern nach Namen (z.B. nur "Chapter" im Titel)
selected_chapters = [
    ch['href'] for ch in all_chapters 
    if 'chapter' in ch['title'].lower()
]

# Audio generieren
audiobook = requests.post(
    f"{API_URL}/audiobook/generate",
    json={
        "file_path": "uploads/buch.epub",
        "chapters": selected_chapters,
        "auto_detect_content": False
    },
    headers=headers
)
```

---

## Integration in Test-Script

Das Test-Script wurde aktualisiert:

```bash
python test_api.py
```

**Neuer Ablauf:**
1. ✅ EPUB validieren
2. ✅ Kapitel extrahieren
3. 🆕 **Kapitel analysieren** (optional)
4. ✅ Audiobook generieren (nutzt analysierte Kapitel)
5. ✅ Admin-Report anzeigen

---

## Zusammenfassung

Der neue `/epub/analyze-chapters` Endpunkt gibt Ihnen volle Kontrolle über die Kapitelauswahl:

1. **Transparent**: Sehen Sie vorab, was verarbeitet wird
2. **Kontrolliert**: Passen Sie die Auswahl an
3. **Effizient**: Analysieren Sie nur einmal
4. **Kostensparend**: Vermeiden Sie unnötige TTS-Generierung

**Empfohlener Workflow**: Immer erst analysieren, dann generieren! 🎯

