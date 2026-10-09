"""Paired benchmark, unchanged gold and conservative parser-selection contracts."""

import json
import sys
from pathlib import Path

import pytest

from axiory.evaluation.fixtures import render_pdf
from axiory.evaluation.goldstandard import corpus
from axiory.evaluation.multi_parser import (
    ParserCase,
    benchmark,
    compare,
    main,
    markdown,
    quality_payload,
)
from axiory.evaluation.reporting import digest
from axiory.evaluation.schemas import BenchmarkConfig
from axiory.ingestion import artifact_id


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    pytest.importorskip("pymupdf")
    return benchmark(tmp_path_factory.mktemp("paired"))


def test_frozen_corpus_and_identical_originals(report):
    baseline = json.loads(Path("docs/benchmarks/sprint3-baseline.json").read_text(encoding="utf-8"))
    assert report["corpus_sha256"] == baseline["cohort"]["corpus_sha256"]
    a, b = (report["parsers"][p]["cases"] for p in ("pypdf", "pymupdf"))
    assert len(a) == len(b) == 24
    for x, y in zip(a, b, strict=True):
        assert x["pdf_sha256"] == y["pdf_sha256"]
        assert x["gold_sha256"] == y["gold_sha256"]
        assert x["extraction"]["version_sha256"] == y["extraction"]["version_sha256"]
        assert x["extraction_sha256"] != y["extraction_sha256"]
        assert x["provenance_passed"] and y["provenance_passed"]
        for case in (x, y):
            assert case["metrics"]["reproducibility"]["value"] == 1
            ParserCase.model_validate_json(json.dumps(case))
    assert all(
        artifact_id(gold) == item["gold_sha256"] for gold, item in zip(corpus(), a, strict=True)
    )


def test_measured_advantages_and_regressions_are_both_reported(report):
    pairs = {p["fixture_id"]: p for p in report["comparison"]["pairs"]}
    assert pairs["columns-column-order"]["text_preference"] == "pypdf"
    assert pairs["table-column-order"]["text_preference"] == "pymupdf"
    assert pairs["plain-de"]["text_preference"] == "no_clear_advantage"
    assert report["comparison"]["production_default"] == "pypdf"
    for name in ("pypdf", "pymupdf"):
        metrics = report["parsers"][name]["aggregate"]
        assert metrics["header_association_precision"]["metric"]["status"] == "unsupported"
        assert metrics["clause_boundary_accuracy"]["metric"]["status"] == "unsupported"
    assert report["parsers"]["pymupdf"]["aggregate"]["table_cell_precision"]["metric"]["value"] == 1


def test_compare_refuses_different_sources_and_failed_provenance(report):
    a = report["parsers"]["pypdf"]["cases"][0]
    b = json.loads(json.dumps(report["parsers"]["pymupdf"]["cases"][0]))
    b["pdf_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="identical"):
        compare(
            [ParserCase.model_validate_json(json.dumps(a))],
            [ParserCase.model_validate_json(json.dumps(b))],
        )
    b["pdf_sha256"] = a["pdf_sha256"]
    b["provenance_passed"] = False
    result = compare(
        [ParserCase.model_validate_json(json.dumps(a))],
        [ParserCase.model_validate_json(json.dumps(b))],
    )
    assert result["pairs"][0]["text_preference"] == "ineligible"


def test_reproducible_quality_without_hiding_timings(tmp_path):
    pytest.importorskip("pymupdf")
    selected = corpus()[:2]
    a = benchmark(tmp_path / "a", fixtures=selected)
    b = benchmark(tmp_path / "b", fixtures=selected)
    assert a["quality_sha256"] == b["quality_sha256"]
    assert digest(quality_payload(a)) == a["quality_sha256"]
    assert a["metadata"]["artifacts_directory"] != b["metadata"]["artifacts_directory"]
    assert a["parsers"]["pypdf"]["aggregate"]["parser_runtime_ms"]["metric"]["value"] > 0


def test_raw_text_is_preserved_when_sorted_text_changes(report):
    case = next(
        c for c in report["parsers"]["pymupdf"]["cases"] if c["fixture_id"] == "headers-footers"
    )
    page = case["extraction"]["pages"][0]
    assert page["raw_text"] != page["text"]
    assert page["elements"]
    assert case["extraction"]["capabilities"]["reading_order"] == "heuristic"
    assert "columns-column-order" in markdown(report)
    assert "unsupported" in markdown(report)


def test_cli_requires_explicit_experimental_flag(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["axiory-parser-benchmark"])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_cli_exports_and_rejects_incomplete_run(report, tmp_path, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["axiory-parser-benchmark", "--allow-experimental-pymupdf", "--output", str(tmp_path)],
    )
    monkeypatch.setattr("axiory.evaluation.multi_parser.benchmark", lambda *args: report)
    main()
    assert (tmp_path / "comparison.json").exists()
    assert (tmp_path / "comparison.md").exists()
    broken = json.loads(json.dumps(report))
    broken["parsers"]["pypdf"]["cases"][0]["provenance_passed"] = False
    monkeypatch.setattr("axiory.evaluation.multi_parser.benchmark", lambda *args: broken)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1


def test_layout_errors_retain_text_and_fail_structure_metrics(tmp_path, monkeypatch):
    pytest.importorskip("pymupdf")
    from axiory.evaluation.multi_parser import CONFIGS, run_case

    def fail(*args):
        raise ValueError("table detector failed")

    monkeypatch.setattr("axiory.parsers.adapters.tables", fail)
    gold = corpus()[0]
    result = run_case(gold, render_pdf(gold), tmp_path, CONFIGS[1], BenchmarkConfig())
    assert result.observation.pages[0]
    assert result.metrics["table_cell_precision"].status == "not_evaluable"
    assert result.diagnostics
