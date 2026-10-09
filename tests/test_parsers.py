"""Schema-2 integrity, layout and optional dependency regression tests."""

import json
import subprocess
import sys
from hashlib import sha256

import pytest
from pydantic import ValidationError

from axiory.evaluation.fixtures import render_pdf
from axiory.evaluation.goldstandard import corpus
from axiory.evaluation.layout_metrics import association_metrics, cell_metrics
from axiory.ingestion import DocumentStore, IntegrityError, ParserVersionError
from axiory.ingestion_models import IngestionLimits, LogicalDocument
from axiory.parsers.adapters import PyMuPDFAdapter, adapter
from axiory.parsers.models import Box, LayoutArtifact, ParserConfig
from axiory.parsers.store import LayoutStore
from axiory.pdf_extraction import ResourceLimitError
from tests.pdf_fixtures import synthetic_pdf
from tests.test_ingestion import evidence_for, replace_json

GOLD = {g.fixture_id: g for g in corpus()}


@pytest.fixture
def document():
    return LogicalDocument(
        id="test-layout",
        product_id="synthetic",
        title="SYNTHETIC",
        kind="policy_conditions",
        synthetic=True,
    )


@pytest.fixture(params=["pypdf", "pymupdf"])
def config(request):
    if request.param == "pymupdf":
        pytest.importorskip("pymupdf")
        return ParserConfig(parser="pymupdf", sort_text=True, tables=True)
    return ParserConfig()


def test_optional_import_and_explicit_gate():
    result = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "import sys; from axiory.parsers.adapters import PypdfAdapter; "
            "assert 'pymupdf' not in sys.modules; print(PypdfAdapter().config.parser)",
        ],
        text=True,
    )
    assert result.strip() == "pypdf"
    with pytest.raises(ValueError, match="experimental"):
        PyMuPDFAdapter()
    with pytest.raises(ValidationError):
        ParserConfig(sort_text=True)


def test_receipt_reload_and_evidence(config, tmp_path, document):
    raw = render_pdf(GOLD["plain-de"])
    store = LayoutStore(tmp_path, config=config, experimental=True)
    receipt = store.ingest(raw, document)
    loaded = LayoutStore(tmp_path, config=config, experimental=True).load(receipt)
    assert loaded.extraction.original_sha256 == sha256(raw).hexdigest()
    assert loaded.extraction.version_sha256 == loaded.receipt.version_sha256
    assert (
        LayoutArtifact.model_validate_json(loaded.extraction.model_dump_json()) == loaded.extraction
    )
    store.verify_evidence(receipt, evidence_for(loaded))
    assert store.ingest(raw, document) == receipt


def test_originals_versions_and_legacy_receipts_are_shared(tmp_path, document):
    pytest.importorskip("pymupdf")
    raw = render_pdf(GOLD["plain-de"])
    old = DocumentStore(tmp_path)
    old_id = old.ingest(raw, document)
    baseline = LayoutStore(tmp_path)
    other = LayoutStore(
        tmp_path, config=ParserConfig(parser="pymupdf", tables=True), experimental=True
    )
    a = baseline.load(baseline.ingest(raw, document))
    b_id = other.ingest(raw, document)
    b = other.load(b_id)
    assert (
        a.receipt.version_sha256
        == b.receipt.version_sha256
        == old.load(old_id).receipt.version_sha256
    )
    assert a.receipt.extraction_sha256 != b.receipt.extraction_sha256
    assert len(list((tmp_path / "originals").glob("*.pdf"))) == 1
    with pytest.raises(IntegrityError, match="extraction mismatch"):
        other.verify_evidence(b_id, evidence_for(a))


@pytest.mark.parametrize("password", ["synthetic-password", ""])
def test_encrypted_pdf_is_explicit(config, tmp_path, document, password):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    receipt = store.ingest(synthetic_pdf("SYNTHETIC", encrypted=True, password=password), document)
    result = store.load(receipt)
    assert result.extraction.status == "encrypted"
    assert result.extraction.pages == ()


def test_damaged_pdf_preserves_original(config, tmp_path, document):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    raw = b"not a PDF: SYNTHETIC"
    receipt = store.ingest(raw, document)
    result = store.load(receipt)
    assert result.extraction.status == "damaged"
    assert store._bytes("originals", sha256(raw).hexdigest(), ".pdf") == raw


def test_resource_admission_never_publishes_success(config, tmp_path, document):
    store = LayoutStore(
        tmp_path, config=config, experimental=True, limits=IngestionLimits(max_pdf_bytes=1)
    )
    with pytest.raises(ResourceLimitError, match="pdf_size_exceeded"):
        store.ingest(synthetic_pdf("SYNTHETIC"), document)
    assert not list(tmp_path.glob("layout_receipts/*.json"))
    store = LayoutStore(
        tmp_path, config=config, experimental=True, limits=IngestionLimits(max_pages=1)
    )
    with pytest.raises(ResourceLimitError, match="page_count_exceeded"):
        store.ingest(synthetic_pdf("SYNTHETIC 1", "SYNTHETIC 2"), document)
    assert not list(tmp_path.glob("layout_receipts/*.json"))
    assert list(tmp_path.glob("originals/*.pdf"))


def test_stricter_reload_limits_and_identity_conflicts(config, tmp_path, document):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    raw = synthetic_pdf("SYNTHETIC 1", "SYNTHETIC 2")
    receipt = store.ingest(raw, document)
    with pytest.raises(ResourceLimitError):
        LayoutStore(
            tmp_path, config=config, experimental=True, limits=IngestionLimits(max_pages=1)
        ).load(receipt)
    data = document.model_dump(mode="json")
    data["product_id"] = "other"
    with pytest.raises(IntegrityError, match="another product"):
        store.ingest(raw, LogicalDocument.model_validate_json(json.dumps(data)))


def tamper(store, receipt, change):
    old = store.load(receipt)
    changed = replace_json(store, "layout_extractions", old.receipt.extraction_sha256, change)
    return replace_json(
        store, "layout_receipts", receipt, lambda data: data.update(extraction_sha256=changed)
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("parser_version", "wrong"),
        ("version_sha256", "b" * 64),
        ("original_sha256", "c" * 64),
    ],
)
def test_forged_parser_and_document_references(config, tmp_path, document, field, value):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    receipt = store.ingest(render_pdf(GOLD["plain-de"]), document)
    forged = tamper(store, receipt, lambda data: data.update({field: value}))
    with pytest.raises(IntegrityError):
        store.load(forged)


def test_wrong_configuration_cannot_reuse_evidence(tmp_path, document):
    pytest.importorskip("pymupdf")
    a = ParserConfig(parser="pymupdf", sort_text=False)
    b = ParserConfig(parser="pymupdf", sort_text=True)
    store = LayoutStore(tmp_path, config=a, experimental=True)
    receipt = store.ingest(render_pdf(GOLD["columns-interleaved"]), document)
    other = LayoutStore(tmp_path, config=b, experimental=True)
    with pytest.raises(ParserVersionError, match="configuration"):
        other.load(receipt)
    different = other.ingest(render_pdf(GOLD["columns-interleaved"]), document)
    assert different != receipt


@pytest.mark.parametrize("kind", ["bbox", "missing-block", "span"])
def test_rehashed_layout_manipulations_fail_reproduction(tmp_path, document, kind):
    pytest.importorskip("pymupdf")
    store = LayoutStore(tmp_path, config=ParserConfig(parser="pymupdf"), experimental=True)
    receipt = store.ingest(render_pdf(GOLD["plain-de"]), document)

    def mutate(data):
        page = data["pages"][0]
        if kind == "bbox":
            page["elements"][0]["bbox"]["x0"] += 1.0
        elif kind == "missing-block":
            page["elements"] = []
            page["reading_order"] = []
        else:
            page["elements"][0]["raw_span"] = {"start": 999, "end": 1000}

    forged = tamper(store, receipt, mutate)
    with pytest.raises((IntegrityError, ValidationError)):
        store.load(forged)


@pytest.mark.parametrize(
    "coords",
    [
        (-1.0, 0.0, 2.0, 2.0),
        (0.0, 0.0, 0.0, 2.0),
        (0.0, 2.0, 2.0, 1.0),
        (0.0, 0.0, float("inf"), 2.0),
        (0.0, 0.0, float("nan"), 2.0),
    ],
)
def test_invalid_coordinates(coords):
    with pytest.raises(ValidationError):
        Box(x0=coords[0], y0=coords[1], x1=coords[2], y1=coords[3])


def test_outside_page_box_rejected(tmp_path, document):
    pytest.importorskip("pymupdf")
    store = LayoutStore(tmp_path, config=ParserConfig(parser="pymupdf"), experimental=True)
    receipt = store.ingest(render_pdf(GOLD["plain-de"]), document)

    def mutate(data):
        data["pages"][0]["elements"][0]["bbox"]["x1"] = 9999.0

    with pytest.raises(ValidationError, match="outside page"):
        store.load(tamper(store, receipt, mutate))


def test_fresh_process_reproduces(config, tmp_path, document):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    receipt = store.ingest(render_pdf(GOLD["plain-de"]), document)
    code = (
        "import sys; from pathlib import Path; "
        "from axiory.parsers.store import LayoutStore; "
        "from axiory.parsers.models import ParserConfig; "
        "s=LayoutStore(Path(sys.argv[1]),config=ParserConfig.model_validate_json(sys.argv[2]),"
        "experimental=True); s.load(sys.argv[3]); print('verified')"
    )
    result = subprocess.check_output(
        [sys.executable, "-c", code, str(tmp_path), config.model_dump_json(), receipt], text=True
    )
    assert "verified" in result


@pytest.mark.parametrize("name", ["french-accents", "italian-accents", "german-unicode"])
def test_unicode_is_retained(config, name):
    from axiory.evaluation.metrics import normalize

    result = adapter(config, experimental=True).extract(
        render_pdf(GOLD[name]), "a" * 64, IngestionLimits()
    )
    assert normalize(result.pages[0].text) == normalize(GOLD[name].expected_text[0])


def test_layout_exception_does_not_discard_raw_text(monkeypatch):
    pytest.importorskip("pymupdf")

    def fail(*args):
        raise ValueError("bad geometry")

    monkeypatch.setattr("axiory.parsers.adapters.text_elements", fail)
    result = PyMuPDFAdapter(experimental=True).extract(
        render_pdf(GOLD["plain-de"]), "a" * 64, IngestionLimits()
    )
    assert result.pages[0].text
    assert result.pages[0].raw_text
    assert result.pages[0].layout_errors == ("elements:ValueError",)


def test_table_scores_penalize_wrong_extra_and_duplicate_cells():
    pytest.importorskip("pymupdf")
    gold = GOLD["table-row-order"]
    result = PyMuPDFAdapter(experimental=True).extract(
        render_pdf(gold), "a" * 64, IngestionLimits()
    )
    assert cell_metrics(gold, result)["table_cell_precision"].value == 1
    data = result.model_dump(mode="json")
    data["pages"][0]["tables"][0]["cells"][0]["text"] = "wrong"
    changed = LayoutArtifact.model_validate_json(json.dumps(data))
    assert cell_metrics(gold, changed)["table_cell_precision"].value < 1
    assert cell_metrics(gold, changed)["table_cell_recall"].value < 1
    extra = json.loads(json.dumps(data["pages"][0]["tables"][0]))
    extra["id"] = "spurious-table"
    data["pages"][0]["tables"].append(extra)
    added = LayoutArtifact.model_validate_json(json.dumps(data))
    assert (
        cell_metrics(gold, added)["table_cell_precision"].value
        < cell_metrics(gold, changed)["table_cell_precision"].value
    )
    assert cell_metrics(GOLD["plain-de"], added)["table_cell_precision"].value == 0


def test_relation_precision_penalizes_hallucinations_and_duplicates():
    score = association_metrics((("h", "v"),), (("h", "v"), ("h", "wrong"), ("h", "v")))
    assert score["header_association_precision"].value == pytest.approx(1 / 3)
    assert score["header_association_recall"].value == 1
    assert association_metrics((), None)["header_association_precision"].status == "unsupported"
    assert association_metrics((), ())["header_association_precision"].status == "not_evaluable"
    assert association_metrics((("h", "v"),), ())["header_association_recall"].value == 0


@pytest.mark.parametrize(
    "text,status",
    [
        ("[image]", "needs_ocr"),
        ("[inline-image]", "needs_ocr"),
        ("[vector]", "not_extractable"),
        (None, "empty"),
    ],
)
def test_uniform_non_text_states(config, text, status):
    result = adapter(config, experimental=True).extract(
        synthetic_pdf(text), "a" * 64, IngestionLimits()
    )
    assert result.status == status


def test_original_byte_tampering_fails(config, tmp_path, document):
    store = LayoutStore(tmp_path, config=config, experimental=True)
    receipt = store.ingest(render_pdf(GOLD["plain-de"]), document)
    loaded = store.load(receipt)
    path = store._path("originals", loaded.version.original_sha256, ".pdf")
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(IntegrityError, match="Hash mismatch"):
        store.load(receipt)
