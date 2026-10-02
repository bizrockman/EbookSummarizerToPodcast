# Ebook Audio Studio

Die WebApp verarbeitet einen EPUB-Auftrag mit optionaler Kürzung, Übersetzung
und Audio. Kapitel werden in EPUB-Lesereihenfolge erkannt. Die lokale Vorauswahl
schließt eindeutig benanntes Zusatzmaterial aus, behält Einleitungen bei und
zeigt Textvorschau, Wortzahl und Auswahlgrund. Nutzer können die Auswahl ändern.
Die Vorauswahl ist eine Heuristik, keine inhaltliche Qualitätsprüfung.

## Start

Abhängigkeiten in der vorhandenen Python-Umgebung und `frontend/node_modules`
installieren. `ffmpeg` und `ffprobe` müssen für Audio im PATH liegen. Schlüssel
bleiben in `.env`; der Browser erhält keinen OpenAI-Schlüssel.
API und Worker brauchen ausgehenden HTTPS-Zugriff auf OpenAI. Beim Start aus einer
eingeschränkten Entwicklungsumgebung müssen beide Prozesse diese Berechtigung
erhalten. Die Modellprüfung vor dem Einreihen ist ein lesender API-Aufruf ohne
Buchtext und ohne generierte Tokens. Sie prüft Modellzugang und Verbindung,
garantiert aber nicht die Unterstützung aller Generierungsoptionen.

```powershell
.venv/Scripts/python.exe start_studio.py
```

WebApp: `http://127.0.0.1:3000`, API: `http://127.0.0.1:8000/docs`.
Standardmäßig arbeiten drei Huey-Threads an verschiedenen Aufträgen. Ein Auftrag
verarbeitet seine Schritte nacheinander und speichert fertige Schritte lokal.
Ein Start mit bestehenden Warteschlangen verarbeitet deren wartende Aufträge.
Mit `--workers 0` öffnet sich die App ohne Verarbeitung der Warteschlange.
Für einen getrennten Testbetrieb:

```powershell
.venv/Scripts/python.exe start_studio.py --runtime evaluation/book-sample/studio-live --api-port 8001 --web-port 3001
```

## Strategien und Dependency Injection

`api/services/production/contracts.py` definiert Text- und Audio-Provider sowie
Kürzungsstrategien als schmale Ports. `providers.py` ist der Composition Root mit
Provider-Factories und einem StrategyRegistry. `BookPipeline` erhält Strategie,
JSON-Generator, Audio-Provider, UsageRecorder, Audio-Assembler, Fortschritt,
Abbruchprüfung und Textspeicherung über den Konstruktor. Die Domäne importiert
kein OpenAI-SDK. Der Worker kann mit anderen Factories ausgeführt werden.

- `BlockReadingStrategy`: Absatz- und Satzzerlegung aus dem Experiment, etwa
  900 Wörter pro Block, proportionales Kürzungsbudget, maximal eine Längenkorrektur
  pro Block. Vorheriges Fassungende und folgendes Quellenfragment helfen bei
  Übergängen. Kein Embedding und keine semantische Redundanzprüfung.
- `TopicCoreStrategy`: Themenkarten mit konkreten Aussagen und Beispielen,
  hierarchische Zusammenführung von maximal sechs Karten, abschließend eine
  Kernfassung mit Zielwortzahl. Die Strategie ist vollständig LLM-getrieben;
  keine Embeddings. Die erste Version benötigt noch vergleichende Qualitätsläufe.
- `original`: Kürzung umgehen, ausgewählten Text direkt ausgeben, übersetzen
  und/oder vertonen. Reiner Originalexport braucht keinen API-Aufruf.

Neue Strategie registrieren, ohne Worker oder Pipeline zu ändern. Für andere
Provider entsprechende Adapter implementieren und ihre Factories registrieren.
ElevenLabs und lokale Modelle werden noch nicht als verfügbare Anbieter angezeigt.
Die aktuelle Oberfläche bietet die zwei ersten Strategien und Original an;
eine zusätzliche Strategie benötigt auch eine passende UI-Auswahl und Optionen.

Übersetzung folgt der Kürzung und bewahrt Beispiele, Ton und idiomatische
Formulierungen. Die Fassung vor der Übersetzung bleibt vergleichbar. Audio liest
exakt den fertigen Text. Begrenzte Audio-Chunks erhalten alle Zeichen; ffmpeg
verbindet die MP3-Dateien. Text ist schon vor der Vertonung verfügbar.

## Jobs und Wiederaufnahme

`POST /productions` erstellt einen persistenten `book_processing`-Job. Eine
identische vorhandene Auswahl wird wieder geöffnet. `GET /productions/{job_id}`
liefert Status, Konfiguration, Ergebnis und Verbrauch. `DELETE /jobs/{job_id}`
bricht ab. Ein laufender API-Aufruf kann noch Kosten verursachen; danach beginnt
kein weiterer Schritt. Ein atomarer Statuswechsel verhindert doppelte Ausführung
desselben Queue-Jobs.

`POST /productions/{job_id}/retry` setzt fehlgeschlagene oder abgebrochene Jobs
als neuen Versuch mit denselben Checkpoints fort. Verbrauch gehört zum jeweiligen
Versuch; die UI verlinkt den vorherigen. Gültige Textantworten und fertige Audio-
Chunks werden wiederverwendet. Ungültige Antworten werden nicht gecacht. Checkpoints
sind innerhalb eines Auftrags bzw. seiner Wiederaufnahme wiederverwendbar;
verschiedene Ziellängen teilen noch keinen allgemeinen Kapitelcache.
Mit optionalem JSON `{"text_model":"gpt-6.1-sol"}` lässt sich beim Fortsetzen ein
falscher Modellname korrigieren. Der alte Versuch behält seine Konfiguration.
Checkpoints enthalten den Modellnamen im Schlüssel, sodass Antworten eines
anderen Modells nicht versehentlich übernommen werden.

Beim API-Start werden laufende Jobs standardmäßig nicht automatisch erneut
eingereiht. Das verhindert Doppelverarbeitung, wenn ein Thread länger als eine
Minute arbeitet und die API neu startet. Nach einem Worker-Abbruch den hängen
gebliebenen Auftrag in der Oberfläche abbrechen und fortsetzen. Dauerhafte
Worker-Leases und automatische Erkennung ausgefallener Worker sind noch offen.

## Verbrauch und Kosten

Vor jedem API-Aufruf wird ein CostLog geschrieben. Erfolgreiche Antworten speichern
Modell, Rohverbrauch, Input, Output, Cache und Reasoning. Unvollständige oder
ungültige Antworten werden trotzdem gezählt. Timeouts und unterbrochene Aufrufe
bleiben als unbekannter Verbrauch erkennbar. SDK-Retries sind deaktiviert.
Lokale Wiederverwendung erzeugt keine erneute API-Abrechnung.

Cache-Lese- und Cache-Schreibtokens sind Teilmengen des Inputs, Reasoning eine
Teilmenge des Outputs.
Die Anzeige zählt diese Werte nicht doppelt. Audio wird für TTS-1 über die exakt
gesendeten Zeichen erfasst. Kosten sind Standardpreis-Schätzungen, keine
Anbieterrechnung. Enthalten sind explizite Preise für GPT-6.1 Sol einschließlich
Cache-Schreibkosten und Aufschlag für lange Eingaben, GPT-5, dessen Snapshot vom
2025-08-07 sowie TTS-1 und TTS-1-HD, geprüft am 2026-10-02:

- https://developers.openai.com/api/docs/models/gpt-5
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/models/tts-1-hd

Andere Modelle erhalten keinen fremden Preis. Eigene Preise lassen sich über
`PRODUCTION_PRICES` als JSON konfigurieren, mit `provider:model` als Schlüssel
und `input`, `cached`, `cache_write`, `output` in USD pro Million Tokens bzw. `character` in USD
pro Zeichen. Fehlen Preis oder Verbrauch, wird die Gesamtschätzung als unvollständig
gekennzeichnet. Verbrauch und Details lassen sich als JSON herunterladen.

## Prüfung und Grenzen

Offline-Tests prüfen Quellenreihenfolge, kostenlose Kapitelauswahl, Originalexport,
Kürzung, Übersetzung vor Audio, exakten Audio-Text, Wiederaufnahme, Abbruch während
eines Aufrufs, unbekannte Kosten und bounded Map/Reduce. Die Sprachadapter werden
mit injizierten Testprovidern geprüft; das ersetzt keine Qualitätsbewertung realer
LLM-Ausgaben. Die App behauptet keine redaktionelle Freigabe.

Dies ist die lokale Grundfunktionalität. Vor öffentlicher Bereitstellung sind
Benutzeranmeldung, Entfernung der vorhandenen Test-API-Schlüssel und eine
gesonderte Härtung der Legacy-Endpunkte nötig. Der neue Ablauf läuft getrennt von
den bestehenden `/summaries`- und alten Audiobook-Endpunkten; frühere Ergebnisse
bleiben lesbar. Die Vergleichsvorschau bleibt unverändert.
