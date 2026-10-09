# Evaluation

Sprint 3 misst PDF-Textqualität an **24 synthetischen Fällen / 29 Seiten**.
Diese kontrollierte Stichprobe ist kein Qualitätsnachweis für reale AVB.
Produktionsmodelle, Ontologie und Claim-Verifikation bleiben unverändert.

## Ausführen und vergleichen

```sh
uv sync --locked --dev
uv run axiory-eval
uv run axiory-eval --output datasets/evaluation-next --compare datasets/evaluation/report.json
```

Optional: --repeats 2 (2 bis 10), --max-pdf-bytes 20971520, --max-pages 200.
JSON und Markdown entstehen im gewählten Output-Verzeichnis. Jeder Lauf erzeugt
einen neuen run-*-Ordner mit Original-PDF, Gold-JSON und separaten Ingestion-Stores
für jede Wiederholung. Keine Wiederholung liest den Cache eines früheren Laufs.
Diese generierten Daten sind in Git ignoriert; keine echten Daten hinzufügen.
Die CLI läuft offline nach Installation.

Exit 0 bedeutet ausführbarer, reproduzierbarer Benchmark, **nicht perfekte Qualität**.
Bekannte Negativfälle, unsupported und messbare Layoutfehler sind Ergebnisse.
Exit 1 bedeutet fehlenden Lauf/abweichenden Extraktionsfingerprint; Diagnoseberichte
werden trotzdem exportiert. Exit 2 bedeutet ungültige Eingaben oder fehlgeschlagenen
Runner/Export. Auch zugelassene Parserfehler bleiben als Original und Receipt erhalten;
bei Admission-Fehlern bleiben die vom Runner erzeugten PDF-/Gold-Dateien zur Diagnose.

## Unabhängiger Goldstandard

schemas.py trennt drei Ebenen:

1. GoldFixture: vorab verfasster Quellinhalt, Seiten, Klauselteile, Tabellenzellen,
   verbundene Zellen, Header/Wert-Beziehungen, Evidenzzitate und Soll-Lesereihenfolge.
2. Observation: tatsächlich extrahierte Rohtexte und explizit verfügbare Strukturen.
3. Fachinterpretation: ausdrücklich not_evaluated; keine Coverage-/Claim-Ableitung.

Schema, Dokumentversion, Corpus und Metrikdefinitionen sind versioniert.
goldstandard.py importiert keinen Parser und verwendet keine Parserausgaben.
Renderer und Annotation lesen denselben verfassten Quellplan. Das vermeidet
Abschreibfehler, ersetzt aber keine visuelle Kontrolle des Renderers: alle 29 Seiten
wurden mit Poppler gerendert und visuell geprüft. Sollwerte werden bei Parserfehlern
nicht nachträglich passend gemacht. Eine erwartete leere Seite bleibt deshalb
expected_extraction_status=empty, obwohl die aktuelle Pipeline not_extractable meldet.

ReportLab erzeugt deterministische PDFs mit eingebettetem, im Paket enthaltenem
Bitstream Vera. Lockfile und Font-SHA fixieren die Abhängigkeiten; Systemfonts sind
nicht nötig. Bildtext wird gerastert, Vektortext als Konturen dargestellt.
Quelltext und PDF-Paint-Reihenfolge sind getrennt: gleiche visuelle Tabellen/Spalten
werden bewusst in unterschiedlicher Zeichenreihenfolge gespeichert.

Der Korpus enthält Fliesstext, Mehrseiten, Spalten, Tabellen (auch Row-/Column-Spans),
Fussnoten, seitenübergreifende Klauseln, Negationen, Ausnahmen, Sublimiten,
Selbstbehalte, Währungen/Bezugsgrössen, DE/FR/IT, kleine/grosse Schrift,
Kopf-/Fusszeilen, doppelte Klauselnummern und mehrdeutige Zitate, leere Seiten,
Bildtext, Vektortext sowie gemischte Seiten. Versicherungsinhalte sind frei erfunden.

## Metrikdefinitionen

R ist der Solltext, H der extrahierte Text. Für CER/WER werden Seiten verbunden und
Whitespace-Folgen auf ein Leerzeichen reduziert; keine Case-, Unicode-, Satzzeichen-
oder fachliche Normalisierung. Originaltexte und Evidence-Offsets bleiben unverändert.
d bezeichnet Levenshtein-Distanz. C ist ein Codepoint-Multiset; Schnitt zählt jeweils
min(Referenzhäufigkeit, Ausgabehäufigkeit).

| Metrik | Zähler / Nenner |
| --- | --- |
| Character Error Rate | d(R,H) / Anzahl Codepoints in R |
| Word Error Rate | d(tokens(R),tokens(H)) / Anzahl whitespacegetrennter Tokens in R |
| Text Completeness | Anzahl gemeinsamer Nicht-Whitespace-Codepoints / Anzahl Referenz-Codepoints ohne Whitespace |
| Unicode Integrity | Anzahl gemeinsamer Nicht-ASCII-Codepoints / Anzahl Nicht-ASCII-Codepoints in R |
| Reading Order Accuracy | korrekt geordnete Paare eindeutig gefundener Soll-Textblöcke / alle Paare dieser gefundenen Blöcke |
| Reading Order Anchor Coverage | eindeutig gefundene Soll-Textblöcke / Anzahl Soll-Textblöcke |
| Clause Boundary Accuracy | exakt passende Klauseln (ID, Seiten, Zitate und Teile) / annotierte Klauseln |
| Table Cell Extraction Accuracy | exakt passende Zellen (Tabelle, Seite, Zeile/Spalte, Spans, Text, Headerflag) / annotierte Zellen |
| Table Header-to-Value Association | korrekte annotierte Links mit korrekter Header- UND Wertzelle / annotierte Links |
| Evidence Span Validity | gültige Kandidaten mit exakter Rohtext-Spanne / ausgegebene Kandidaten |
| Page Reference Accuracy | Kandidaten mit richtiger physischer Sollseite / ausgegebene Kandidaten |
| Missing Evidence Rate | Sollzitate ohne gültigen, textgleichen Kandidaten auf richtiger Seite / Sollzitate |
| Extraction Failure Rate | Wiederholungen mit Status ausser success/partial / alle Wiederholungen |
| Partial Extraction Rate | Wiederholungen mit Status partial / alle Wiederholungen |
| Reproducibility | Extraktionsfingerprints gleich erstem Lauf / Anzahl weiterer Wiederholungen |
| Runtime per Document | Summe Millisekunden für Ingestion plus verifizierten Reload / Wiederholungen |
| Expected Status Match (Zusatzdiagnose) | erster Status gleich verfasster Erwartung (0/1) / 1 |

Nenner 0 ergibt not_evaluable mit Begründung und ohne Zahlenwert. Fehlende
Parserfähigkeit ergibt unsupported, niemals künstlich 0 oder 1. Kein Baseline-Artefakt
ergibt Reproducibility=not_evaluable; spätere fehlgeschlagene Läufe zählen als Abweichung.
Nicht extrahierbare Negativfälle zählen in Failure Rate auch dann, wenn ihr Zustand
erwartet ist. Das misst Textverfügbarkeit, nicht nur Softwaredefekte.

Aggregation pro Layout und insgesamt ist ein **Mikromittel**: Summe messbarer Zähler /
Summe zugehöriger Nenner. Zusätzlich stehen Fallzahlen für measured, unsupported und
not_evaluable. Fehlende Fähigkeiten werden nicht in erfolgreiche Nenner eingeschlossen.
Es gibt keinen Gesamtqualitätsscore. CER/WER können wegen Einfügungen grösser als 1 sein.
Vollständigkeit und Unicode Integrity sind nur Zeichen-Retention: Reihenfolge,
zusätzliche Zeichen und semantische Bedeutung werden damit nicht geprüft.
Deshalb immer zusammen mit CER/WER und Fundstellen betrachten.

Reading Order misst ausschliesslich die Reihenfolge exakt auffindbarer Textanker im
serialisierten Text (physische Seite, Rohtext-Offset). Fehlende/mehrdeutige Anker werden
aus den Paaren ausgeschlossen und separat über Anchor Coverage sichtbar.
Dies ist kein Nachweis einer geometrisch rekonstruierten Layoutstruktur.

pypdf liefert in diesem Adapter keine Klausel-/Tabellenstruktur: die drei betreffenden
Metriken bleiben unsupported bei annotierten Fällen. Die implementierten Scorer sind
mit expliziten richtigen und falschen Strukturbeispielen getestet. Ein späterer Adapter
muss IDs vorab zuordnen; diese recallartigen Scores bestrafen zusätzliche Strukturen
noch nicht. Vor einem produktiven Strukturvergleich sind Precision-Metriken nötig.

## Fundstellen und Vertrauensgrenzen

Der aktuelle Evidence-Adapter ist ein **goldgestützter exakter Zitat-Locator**:
Er sucht bekannte Sollzitate in allen Rohtextseiten. Nur ein eindeutig auftretendes
Zitat erzeugt einen Kandidaten; die Sollseite wird nicht als Suchhilfe verwendet.
Mehrdeutige und fehlende Zitate bleiben sichtbar. Offset ist ein Unicode-Zeichenindex,
end exklusiv. Kandidaten enthalten Sollziel, Seite, start/end und Zitat.

Die Ingestion verifiziert Original-, Manifest- und Extraktionshashes und reproduziert
beim Reload den Parsertext. Report enthält Receipt und vollständiges Extraktionsartefakt;
gespeicherte Stores erlauben unabhängiges Nachprüfen. Evaluationskandidaten vergeben
keinen produktiven Verifikationsstatus. Ein gültiger Span beweist weder semantisch
richtige Interpretation noch die vollständige Erfassung von Ausnahmen.

## Fehlerklassen

| Klasse | Auslöser |
| --- | --- |
| missing_text | Completeness < 1 |
| incorrect_reading_order | messbare Ankerreihenfolge < 1 |
| table_structure_lost | Zellscore < 1 oder fehlende Strukturfähigkeit |
| incorrect_value_association | Header/Wert-Score < 1 oder fehlende Fähigkeit |
| broken_clause_boundary | Klauselscore < 1 oder fehlende Fähigkeit |
| invalid_evidence_span | Spanvalidität < 1 |
| incorrect_page_reference | Seitenreferenzgenauigkeit < 1 |
| unicode_corruption | Unicode-Retention < 1 |
| extraction_failure | kein success/partial-Textresultat |

Mehrere Klassen pro Fall sind möglich. basis=measured unterscheidet beobachtete
Abweichungen von basis=capability_gap. Fehlende/mehrdeutige Zitate, abweichender
Sollstatus und einzelne Seitenfehler erscheinen zusätzlich als Diagnose.
Diese Taxonomie ist keine vollständige Erkennung jeder möglichen Fehlerursache.

## Vergleichbarkeit und Reproduzierbarkeit

Report speichert Schema-/Corpus-/Metrikversion, PDF-/Gold-Hashes, Generator/Font-SHA,
Parser-/Paketversionen, Konfiguration, Git-Commit/Dirty-Zustand, Python, Plattform,
UTC-Zeitstempel und Rohzeiten. Unbekannte Git-Metadaten bleiben null mit Begründung.

comparison_key bindet Korpusbytes, Sollwerte, Metrikversion und Konfiguration.
Nur gleiche Schlüssel erlauben Deltas (aktuell minus vorher); Parser-/Codeversionen
dürfen verschieden sein. Historische Reports werden schema- und hashgeprüft, Aggregate
gegen Falldaten validiert. Hashes sind Integritätschecks, keine Signaturen.
Zeitwerte werden nicht automatisch zwischen Maschinen verglichen.
quality_sha256 entfernt Zeit-/Umgebungsmetadaten und Laufzeitwerte, behält aber
Extraktion und Qualitätsdaten. Wiederholte frische Läufe müssen denselben Fingerprint
liefern. Andere Plattformen/Renderer können andere PDF-Bytes erzeugen; dann sind
Läufe ausdrücklich nicht vergleichbar, statt stillschweigend zusammengeführt zu werden.

## Grenzen und weitere Evaluation

Der kleine Korpus verwendet eine Fontfamilie und kontrollierte Layouts. Er deckt keine
realistische Vielfalt von AVB, Ligaturen, komplexen Font-CMaps, Handschrift oder
beschädigten Dokumenten ab; entsprechende Integritätsfälle sind separat in Sprint 2
getestet. PDF-Grössen-/Seitenlimits ersetzen keine isolierten CPU-/RAM-/Zeitlimits.
Leere Seiten können nichttextuelle PDF-Operatoren enthalten. success kann trotz
verlorenem Bildtext auftreten; Textstatus ist kein Vollständigkeitsbeweis.

Vor einem Parservergleich: gleichen unveränderten Korpus verwenden, weiteren Adapter
mit explizitem Fähigkeitsvertrag entwickeln, Layoutkoordinaten und Offsetabbildung
erhalten, Metrikversionen fixieren, passende Struktur-Precision hinzufügen.
Keine automatische Reparatur der Sollwerte oder semantische Ableitung aus Textscore.

Nach dem Gate für echte Daten: fachlich doppelt annotierte Quellen, Konfliktklärung,
produktgetrennte Entwicklungs-/Testsplits, Unknown-Recall, false excluded,
Ontologie-/Betrag-/Währungs-/Basisübereinstimmung und semantisch stützende Zitate.
Freigabeschwellen bestimmen Domänenverantwortliche. Sprint-1-/2-Regressionen zu
Hashintegrität, Ressourcenlimits, Identitätsbindung und Demo bleiben vollständig bestehen.

## Sprint 4: gepaarter Parservergleich

axiory-eval und seine bestehenden Ergebnisse bleiben unverändert reproduzierbar.
Die separate opt-in CLI axiory-parser-benchmark verwendet denselben Korpus und
Metrikversion 2; sie erweitert die Auswertung um Struktur-Precision/Recall,
Parserlaufzeiten, Provenienz-Gates und fallweise Vor-/Nachteile. Neue PypdfAdapter-
Schema-2-Artefakte bewahren exakt die bisherigen Seitentexte, ändern aber bewusst
Artefaktformat und Extraktionshash. Alte Referenzen werden nicht migriert.

Die Tabellen-Zellmetriken verlangen keine ungesicherten Headerflags. Daher sind
sie nicht identisch mit dem strengeren Sprint-3-Tabellenscore. Header-Kanten und
Klauselgrenzen bleiben unsupported; zusätzliche Tabellenzellen senken Precision.
Originale und Sollwerte werden auf Hashgleichheit zwischen beiden Parsern geprüft.

Definitionen, Entscheidungsregel, Lizenzkontext und gemessene Berichte:
[PARSER_BENCHMARK](PARSER_BENCHMARK.md). Der Vergleich enthält keine erfundenen
Signifikanzen, keinen gewichteten Gesamtscore und keine Produktionsfreigabe.

## Separate Semantik-Evaluation

Sprint 5 ergänzt einen unabhängigen 120-Fälle-Korpus. Dieser Layoutgoldstandard
bleibt unverändert. Verfahren, Zähler/Nenner und Grenzen des Offline-Mock-Vergleichs:
[LLM_EVALUATION](LLM_EVALUATION.md).
