# Semantische Evaluation (Sprint 5)

Gemessen wurde **OFFLINE_SCRIPTED_MOCK**, kein echtes LLM. Der optionale reale
Provider ist über SDK-Vertragstests angebunden, aber es wurden keine kostenpflichtigen
Live-Aufrufe ausgeführt. Diese Ergebnisse belegen technische Abläufe und bekannte
Fehlerpfade, keine Versicherungsqualität und keinen wirtschaftlichen Verifier-Nutzen.

## Korpus und Unabhängigkeit

120 explizit annotierte synthetische Fälle unter datasets/semantic/gold-v1.json,
zwölf Szenarien in zehn Produktfamilien. Entwicklung: 72 Fälle/sechs Familien;
Holdout: 48 Fälle/vier andere Familien. Jede Familie enthält Deckung, Ausschluss,
Bedingung, Sublimit, Bezugsgrösse, Negation, Ausnahme, Mehrdeutigkeit, fehlende
Information, Widerspruch, Seitenübergang und eine vereinfachte textuelle Tabelle.
Die fünf travel-1-Kategorien und CHF sind vertreten. Quellen und semantische
Annotation sind festgeschrieben, nicht aus Extraktionsantworten abgeleitet.

Der bestehende Sprint-3-Layoutgoldstandard und PDF-Renderer wurden nicht geändert.
Die neuen Texte sind vereinfachtes Englisch. Familien teilen Templates; der Split
verhindert Produktleckage, aber nicht sprachliche Templateähnlichkeit. Keine fachliche
Zweitannotation, keine repräsentative DE/FR/IT-Stichprobe. Der Holdout ist eine
technische Regression, keine belastbare Generalisierungsmessung.

## Versuchsdesign

A: Enge Rulesbaseline mit expliziter Enthaltung ausserhalb ihrer Grammatik.
B: Skriptierter Mock-Extractor mit absichtlichen Fehlern bei Negation, Ausnahme,
Sublimit und Widerspruch. Keine Goldannotation als Input, aber bewusst bekannte
Fixturegrammatik. C: exakt dieselbe Extraktion plus separat gespeichertes Mock-
Verdict und experimentelles review_gate. Ein zurückgehaltener Claim wird als fehlend
gewertet, nicht korrigiert oder in unknown/excluded umgewandelt. Das vollständige
Ergebnis behält alle Claims. Beide Modi nutzen dieselben Original-PDFs und Kontexte.

Jeder Verifier-Lauf wird offline aus aufgezeichneten Rohantworten replayt. Verglichen
werden Claims, Verdicts und Fehler. Volatile Run-IDs, Call-Latenzen und Dateihashes
der Callrecords sind kein Teil des stabilen Qualitätsfingerprints.

## Metrikdefinitionen

Ein Fall hat genau eine erwartete Kategorie. Vollständig korrekt heisst gleicher
Status, Betrag/Währung/Basis/Sublimiten sowie gleiche Bedingungen/Ausschlüsse.
Freitextlisten werden hier als exakte Stringmengen verglichen: richtige Paraphrasen
können als Fehler zählen. Unknown-Reasons müssen vorhanden sein, ihre Formulierung
wird nicht als exakter Goldtext verlangt. Nullnenner ergeben null/unavailable.

| Metrik | Zähler / Nenner |
|---|---|
| Claim Precision | vollständig korrekte covered/excluded-Claims / ausgegebene covered/excluded-Claims |
| Claim Recall | dieselben korrekten Claims / Goldfälle covered/excluded |
| Coverage Status Accuracy | korrekter Status / alle Fälle; fehlende Ausgabe ist falsch |
| Limit Extraction Accuracy | vollständig richtige Limitgruppe inkl. Sublimiten / Goldfälle mit Limit |
| Evidence Support Accuracy | vollständig korrekte Claims mit verifizierten Spannen und allen Goldankern / ausgegebene Claims inkl. unknown |
| Unsupported Claim Rate | nicht vollständig gold-/evidenzgestützte Behauptungen / ausgegebene covered/excluded-Claims |
| False Exclusion Rate | fälschlich excluded / Goldfälle, die nicht excluded sind |
| Unknown Recall | richtig unknown / Gold-unknown |
| Critical Error Rate | Fälle mit falscher behaupteter Deckung/Ausschluss/Limite/Einschränkung oder Evidenz / alle Fälle |

Kritische Fehler zählen gefährliche Behauptungen, nicht konservative Enthaltung;
Claim Recall und Coverage Status Accuracy verhindern, dass Nullausgabe als gute
Gesamtleistung erscheint. Evidence Support nutzt unabhängige Goldanker plus
vollständige Claimkorrektheit, nicht nur den technischen source_matched-Status.

## Gemessene Offline-Ergebnisse

Alle folgenden Brüche haben **Fallzahl N=120**. Zähler/Nenner sind keine Schätzwerte.

| Metrik | Rules | Mock-Extractor | Mock + Verifier-Gate |
|---|---:|---:|---:|
| claim_precision | 50/50 | 60/100 | 60/60 |
| claim_recall | 50/90 | 60/90 | 60/90 |
| coverage_status_accuracy | 80/120 | 90/120 | 80/120 |
| limit_extraction_accuracy | 40/60 | 50/60 | 50/60 |
| evidence_support_accuracy | 80/120 | 80/120 | 80/80 |
| unsupported_claim_rate | 0/50 | 40/100 | 0/60 |
| false_exclusion_rate | 0/110 | 30/110 | 0/110 |
| unknown_recall | 30/30 | 20/30 | 20/30 |
| critical_error_rate | 0/120 | 40/120 | 0/120 |

Im Holdout (N=48): Precision 20/20 → 24/40 → 24/24, Recall 20/36 → 24/36 → 24/36;
kritische Fehler 0/48 → 16/48 → 0/48. Vollständige Dev-/Holdout-Nenner stehen im
[JSON-Snapshot](benchmarks/sprint5-summary.json). Die identischen Prozentsätze über
Splits sind durch die Templateverteilung bedingt und kein Generalisierungsbeleg.

Der Mock produziert 40 kritische Fehler: je zehn Negations-, Ausnahme-, Sublimit-
und Widerspruchsfälle. Der gezielt dafür programmierte Mock-Verifier hält alle 40
zurück. Deshalb steigt die Precision künstlich von 60/100 auf 60/60; Statusgenauigkeit
fällt von 90/120 auf 80/120. Unknown Recall bleibt 20/30, da ein zurückgehaltener
Widerspruch nicht automatisch zu unknown korrigiert wird. Das zeigt die Wirkung
eines Review-Gates, **nicht die Verbesserung durch einen echten Verifikationsagenten**.

## Kosten, Latenz und Messlücken

120 simulierte Extraktoraufrufe gegenüber 240 simulierten Aufrufen für Extraktor plus
Verifier, zusätzlich 240 offline Replayaufrufe. Keine bezahlten API-Aufrufe. Tokens,
Live-API-Kostenschätzungen und menschliche Reviewminuten sind nicht gemessen und
bleiben null mit measured_count=0; nicht als Nullverbrauch bzw. Nullaufwand ausgeben.
Der Report enthält pro Modus Summe, Zahl der Aufrufe, gemessene Anzahl und Fallzahl.
Latenz misst Provideraufruf plus Rohantwortpersistenz, nicht die gesamte Ingestion.
Die Mock-Laufzeit ist lokaler Python-/Dateisystemaufwand, keine Prognose für API-Latenz.
Ein Verifier-Nutzen unter realen Kosten-/Latenzbedingungen ist damit **offen**.

## Reproduktion und Berichte

```sh
uv run axiory-semantic-eval
uv run axiory-semantic-eval --output datasets/evaluation-semantic/repeat
```

Qualitätsfingerprint des Referenzlaufs: `5ed116194207ccb6105c831ce1e383066bfdd09d28570b2189a6da2817d7789f`.
Der stabile Fingerprint umfasst Goldhash, Fallresultate und Qualitätsmetriken;
Laufzeit, Umgebung und Run-IDs bleiben separat. report.json enthält einzelne
Fehlerfälle, Run-/Replay-IDs und Messlücken. Pro Fall sind vollständige verifizierbare
Originale, Kontexte, Requests und Rohantworten im zugehörigen Store verfügbar.
Die CI veröffentlicht diese synthetischen Artefakte zeitlich begrenzt; der versionierte
JSON-Snapshot dokumentiert die Messung, ersetzt aber keinen vollständigen Store.

Standard-CI führt Ruff, Tests, Demo, Layout- und Semantikbenchmark ohne API-Keys aus.
Ein separater Job installiert llm-openai und prüft Requests, strukturierte Antworten,
Kostenmessung, Retry-Klassifikation und Timeout-Verhalten mit In-Memory-HTTP.
Der PyMuPDF-Regressionsjob bleibt erhalten. Ein Live-Einzelfallpilot erfordert
ausdrückliche Aktivierung; siehe [LLM_EXTRACTION](LLM_EXTRACTION.md).

## Nächster Qualitätsgewinn

Neue, voneinander unabhängige synthetische Klauselfamilien in DE/FR/IT doppelt
annotieren, insbesondere verschachtelte Ausnahmen, verschiedene Limiten derselben
Zahl, Dokumentprioritäten und reale Tabellengeometrie. Holdout vor Promptanpassungen
fixieren. Dann budgetierten Live-Vergleich mit denselben Extraktorantworten für A/B,
konservativem Fehlergrading und erfasstem menschlichem Reviewaufwand ausführen.
Erst daraus Modell-/Verifierentscheidung und Freigabeschwellen ableiten.

## Ausgeführte Regressionen

Vollständige Suite mit llm-openai und experimental-pymupdf: **307 bestanden**.
Ruff Lint und Formatcheck bestanden; axiory-demo, axiory-eval und optionaler
axiory-parser-benchmark erfolgreich. Sprint-3-Fingerprint bleibt
f6a854948483cccde0c42e237e9963c3ad9843100b172bbd218dd3205f3e932d,
Sprint-4-Fingerprint bleibt
649c62251741506a839036c8473a3c597292dfe589831adf65f43b1e5b676bc8.
Die SDK-Tests nutzen ausschliesslich einen In-Memory-Transport. Benchmark-Exit 0
bedeutet erfolgreiche Ausführung, nicht ausreichende fachliche Qualität.

Standardinstallation ohne Extras: **269 bestanden, 38 bewusst übersprungen**
(33 PyMuPDF- und fünf OpenAI-SDK-Vertragstests). Die Extrasuite deckt alle 307 ab.
