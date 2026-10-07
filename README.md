# Axiory

B2B Insurance Intelligence Engine für nachvollziehbare Versicherungsvergleiche.
Das erste MVP soll öffentlich zugängliche AVB und Produktinformationen Schweizer
Reiseversicherungen strukturieren. Dieses Repository enthält zunächst **nur synthetische
Daten**, validierte Domänenmodelle und eine deterministische CLI-Demo.

## Installation

Voraussetzungen: Git, Python 3.12+ und [uv](https://docs.astral.sh/uv/getting-started/installation/).
Die Referenzumgebung ist Python 3.12, festgelegt in `.python-version`.
Nach dem Klonen im Repository-Verzeichnis:

```sh
uv python install 3.12
uv sync --locked --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run axiory-demo
```

Alternativ: `uv run python -m axiory.demo`. Die Demo schreibt deterministisches JSON
nach stdout: zwei fiktive Produkte, Annullierungslimiten von CHF 5'000 bzw. 8'000,
explizit ausgeschlossenes Gepäck und unbekannte medizinische Deckung. Vollständige
synthetische Quelltexte, SHA-256-Hashes und Fundstellen sind enthalten.
Es braucht weder API-Schlüssel noch Netzwerkzugriff zur Ausführung nach Installation.

Für Codex Cloud dient `sh scripts/setup.sh` als Setup-Befehl. Während des Setups
müssen Python-/Paketdownloads erlaubt sein; anschliessend funktionieren Tests und
Demo offline. `uv.lock` fixiert die Python-Abhängigkeiten; CI nutzt uv 0.12.23.
Abhängigkeiten bewusst mit `uv lock --upgrade` aktualisieren und danach prüfen.

## Struktur

```text
src/axiory/        Modelle, mechanische Provenienzprüfung, Demo/CLI
tests/            Modellinvarianten, Quellenintegrität, CLI
docs/             Produkt, Architektur, Roadmap, Evaluation, ADRs
datasets/         Datenregeln; noch keine echten Versicherungsdaten
scripts/          Reproduzierbares Cloud-Setup
.github/workflows/ci.yml
```

## Prinzipien und Grenzen

Jede positive oder negative Deckungsaussage benötigt Evidenz. `unknown` ist keine
Ablehnung; fehlende Beträge bedeuten auch nicht unbegrenzte Deckung. Aussagen erhalten
erst nach mechanischer Prüfung den Status `source_matched`. Das ist keine semantische
oder juristische Bestätigung. Geldbeträge werden als Decimal verarbeitet und als
JSON-Strings ausgegeben. Vergleiche behalten Bedingungen und Bezugsgrössen bei.

Noch nicht implementiert: Download/Ingestion, PDF/OCR, persistente Artefakte,
LLM-Extraktion, fachlich geprüfte Ontologie und manuelle Freigabe. Die Demo baut
strukturierte Fixtures; sie extrahiert keine Texte automatisch und erstellt kein Ranking.
Pydantic validiert Struktur und Invarianten, nicht Wahrheit. Echte Daten bleiben bis
zum Ingestion-/Provenienz-Gate in [ROADMAP](docs/ROADMAP.md) ausgeschlossen.

**Nächster Schritt:** versionierte Ingestion mit unveränderten Quelldateien,
Abrufmetadaten, Hashes und reproduzierbarer Text-/Seitenzuordnung implementieren.
Danach einen manuell annotierten Evaluationssatz aufbauen.

Details: [Produkt](docs/PRODUCT.md), [Architektur](docs/ARCHITECTURE.md),
[Evaluation](docs/EVALUATION.md), [ADRs](docs/adr/0001-evidence-first-foundation.md).
Lizenz und Distributionsmodell sind noch nicht festgelegt.
