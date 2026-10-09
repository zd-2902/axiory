"""Independent known-answer metrics and end-to-end synthetic evaluation contracts."""

import json
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from typing import get_args

import pytest
from pydantic import ValidationError

from axiory.evaluation.fixtures import render_pdf
from axiory.evaluation.goldstandard import corpus
from axiory.evaluation.metrics import classify, distance, locate_evidence, measured, score
from axiory.evaluation.reporting import compare_reports, digest, export, stable_payload
from axiory.evaluation.runner import benchmark, evaluate_case, main
from axiory.evaluation.schemas import (
    BenchmarkConfig,
    CaseResult,
    FailureClass,
    GoldFixture,
    GoldTable,
    LocatedEvidence,
    Metric,
    Observation,
    TableCell,
)
from axiory.ingestion_models import IngestionLimits

FIXTURES = corpus()


def fixture(name):
    return next(item for item in FIXTURES if item.fixture_id == name)


@pytest.mark.parametrize("gold", FIXTURES, ids=lambda gold: gold.fixture_id)
def test_generation_is_deterministic_and_gold_roundtrips(gold):
    assert render_pdf(gold) == render_pdf(gold)
    assert GoldFixture.model_validate_json(gold.model_dump_json()) == gold
    assert gold.interpretation_status == "not_evaluated"


def test_corpus_covers_languages_and_independent_source(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Gold must not depend on the parser")

    monkeypatch.setattr("pypdf.PdfReader", forbidden)
    assert len(corpus()) >= 20
    assert {gold.language for gold in corpus()} == {"de", "fr", "it"}
    for gold in corpus():
        assert render_pdf(gold).startswith(b"%PDF")


def test_generation_is_deterministic_in_fresh_process():
    code = (
        "from hashlib import sha256; "
        "from axiory.evaluation.goldstandard import corpus; "
        "from axiory.evaluation.fixtures import render_pdf; "
        "print(sha256(render_pdf(corpus()[0])).hexdigest())"
    )
    result = subprocess.check_output([sys.executable, "-c", code], text=True).strip()
    assert result == sha256(render_pdf(FIXTURES[0])).hexdigest()


@pytest.mark.parametrize(
    "mutation",
    [
        {"extra": True},
        {"expected_text": ["parser-derived replacement"]},
        {"paint_order": []},
        {"schema_version": "99"},
        {"expected_evidence": [{"page": 100, "quote": "absent"}]},
    ],
)
def test_gold_rejects_incoherent_annotations(mutation):
    data = FIXTURES[0].model_dump(mode="json")
    data.update(mutation)
    with pytest.raises(ValidationError):
        GoldFixture.model_validate_json(json.dumps(data))


def test_table_rejects_overlapping_merged_cells_and_dangling_links():
    cell = TableCell(row=0, column=0, text="header", column_span=2, header=True)
    with pytest.raises(ValidationError, match="Overlapping"):
        GoldTable(id="t", page=1, cells=(cell, TableCell(row=0, column=1, text="value")))
    with pytest.raises(ValidationError, match="association"):
        GoldTable(id="t", page=1, cells=(cell,), associations=((0, 0, 1, 1),))


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ("kitten", "sitting", 3),
        ("", "abc", 3),
        ("abc", "", 3),
        (["one", "two"], ["two", "one"], 2),
        ("é", "e", 1),
    ],
)
def test_known_edit_distances(left, right, expected):
    assert distance(left, right) == expected


def test_metric_contract_and_roundtrip():
    assert measured(3, 2).value == 1.5  # Insertions can make CER > 1.
    assert measured(0, 0).status == "not_evaluable"
    metric = measured(2, 3)
    assert Metric.model_validate_json(metric.model_dump_json()) == metric
    for data in [
        {"status": "measured", "numerator": 1.0, "denominator": 0.0},
        {"status": "measured", "numerator": 1.0, "denominator": 2.0, "value": 1.0},
        {"status": "unsupported", "value": 0.0, "reason": "No adapter"},
        {"status": "measured", "numerator": float("nan"), "denominator": 1.0},
    ]:
        with pytest.raises(ValidationError):
            Metric(**data)


def test_missing_text_is_zero_recall_but_empty_reference_is_not_evaluable():
    metrics = score(FIXTURES[0], Observation(status="empty", pages=("",)))
    assert metrics["text_completeness"].value == 0
    assert metrics["character_error_rate"].value == 1
    assert metrics["missing_evidence_rate"].value == 1
    assert metrics["evidence_span_validity"].status == "not_evaluable"
    empty = score(fixture("empty-page"), Observation(status="empty", pages=("",)))
    assert empty["character_error_rate"].status == "not_evaluable"


def test_reordered_text_is_not_hidden_by_completeness():
    gold = FIXTURES[0]
    lines = gold.expected_text[0].splitlines()
    metrics = score(gold, Observation(status="success", pages=("\n".join(reversed(lines)),)))
    assert metrics["text_completeness"].value == 1
    assert metrics["character_error_rate"].value > 0
    assert metrics["reading_order_accuracy"].value == 0
    assert metrics["reading_order_anchor_coverage"].value == 1


def test_unicode_loss_and_missing_order_anchors():
    gold = fixture("german-unicode")
    metrics = score(
        gold,
        Observation(
            status="success",
            pages=tuple(text.encode("ascii", "ignore").decode() for text in gold.expected_text),
        ),
    )
    assert metrics["unicode_integrity"].value == 0
    absent = score(gold, Observation(status="empty", pages=("",)))
    assert absent["reading_order_accuracy"].status == "not_evaluable"
    assert absent["reading_order_anchor_coverage"].value == 0


def test_evidence_locator_does_not_use_gold_page_to_resolve_ambiguity():
    gold = FIXTURES[0]
    assert locate_evidence(gold, gold.expected_text)
    assert locate_evidence(gold, gold.expected_text * 2) == ()
    repeated = fixture("repeated-clause-numbers")
    assert len(locate_evidence(repeated, repeated.expected_text)) < len(repeated.expected_evidence)


def test_invalid_span_and_wrong_page_are_distinct():
    gold = FIXTURES[0]
    target = gold.expected_evidence[0]
    wrong_span = LocatedEvidence(target=0, page=target.page, start=0, end=99999, quote=target.quote)
    metrics = score(
        gold, Observation(status="success", pages=gold.expected_text, evidence=(wrong_span,))
    )
    assert metrics["evidence_span_validity"].value == 0
    assert metrics["page_reference_accuracy"].value == 1
    wrong_page = locate_evidence(gold, ("", *gold.expected_text))
    metrics = score(
        gold, Observation(status="success", pages=("", *gold.expected_text), evidence=wrong_page)
    )
    assert metrics["evidence_span_validity"].value == 1
    assert metrics["page_reference_accuracy"].value == 0
    assert metrics["missing_evidence_rate"].value == 1


def test_structural_capability_is_not_inferred_from_serialized_text():
    gold = fixture("table-row-order")
    metrics = score(gold, Observation(status="success", pages=gold.expected_text))
    assert metrics["character_error_rate"].value == 0
    assert metrics["table_cell_extraction_accuracy"].status == "unsupported"
    assert metrics["table_header_value_association"].value is None
    metrics = score(gold, Observation(status="success", pages=gold.expected_text, tables=()))
    assert metrics["table_cell_extraction_accuracy"].value == 0
    metrics = score(
        gold, Observation(status="success", pages=gold.expected_text, tables=gold.expected_tables)
    )
    assert metrics["table_cell_extraction_accuracy"].value == 1
    assert metrics["table_header_value_association"].value == 1


def test_wrong_table_value_invalidates_header_association():
    gold = fixture("table-row-order")
    data = gold.expected_tables[0].model_dump(mode="json")
    for cell in data["cells"]:
        if not cell["header"]:
            cell["text"] = "wrong value"
    wrong = GoldTable.model_validate_json(json.dumps(data))
    metrics = score(gold, Observation(status="success", pages=gold.expected_text, tables=(wrong,)))
    assert metrics["table_cell_extraction_accuracy"].value < 1
    assert metrics["table_header_value_association"].value == 0


def test_clause_boundaries_require_explicit_structured_output():
    gold = fixture("clause-across-pages")
    assert (
        score(gold, Observation(status="success", pages=gold.expected_text))[
            "clause_boundary_accuracy"
        ].status
        == "unsupported"
    )
    assert (
        score(gold, Observation(status="success", pages=gold.expected_text, clauses=()))[
            "clause_boundary_accuracy"
        ].value
        == 0
    )
    assert (
        score(
            gold,
            Observation(status="success", pages=gold.expected_text, clauses=gold.expected_clauses),
        )["clause_boundary_accuracy"].value
        == 1
    )


def test_failure_taxonomy_covers_all_nine_classes_without_fake_scores():
    metrics = score(FIXTURES[0], Observation(status="error", pages=()))
    for name in (
        "text_completeness",
        "reading_order_accuracy",
        "clause_boundary_accuracy",
        "table_cell_extraction_accuracy",
        "table_header_value_association",
        "evidence_span_validity",
        "page_reference_accuracy",
        "unicode_integrity",
    ):
        metrics[name] = measured(0, 1)
    failures = classify(metrics, Observation(status="error", pages=()))
    assert {item.kind for item in failures} == set(get_args(FailureClass))
    assert all(item.basis == "measured" for item in failures)
    gold = fixture("table-row-order")
    failures = classify(
        score(gold, Observation(status="success", pages=gold.expected_text)),
        Observation(status="success", pages=gold.expected_text),
    )
    assert all(item.basis == "capability_gap" for item in failures)


@pytest.fixture(scope="module")
def full_report(tmp_path_factory):
    return benchmark(tmp_path_factory.mktemp("full-evaluation"))


def test_full_corpus_uses_existing_ingestion_and_preserves_findings(full_report):
    cases = {
        item["fixture_id"]: CaseResult.model_validate_json(json.dumps(item))
        for item in full_report["cases"]
    }
    assert len(cases) == 24
    assert all(case.metrics["reproducibility"].value == 1 for case in cases.values())
    for name in ("french-accents", "italian-accents", "german-unicode"):
        assert cases[name].metrics["character_error_rate"].value == 0
        assert cases[name].metrics["unicode_integrity"].value == 1
    for name in ("columns-interleaved", "table-column-order", "headers-footers"):
        assert cases[name].metrics["reading_order_accuracy"].value < 1
        assert cases[name].metrics["text_completeness"].value == 1
    assert cases["image-only"].observation.status == "needs_ocr"
    assert cases["vector-text"].observation.status == "not_extractable"
    assert cases["mixed-text-image"].observation.status == "partial"
    assert cases["empty-page"].metrics["expected_status_match"].value == 0
    assert cases["empty-page"].observation.status == "not_extractable"


def test_repeat_runs_are_comparable_with_different_paths_and_times(tmp_path):
    before = benchmark(tmp_path / "before", fixtures=FIXTURES[:2])
    after = benchmark(tmp_path / "after", fixtures=FIXTURES[:2])
    assert before["metadata"]["artifacts_directory"] != after["metadata"]["artifacts_directory"]
    assert before["quality_sha256"] == after["quality_sha256"]
    assert all(delta == 0 for delta in compare_reports(before, after)["deltas"].values())
    for case in after["cases"]:
        root = tmp_path / "after" / after["metadata"]["artifacts_directory"] / case["fixture_id"]
        assert (root / (case["fixture_id"] + ".pdf")).exists()
        assert (root / (case["fixture_id"] + ".gold.json")).exists()
    changed = benchmark(
        tmp_path / "changed", config=BenchmarkConfig(repeats=3), fixtures=FIXTURES[:2]
    )
    assert not compare_reports(before, changed)["comparable"]


def test_previous_report_tampering_is_rejected(full_report):
    broken = deepcopy(full_report)
    broken["cases"][0]["metrics"]["character_error_rate"]["value"] = 99.0
    with pytest.raises(ValueError, match="Invalid previous"):
        compare_reports(broken, full_report)
    broken = deepcopy(full_report)
    broken["aggregate"]["character_error_rate"]["metric"]["value"] = 99.0
    broken["quality_sha256"] = digest(stable_payload(broken))
    with pytest.raises(ValueError, match="Aggregate"):
        compare_reports(broken, full_report)
    assert not compare_reports({"report_schema_version": "future"}, full_report)["comparable"]


def test_resource_failure_is_reported_not_success(tmp_path):
    case = evaluate_case(
        FIXTURES[0], tmp_path, BenchmarkConfig(limits=IngestionLimits(max_pdf_bytes=1))
    )
    assert case.observation.status == "error"
    assert case.receipt_id is None
    assert case.metrics["extraction_failure_rate"].value == 1
    assert case.metrics["reproducibility"].status == "not_evaluable"
    assert case.repeat_fingerprints == (None, None)
    assert any("ResourceLimitError" in item for item in case.diagnostics)


def test_failure_on_later_repeat_is_not_hidden(tmp_path, monkeypatch):
    from axiory.ingestion import DocumentStore

    original = DocumentStore.ingest
    calls = 0

    def fail_second(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated write failure")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DocumentStore, "ingest", fail_second)
    case = evaluate_case(FIXTURES[0], tmp_path, BenchmarkConfig())
    assert case.observation.status == "success"
    assert case.metrics["reproducibility"].value == 0
    assert case.metrics["extraction_failure_rate"].value == 0.5
    assert any(failure.kind == "extraction_failure" for failure in case.failures)


def test_cli_exports_json_markdown_and_compare(tmp_path, monkeypatch, full_report):
    export(full_report, tmp_path / "previous")
    monkeypatch.setattr("axiory.evaluation.runner.benchmark", lambda *args: full_report.copy())
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "axiory-eval",
            "--output",
            str(tmp_path / "result"),
            "--compare",
            str(tmp_path / "previous" / "report.json"),
        ],
    )
    main()
    report = json.loads((tmp_path / "result" / "report.json").read_text(encoding="utf-8"))
    assert report["comparison"]["comparable"]
    assert "unsupported" in (tmp_path / "result" / "report.md").read_text(encoding="utf-8")


def test_cli_invalid_config_and_failed_repeat_exit_nonzero(tmp_path, monkeypatch, full_report):
    monkeypatch.setattr(sys, "argv", ["axiory-eval", "--repeats", "1"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
    broken = deepcopy(full_report)
    broken["cases"][0]["repeat_fingerprints"][-1] = None
    monkeypatch.setattr("axiory.evaluation.runner.benchmark", lambda *args: broken)
    monkeypatch.setattr(sys, "argv", ["axiory-eval", "--output", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1


@pytest.mark.parametrize("data", [[], None, "not a report"])
def test_compare_rejects_non_object_input(data, full_report):
    with pytest.raises(ValueError, match="expected an object"):
        compare_reports(data, full_report)
