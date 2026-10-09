# ADR 0003: Synthetische Layout-Evaluation und unabhängiger Goldstandard

- Status: angenommen für Sprint 3
- Datum: 2026-10-09
- Grundlage: ADR 0002; Sprint-3-Branch baut auf dem noch offenen PR #1 auf.
- Entscheidung: additive Evaluationsmodule, keine Änderung produktiver Provenienzschemas.

## Problem

Hash- und Spanintegrität beweisen nicht, dass PDF-Text vollständig und in sinnvoller
Reihenfolge extrahiert wurde. Ohne unabhängige Sollwerte können plausible Parsertexte
verlorene Ausnahmen, Tabellenbezüge und Bildtexte verdecken.

## Entscheidung

Ein vorab verfasster, versionierter Pydantic-Quellplan definiert 24 synthetische Fälle.
ReportLab rendert diesen Plan mit invariantem PDF-Modus und eingebettetem Vera-Font.
Der Font stammt aus dem gelockten Python-Paket; kein Systemfont-Download.
Renderer und Goldstandard teilen Quelldaten, importieren aber keine Parserresultate.
Visuelle PDF-Prüfung bleibt erforderlich, weil gemeinsame Quelldaten Renderfehler
allein nicht ausschliessen. Spalten-/Tabellenpaare trennen visuellen Aufbau und Paint-Order.

Separate GoldFixture-, Observation-, Metric- und CaseResult-Modelle behalten
Quellinhalt, Extraktion und noch nicht implementierte Fachinterpretation auseinander.
Strukturscores verlangen explizite strukturierte Ausgabe; pypdf bietet hier nur Text.
Tabellen-/Klauselwerte bleiben unsupported. Die Lesereihenfolge wird als begrenzter
Textanker-Proxy mit eigener Ankerabdeckung gemessen. Kein geometrischer Erfolg wird behauptet.

Jede Wiederholung verarbeitet die erzeugten Originalbytes durch den bestehenden
DocumentStore und verifizierten Reload in einem frischen Store. Originale, Gold,
Receipt, Extraktionsartefakt und Rohtext bleiben lokal erhalten. Der goldgestützte
Zitat-Locator ist eine offen bezeichnete Baseline, kein autonomer Claims-Extractor.
Er benutzt keine Sollseiten zum Auflösen mehrdeutiger Zitate.

JSON/Markdown berichten Zähler, Nenner, fehlende Fähigkeiten und Fehlerklassen.
Qualitätsfingerprints schliessen volatile Laufzeit-/Umgebungsdaten aus.
Ein Vergleichsschlüssel bindet Korpus, Generator, Sollwerte, Metrikversion und Limits.
Code-/Parserversionen bleiben als Vergleichsdimension erlaubt. Gespeicherte Reports
werden vor Vergleich validiert; Hashes attestieren keine vertrauenswürdige Herkunft.
Ausführliche Mathematik und Vertrauensgrenzen stehen in [EVALUATION](../EVALUATION.md).

## Abhängigkeiten und Alternativen

ReportLab ist eine zusätzliche direkte Laufzeitabhängigkeit für die installierte
Evaluations-CLI; Pillow und charset-normalizer sind transitiv gelockt.
Ein handgeschriebener Minimal-PDF-Generator wäre kleiner, würde aber Fonts,
Unicode und visuelle Tabellen nur unzureichend prüfen.
Eine neue Extraktionsbibliothek wird noch nicht eingeführt: zuerst pypdf messen.
Keine Datenbank, OCR, Web-API, LLMs oder Agenten.

[pypdf dokumentiert](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
fehlende PDF-Semantik und Grenzen bei Scans/Tabellen.
[ReportLab TrueType-Fonts](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/)
ermöglichen die eingebettete Schrift.

## Invarianten und Konsequenzen

- PDF-/Goldhash und Schema-/Corpus-/Metrikversion bleiben nachvollziehbar.
- Sollwerte dürfen nicht aus getesteten Parserausgaben entstehen.
- Leere Nenner und fehlende Fähigkeiten erhalten keinen erfundenen Zahlenwert.
- Stabile Hashes und gültige Spannen sind kein fachlicher Wahrheitsnachweis.
- Alle Daten bleiben synthetisch; generierte PDFs und lokale Stores gehören nicht in Git.
- Qualitätsfehler sind sichtbare Ergebnisse; ausgefallene/nicht reproduzierbare Läufe
  führen zusätzlich zu Exit 1. Fehler werden nicht als erfolgreiche Evaluation maskiert.
- Bestehende Store-, Identitäts-, Ressourcen- und Evidence-Invarianten bleiben erhalten.
- Grössen-/Seitenlimits begrenzen keine harte CPU-/RAM-/Zeitnutzung; isolierter Worker bleibt offen.
- Kleiner Korpus, eine Fontfamilie, goldgestützte Fundstellen und recallartige
  Strukturscores begrenzen die Aussagekraft. Kein Produktionsfreigabescore.

## Nächste Entscheidung

Einen koordinatenbewussten zweiten Parser an demselben Goldstandard vergleichen.
Vor Strukturvergleich zusätzliche Precision- und Zuordnungskriterien festlegen.
Parallel den isolierten Worker spezifizieren; echte Quellen erst nach dokumentiertem Gate.
