"""Resource admission and persistent identity regressions, using synthetic PDFs only."""

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from threading import Barrier

import pytest
from pydantic import ValidationError

from axiory.ingestion import DocumentStore, IdentityConflictError, artifact_id, canonical_bytes
from axiory.ingestion_models import IngestionLimits, LogicalDocument, VersionMetadata
from axiory.pdf_extraction import ResourceLimitError, extract_pdf
from tests.pdf_fixtures import synthetic_pdf


@pytest.fixture
def document():
    return LogicalDocument(
        id="synthetic-identity",
        product_id="synthetic-product",
        title="SYNTHETIC limits fixture",
        kind="policy_conditions",
        synthetic=True,
    )


def changed_document(document, **changes):
    return LogicalDocument.model_validate({**document.model_dump(), **changes})


def test_oversized_pdf_is_rejected_before_parser_or_persistence(tmp_path, document, monkeypatch):
    original = synthetic_pdf("SYNTHETIC oversized")
    limits = IngestionLimits(max_pdf_bytes=len(original) - 1)
    store = DocumentStore(tmp_path, limits=limits)

    def forbidden_parser(*args, **kwargs):
        pytest.fail("Oversized input must never reach PdfReader")

    monkeypatch.setattr("axiory.pdf_extraction.pypdf.PdfReader", forbidden_parser)
    for operation in (
        lambda: store.ingest(original, document),
        lambda: extract_pdf(original, limits=limits),
    ):
        with pytest.raises(ResourceLimitError) as caught:
            operation()
        assert caught.value.code == "pdf_size_exceeded"
        assert caught.value.actual == len(original)
        assert caught.value.limit == len(original) - 1
    assert list(tmp_path.iterdir()) == []


def test_page_limit_rejects_before_text_and_preserves_original(tmp_path, document, monkeypatch):
    original = synthetic_pdf("SYNTHETIC one", "SYNTHETIC two", "SYNTHETIC three")
    store = DocumentStore(tmp_path, limits=IngestionLimits(max_pages=2))

    def forbidden_text(*args, **kwargs):
        pytest.fail("No page may be extracted after the count exceeds the limit")

    monkeypatch.setattr("pypdf._page.PageObject.extract_text", forbidden_text)
    with pytest.raises(ResourceLimitError) as caught:
        store.ingest(original, document)
    assert caught.value.code == "page_count_exceeded"
    assert (caught.value.actual, caught.value.limit) == (3, 2)
    assert (tmp_path / "originals" / f"{sha256(original).hexdigest()}.pdf").read_bytes() == original
    assert not (tmp_path / "extractions").exists()
    assert not (tmp_path / "receipts").exists()


def test_exact_boundaries_and_policy_changes_preserve_hashes(tmp_path, document):
    original = synthetic_pdf("SYNTHETIC one", "SYNTHETIC two")
    baseline = DocumentStore(tmp_path).ingest(original, document)
    strict = DocumentStore(
        tmp_path, limits=IngestionLimits(max_pdf_bytes=len(original), max_pages=2)
    )
    assert strict.ingest(original, document) == baseline
    assert strict.load(baseline).extraction.status == "success"
    assert extract_pdf(original) == extract_pdf(
        original, limits=IngestionLimits(max_pdf_bytes=len(original), max_pages=2)
    )


@pytest.mark.parametrize(
    "constraint,code",
    [
        ({"max_pdf_bytes": 1}, "pdf_size_exceeded"),
        ({"max_pages": 1}, "page_count_exceeded"),
    ],
)
def test_reload_and_reingestion_cannot_bypass_current_limits(tmp_path, document, constraint, code):
    original = synthetic_pdf("SYNTHETIC one", "SYNTHETIC two")
    receipt = DocumentStore(tmp_path).ingest(original, document)
    strict = DocumentStore(tmp_path, limits=IngestionLimits(**constraint))
    for operation in (lambda: strict.load(receipt), lambda: strict.ingest(original, document)):
        with pytest.raises(ResourceLimitError) as caught:
            operation()
        assert caught.value.code == code
    # No replacement result or changed receipt after rejection.
    assert len(list((tmp_path / "receipts").glob("*.json"))) == 1
    assert DocumentStore(tmp_path).load(receipt).extraction.status == "success"


def test_retry_after_page_limit_rejection(tmp_path, document):
    original = synthetic_pdf("SYNTHETIC one", "SYNTHETIC two")
    with pytest.raises(ResourceLimitError):
        DocumentStore(tmp_path, limits=IngestionLimits(max_pages=1)).ingest(original, document)
    receipt = DocumentStore(tmp_path, limits=IngestionLimits(max_pages=2)).ingest(
        original, document
    )
    assert DocumentStore(tmp_path).load(receipt).extraction.status == "success"
    assert len(list((tmp_path / "originals").glob("*.pdf"))) == 1


@pytest.mark.parametrize("field", ["max_pdf_bytes", "max_pages"])
@pytest.mark.parametrize("value", [0, -1, True, "100", 1.5, None])
def test_limit_configuration_is_strict(field, value):
    with pytest.raises(ValidationError):
        IngestionLimits.model_validate({field: value})


def test_identity_conflict_has_no_new_artifacts_after_restart(tmp_path, document):
    original = synthetic_pdf("SYNTHETIC original")
    first = DocumentStore(tmp_path).ingest(original, document)
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    conflict = changed_document(document, product_id="different-product")
    with pytest.raises(IdentityConflictError):
        DocumentStore(tmp_path).ingest(synthetic_pdf("SYNTHETIC changed"), conflict)
    after = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*") if path.is_file())
    assert before == after
    assert DocumentStore(tmp_path).load(first).document == document


def test_repeat_and_metadata_revisions_keep_identity(tmp_path, document):
    original = synthetic_pdf("SYNTHETIC original")
    first = DocumentStore(tmp_path).ingest(original, document)
    assert DocumentStore(tmp_path).ingest(original, document) == first
    revised = changed_document(document, title="SYNTHETIC revised title", language="de")
    second = DocumentStore(tmp_path).ingest(
        original, revised, metadata=VersionMetadata(declared_version="revision-2")
    )
    assert second != first
    assert DocumentStore(tmp_path).load(second).document.product_id == document.product_id
    assert DocumentStore(tmp_path).load(first).document == document
    assert len(list((tmp_path / "identities").glob("*.json"))) == 1


def test_distinct_document_ids_can_share_pdf_bytes_across_products(tmp_path, document):
    original = synthetic_pdf("SYNTHETIC shared")
    store = DocumentStore(tmp_path)
    first = store.ingest(original, document)
    other = changed_document(document, id="another-document", product_id="another-product")
    second = store.ingest(original, other)
    assert store.load(first).version.original_sha256 == store.load(second).version.original_sha256
    assert len(list((tmp_path / "originals").glob("*.pdf"))) == 1


def test_pre_registry_store_binds_without_rewriting_existing_artifacts(tmp_path, document):
    store = DocumentStore(tmp_path)
    original = synthetic_pdf("SYNTHETIC old-store")
    receipt = store.ingest(original, document)
    binding = next((tmp_path / "identities").glob("*.json"))
    binding.unlink()  # Simulate the previous PR implementation, which had only snapshots.
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert DocumentStore(tmp_path).load(receipt).document == document
    with pytest.raises(IdentityConflictError):
        DocumentStore(tmp_path).ingest(
            original, changed_document(document, product_id="conflicting-product")
        )
    assert not binding.exists()
    assert DocumentStore(tmp_path).ingest(original, document) == receipt
    assert binding.exists()
    assert all(path.read_bytes() == data for path, data in before.items())


def test_existing_conflicting_snapshots_fail_closed_on_load_and_ingest(tmp_path, document):
    store = DocumentStore(tmp_path)
    original = synthetic_pdf("SYNTHETIC")
    receipt = store.ingest(original, document)
    conflict = changed_document(document, product_id="historical-conflict")
    # Simulate an inconsistent old store; both snapshots have valid hashes.
    (tmp_path / "documents" / f"{artifact_id(conflict)}.json").write_bytes(
        canonical_bytes(conflict)
    )
    for operation in (lambda: store.load(receipt), lambda: store.ingest(original, document)):
        with pytest.raises(IdentityConflictError):
            operation()


def test_identity_binding_tampering_is_rejected(tmp_path, document):
    store = DocumentStore(tmp_path)
    original = synthetic_pdf("SYNTHETIC")
    receipt = store.ingest(original, document)
    path = next((tmp_path / "identities").glob("*.json"))
    data = json.loads(path.read_bytes())
    data["product_id"] = "tampered-product"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(IdentityConflictError):
        DocumentStore(tmp_path).load(receipt)


def test_binding_survives_new_process(tmp_path, document):
    DocumentStore(tmp_path).ingest(synthetic_pdf("SYNTHETIC"), document)
    conflict = changed_document(document, product_id="different-product")
    code = (
        "import sys; from pathlib import Path; "
        "from axiory.ingestion import DocumentStore, IdentityConflictError; "
        "from axiory.ingestion_models import LogicalDocument; "
        "from tests.pdf_fixtures import synthetic_pdf; "
        "doc = LogicalDocument.model_validate_json(sys.argv[2]); "
        "\ntry: DocumentStore(Path(sys.argv[1])).ingest(synthetic_pdf('SYNTHETIC'), doc)"
        "\nexcept IdentityConflictError: sys.exit(0)"
        "\nelse: sys.exit(1)"
    )
    subprocess.run(
        [sys.executable, "-c", code, str(tmp_path), conflict.model_dump_json()],
        check=True,
        capture_output=True,
        text=True,
    )


def test_two_competing_first_writers_cannot_bind_different_products(
    tmp_path, document, monkeypatch
):
    barrier = Barrier(2)
    publish = DocumentStore._publish

    def synchronized_publish(path, data):
        if path.parent.name == "identities":
            barrier.wait(timeout=10)
        publish(path, data)

    monkeypatch.setattr(DocumentStore, "_publish", staticmethod(synchronized_publish))

    def ingest(doc):
        try:
            return DocumentStore(tmp_path).ingest(synthetic_pdf("SYNTHETIC"), doc)
        except IdentityConflictError:
            return None

    competing = changed_document(document, product_id="competing-product")
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(ingest, [document, competing]))
    receipts = [result for result in outcomes if result is not None]
    assert len(receipts) == 1
    assert DocumentStore(tmp_path).load(receipts[0]).extraction.status == "success"
    assert len(list((tmp_path / "documents").glob("*.json"))) == 1
