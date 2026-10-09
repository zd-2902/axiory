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

Noch nicht implementiert: Netzwerk-Ingestion, OCR, LLM-Extraktion, UI, fachlicher
Review und produktiver Betrieb. PDF-Seitenreferenzen bieten keine visuellen Bounding
Boxes oder Tabellenstruktur. Parserupgrades benötigen versionierte Re-Extraktion.
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

**Nächster Schritt:** einen zweiten, koordinatenbewussten Parser am eingefrorenen
Korpus vergleichen und Struktur-/Zuordnungsmetriken ergänzen. Harte Ressourcenlimits
im isolierten Worker und kontrollierte Quellenaufnahme bleiben Voraussetzung für
reale Dokumente; keine LLM- oder UI-Erweiterung in diesem Sprint.

[Produkt](docs/PRODUCT.md) · [Architektur](docs/ARCHITECTURE.md) ·
[Evaluation](docs/EVALUATION.md) · [ADR 0002](docs/adr/0002-versioned-pdf-ingestion.md)

Lizenz und Distributionsmodell sind noch nicht festgelegt.

Review-Fixes: DocumentStore akzeptiert IngestionLimits (Standard 20 MiB / 200 Seiten).
Überschreitungen werfen ResourceLimitError, ohne ein neues Extraktionsergebnis zu
veröffentlichen. Eine Dokument-ID bleibt dauerhaft an ein Produkt gebunden;
Konflikte ergeben IdentityConflictError. Details und Konfiguration: [INGESTION](docs/INGESTION.md).
