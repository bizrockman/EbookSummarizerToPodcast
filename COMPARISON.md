# Zweisprachiger Lesevergleich

## Zweites Werk und Produktentscheidung

Nach Sichtung des Blitzscaling-Vergleichs sollen in der App die Ursprungsidee
und der Hybrid erhalten bleiben. Bildhafte Beispiele sind dem Nutzer wichtig;
harte Übergänge bleiben ein zu verbessernder Punkt. Die Umstellung der App auf
diese beiden Modi ist noch nicht umgesetzt.

Vorher folgt ein Verifikationslauf mit David Nasaws *The Chief: The Life of
William Randolph Hearst*. Eine protokollierte Zufallsauswahl aus 151 möglichen
zusammenhängenden Ausschnitten fiel auf Kapitel 14, *A War of Kings*, Textblöcke
5 bis 8: 3.939 Wörter. Der Seed steht in `selection-info.json`; es wurde nicht
anhand der Ergebnisse neu ausgewählt. Bei der Vorbereitung eingefügte
Satzumbrüche wurden durch die originalen Absatzabstände ersetzt, ohne die
gewählten Wörter oder Abschnittsgrenzen zu ändern. Ein früher Vorlauf wurde
deswegen abgebrochen und sein bekannter Verbrauch separat protokolliert.

Ergebnisse des zweiten Werks: `evaluation/book-sample/hearst-verification/`.
Der aktuelle Ansatz wurde nach den zunächst gescheiterten Läufen repariert.
Die fertigen englischen Lesetexte umfassen: Original 3.939 Wörter,
Ursprungsidee 586, aktueller Ansatz 571 und Hybrid 580, jeweils auch auf Deutsch.
Fehlversuche und Zwischenfassungen bleiben separat gespeichert. Die endgültige
Fassung des aktuellen Ansatzes hat zusätzlich nach dem Längenabgleich eine
satzweise Quellenprüfung bestanden (`current-final-audit.json`).
Das gemeinsame Ziel von 600 Wörtern mit 5 Prozent Toleranz bleibt gleich.
Die Übersetzung berücksichtigt historische Sprecher, Zitate und Chronologie.
Im Hearst-Lauf wurde die Satzzerlegung der Quellenprüfung korrigiert: Initialen
wie `W. R.` und Anreden wie `Mrs.` bleiben an der zugehörigen Aussage.
Außerdem nennt die Fehlermeldung bei nicht wortgetreuen Belegen jetzt den
beanstandeten Auszug und erklärt, dass keine Anführungszeichen ergänzt werden
dürfen. Äußere Zitatzeichen und eine abweichende Großschreibung des ersten
Buchstabens dürfen deterministisch auf einen tatsächlich vorhandenen
Quellenauszug zurückgeführt werden. Diese Formatkorrekturen werden protokolliert;
Wörter, Verneinungen und innere Auslassungen werden nicht passend gemacht.
Auch Ausrufezeichen in Titeln wie `Stop! Look! Listen!` bleiben zusammen.
Diese Reparaturen und
die zusätzlichen Wiederholungen sind bei einem Vergleich des Aufwands zu beachten.
Der aktuelle Ansatz erhält nun auch beim Längenabgleich den Originaltext und
wird nach jedem weiteren Umschreiben erneut geprüft. Ursprungsidee und Hybrid
bleiben für den Vergleich unverändert; ihre Abschlussdiagnose blockiert oder
korrigiert die Texte nicht. Deshalb sind die Prüfregeln der drei Verfahren
unterschiedlich, und ihre Ergebnisse keine kontrollierte Messung allein der
Inhaltsauswahl. Eine bestandene LLM-Prüfung garantiert keine Fehlerfreiheit.
Direkt abgeglichene Inhaltsfehler stehen getrennt in `verification-notes.json`;
die dort dokumentierten Fehler von Ursprungsidee und Hybrid bleiben im Text
sichtbar. Die Reparaturrunden des aktuellen Ansatzes sind separat nachvollziehbar.
Wenige dokumentierte deutsche Wortlautkorrekturen passen wörtlich übernommene
englische Wendungen an, beispielsweise `Society with a capital S` als
`feine Gesellschaft`.

Fortsetzen des zweiten Laufs (kann Modellnutzung verursachen):

```powershell
$env:COMPARISON_OUTPUT = 'evaluation/book-sample/hearst-verification'
python scripts/compare_approaches.py --source-json evaluation/book-sample/hearst-verification/source.json
python scripts/refine_comparison_german.py
python scripts/finish_comparison.py
```

Die folgenden Angaben beschreiben den ersten Vergleich.

Der Vergleich vom 29. September 2026 verwendet die TOC-Einträge 6, 7, 8 und 9
der lokal vorhandenen Datei `Blitzscaling.epub`: 3.906 Wörter. Er enthält das
englische Original, drei englische Kurzfassungen und die vier zugehörigen
deutschen Übersetzungen.

Die Ergebnisse liegen lokal unter
`evaluation/book-sample/comparison-20260929/`. Dieser Ordner ist wegen der
enthaltenen Originalauszüge von Git ausgeschlossen.

## Lesen

`index.html` lässt sich direkt im Browser öffnen. Sie enthält sämtliche Texte
und funktioniert ohne Server oder Internet. Die englischen Texte stehen oben,
die deutschen darunter. Wahlweise lassen sich zwei Fassungen gegenüberstellen.
Alle Texte sind zusätzlich einzeln als TXT verfügbar; `lesevergleich.zip`
enthält die Seite, Texte, Messdaten und eine kurze Anleitung.

## Vergleichsbedingungen

- Gleiches konfiguriertes Schreibmodell, Ziel 600 englische Wörter mit 5 % Toleranz.
- Ursprungsidee: Originalpassagen in kleine Einheiten zerlegen, Embeddings mit
  `text-embedding-3-small`, Nachbarschaftsgraph, Louvain mit festem Seed,
  redundanzbewusste technische Auswahl bis 1.200 Wörter, dann LLM-Überarbeitung.
  Dies ist eine neue Umsetzung der Idee, kein unveränderter Legacy-Codepfad.
- Hybrid: gleiche Technik mit 1.800 Wörtern Kandidatenmaterial; anschließend
  LLM-Auswahl von etwa 1.200 Quellwörtern und Ausformulierung.
- Aktueller Ansatz: der vorhandene `AbridgementEngine`, mit dem gemeinsamen
  Vergleichsziel statt einer der vier festen UI-Prozentstufen.
- Alle drei Fassungen erhalten anschließend denselben Längenabgleich. Der
  Schreibauftrag wird bei Über- oder Unterschreitung angepasst. Dieser Schritt
  kann auch Stil und Inhalt beeinflussen und wird deshalb mitgezählt.
- Gleiche abschließende diagnostische Prüfung, die die Texte nicht verändert.
  Die aktuelle Pipeline besitzt zusätzlich ihre internen Quellenprüfungen.
- Deutsche Übersetzung aus der jeweiligen englischen Fassung, zweisprachige
  Revision und abschließender Auftrag zur idiomatischen Sprachüberarbeitung.
  Einzelne danach noch erkennbare falsche Freunde werden dokumentiert korrigiert.
  Die Übersetzung darf die Inhaltsauswahl der englischen Kurzfassung nicht ergänzen.

## Messdaten und Grenzen

`comparison-report.json` enthält Tokenverbrauch und Antwortzeiten je Verfahren
und Phase. Erfasst ist der gesamte Aufwand dieser Vergleichserstellung, auch
verworfene Längenversuche und Wiederholungen. Es handelt sich nicht um eine
bereinigte Laufzeit- oder Kostenrangliste einzelner Produktionsläufe.
Embeddings wurden für beide technischen Varianten einmal gemeinsam berechnet.
Zeiten sind summierte API-Antwortzeiten; die Verfahren liefen teilweise parallel.
Interne Reasoning-Tokens können in den Ausgabetokens enthalten sein.

`manifest.json`, Auswahlprotokolle, Engine-Ergebnis und gespeicherte API-Antworten
halten Quelle, Parameter und Zwischenergebnisse fest. Antworten werden bei einer
Wiederaufnahme wiederverwendet; ungültige Belegantworten bleiben zur Kostenerfassung
archiviert und können neu angefordert werden.

Ein einzelner Ausschnitt und jeweils eine präsentierte Fassung erlauben noch
keinen allgemeinen Qualitätsvergleich. Die automatischen Diagnosen sind
fehlbar und bleiben auf der Seite zunächst eingeklappt, um das Lesen nicht
vorab zu beeinflussen. Die deutschen Fassungen sind LLM-Übersetzungen mit
Sprachkorrekturen, keine von menschlichen Fachübersetzern zertifizierten Texte.

## Erneut ausführen

Die ersten beiden Befehle können externe Modellaufrufe und Kosten verursachen:

```powershell
python scripts/compare_approaches.py
python scripts/refine_comparison_german.py
python scripts/finish_comparison.py
```

Nur die Darstellung aus vorhandenen Daten neu erzeugen:

```powershell
python scripts/compare_approaches.py --render-only
```
