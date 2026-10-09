"""Paired parser benchmark using unchanged Sprint-3 PDFs and gold annotations."""

import argparse
import json
import platform
import tempfile
from datetime import UTC, datetime
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

from axiory.evaluation.fixtures import generator_metadata, render_pdf
from axiory.evaluation.goldstandard import corpus
from axiory.evaluation.layout_metrics import association_metrics, cell_metrics, findings
from axiory.evaluation.metrics import aggregate, locate_evidence, measured, score, unavailable
from axiory.evaluation.reporting import digest
from axiory.evaluation.runner import git_metadata
from axiory.evaluation.schemas import BenchmarkConfig, CaseResult, GoldFixture, Observation
from axiory.ingestion import artifact_id
from axiory.ingestion_models import LogicalDocument, PdfEvidence, VersionMetadata
from axiory.parsers.adapters import PyMuPDFAdapter
from axiory.parsers.models import LayoutArtifact, ParserConfig
from axiory.parsers.store import LayoutStore


class ParserCase(CaseResult):
    extraction: LayoutArtifact | None
    extraction_sha256: str | None
    provenance_passed: bool
    parse_runtimes_ms: tuple[float, ...]


CONFIGS = (
    ParserConfig(),
    ParserConfig(parser="pymupdf", sort_text=True, tables=True),
)


def run_case(gold, raw, destination, config, benchmark_config):
    destination.mkdir(parents=True, exist_ok=True)
    observations, fingerprints, parse_times, store_times = [], [], [], []
    diagnostics = []
    verified = True
    for repeat in range(benchmark_config.repeats):
        receipt = extracted = None
        parse_time = 0.0
        started = perf_counter()
        try:
            store = LayoutStore(
                destination / str(repeat),
                config=config,
                experimental=True,
                limits=benchmark_config.limits,
            )
            receipt = store.ingest(
                raw,
                LogicalDocument(
                    id=gold.fixture_id,
                    product_id="synthetic-evaluation",
                    title=gold.fixture_id,
                    kind="policy_conditions",
                    language=gold.language,
                    synthetic=True,
                ),
                metadata=VersionMetadata(declared_version=gold.document_version),
            )
            stored = store.load(receipt)
            extracted = stored.extraction
            pages = tuple(page.text for page in extracted.pages)
            candidates = locate_evidence(gold, pages)
            for index, item in enumerate(candidates):
                evidence = PdfEvidence(
                    id=f"evidence-{index}",
                    document_id=stored.document.id,
                    version_sha256=stored.receipt.version_sha256,
                    extraction_sha256=stored.receipt.extraction_sha256,
                    page_number=item.page,
                    start_char=item.start,
                    end_char=item.end,
                    quote=item.quote,
                )
                # Already hash-checked and reproduced by load; do not parse once per quote.
                store._verify_evidence(stored, evidence)
            store_time = (perf_counter() - started) * 1000
            parse_started = perf_counter()
            repeated = store.parser.extract(raw, stored.receipt.version_sha256, store.limits)
            parse_time = (perf_counter() - parse_started) * 1000
            if repeated != extracted:
                raise ValueError("Timed parser result differs from verified artifact")
            observation = Observation(
                status=extracted.status,
                pages=pages,
                evidence=candidates,
            )
            fingerprints.append(artifact_id(extracted))
            for page in extracted.pages:
                diagnostics.extend(f"Page {page.number}: {error}" for error in page.layout_errors)
        except (ValueError, OSError) as exc:
            verified = False
            store_time = (perf_counter() - started) * 1000
            observation = Observation(status="error", pages=())
            fingerprints.append(None)
            diagnostics.append(f"repeat {repeat}: {type(exc).__name__}: {exc}")
        store_times.append(store_time)
        parse_times.append(parse_time)
        observations.append((receipt, extracted, observation))
    receipt, extracted, observation = observations[0]
    metrics = score(gold, observation)
    reasons = {
        "clause_boundary_accuracy": "Adapter does not output clause boundaries",
        "table_cell_extraction_accuracy": (
            "Legacy score requires table structure and reliable header flags; "
            "see separate cell precision/recall"
        ),
        "table_header_value_association": "No reliable header/value relations",
    }
    for name, reason in reasons.items():
        if metrics[name].status == "unsupported":
            metrics[name] = unavailable("unsupported", reason)
    if extracted:
        metrics.update(cell_metrics(gold, extracted))
    else:
        for name in ("table_cell_precision", "table_cell_recall"):
            metrics[name] = unavailable("not_evaluable", "No extraction")
    metrics.update(association_metrics((), None))
    metrics["reproducibility"] = (
        measured(sum(item == fingerprints[0] for item in fingerprints[1:]), len(fingerprints) - 1)
        if fingerprints[0]
        else measured(0, 0)
    )
    metrics["extraction_failure_rate"] = measured(
        sum(item[2].status not in ("success", "partial") for item in observations),
        len(observations),
    )
    metrics["partial_extraction_rate"] = measured(
        sum(item[2].status == "partial" for item in observations), len(observations)
    )
    metrics["runtime_per_document_ms"] = measured(sum(store_times), len(store_times))
    metrics["parser_runtime_ms"] = (
        measured(sum(parse_times), len(parse_times)) if verified else measured(0, 0)
    )
    if metrics["expected_status_match"].value == 0:
        diagnostics.append(
            f"Expected {gold.expected_extraction_status}; actual {observation.status}"
        )
    return ParserCase(
        fixture_id=gold.fixture_id,
        layout_type=gold.layout_type,
        pdf_sha256=sha256(raw).hexdigest(),
        gold_sha256=artifact_id(gold),
        receipt_id=receipt,
        extraction=extracted,
        extraction_sha256=artifact_id(extracted) if extracted else None,
        observation=observation,
        metrics=metrics,
        failures=findings(metrics, observation, extracted),
        diagnostics=tuple(diagnostics),
        repeat_fingerprints=tuple(fingerprints),
        runtimes_ms=tuple(store_times),
        parse_runtimes_ms=tuple(parse_times),
        provenance_passed=verified,
    )


# Predeclared guardrails, not a fitted or weighted overall quality score.
DIRECTIONS = {
    "character_error_rate": -1,
    "word_error_rate": -1,
    "text_completeness": 1,
    "reading_order_accuracy": 1,
    "reading_order_anchor_coverage": 1,
    "evidence_span_validity": 1,
    "page_reference_accuracy": 1,
    "missing_evidence_rate": -1,
}


def compare(left, right):
    pairs = []
    for a, b in zip(left, right, strict=True):
        if (a.fixture_id, a.pdf_sha256, a.gold_sha256) != (
            b.fixture_id,
            b.pdf_sha256,
            b.gold_sha256,
        ):
            raise ValueError("Comparison requires identical fixture bytes and gold")
        improved, regressed, unavailable = [], [], []
        for name, direction in DIRECTIONS.items():
            x, y = a.metrics[name], b.metrics[name]
            if x.status != "measured" or y.status != "measured":
                unavailable.append(name)
            elif (y.value - x.value) * direction > 1e-12:
                improved.append(name)
            elif (y.value - x.value) * direction < -1e-12:
                regressed.append(name)
        eligible = all(
            c.provenance_passed
            and c.metrics["reproducibility"].value == 1
            and c.extraction is not None
            and not any(page.layout_errors for page in c.extraction.pages)
            for c in (a, b)
        )
        decision = (
            "ineligible"
            if not eligible
            else "tradeoff"
            if improved and regressed
            else "pymupdf"
            if improved
            else "pypdf"
            if regressed
            else "no_clear_advantage"
        )
        pairs.append(
            {
                "fixture_id": a.fixture_id,
                "layout_type": a.layout_type,
                "improved": improved,
                "regressed": regressed,
                "unavailable": unavailable,
                "text_preference": decision,
                "parser_time_ratio_pymupdf_over_pypdf": (
                    b.metrics["parser_runtime_ms"].value / a.metrics["parser_runtime_ms"].value
                    if a.metrics["parser_runtime_ms"].value and b.metrics["parser_runtime_ms"].value
                    else None
                ),
            }
        )
    layouts = {
        layout: [pair for pair in pairs if pair["layout_type"] == layout]
        for layout in sorted({pair["layout_type"] for pair in pairs})
    }
    return {
        "rule_version": "1",
        "rule": "Provenance + reproducibility, then per-case Pareto comparison of text guardrails",
        "pairs": pairs,
        "by_layout": layouts,
        "production_default": "pypdf",
        "experimental_only": "pymupdf",
        "structural_policy": (
            "Table claims require explicit measured precision/recall; no header facts"
        ),
        "uncertainty": "24 synthetic cases, no statistical significance or weighted overall score",
    }


def quality_payload(report):
    copy = json.loads(json.dumps(report))
    copy.pop("metadata", None)
    copy.pop("quality_sha256", None)
    for results in copy["parsers"].values():
        for case in results["cases"]:
            case.pop("runtimes_ms", None)
            case.pop("parse_runtimes_ms", None)
            for name in ("runtime_per_document_ms", "parser_runtime_ms"):
                case["metrics"].pop(name, None)
        for group in [results["aggregate"], *results["by_layout"].values()]:
            for name in ("runtime_per_document_ms", "parser_runtime_ms"):
                group.pop(name, None)
    for pair in copy["comparison"]["pairs"]:
        pair.pop("parser_time_ratio_pymupdf_over_pypdf", None)
    for pairs in copy["comparison"]["by_layout"].values():
        for pair in pairs:
            pair.pop("parser_time_ratio_pymupdf_over_pypdf", None)
    return copy


def benchmark(output, config=None, fixtures=None):
    config = config or BenchmarkConfig()
    fixtures = corpus() if fixtures is None else fixtures
    fixtures = tuple(GoldFixture.model_validate_json(f.model_dump_json()) for f in fixtures)
    if not fixtures or len({f.fixture_id for f in fixtures}) != len(fixtures):
        raise ValueError("Distinct nonempty fixtures required")
    PyMuPDFAdapter(experimental=True)  # Fail clearly before generating files if extra is absent.
    output.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    all_cases = {c.parser: [] for c in CONFIGS}
    for gold in fixtures:
        raw = render_pdf(gold)  # Render exactly once for both adapters.
        root = run / gold.fixture_id
        root.mkdir()
        (root / "original.pdf").write_bytes(raw)
        (root / "gold.json").write_text(gold.model_dump_json(indent=2), encoding="utf-8")
        # Alternate first parser to reduce systematic order bias; no significance claim.
        configs = CONFIGS if len(all_cases["pypdf"]) % 2 == 0 else tuple(reversed(CONFIGS))
        for parser_config in configs:
            all_cases[parser_config.parser].append(
                run_case(gold, raw, root / parser_config.parser, parser_config, config)
            )
    report = {
        "report_schema_version": "multi-parser-1",
        "metrics_version": "2",
        "configuration": config.model_dump(mode="json"),
        "corpus_sha256": digest(
            [(c.fixture_id, c.pdf_sha256, c.gold_sha256) for c in all_cases["pypdf"]]
        ),
        "generator": generator_metadata(),
        "metadata": {
            **git_metadata(),
            "timestamp": datetime.now(UTC).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "dependencies": {
                name: version(name)
                for name in ("pypdf", "pymupdf", "reportlab", "pillow", "pydantic")
            },
            "artifacts_directory": run.name,
        },
        "parsers": {
            name: {
                "cases": [c.model_dump(mode="json") for c in cases],
                "aggregate": aggregate(cases),
                "by_layout": {
                    layout: aggregate([c for c in cases if c.layout_type == layout])
                    for layout in sorted({c.layout_type for c in cases})
                },
            }
            for name, cases in all_cases.items()
        },
        "comparison": compare(all_cases["pypdf"], all_cases["pymupdf"]),
    }
    report["quality_sha256"] = digest(quality_payload(report))
    return report


def markdown(report):
    lines = [
        "# Multi-Parser-Benchmark (synthetisch)",
        "",
        f"Git: {report['metadata']['git_commit']}; Dirty: {report['metadata']['git_dirty']}.",
        f"Corpus: {report['corpus_sha256']}.",
        f"Quality: {report['quality_sha256']}.",
        "",
        "Keine Signifikanzbehauptung; kein Gesamtscore. Tabellen sind geometrische Heuristiken.",
        "Fundstellen nutzen bekannte Goldzitate. pypdf bleibt Produktionsdefault;",
        "PyMuPDF bleibt wegen offener Lizenzstrategie experimentell.",
        "",
        "| Metrik | pypdf (Z/N) | PyMuPDF (Z/N) |",
        "| --- | --- | --- |",
    ]

    def show(metric):
        if metric["status"] != "measured":
            return metric["status"]
        return f"{metric['value']:.6f} ({metric['numerator']:.3f}/{metric['denominator']:.3f})"

    for name in report["parsers"]["pypdf"]["aggregate"]:
        lines.append(
            "| "
            + name
            + " | "
            + " | ".join(
                show(report["parsers"][p]["aggregate"][name]["metric"])
                for p in ("pypdf", "pymupdf")
            )
            + " |"
        )
    lines += ["", "## Fähigkeiten", "", "| Fähigkeit | pypdf | PyMuPDF |", "| --- | --- | --- |"]
    for name in (
        "blocks",
        "lines",
        "coordinates",
        "reading_order",
        "tables",
        "header_associations",
        "clauses",
    ):
        values = []
        for parser in ("pypdf", "pymupdf"):
            extraction = report["parsers"][parser]["cases"][0]["extraction"]
            values.append(extraction["capabilities"][name] if extraction else "unavailable")
        lines.append(f"| {name} | {values[0]} | {values[1]} |")
    lines += [
        "",
        "## Fälle und Layouts",
        "",
        "| Fall | Layout | Textpräferenz | verbessert | verschlechtert | Zeitverhältnis |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for pair in report["comparison"]["pairs"]:
        ratio = pair["parser_time_ratio_pymupdf_over_pypdf"]
        lines.append(
            f"| {pair['fixture_id']} | {pair['layout_type']} | {pair['text_preference']} | "
            f"{', '.join(pair['improved']) or '—'} | {', '.join(pair['regressed']) or '—'} | "
            f"{ratio if ratio is not None else 'n.a.'} |"
        )
    lines += ["", "## Diagnosen", ""]
    for name, results in report["parsers"].items():
        for case in results["cases"]:
            for diagnostic in case["diagnostics"]:
                lines.append(f"- {name}/{case['fixture_id']}: {diagnostic}")
    lines += [
        "",
        "## Grenzen",
        "",
        "Nur 24 kontrollierte Fälle; eine Fontfamilie. Kleine Unterschiede sind deskriptiv,",
        "nicht statistisch abgesichert. Laufzeiten umfassen verschiedene Fähigkeitsumfänge;",
        "parser_runtime_ms misst Parsing inklusive Layout/Tabellen, separat von Store/Reload.",
        "Keine harten CPU-/RAM-/Zeitlimits, kein OCR, keine fachliche Versicherungsprüfung.",
        "Klauseln und verlässliche Header/Wert-Relationen bleiben unsupported.",
        "Vollständige Nenner, Parserkonfigurationen, Artefakte und Fähigkeiten stehen im JSON.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-experimental-pymupdf", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("datasets/evaluation-parsers"))
    parser.add_argument("--repeats", type=int, default=2)
    args = parser.parse_args()
    if not args.allow_experimental_pymupdf:
        parser.error(
            "Explicit --allow-experimental-pymupdf required; read docs/PARSER_BENCHMARK.md"
        )
    try:
        report = benchmark(args.output, BenchmarkConfig(repeats=args.repeats))
        (args.output / "comparison.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (args.output / "comparison.md").write_text(markdown(report), encoding="utf-8")
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Benchmark failed: {exc}\n")
    print(f"Comparison: {args.output / 'comparison.md'}")
    print(f"Quality fingerprint: {report['quality_sha256']}")
    if any(
        not case["provenance_passed"] or case["metrics"]["reproducibility"]["value"] != 1
        for results in report["parsers"].values()
        for case in results["cases"]
    ):
        parser.exit(1, "Incomplete or non-reproducible benchmark; inspect diagnostics.\n")


if __name__ == "__main__":
    main()
