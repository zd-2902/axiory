# ADR 0007 – Versionierte Korrekturen nach dem Live-Pilot

- Status: angenommen
- Datum: 2026-10-15

## Kontext

Der erste vollständige 24-Fälle-Pilot zeigte einen Regexfehler bei Satzpunkten,
inkonsistente nullable Geldfelder, falsches Zurückhalten korrekter unknown-Kandidaten
und semantische Fehler bei Tabellen und Bedingungen. Historische Rohantworten,
Requests, Hashes und Ergebnisse müssen weiterhin exakt replaybar bleiben.

## Entscheidung

`experiment-config-2` bindet `protocol_version=pilot-fixes-2`; der CLI-Standard ist
`datasets/multilingual/pilot-config-v2.json`. Die unveränderte v1-Konfiguration bleibt
explizit wählbar. Manifest und Sessionjournal binden die Konfiguration; Replay wählt
Schemas, Prompts, Quellenprüfung und Gates aus dieser versionierten Konfiguration.
Unbekannte Konfigurationsversionen werden abgelehnt. Keine Migration gespeicherter
v1-Dateien, keine Änderung an Gold, Ontologie travel-2 oder kanonischem CandidateV2.

Das v2-Provider-Schema verwendet statusabhängige verschachtelte anyOf-Alternativen.
Ein Limit ist ein vollständiges Objekt aus amount/currency/basis oder null.
unknown/excluded lassen keine Geldangaben zu. Nach DTO-Validierung erfolgt eine
verlustfreie Abbildung in CandidateV2 und erneute Fachvalidierung. Raw Replies werden
vorher gespeichert. Unzulässige Werte werden nicht ergänzt, entfernt oder repariert.
Die offizielle [Structured-Outputs-Dokumentation](https://developers.openai.com/api/docs/guides/structured-outputs)
beschreibt verschachtelte anyOf-Alternativen; semantische Wahrheit garantiert sie nicht.

Die v2-Zahlenprüfung akzeptiert Satzzeichen und explizite Schweizer Gruppierungen
(Apostroph, typografisches Apostroph, Leerzeichen/NBSP) sowie Dezimalpunkt/-komma mit
maximal zwei Stellen. Mehrdeutige Gruppierung wie 1.875 oder 1,875, Datumsangaben,
negative Zahlen, IDs und Fragmente werden nicht als Beträge ausgegeben. CHF und Betrag
müssen wie bisher im verifizierten Zitat vorhanden sein. Das beweist keine Beziehung
zwischen Tabellenzeile, Betrag und Deckungsart. Quellenbytes/Offsets werden nie normalisiert.

v2-Reviews bestätigen einen quellengestützt unbekannten Status ausdrücklich mit
`supported_unknown`; `supported` gilt für covered/excluded. `insufficient_evidence`
bleibt eine Ablehnung und wird nicht automatisch umgedeutet. Beide Reviewgates müssen
korrekten Kandidatenstatus, Quellenprüfung und alle sechs unterschiedlichen Checks
bestehen. Ein supported_unknown-Urteil für covered/excluded ist ungültig. Menschliche
Freigabe bleibt ungesetzt. Legacy-Urteile und v1-Gates bleiben unverändert.

Alle drei Prompts erhalten Version 2. Zusätzliche Anweisungen betreffen die Zuordnung
von Tabellenzeilen, vollständige Bedingungsatome, gleichrangige Widersprüche und das
Verbot erfundener Ausschlussatome. Keine zusätzlichen Agenten, Modelle oder Abhängigkeiten.

## Evaluation und Grenzen

Regressionen prüfen die Schutzmechanismen, nicht Modellintelligenz. Die bekannten
Tabellen-/Bedingungsfehler können mit einem fälschlich supported urteilenden Modell
weiterhin alle Gates passieren; entsprechende Tests halten diese Grenze sichtbar.
Historische Metriken bleiben unverändert. `scripts/reassess_pilot_sources.py` verifiziert
zuerst den ursprünglichen Replay und erzeugt ein separates, nicht überschreibbares
OFFLINE_SOURCE_REASSESSMENT mit Originalmanifest-/Kandidatenreferenzen. Es repariert
keine Rohantwort und interpretiert kein Review um.

Bekannte Pilotfälle sind jetzt Entwicklungsfälle. Ein erneuter Live-Lauf ist ein
diagnostischer Vergleich unter dem verbleibenden Gesamtbudget, kein unabhängiger
Holdoutnachweis. Für Modellfreigabe fehlen neue Testfamilien und unabhängiger Fachreview.
Keine automatische kostenpflichtige Vollkorpusausführung.
