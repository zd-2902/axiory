# Axiory

B2B Insurance Intelligence Engine für nachvollziehbare Versicherungsvergleiche.
Ziel des MVP sind öffentlich zugängliche AVB und Produktinformationen Schweizer
Reiseversicherungen. Aktuell werden ausschliesslich **synthetische Daten** verwendet.

## Installation und Qualität

Voraussetzungen: Git, Python 3.12+ und [uv](https://docs.astral.sh/uv/getting-started/installation/).
Referenzumgebung: Python 3.12, festgelegt in .python-version.

```sh
uv python install 3.12
uv sync --locked --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run axiory-demo
uv run axiory-eval
```

Codex Cloud: `sh scripts/setup.sh` als Setup-Befehl. Python-/Paketdownloads müssen
beim Setup erlaubt sein; danach laufen Tests und Demo offline. uv.lock fixiert die
Python-Abhängigkeiten, CI verwendet uv 0.12.23. Updates mit `uv lock --upgrade`
bewusst durchführen und die vollständigen Prüfungen wiederholen.

## Funktionen

Die deterministische Text-Demo (`uv run axiory-demo` oder
`uv run python -m axiory.demo`) gibt JSON für zwei fiktive Produkte aus:
Annullierung CHF 5'000 bzw. 8'000, expliziter Gepäckausschluss, unbekannte medizinische
Deckung, Originaltexte, Hashes und Fundstellen. Keine API-Schlüssel erforderlich.

Sprint 2 ergänzt eine lokale Python-API für **versionierte synthetische PDF-Ingestion**:
unveränderte Originalbytes, SHA-256, logische Dokumente, immutable Versionsmanifeste,
Quellmetadaten, seitenweise Texte mit Parser-Version und separate Extraktionshashes.
Exakte Evidence-Spannen werden nach erneutem Laden gegen die reproduzierte Extraktion
geprüft. Leere, gescannte, verschlüsselte und beschädigte PDFs erhalten explizite
Zustände; es gibt kein OCR. Ein Beispiel zum Ausführen steht in
[INGESTION](docs/INGESTION.md).

## Struktur

```text
src/axiory/models.py             Versicherungsmodelle und Legacy-Kompatibilität
src/axiory/demo.py               Bestehende synthetische Text-Demo
src/axiory/provenance.py         Legacy-UTF-8-Quellenprüfung
src/axiory/ingestion_models.py   Strikte PDF-/Versions-/Evidence-Schemas
src/axiory/pdf_extraction.py     Deterministischer pypdf-Adapter
src/axiory/ingestion.py          Dateispeicher, Ingestion, Reload, Verifikation
src/axiory/extraction/          Context, Provider, Evidence, Verifier und Replay
src/axiory/evaluation/          Synthetischer Korpus, Goldstandard, Metriken, Reports
tests/                          Synthetische PDF-Generatoren und Regressionen
docs/                           Produkt, Architektur, Roadmap, Evaluation, ADRs
datasets/                       Datenregeln; lokale Ingestion-Artefakte ignoriert
scripts/                        Reproduzierbares Cloud-Setup
.github/workflows/ci.yml         Linting, Formatprüfung, Tests, Demo und Benchmark
```

## Prinzipien und Grenzen

Unbekannte Deckung bleibt unknown; fehlende Limiten bedeuten nicht unbegrenzte Deckung.
Positive und negative Claims brauchen Evidenz. Schema-Konformität und Quellenabgleich
beweisen keine semantische oder juristische Richtigkeit. Importierte Verifikationsflags
sind keine Prüfnachweise. Geldbeträge verwenden Decimal; Bedingungen und Bezugsgrössen
bleiben Teil des Vergleichs. Die Ontologie ist noch provisorisch.

Noch nicht implementiert: Netzwerk-Ingestion, OCR, UI, fachlicher
Review und produktiver Betrieb. Die Legacy-PDF-Seitenreferenzen enthalten keine visuellen Bounding
Boxes; experimentelle Layoutartefakte ergänzen Geometrie und heuristische Tabellen. Parserupgrades benötigen versionierte Re-Extraktion.
Der lokale Store benötigt Hardlinks. Konfigurierbare Zulassungsgrenzen für PDF-Grösse
und Seitenzahl sind implementiert; harte CPU-/RAM-/Zeitlimits und Parser-Sandbox fehlen.
Echte Versicherungsdaten bleiben bis zur Freigabe des
[Ingestion-/Provenienz-Gates](docs/ROADMAP.md) ausgeschlossen.

## Layout-Benchmark (Sprint 3)

`uv run axiory-eval` erzeugt 24 synthetische PDFs und verarbeitet sie mit der
bestehenden Ingestion. JSON-/Markdown-Berichte liegen unter `datasets/evaluation/`;
je Lauf bleiben Originale, Goldannotation und überprüfbare Stores im run-*-Ordner.
Keine API-Schlüssel oder Systemfonts nötig. ReportLab und eingebettetes Vera sind
über uv.lock verfügbar. Tabellen-/Klauselstruktur bleibt beim pypdf-Adapter unsupported.
Die Text-/Fundstellenmetriken bewerten keine fachliche Versicherungsinterpretation.

Vergleich mit unverändertem Korpus:

```sh
uv run axiory-eval --output datasets/evaluation-next --compare datasets/evaluation/report.json
```

CLI-Optionen, Mathematik, Fehlerklassen und Vertrauensgrenzen:
[Evaluation](docs/EVALUATION.md), [ADR 0003](docs/adr/0003-layout-evaluation.md).
Die CI veröffentlicht die generierten synthetischen Reports und Stores als Artefakt.

## Multi-Parser-Experiment (Sprint 4)

Neue ParserProtocol-, PypdfAdapter- und PyMuPDFAdapter-Schnittstellen unter
src/axiory/parsers. Schema-2-Layoutartefakte ergänzen überprüfbare Blöcke, Zeilen,
Koordinaten und heuristische Tabellen. DocumentStore/Schema 1 bleiben unverändert;
LayoutStore nutzt dieselben Originale und Dokumentversionen mit neuen Receipts.

PyMuPDF ist wegen offener AGPL-/kommerzieller Lizenzstrategie **keine Standardabhängigkeit**:

```sh
uv sync --locked --dev --extra experimental-pymupdf
uv run --extra experimental-pymupdf axiory-parser-benchmark --allow-experimental-pymupdf
```

Vergleichsberichte: datasets/evaluation-parsers/comparison.json und comparison.md.
Derselbe unveränderte 24-Fälle-Goldstandard wird für beide Parser verwendet.
Details, Metrikdefinitionen und Grenzen: [Parserbenchmark](docs/PARSER_BENCHMARK.md),
[ADR 0004](docs/adr/0004-multi-parser-architecture.md).

**Offene Parserarbeit:** Sortierkonfigurationen und spaltenbewusste Ordnung gezielt
vergleichen, Struktur-Goldstandard erweitern und isolierten Worker entwickeln.
Lizenzstrategie und Ingestion-Gate bleiben vor echten Quellen erforderlich.

[Produkt](docs/PRODUCT.md) · [Architektur](docs/ARCHITECTURE.md) ·
[Evaluation](docs/EVALUATION.md) · [ADR 0002](docs/adr/0002-versioned-pdf-ingestion.md)

Lizenz und Distributionsmodell sind noch nicht festgelegt.

Review-Fixes: DocumentStore akzeptiert IngestionLimits (Standard 20 MiB / 200 Seiten).
Überschreitungen werfen ResourceLimitError, ohne ein neues Extraktionsergebnis zu
veröffentlichen. Eine Dokument-ID bleibt dauerhaft an ein Produkt gebunden;
Konflikte ergeben IdentityConflictError. Details und Konfiguration: [INGESTION](docs/INGESTION.md).

## Strukturierte Extraktion (Sprint 5)

```sh
uv run axiory-semantic-eval
```

120 separate synthetische Semantikfälle (72 Entwicklung/48 Holdout) vergleichen
Rules, deterministischen Mock-Extractor und ein experimentelles Verifier-Gate.
Der Benchmark läuft ohne API-Schlüssel; er misst **keine Live-LLM-Qualität**.
Neue travel-1-Claims bewahren Bedingungen, Ausschlüsse, Sublimiten und exakte
pdf-1-Fundstellen. Rohantworten, Prompts, Modellkennungen, Kosten-/Tokenmesslücken
und nachvollziehbare Korrekturversionen werden separat gespeichert. Der optionale
OpenAI-SDK-Adapter benötigt --live, explizite Modell-/Budgetwahl und ausschliesslich
synthetische Eingaben. Kein Live-Aufruf in Standardtests oder CI.

[Installation, Architektur und Replay](docs/LLM_EXTRACTION.md),
[Metriken und Ergebnisse](docs/LLM_EVALUATION.md),
[ADR 0005](docs/adr/0005-llm-extraction-architecture.md).

Nächster fachlicher Schritt: vielfältigere, doppelt annotierte synthetische DE/FR/IT-
Klauseln und Tabellen; danach ein begrenzter, ausdrücklich aktivierter Live-Vergleich
mit Fehleranalyse und Reviewaufwand. Worker-Isolation und Quellenfreigabe bleiben
Voraussetzung vor echten AVB. Verifier-Ausgaben sind keine fachliche Freigabe.

## Mehrsprachiger gepaarter LLM-Benchmark (Sprint 6)

120 zusätzliche synthetische DE/FR/IT-Fälle mit eingefrorenem 24-Fälle-Pilot. A extrahiert,
B prüft dieselbe gespeicherte Antwort, C ergänzt eine kritische Prüfung. Gemeinsames
Budgetjournal, Offline-Replay und explizite Gates; kein Agentenframework.

```sh
uv run axiory-real-eval --dry-run
uv run axiory-real-eval --all-offline --output datasets/evaluation-real/offline-120
uv run axiory-real-eval --replay datasets/evaluation-real/offline-120
```

Ohne --live keine API-Aufrufe. Der Live-Pilot benötigt OPENAI_API_KEY als Secret und
ist auf 24 Fälle/2 USD begrenzt; die 120 Fälle bleiben offline. Offline-Metriken sind
kein Nachweis echter Modellleistung. Goldannotation ist noch nicht unabhängig geprüft.
Neue Module: src/axiory/experiments; Freeze/Gold: datasets/multilingual.

Installation des optionalen SDK, Preisannahmen, Metrikdefinitionen und Grenzen:
[Real LLM Benchmark](docs/REAL_LLM_BENCHMARK.md),
[Ergebnisse](docs/SPRINT6_RESULTS.md), [ADR 0006](docs/adr/0006-real-llm-evaluation.md).
24-Fälle-Live-Pilot abgeschlossen: 64 Antworten, vier Schemafehler, geschätzte Kosten
0.060195 USD. Ergebnisse und Grenzen stehen im [Sprint-6-Bericht](docs/SPRINT6_RESULTS.md).
Nächster Schritt: Zahlenprüfung und unknown-Reviewgates korrigieren, Tabellen-/Bedingungsfehler
fachlich prüfen, bevor weitere bezahlte Evaluationen erwogen werden.
