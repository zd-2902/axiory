# Synthetische PDF-Ingestion verwenden

Installation wie in README: `uv sync --locked --dev`. Die API arbeitet lokal und
lädt keine URLs herunter. Die Text-Demo bleibt unter `uv run axiory-demo` verfügbar.

## Ausführbares Beispiel

Aus dem Repository-Verzeichnis mit `uv run python` ausführen (oder in einem lokalen
Skript speichern). Der synthetische Fixture-Generator gehört zu den Tests, nicht zur
installierten Bibliothek.

```python
from pathlib import Path

from axiory.ingestion import DocumentStore
from axiory.ingestion_models import LogicalDocument, PdfEvidence
from tests.pdf_fixtures import synthetic_pdf

store = DocumentStore(Path("datasets/ingestion"))
document = LogicalDocument(
    id="synthetic-avb",
    product_id="synthetic-travel",
    title="SYNTHETISCHE Bedingungen",
    kind="policy_conditions",
    language="de",
    synthetic=True,
)
original = synthetic_pdf("SYNTHETISCH: Beispielseite eins", "SYNTHETISCH: Beispielseite zwei")
receipt_id = store.ingest(original, document)
stored = store.load(receipt_id)
print(receipt_id, stored.extraction.status)

page = stored.extraction.pages[1]
evidence = PdfEvidence(
    id="synthetic-evidence",
    document_id=document.id,
    version_sha256=stored.receipt.version_sha256,
    extraction_sha256=stored.receipt.extraction_sha256,
    page_number=page.number,
    start_char=0,
    end_char=len(page.text),
    quote=page.text,
)
# Nach Prozessneustart anhand Receipt-ID und serialisierter Evidence:
reloaded = PdfEvidence.model_validate_json(evidence.model_dump_json())
DocumentStore(Path("datasets/ingestion")).verify_evidence(receipt_id, reloaded)
```

Für eine vorhandene synthetische PDF stattdessen
`Path("synthetic.pdf").read_bytes()` übergeben. Bei bekannten Metadaten akzeptiert
ingest zusätzlich source_url, retrieved_at (datetime mit Zeitzone) und
metadata=VersionMetadata(declared_version=..., valid_from=..., valid_until=...).
Im Beispiel gibt es keinen Abruf und kein veröffentlichtes Versionslabel: beide
bleiben unbekannt. Keine Zeiten aus der Systemuhr ergänzen.

Receipt-ID und serialisierte Evidence müssen vom aufrufenden Workflow aufbewahrt
werden. store.load prüft alle Artefakte inklusive erneuter Extraktion und ist
bewusst teurer als blosses Lesen eines Text-Caches.

## Ergebnisse richtig behandeln

| Status | Bedeutung |
| --- | --- |
| success | Jede Seite lieferte Text; keine Garantie fachlicher Vollständigkeit |
| partial | Mindestens eine Textseite und mindestens eine problematische/leere Seite |
| empty | Leere Eingabe, null Seiten oder ausschliesslich leere Seiten |
| needs_ocr | Kein Text; mindestens eine Seite mit Bildindikator |
| not_extractable | Kein nutzbarer Text, z.B. Vektorgrafik oder Seitenparserfehler |
| encrypted | Verschlüsselte PDF; auch bei möglichem leerem Passwort |
| damaged | PDF-/Seitenbaum konnte nicht gelesen werden |

Ein Receipt für encrypted/damaged dokumentiert einen Fehler; die Originalbytes bleiben
gespeichert. Bei partial problematische Seiten anzeigen und nicht als fehlende Deckung
interpretieren. Erfolgreiche Seiten gehen bei Fehlern anderer Seiten nicht verloren.
error_type enthält den Typ einer Parserausnahme, keine volatile Exception-Nachricht.

Integritätsverletzungen ergeben IntegrityError, invalide Schemas ValidationError,
abweichende Parser-Versionen ParserVersionError, Speicherfehler OSError.
Bei I/O-Fehlern existiert kein abgeschlossenes Receipt für diesen Lauf. Nach Behebung
mit gleichen Eingaben wiederholen. Beschädigte bestehende Artefakte werden nicht
ersetzt; dafür ist eine bewusste Wiederherstellung aus vertrauenswürdiger Quelle nötig.

datasets/ingestion ist von Git ausgeschlossen, PDFs zusätzlich global ignoriert.
Format, Migration, Grenzen: [ADR 0002](adr/0002-versioned-pdf-ingestion.md).

## Konfigurierbare Limits und Identitätskonflikte

Standard: 20 MiB PDF-Bytes und 200 Seiten. Beide Grenzen sind inklusiv und müssen
strikt positive Ganzzahlen sein. Beispielsweise:

```python
from pathlib import Path

from axiory.ingestion import DocumentStore, IdentityConflictError
from axiory.ingestion_models import IngestionLimits
from axiory.pdf_extraction import ResourceLimitError

store = DocumentStore(
    Path("datasets/ingestion"),
    limits=IngestionLimits(max_pdf_bytes=5 * 1024 * 1024, max_pages=50),
)
# Beim ingest/load/verify_* ResourceLimitError explizit als Ablehnung behandeln.
# exc.code: "pdf_size_exceeded" oder "page_count_exceeded"
# exc.actual / exc.limit enthalten Messwert und Grenzwert.
# IdentityConflictError bedeutet: Dokument-ID/Produktzuordnung widersprüchlich.
```

Grössenüberschreitung: keine Speicherung, kein Parsing. Seitenüberschreitung:
Original und Metadaten bleiben gespeichert, aber keine Extraktion/neues Receipt.
Die Ausnahmen werden nicht als erfolgreiche Extraktion zurückgegeben. Aufrufer müssen
sie anzeigen oder protokollieren. Eine Wiederholung mit bewusst angepassten Limits
ist möglich; alte erfolgreiche Receipts werden nicht gelöscht. Reloads und Evidence-
Prüfungen dürfen die aktuell konfigurierten Limits ebenfalls nicht umgehen.

Dokument-ID und Produkt werden dauerhaft gebunden. Ein anderes Produkt mit gleicher
ID löst IdentityConflictError aus, auch nach Neustart oder bei alten Snapshots ohne
Index. Metadatenrevisionen desselben Produkts sind weiterhin möglich. Für einen
Produktwechsel eine neue Dokument-ID verwenden. Bestehende widersprüchliche Daten
werden nicht automatisch repariert.

Diese Schranken ersetzen keine CPU-/Speicher-/Zeitlimits: Ein isolierter Worker
bleibt nötig. Insbesondere erfolgt die Seitenbaum-Analyse vor der Seitenzahlprüfung;
komprimierte Inhalte können deutlich mehr Speicher als ihre PDF-Bytes benötigen.
