# Geordnete Lesefassungen: erster Vergleichslauf

Dieser Versuch verwendet die bereits freigegebenen Ausschnitte aus *Blitzscaling*
und *The Chief: The Life of William Randolph Hearst*. Er untersucht drei
Verfahren bei 60, 40 und 20 Prozent der englischen Originalwortzahl. Jede Stufe
entsteht aus dem Original. Die vorhandenen Originalübersetzungen werden
wiederverwendet. Die Ergebnisse liegen in
`evaluation/book-sample/reading-experiment-v1/`, einem von Git ausgeschlossenen
Verzeichnis mit Buchtexten.

## Algorithmus

1. Der Text wird ohne Wortverlust in seiner ursprünglichen Reihenfolge zerlegt.
   Absätze und Satzgrenzen bilden Analyseeinheiten von möglichst höchstens
   160 Wörtern. Zusammenhängende Einheiten bilden Leseblöcke von möglichst
   höchstens 480 Wörtern. Kapitelgrenzen bleiben erhalten. Ein einzelner längerer
   Satz wird nicht künstlich abgeschnitten.
2. Embeddings schlagen ähnliche Einheiten vor. Pro Einheit werden die zwei
   ähnlichsten Nachbarn berücksichtigt, sofern ihre Kosinusähnlichkeit mindestens
   0,55 beträgt. Insgesamt werden höchstens 32 unterschiedliche Paare je
   Ausschnitt geprüft. Dieser begrenzte Suchlauf findet nicht zwingend jede
   Wiederholung.
3. Das LLM unterscheidet wiederholte Aussagen von Ergänzungen, anderen
   Ereignissen und erzählerischen Rückbezügen. Eine Wiederholung beeinflusst
   das Budget nur bei mindestens 0,85 gemeldeter Sicherheit, ausdrücklich
   erlaubter Kürzung und zwei wörtlich nachweisbaren Quellstellen. Diese
   Zahlen sind heuristische Parameter, keine kalibrierten Wahrscheinlichkeiten.
4. Jeder Leseblock bleibt vertreten. Ohne Redundanzprüfung erhält er ein
   annähernd proportionales Wortbudget. Mit Redundanzprüfung verringern
   bestätigte Wiederholungen das Gewicht des späteren Blocks. Überlappende
   wiederholte Spannen werden nur einmal gewichtet. Ein Mindestbudget
   verhindert, dass ein ganzer Block verschwindet. Das Gesamtbudget bleibt
   gleich, die gewonnenen Wörter werden auf andere Blöcke verteilt.
5. Das LLM schreibt die gekürzten Blöcke in Quellreihenfolge. Es erhält die
   Originalblöcke, Budgets und gegebenenfalls die bestätigten Wiederholungen.
   Das Original steht im ersten Versuch noch vollständig im Schreibauftrag;
   die technische Vorarbeit spart daher hier noch keine Input-Tokens beim
   Schreiben. Ein kleineres Schreibmodell oder eine zusätzliche technische
   Textverdichtung wären getrennte Folgeversuche.
6. Höchstens zwei gezielte Längenreparaturen versuchen, die Blockbudgets mit
   15 Prozent Toleranz einzuhalten. Eine gemeinsame Diagnose prüft anschließend
   falsche Aussagen, erfundene Inhalte und gebrochene Bezüge. Höchstens eine
   Korrekturrunde bearbeitet konkret beanstandete Blöcke. Danach wird erneut
   diagnostiziert. Verbleibende Hinweise und Abweichungen werden angezeigt,
   die Diagnose ist kein Qualitätszertifikat.
7. Jede englische Fassung wird ins Deutsche übersetzt und zweisprachig
   sprachlich überarbeitet. Die Übersetzung darf keine im englischen Text
   fehlenden Inhalte wieder einfügen.

## Vergleich

- **Blockweise:** Schritte 1 und 4-7 ohne Wiederholungshinweise.
- **Mit Redundanzprüfung:** der gesamte Ablauf einschließlich Schritte 2-3.
- **Direktes LLM:** vollständiger Originalausschnitt und ein gemeinsames Budget;
  das Modell wählt die Inhalte. Anschließend gelten dieselben begrenzten
  Reparatur-, Diagnose- und Übersetzungsschritte.

Die direkte Referenz verwendet hier die gemeinsame kurze Prüfpipeline. Der
`AbridgementEngine` aus dem vorherigen Vergleich enthält zusätzliche interne
Quellenprüfungen. Seine damaligen Verbrauchszahlen sind deshalb kein direkt
vergleichbarer Einzelwert für diese neue Referenz.

Es gibt keine globale Auswahl einiger Lieblingsthemen. Themenähnlichkeit
allein entfernt keinen Inhalt. Die Zusicherung nichtleerer Blöcke garantiert
allerdings nicht, dass jede Aussage oder jeder Absatz innerhalb eines Blocks
erhalten bleibt. Bei starker Kürzung müssen auch wesentliche Details weichen.
Eine separate satzweise Prüfung, ein eigenes kleines Prüfmodell und ein
eigenständiger Übergangsalgorithmus sind in diesem ersten Versuch nicht
implementiert. Alle Modellschritte verwenden das konfigurierte Schreibmodell.

Auch die Grenzen der ausgewählten Quellpassagen bleiben hier erhalten. Beim
Hearst-Ausschnitt sind das vier technische Teilpassagen desselben Kapitels,
keine vier eigenständigen Kapitel. An diesen Grenzen entstehen auch kurze
Endblöcke, der kürzeste mit 37 Wörtern. Bei 20 Prozent Restlänge ist dessen
Budget entsprechend knapp. Ob solche Grenzen vor der Budgetplanung besser
zusammengeführt werden sollten, gehört zur Bewertung dieses ersten Versuchs.
Die Vorschau zeigt dafür Ziel und tatsächliche Wortzahl jedes Blocks.

## Verbrauch und Wiederaufnahme

`scripts/experiment_usage.py` protokolliert jeden tatsächlichen API-Versuch
atomar unter `calls/`, einschließlich Fehlversuchen. Input, Output,
API-Cache-Anteil und Reasoning-Anteil bleiben in ihren ursprünglichen
Verbrauchsfeldern erhalten. Cache ist eine Teilmenge des Inputs, Reasoning
eine Teilmenge des Outputs. Beides wird nicht doppelt addiert. Embeddings
und Redundanzanalyse werden einmal je Ausschnitt berechnet.

Identische Anfragen verwenden einen lokalen Antwortcache, auch zwischen
Varianten. Ein solcher Treffer wird im Ereignisprotokoll festgehalten und
erzeugt keinen neuen API-Aufruf. Die Tabelle zeigt tatsächlich angefallenen
Verbrauch; sie ist dadurch keine Schätzung unabhängig neu gestarteter
Einzelvarianten. Ein Timeout ohne API-Verbrauchsangabe bedeutet unbekannten
Verbrauch, nicht null Kosten. Preise werden hier nicht geschätzt.

Die Quelle, Parameter, Modellkennung und Script-Prüfsummen werden im Manifest
gespeichert. Zwischenfassungen, Diagnosen, tatsächliche Blocklängen und
Zielabweichungen bleiben nachvollziehbar. Abgeschlossene Fassungen werden bei
einer Wiederaufnahme nicht erneut erzeugt.

`api-usage.json` enthält die ursprünglichen API-Verbrauchsfelder je Versuch
und die lokalen Wiederverwendungsereignisse. Diese Datei und die Manifeste
sind auch im herunterladbaren ZIP enthalten.

Jede Kachel zeigt Input und Output des gesamten zugehörigen Laufs einschließlich
Übersetzung. Die englische und die deutsche Kachel zeigen somit denselben
Gesamtverbrauch und dürfen nicht addiert werden. Ein Expander schlüsselt die
Schritte auf. Bei der Redundanzvariante wird die gemeinsame Analyse gleichmäßig
auf die drei geplanten Stufen verteilt. Ganzzahlige Rundungsreste werden so
zugeordnet, dass die Kachelsummen exakt mit dem gemessenen Verbrauch übereinstimmen.
Für nur eine Stufe ohne spätere Wiederverwendung wäre der volle Analyseaufwand
relevant. Die übernommenen Originale verursachen hier keine neuen API-Aufrufe;
historische Übersetzungskosten werden nicht als neu gemessener Verbrauch angezeigt.

## Ausführen

Der erste Befehl verursacht externe Modellaufrufe und API-Kosten:

```powershell
python scripts/run_reading_experiment.py
```

Nur vorhandene Ergebnisse darstellen, ohne API-Aufrufe:

```powershell
python scripts/run_reading_experiment.py --render-only
```

Die eigenständige `index.html` funktioniert auch ohne Server. Sie enthält
beide Bücher, alle drei Restlängen, die englischen und deutschen Fassungen,
Wiederholungsentscheidungen und Verbrauchsdaten. Texte sind zusätzlich als
TXT und gemeinsam mit der Seite als ZIP verfügbar. Lesebewertungen werden
je Buch, Stufe, Verfahren und Sprache im Browser gespeichert und lassen sich
exportieren.

Die zwei Ausschnitte erlauben einen ersten Vergleich von Sachbuch und
Biographie. Sie belegen noch keine Eignung für ganze Bücher oder Romane.
Der neue Kern und die Experimentvorschau sind noch kein integrierter
Produktionsmodus der App.

## Erster vollständiger Lauf vom 2. Oktober 2026

Alle 18 englischen Fassungen und ihre 18 deutschen Übersetzungen sind erstellt.
Das ZIP enthält außerdem die vier wiederverwendeten Originaltexte, die
Vorschau, den Bericht und die Verbrauchsprotokolle. Alle 125 API-Versuche haben
vollständige Verbrauchsangaben: insgesamt 716.861 Input- und 373.885
Output-Tokens. Davon sind 170.240 Input-Tokens API-Cache und 173.632
Output-Tokens Reasoning. Verwendet wurden `gpt-5-2025-08-07` und
`text-embedding-3-small`. Historische Originalübersetzungen sind nicht enthalten.

Die Wiederholungsanalyse hat eine Aussage bei Blitzscaling und drei bei Hearst
für die Budgetplanung bestätigt. Das ist keine Messung ihrer vollständigen
Trefferquote. Beide blockweisen Verfahren erhalten Hearsts politischen
Einstieg auf allen drei Stufen. Die direkte 20-Prozent-Fassung lässt ihn weg.

Acht der 18 Fassungen verfehlen die Gesamtlängentoleranz, besonders auf der
20-Prozent-Stufe. Bei Hearst liegen dort alle drei außerhalb des Zielbereichs.
Vier Fassungen enthalten nach der begrenzten Korrekturrunde noch automatische
Prüfhinweise. Die Vorschau kennzeichnet beides. Damit ist der erste Lauf
vollständig, die Längensteuerung und die Zuverlässigkeit der Nachprüfung
bleiben Entwicklungsaufgaben. Die Lesefluss- und Stilbewertung steht noch aus.
