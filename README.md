# Ebook Audio Studio

Bücher in mehreren Tiefen lesen, übersetzen und anschließend als Hörbuch hören.
Der aktuelle Workflow liegt in **FastAPI + Next.js**; die Streamlit-Dateien sind Legacy.

## Lokal starten

Die vorhandene Python-Umgebung benötigt die Abhängigkeiten aus `requirements_api.txt`.
In `.env` müssen `OPENAI_API_KEY` und `OPENAI_DEFAULT_MODEL` gesetzt sein.
Für die Audiozusammenführung werden FFmpeg und ffprobe benötigt.

API, drei Worker-Threads und Frontend gemeinsam starten:

```powershell
.venv/Scripts/python.exe start_studio.py
```

Aufbau, getrennte Strategien, Konfiguration und Grenzen:
[BOOK_STUDIO.md](BOOK_STUDIO.md).

Alternativ Backend und Queue-Worker separat: `python start_dev.py`

Frontend, in `frontend`: `npm install` und anschließend `npm run dev`

Öffne [die Bibliothek](http://localhost:3000) oder
[eine neue Lesefassung](http://localhost:3000/workflow).
Die Frontend-Konfiguration nutzt `NEXT_PUBLIC_API_BASE_URL` und
`NEXT_PUBLIC_API_KEY`. Die bestehenden Dummy-Zugangsdaten dienen dem lokalen Betrieb.

## Ablauf

1. EPUB hochladen oder vorhandenes Buch wählen.
2. Lokale Vorauswahl der Inhaltskapitel anhand der Textvorschau prüfen und ändern.
3. Blockweise Lesefassung, thematische Kernfassung oder Original wählen.
4. Ziellänge, Sprache und optional Audio festlegen.
5. Auftrag im Hintergrund verarbeiten, Fortschritt und Verbrauch verfolgen.
6. Text lesen, Originalstellen vergleichen und Text oder MP3 herunterladen.

Fehlgeschlagene Aufträge können von ihrer Ergebnisseite fortgesetzt werden.
Erfolgreiche Text- und Audioschritte werden wiederverwendet. Der fertige Text
bleibt bei einem Audiofehler verfügbar. Kosten und Tokenverbrauch werden pro
Versuch erfasst. Jede neue Ziellänge greift auf die Originalkapitel zurück.

Historischer Ansatz, Forschungsquellen und Prüfverfahren:
[ABRIDGEMENT_DESIGN.md](ABRIDGEMENT_DESIGN.md).

Konkrete Prüfergebnisse, Buchprobe und noch offene Qualitätsnachweise:
[EVALUATION.md](EVALUATION.md).

Tests: `python -m unittest discover -s tests -v`

Frontend-Prüfung, in `frontend`: `npm run build`
