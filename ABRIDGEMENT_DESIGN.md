# Lesefassungen statt Zusammenfassungen von Zusammenfassungen

## Entscheidung

Der neue Web-Workflow erzeugt eigenständige gekürzte Fassungen eines Sachbuchs.
Die vier Zielgrößen sind 65 %, 35 %, 12 % und 4 % der ausgewählten Originalwörter.
Sie sind redaktionelle Längenziele, keine Zusage über erhaltene Informationsanteile.
Bei 4 % bleibt vor allem Orientierung; Erzählton und viele Beispiele brauchen mehr Platz.

Jede Fassung wird erneut aus Originalabschnitten geschrieben. Die kürzere Fassung
ist niemals die einzige Quelle für eine längere. Das ermöglicht späteres Vertiefen.
Bereits erstellte Stufen werden anhand von Buch, Auswahl, Sprache, Modell und
Pipeline-Version wiedergefunden. Die Lesefassung bleibt vor TTS zugänglich.

## Was im Legacy-Ansatz problematisch war

- Im alten Web-Workflow war die Kürzungsstufe wirkungslos. Der gesamte Text ging an TTS.
- Die frühe Reduktion jedes Chunks auf 75-100 Wörter beseitigt Beispiele und
  argumentative Details, bevor entschieden wird, welche davon wichtig sind.
- Der Legacy-Splitter teilt zunächst an Punkten und Kommata, verliert dabei
  Kommata und hängt einen verbleibenden kurzen Schlussblock nicht zuverlässig an.
  Benachbarte Fenster teilen bei den verwendeten Parametern einen von fünf
  Satzblöcken. Ein Teil der ähnlichen Inhalte entsteht deshalb schon durch die
  Vorverarbeitung, unabhängig von Wiederholungen des Autors.
- Embedding-Ähnlichkeit von Zusammenfassungen findet verwandte Themen. Sie zeigt
  nicht, ob zwei Passagen dasselbe behaupten, sich widersprechen oder zusätzliche
  Evidenz liefern. Ein Louvain-Cluster ist deshalb keine ausreichende Streichregel.
- Die graphbasierte Gruppierung kann die Reihenfolge von Voraussetzungen und
  Schlussfolgerungen verändern. Gleich große Cluster sind kein Qualitätsmaß.
- Die Suche nach einer passenden Themenzahl war unbeschränkt, änderte die
  Eingabematrix und verwendete ungesetzte Zufallsseeds. Sie ist jetzt begrenzt,
  verändert die Eingabe nicht und ordnet Mitglieder reproduzierbar.
- Die API las Manifest- statt Spine-Reihenfolge und ignorierte Fragmentanker.
  Mehrere Kapitel in einer XHTML-Datei wurden so wiederholt eingelesen. Der neue
  Import verwendet nicht überlappende TOC-Intervalle und meldet fehlende Anker.

Der alte Streamlit-Workflow bleibt ein Legacy-Experiment. Der neue
Zusammenfassungskern läuft in API und Next.js unter `/workflow`.

## Was die Forschung trägt - und was nicht

**Hierarchische Verarbeitung:** SummN zeigt, dass mehrstufiges Segmentieren und
Verdichten lange Eingaben mit beschränktem Modellkontext verarbeiten kann. Die
Evaluation betrifft unter anderem Meetings, TV-Dialoge und Regierungsberichte;
sie beweist nicht die literarische Qualität gekürzter Sachbücher.
[Zhang et al., ACL 2022](https://aclanthology.org/2022.acl-long.112/)

**Buchlänge und menschliche Prüfung:** Wu et al. zerlegen Buchzusammenfassungen
rekursiv und trainieren mit menschlichem Feedback. Das belegt die praktische
Verwendbarkeit der Zerlegung, aber auch den Abstand zur menschlichen Qualität:
In ihrer Untersuchung erreichten nur wenige Ergebnisse menschliches Niveau.
[Wu et al., 2021](https://arxiv.org/abs/2109.10862)

**Narrativer Zusammenhang:** NexusSum untersucht hierarchische LLM-Verarbeitung
für lange narrative Texte. Für dieses Produkt ist die Trennung zwischen Planung
und Ausformulierung relevant; die Übertragung auf Sachbuch-Lesefassungen ist eine
Designentscheidung, keine durch diese Arbeit nachgewiesene Produktqualität.
[NexusSum, ACL 2025](https://aclanthology.org/2025.acl-long.500/)

Meine Ableitung: Hierarchie als Verarbeitungstechnik behalten, irreversible
Verdichtung als alleinige Wissensquelle vermeiden. Themenwissen hilft dem
Redaktionsplan; Originalbelege bleiben beim Schreiben und Prüfen verfügbar.

## Implementierte Pipeline

1. EPUB-Spine und TOC-Fragmentgrenzen auslesen; die gewählte Kapitelreihenfolge erhalten.
2. Originale auf maximal 1.800 Wörter / 12.000 Zeichen pro Einheit begrenzen.
   Die Größen sind konservative Eingabegrenzen, keine exakte Tokenberechnung.
3. Inhaltskarten mit Argument, Beispielen, Einschränkungen und Ton erstellen.
4. Einen globalen Redaktionsplan bilden. Bei sehr vielen Karten nur die
   Planungsnotizen hierarchisch zusammenführen, niemals die Originalquellen ersetzen.
5. Redaktionelle Gewichte vergeben: Wiederholungen weniger Platz, eigenständigen
   Argumenten und Beispielen mehr. Die Gewichte verteilen ein gemeinsames Wortbudget.
6. Zusammenhängende Prosa aus dem Original, dem Plan und dem vorigen Textende
   schreiben. Die vorherige Fassung und der Plan gelten nicht als Faktenbelege.
7. Jede Einheit gegen ihr Original prüfen: Belegbarkeit, Negationen, Kausalität,
   Einschränkungen und gebrochene Verweise. Jeder Satz benötigt eine oder mehrere
   Belegstellen, deren tatsächliches Vorkommen im Original zusätzlich deterministisch
   geprüft wird. Zusammengeführte Aussagen dürfen mehrere entfernte Belege verwenden.
   Die Prüfung erfolgt in Gruppen von höchstens zwölf ausdrücklich nummerierten
   Sätzen, damit lange Antworten nicht unbemerkt einzelne Belege auslassen.
   Höchstens zwei Korrekturrunden sind erlaubt; die zweite nur bei offenen
   Quellenproblemen. Die Überarbeitung erhält den konkreten beanstandeten Satz.
   Bleiben einzelne unbelegte Zusätze übrig,
   können diese entfernt werden, sofern sie höchstens 20 % des Entwurfs ausmachen.
   Anschließend wird der gesamte verbleibende Entwurf erneut geprüft. Die entfernten
   Sätze werden im Ergebnis protokolliert; größere Eingriffe führen zum Fehlschlag.
8. Unbelegte Fassungen nicht veröffentlichen. Verfehlte Längenziele sichtbar machen.
   Länge bleibt ein redaktionelles Ziel: Eine quellengeprüfte Fassung darf trotz
   Längenabweichung gelesen und auf Wunsch vertont werden.
9. Original und Lesetext abschnittsweise nebeneinander zugänglich halten. Die
   gespeicherte Fassung optional über den vorhandenen TTS-Worker vertonen.

Zwischenergebnisse liegen als JSON-Cache unter `uploads/.editions/`, getrennt
nach Benutzer und Buch. Cache-Schlüssel enthalten Modell, Pipeline-Version,
Aufgabe und Eingaben. Ein Retry kann abgeschlossene Modellschritte wiederverwenden.
Ausgabe-Dateinamen enthalten Job-IDs, damit Stufen und Stimmen einander nicht überschreiben.

## Qualitätsprüfung

Automatisierte Tests: Originalzugriff in allen Stufen, Cache und Modellwechsel,
ungültige Antworten, Ablehnung unbelegter Texte, Budgetverteilung,
EPUB-Fragmentgrenzen, Rechteprüfung und Bindung von Audio an die gewählte Fassung.

`python -m unittest discover -s tests -v`

Ein selbst geschriebener englischer Sachtext unter
`tests/fixtures/editorial_sample.txt` enthält Wiederholungen, eine Metapher und
eine wichtige Einschränkung. Ein bewusster Live-Test mit dem konfigurierten Modell:

`python scripts/evaluate_abridgement.py --levels standard compact`

Ergebnisse werden unter `evaluation/` gespeichert. Der Live-Test verursacht
Modellnutzung; Unit-Tests rufen keine externen Modelle auf.

Für einen belastbaren Buchvergleich sind zusätzlich nötig:

- Blindvergleich gleicher Wortbudgets: Legacy-Topics, einfache kapitelweise
  Verdichtung und neue Pipeline, jeweils an mehreren unterschiedlichen Sachbüchern.
- Menschliche Bewertung von Lesefluss, Ton, Argumentationsbogen und Beispielauswahl.
- Quellenbezogene Fragen zu Kernaussagen, Begründungen und Gegenargumenten.
- Gesonderte Suche nach erfundenen Fakten und verfälschten Einschränkungen.

Ein bestandener Modellcheck ist keine unabhängige Wahrheitsgarantie. Derselbe
Modelltyp kann beim Schreiben und Prüfen denselben Fehler machen. Ein kurzer
Testtext belegt keine Qualität über ein ganzes Buch hinweg.

Beim Entwicklungstest wurden tatsächlich Längenüberschreitungen und eine frei
ergänzte Verallgemeinerung beobachtet. Ein pauschaler Ja/Nein-Modellcheck übersah
letztere. Daraus entstanden die satzweise Belegprüfung, kleine Zähltoleranzen und
eine Wiederholungsfunktion mit neuen Entwürfen statt immer desselben Cache-Treffers.
Auch die neue Prüfung kann falsche Freigaben und falsche Ablehnungen produzieren.

## Bewusste Grenzen

- Der neue Worker nutzt derzeit OpenAI mit `OPENAI_DEFAULT_MODEL`. Der Legacy-Code
  hat weitere Provider; diese sind noch nicht an den neuen Kern angeschlossen.
- Semantische Wiederholungen werden redaktionell anhand von Karten und Plan
  beurteilt. Es gibt noch keinen evaluierten Claim-Graph und keine Garantie, jede
  weit auseinanderliegende Wiederholung korrekt zusammenzuführen.
- Die Prüfung ist abschnittsweise. Ein unabhängiger vollständiger Buch-Lesetest
  und ein umfassender finaler Stilpass fehlen als Nachweis noch.
- Tokenverbrauch wird gespeichert. Für beliebige Modelle werden keine alten
  Dollarpreise als aktuelle Kosten ausgegeben; die vorhandene Kostenübersicht
  enthält diese neuen LLM-Kosten deshalb noch nicht.
- Der vorhandene Queue-Recovery-Mechanismus ist auf lokalen Betrieb mit einem
  Worker ausgerichtet. Verteilte Worker-Leases und genau-einmaliges Billing sind
  keine zugesicherten Eigenschaften.
- Audio verwendet die bestehende TTS-Implementierung und MP3. Kapitelmarken,
  M4B und eine geräteübergreifende Hörposition sind noch nicht implementiert.
