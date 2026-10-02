# Prüfung des neuen Zusammenfassungskerns

Stand: 28. September 2026. Lokaler Entwicklungsstand, keine Freigabe für einen
unbeaufsichtigten Produktionsbetrieb.

## Fachliche Entscheidung

Themenähnlichkeit hilft beim Finden verwandter Stellen, genügt aber nicht als
Entscheidung darüber, was gestrichen werden darf. Eine Wiederholung kann eine
neue Begründung, Einschränkung oder ein bewusstes Leitmotiv enthalten.

Der neue Kern kombiniert deshalb hierarchische Inhaltsplanung mit dem Schreiben
aus Originalstellen. Der Plan verteilt ein festes Wortbudget nach redaktioneller
Bedeutung. Die Abschnitte bleiben in Buchreihenfolge. Jede Lesetiefe entsteht
eigenständig aus dem Original; eine ausführlichere Fassung muss keine verloren
gegangenen Details aus einer Kurzfassung rekonstruieren.

Das ist eine begründete Architekturentscheidung, noch kein empirischer Nachweis,
dass sie den Legacy-Ansatz bei gleichem Budget auf jedem Buch übertrifft.
Forschungsquellen und Alternativen stehen in [ABRIDGEMENT_DESIGN.md](ABRIDGEMENT_DESIGN.md).

## Technische Prüfung

- 25 automatisierte Tests bestanden: Quellenzugriff, Cache, Stufen, Wortbudgets,
  EPUB-Reihenfolge und Fragmentgrenzen, Belegprüfung, Rechte und Audioübergabe.
- Next.js-Produktionsbuild einschließlich Typprüfung und Linting bestanden.
- Workflow im Browser geprüft: Bibliothek, Buchauswahl, Kapitel und Lesestufen;
  Erzeugung ohne ausgewählte Kapitel ist deaktiviert.
- Die Audiointegration wurde mit einem TTS-Testdouble geprüft. Es spricht die
  gespeicherte Lesefassung. Ein echter TTS-Durchlauf wurde hier nicht durchgeführt.
- Die vollständige neue Reader-Seite wurde noch nicht mit einem echten,
  durch den Queue-Worker abgeschlossenen Auftrag im Browser geprüft.

## Live-Probe am vorhandenen EPUB

Modell: das konfigurierte `gpt-5`. Auswahl: vier aufeinanderfolgende TOC-Einträge
aus *Blitzscaling*, nullbasierte Indizes 6-9, insgesamt 3.906 Wörter. Damit wird
auch ein Kapitel geprüft, dessen Unterabschnitte dieselbe XHTML-Datei verwenden.
Die Versuche betreffen einen Buchausschnitt, nicht das gesamte Buch.

Reproduktion (verursacht Modellnutzung):

```powershell
python scripts/evaluate_abridgement.py --epub Blitzscaling.epub --chapters 6 7 8 9 --levels standard compact --output-dir evaluation/book-sample
```

Jeder Durchlauf erzeugt einen eigenen Zeitstempelordner mit Ergebnistexten,
Quellenbelegen und `report.json`. Der gemeinsame Cache spart unveränderte Schritte.
Der Ordner ist von Git ausgeschlossen, da er Originalauszüge enthält.

Beobachtungen während der Entwicklung:

1. Eine erste kompakte Fassung bestand den automatischen Quellencheck:
   587 Wörter, rund 15 % der Auswahl. Beim Lesen wirkte sie jedoch wie eine
   verdichtete Sammlung von Firmen, Zahlen und Beispielen. Quellenbezug allein
   reicht also nicht für einen angenehmen Lesetext.
2. Der Schreibauftrag verlangt inzwischen einen nachvollziehbaren Gedankenbogen,
   weniger Beispielinventare, gezielte Zahlen und natürlichere Absatzprosa.
3. Dabei wurde eine Aussage über Softwareentwicklung unzulässig auf Technologie
   allgemein ausgeweitet. Der Quellencheck stoppte die Fassung. Die Korrektur
   erhält nun den konkreten beanstandeten Satz zusammen mit der Begründung.
4. Ein langer Standardentwurf führte zu ausgelassenen Satzprüfungen. Prüfungen
   werden deshalb in Gruppen von höchstens zwölf explizit nummerierten Sätzen
   aufgeteilt. Fehlende Checks werden weiterhin abgelehnt.

Die ersten Versuche sind kein fairer Geschwindigkeitsvergleich: Cache-Treffer,
fehlgeschlagene Versuche und geänderte Schreibaufträge beeinflussen die Werte.
Tokenzahlen enthalten auch interne Modellausgabe und Überarbeitungen; sie sind
nicht mit der Wortzahl des fertigen Textes gleichzusetzen.

Der Standardversuch mit der Satzgruppenprüfung wurde nach 549 Sekunden abgelehnt:
Im letzten Abschnitt machte der Entwurf aus zwei getrennten Aussagen über
technologischen Rückstand und finanzielle Probleme einen unbelegten Vergleich
mit demselben Wettbewerber. Verbrauch dieses Versuchs: 99.723 Eingabe- und
53.322 Ausgabetokens, trotz wiederverwendeter Planung. Dieser Versuch lief noch
mit dem vorherigen Schreibauftrag und ohne das anschließend ergänzte konkrete
Satzfeedback bei der Überarbeitung. Es wurde keine Standardfassung veröffentlicht.

Der abschließende Kompaktversuch mit konkretem Satzfeedback und höchstens zwei
Korrekturrunden bestand die automatische Prüfung: **594 Wörter, 15,21 %** der
Quelle, keine Längenwarnung innerhalb der festgelegten Toleranz. Ziel waren 12 %.
Der Durchlauf dauerte 205,62 Sekunden bei 16 Cache-Treffern und verbrauchte
32.260 Eingabe- sowie 15.863 Ausgabetokens. Das ist ein Wiederholungslauf,
kein Gesamtpreis und keine Laufzeitmessung ab leerem Cache.

Ergebnis: [kompakte Lesefassung](evaluation/book-sample/20260928T115544037183Z/compact.txt),
[Messdaten](evaluation/book-sample/20260928T115544037183Z/report.json).
Diese Links zeigen auf lokale, bewusst nicht versionierte Artefakte.

Redaktioneller Leseeindruck: Die Unterschiede zwischen den Wachstumsformen
und die Argumentation über Geschwindigkeit, Finanzierung und Risiken sind
nachvollziehbar. Metaphern aus dem Original bleiben erhalten. Der Text ist aber
weiterhin stellenweise dicht, mit mehreren Firmenbeispielen und Kennzahlen;
auch die Definition wird erneut aufgegriffen. Der Auftrag zur stärkeren
Beispielauswahl wird also nicht durchgehend eingehalten. Der automatische
Quellencheck bewertet diese stilistischen Schwächen nicht zuverlässig.

## Was noch nachgewiesen werden muss

Die gleiche Modellfamilie schreibt und prüft. Wörtlich vorhandene Belege und
bestandene Modellprüfungen sind keine unabhängige Garantie gegen Sinnfehler.
Auch unberechtigte Ablehnungen sind möglich. Bei sehr kurzen Fassungen kann
ein einziger fehlerhafter Satz einen großen Anteil ausmachen; die Pipeline
bricht dann bewusst ab, statt fast den gesamten Abschnitt zu löschen.

Für eine belastbare Produktfreigabe fehlen insbesondere ein Vergleich mit dem
Legacy-Verfahren bei identischen Wortbudgets, mehrere vollständige Sachbücher,
menschliche Bewertungen von Lesefluss und Ton sowie ein echter Audio-Endtest.
Die bisherigen Laufzeiten und Tokenmengen sprechen außerdem dafür, vor großen
Buchläufen Kosten und Laufzeit anhand kleiner Auswahlen zu prüfen.

65 %, 35 %, 12 % und 4 % sind Längenziele. Bei 4 % lässt sich der ursprüngliche
Erzählton nur eingeschränkt erhalten. Diese Stufe dient vor allem der Orientierung;
die mittleren Stufen sind für das eigentliche Lese- und Hörerlebnis gedacht.
