import json
import subprocess
import sys
from datetime import UTC, date, datetime
from hashlib import sha256

import pytest
from pydantic import ValidationError

from axiory.demo import build_demo
from axiory.ingestion import DocumentStore, IntegrityError, ParserVersionError
from axiory.ingestion_models import (
    LogicalDocument,
    PdfEvidence,
    VersionMetadata,
)
from axiory.models import Claim, Coverage, Document
from axiory.provenance import verify_source
from tests.pdf_fixtures import synthetic_pdf


@pytest.fixture
def document():
    return LogicalDocument(
        id="synthetic-conditions",
        product_id="travel-a",
        title="SYNTHETIC conditions",
        kind="policy_conditions",
        synthetic=True,
    )


@pytest.fixture
def store(tmp_path):
    return DocumentStore(tmp_path / "store")


def evidence_for(stored, page_number=1, quote=None):
    text = stored.extraction.pages[page_number - 1].text
    quote = text if quote is None else quote
    start = text.index(quote)
    return PdfEvidence(
        id="synthetic-evidence",
        document_id=stored.document.id,
        version_sha256=stored.receipt.version_sha256,
        extraction_sha256=stored.receipt.extraction_sha256,
        page_number=page_number,
        start_char=start,
        end_char=start + len(quote),
        quote=quote,
    )


def replace_json(store, collection, digest, mutate):
    """Simulate an attacker recomputing hashes, not just accidental corruption."""
    data = json.loads((store.root / collection / f"{digest}.json").read_bytes())
    mutate(data)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    new_digest = sha256(raw).hexdigest()
    (store.root / collection / f"{new_digest}.json").write_bytes(raw)
    return new_digest


def with_extraction(store, receipt, change):
    stored = store.load(receipt)
    replacement = replace_json(store, "extractions", stored.receipt.extraction_sha256, change)
    return replace_json(
        store, "receipts", receipt, lambda data: data.update(extraction_sha256=replacement)
    )


def test_multipage_roundtrip_original_bytes_and_stable_evidence(store, document):
    original = synthetic_pdf("  SYNTHETIC Ã„pfel und GepÃ¤ck.  ", "SYNTHETIC Seite zwei")
    receipt = store.ingest(
        original,
        document,
        source_url="https://example.invalid/synthetic.pdf",
        retrieved_at=datetime(2026, 10, 7, 10, tzinfo=UTC),
        metadata=VersionMetadata(declared_version="test-v1", valid_from=date(2026, 1, 1)),
    )
    stored = DocumentStore(store.root).load(receipt)
    assert stored.extraction.status == "success"
    assert [page.number for page in stored.extraction.pages] == [1, 2]
    assert stored.extraction.pages[0].text == "  SYNTHETIC Ã„pfel und GepÃ¤ck.  "
    assert stored.version.declared_version == "test-v1"
    assert stored.version.valid_from == date(2026, 1, 1)
    assert stored.acquisition.retrieved_at == datetime(2026, 10, 7, 10, tzinfo=UTC)
    assert str(stored.acquisition.source_url) == "https://example.invalid/synthetic.pdf"
    assert stored.version.original_sha256 == sha256(original).hexdigest()
    assert (
        store.root / "originals" / f"{sha256(original).hexdigest()}.pdf"
    ).read_bytes() == original
    for page in (1, 2):
        evidence = evidence_for(stored, page)
        reloaded = PdfEvidence.model_validate_json(evidence.model_dump_json())
        DocumentStore(store.root).verify_evidence(receipt, reloaded)


def test_determinism_duplicates_and_distinct_acquisitions(store, document, tmp_path):
    original = synthetic_pdf("SYNTHETIC document")
    assert synthetic_pdf("SYNTHETIC document") == original
    first = store.ingest(original, document)
    assert store.ingest(original, document) == first
    other_store = DocumentStore(tmp_path / "independent")
    assert other_store.ingest(original, document) == first
    second = store.ingest(
        original,
        document,
        source_url="https://example.invalid/another.pdf",
        retrieved_at=datetime(2026, 10, 7, tzinfo=UTC),
    )
    assert second != first
    a, b = store.load(first), store.load(second)
    assert a.receipt.version_sha256 == b.receipt.version_sha256
    assert a.receipt.extraction_sha256 == b.receipt.extraction_sha256
    assert len(list((store.root / "originals").glob("*.pdf"))) == 1
    assert len(list((store.root / "versions").glob("*.json"))) == 1
    assert len(list((store.root / "extractions").glob("*.json"))) == 1
    assert a.acquisition.source_url is None and a.acquisition.retrieved_at is None
    assert a.version.declared_version is None and a.version.valid_from is None


def test_multiple_versions_and_metadata_revisions_are_append_only(store, document):
    first = store.ingest(synthetic_pdf("SYNTHETIC v1"), document)
    second = store.ingest(synthetic_pdf("SYNTHETIC v2"), document)
    third = store.ingest(
        synthetic_pdf("SYNTHETIC v1"),
        document,
        metadata=VersionMetadata(declared_version="published-label"),
    )
    a, b, c = (store.load(x) for x in (first, second, third))
    assert a.document.id == b.document.id == c.document.id
    assert len({x.receipt.version_sha256 for x in (a, b, c)}) == 3
    assert a.receipt.extraction_sha256 == c.receipt.extraction_sha256
    assert a.version.original_sha256 != b.version.original_sha256
    assert store.load(first) == a
    assert len(list((store.root / "originals").glob("*.pdf"))) == 2


@pytest.mark.parametrize(
    "collection,attribute,suffix",
    [
        ("originals", "original_sha256", ".pdf"),
        ("extractions", "extraction_sha256", ".json"),
        ("versions", "version_sha256", ".json"),
        ("acquisitions", "acquisition_sha256", ".json"),
        ("documents", "document_sha256", ".json"),
    ],
)
def test_manipulated_stored_artifact_rejected(store, document, collection, attribute, suffix):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    stored = store.load(receipt)
    owner = (
        stored.version if attribute in ("original_sha256", "document_sha256") else stored.receipt
    )
    path = store.root / collection / f"{getattr(owner, attribute)}{suffix}"
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(IntegrityError, match="Hash mismatch"):
        store.verify_evidence(receipt, evidence_for(stored))


def test_rehashed_fabricated_extraction_is_not_trusted(store, document):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    forged = with_extraction(
        store, receipt, lambda data: data["pages"][0].update(text="invented coverage")
    )
    with pytest.raises(IntegrityError, match="cannot be reproduced"):
        store.load(forged)


@pytest.mark.parametrize(
    "mutation,error",
    [
        (lambda data: data.update(parser_version="0.0.0"), ParserVersionError),
        (lambda data: data.update(original_sha256="0" * 64), IntegrityError),
        (lambda data: data["pages"][0].update(number=2), ValidationError),
        (lambda data: data["pages"][0].update(number=True), ValidationError),
        (lambda data: data.update(verification="source_matched"), ValidationError),
        (lambda data: data.update(status="encrypted"), ValidationError),
    ],
)
def test_untrusted_extraction_metadata_rejected(store, document, mutation, error):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    forged = with_extraction(store, receipt, mutation)
    with pytest.raises(error):
        store.load(forged)


@pytest.mark.parametrize(
    "changes",
    [
        {"page_number": 2},
        {"start_char": 1, "end_char": 10},
        {"end_char": 100, "quote": "x" * 100},
        {"quote": "X" * 9},
        {"document_id": "wrong"},
        {"version_sha256": "0" * 64},
        {"extraction_sha256": "0" * 64},
    ],
)
def test_invalid_evidence_references_and_spans(store, document, changes):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    payload = evidence_for(store.load(receipt)).model_dump()
    evidence = PdfEvidence.model_validate({**payload, **changes})
    with pytest.raises(IntegrityError):
        store.verify_evidence(receipt, evidence)


@pytest.mark.parametrize(
    "changes",
    [
        {"start_char": -1},
        {"page_number": 0},
        {"page_number": True},
        {"start_char": "0"},
        {"end_char": 0},
        {"quote": "wrong-length"},
        {"extra": "untrusted"},
        {"version_sha256": "../escape"},
    ],
)
def test_pdf_evidence_strict_validation(store, document, changes):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    with pytest.raises(ValidationError):
        PdfEvidence.model_validate({**evidence_for(store.load(receipt)).model_dump(), **changes})


@pytest.mark.parametrize(
    "original,expected,page_statuses",
    [
        (b"", "empty", []),
        (b"not a PDF", "damaged", []),
        (b"%PDF-1.7\nbroken", "damaged", []),
        (synthetic_pdf(encrypted=True), "encrypted", []),
        (synthetic_pdf("SYNTHETIC secret", encrypted=True), "encrypted", []),
        (synthetic_pdf(), "empty", []),
        (synthetic_pdf(None), "empty", ["empty"]),
        (synthetic_pdf("[image]"), "needs_ocr", ["needs_ocr"]),
        (synthetic_pdf("[vector]"), "not_extractable", ["not_extractable"]),
        (synthetic_pdf("[broken-stream]"), "not_extractable", ["error"]),
        (
            synthetic_pdf("SYNTHETIC first", "[broken-stream]", "SYNTHETIC third"),
            "partial",
            ["text", "error", "text"],
        ),
        (
            synthetic_pdf("SYNTHETIC first", None, "[image]"),
            "partial",
            ["text", "empty", "needs_ocr"],
        ),
    ],
)
def test_explicit_failure_states_preserve_originals_and_all_pages(
    store, document, original, expected, page_statuses
):
    receipt = store.ingest(original, document)
    stored = DocumentStore(store.root).load(receipt)
    assert stored.extraction.status == expected
    assert [page.status for page in stored.extraction.pages] == page_statuses
    assert (
        store.root / "originals" / f"{sha256(original).hexdigest()}.pdf"
    ).read_bytes() == original
    if expected == "partial":
        store.verify_evidence(receipt, evidence_for(stored, 1))
        assert stored.extraction.pages[2].text or page_statuses[2] == "needs_ocr"


def test_no_evidence_for_empty_page(store, document):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC", None), document)
    evidence = evidence_for(store.load(receipt))
    evidence = PdfEvidence.model_validate({**evidence.model_dump(), "page_number": 2})
    with pytest.raises(IntegrityError):
        store.verify_evidence(receipt, evidence)


def test_storage_failure_does_not_discard_original_or_publish_receipt(store, document, monkeypatch):
    original = synthetic_pdf("SYNTHETIC")
    put = store._put

    def fail_extraction(collection, data, suffix=".json"):
        if collection == "extractions":
            raise OSError("synthetic disk failure")
        return put(collection, data, suffix)

    monkeypatch.setattr(store, "_put", fail_extraction)
    with pytest.raises(OSError, match="disk failure"):
        store.ingest(original, document)
    assert (
        store.root / "originals" / f"{sha256(original).hexdigest()}.pdf"
    ).read_bytes() == original
    assert not (store.root / "receipts").exists()
    monkeypatch.setattr(store, "_put", put)
    assert store.load(store.ingest(original, document)).extraction.status == "success"


def test_corrupted_existing_original_is_not_overwritten(store, document):
    original = synthetic_pdf("SYNTHETIC")
    receipt = store.ingest(original, document)
    path = store.root / "originals" / f"{sha256(original).hexdigest()}.pdf"
    path.write_bytes(b"corrupt")
    with pytest.raises(IntegrityError, match="modified"):
        store.ingest(original, document)
    assert path.read_bytes() == b"corrupt"
    with pytest.raises(IntegrityError):
        store.load(receipt)


def test_missing_artifact_and_unsafe_receipt_id(store, document):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    stored = store.load(receipt)
    (store.root / "extractions" / f"{stored.receipt.extraction_sha256}.json").unlink()
    with pytest.raises(IntegrityError, match="Missing"):
        store.load(receipt)
    with pytest.raises(IntegrityError, match="identifier"):
        store.load("../outside")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"retrieved_at": datetime(2026, 10, 7)},
        {"retrieved_at": "2026-10-07T00:00:00Z"},
        {"source_url": "file:///private"},
    ],
)
def test_invalid_acquisition_metadata_before_persistence(store, document, kwargs):
    with pytest.raises(ValidationError):
        store.ingest(synthetic_pdf("SYNTHETIC"), document, **kwargs)
    assert list(store.root.iterdir()) == []


@pytest.mark.parametrize("synthetic", [False, 1, "true"])
def test_real_or_implicitly_synthetic_documents_rejected(document, synthetic):
    with pytest.raises(ValidationError):
        LogicalDocument.model_validate({**document.model_dump(), "synthetic": synthetic})


def test_invalid_validity_dates():
    with pytest.raises(ValidationError):
        VersionMetadata(valid_from=date(2026, 2, 1), valid_until=date(2026, 1, 1))


def test_claim_integration_ignores_imported_status_and_rejects_legacy_evidence(store, document):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    evidence = evidence_for(store.load(receipt))
    claim = Claim(
        id="synthetic-claim",
        product_id=document.product_id,
        coverage=Coverage(code="travel.baggage", status="excluded"),
        evidence=(evidence,),
        method="human",
        method_version="synthetic-test",
        verification="human_reviewed",
    )
    imported = Claim.model_validate_json(claim.model_dump_json())
    assert isinstance(imported.evidence[0], PdfEvidence)
    store.verify_claim(receipt, imported)
    wrong_product = Claim.model_validate({**claim.model_dump(), "product_id": "another-product"})
    with pytest.raises(IntegrityError):
        store.verify_claim(receipt, wrong_product)
    wrong_quote = PdfEvidence.model_validate({**evidence.model_dump(), "quote": "X" * 9})
    forged = Claim.model_validate({**claim.model_dump(), "evidence": (wrong_quote,)})
    with pytest.raises(IntegrityError):
        store.verify_claim(receipt, forged)
    legacy = Claim.model_validate(build_demo()["claims"][0])
    with pytest.raises(IntegrityError, match="Legacy"):
        store.verify_claim(receipt, legacy)
    legacy_doc = Document.model_validate(build_demo()["documents"][0])
    with pytest.raises(ValueError, match="PDF evidence"):
        verify_source(claim, legacy_doc, b"irrelevant")


def test_inline_scanned_image_and_empty_password_encryption(store, document):
    scan = store.load(store.ingest(synthetic_pdf("[inline-image]"), document))
    assert scan.extraction.status == "needs_ocr"
    encrypted = store.load(
        store.ingest(synthetic_pdf("SYNTHETIC", encrypted=True, password=""), document)
    )
    assert encrypted.extraction.status == "encrypted"


def test_evidence_survives_a_new_python_process(store, document, tmp_path):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC separate process"), document)
    evidence = evidence_for(store.load(receipt))
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(evidence.model_dump_json(), encoding="utf-8")
    code = (
        "import sys; from pathlib import Path; "
        "from axiory.ingestion import DocumentStore; "
        "from axiory.ingestion_models import PdfEvidence; "
        "e = PdfEvidence.model_validate_json(Path(sys.argv[3]).read_bytes()); "
        "DocumentStore(Path(sys.argv[1])).verify_evidence(sys.argv[2], e)"
    )
    subprocess.run(
        [sys.executable, "-c", code, str(store.root), receipt, str(evidence_path)],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "collection,field,value,receipt_field",
    [
        ("acquisitions", "version_sha256", "0" * 64, "acquisition_sha256"),
        ("versions", "document_id", "wrong-logical-document", "version_sha256"),
    ],
)
def test_rehashed_broken_manifest_references(
    store, document, collection, field, value, receipt_field
):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    stored = store.load(receipt)
    replacement = replace_json(
        store,
        collection,
        getattr(stored.receipt, receipt_field),
        lambda data: data.update({field: value}),
    )
    forged = replace_json(
        store,
        "receipts",
        receipt,
        lambda data: data.update({receipt_field: replacement}),
    )
    with pytest.raises(IntegrityError, match="reference mismatch"):
        store.load(forged)


def test_noncanonical_json_and_receipt_corruption_rejected(store, document):
    receipt = store.ingest(synthetic_pdf("SYNTHETIC"), document)
    path = store.root / "receipts" / f"{receipt}.json"
    raw = path.read_bytes() + b" "
    new_id = sha256(raw).hexdigest()
    (store.root / "receipts" / f"{new_id}.json").write_bytes(raw)
    with pytest.raises(IntegrityError, match="Noncanonical"):
        store.load(new_id)
    path.write_bytes(raw)
    with pytest.raises(IntegrityError, match="Hash mismatch"):
        store.load(receipt)
