"""axiory-eval: reproducible quality measurements, separately recorded volatile metadata."""

import argparse
import json
import platform
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from time import perf_counter

import pypdf

from axiory.evaluation.fixtures import generator_metadata, render_pdf
from axiory.evaluation.goldstandard import CORPUS_VERSION, corpus
from axiory.evaluation.metrics import classify, locate_evidence, measured, occurrences, score
from axiory.evaluation.reporting import build_report, compare_reports, digest, export
from axiory.evaluation.schemas import BenchmarkConfig, CaseResult, GoldFixture, Observation
from axiory.ingestion import DocumentStore, artifact_id
from axiory.ingestion_models import IngestionLimits, LogicalDocument, VersionMetadata

METRICS_VERSION = "1"


def git_metadata() -> dict:
    executable = shutil.which("git")
    if not executable:
        return {"git_commit": None, "git_dirty": None, "git_reason": "git not on PATH"}
    try:
        command = [executable, "-c", f"safe.directory={Path.cwd().as_posix()}"]
        commit = subprocess.check_output([*command, "rev-parse", "HEAD"], stderr=subprocess.DEVNULL)
        status = subprocess.check_output(
            [*command, "status", "--porcelain"], stderr=subprocess.DEVNULL
        )
        return {
            "git_commit": commit.decode().strip(),
            "git_dirty": bool(status.strip()),
            "git_reason": None,
        }
    except (OSError, subprocess.CalledProcessError):
        return {"git_commit": None, "git_dirty": None, "git_reason": "No readable Git checkout"}


def evaluate_case(gold: GoldFixture, destination: Path, config: BenchmarkConfig) -> CaseResult:
    from hashlib import sha256

    raw = render_pdf(gold)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / f"{gold.fixture_id}.pdf").write_bytes(raw)
    (destination / f"{gold.fixture_id}.gold.json").write_text(
        gold.model_dump_json(indent=2), encoding="utf-8"
    )
    results = []
    fingerprints = []
    timings = []
    diagnostics = []
    for repeat in range(config.repeats):
        receipt = artifact = None
        started = perf_counter()
        try:
            store = DocumentStore(destination / "store" / str(repeat), limits=config.limits)
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
            artifact = store.load(receipt).extraction
            observation = Observation(
                status=artifact.status, pages=tuple(page.text for page in artifact.pages)
            )
            fingerprints.append(artifact_id(artifact))
        except (ValueError, OSError) as exc:
            observation = Observation(status="error", pages=())
            fingerprints.append(None)
            diagnostics.append(f"repeat {repeat}: {type(exc).__name__}: {exc}")
        timings.append((perf_counter() - started) * 1000)
        results.append((receipt, artifact, observation))
    receipt, artifact, raw_observation = results[0]
    observation = Observation(
        status=raw_observation.status,
        pages=raw_observation.pages,
        evidence=locate_evidence(gold, raw_observation.pages),
    )
    metrics = score(gold, observation)
    metrics["reproducibility"] = (
        measured(
            sum(other == fingerprints[0] for other in fingerprints[1:]),
            len(fingerprints) - 1,
        )
        if fingerprints[0] is not None
        else measured(0, 0, "No baseline extraction artifact")
    )
    metrics["extraction_failure_rate"] = measured(
        sum(item[2].status not in ("success", "partial") for item in results), len(results)
    )
    metrics["partial_extraction_rate"] = measured(
        sum(item[2].status == "partial" for item in results), len(results)
    )
    metrics["runtime_per_document_ms"] = measured(sum(timings), len(timings))
    for target in gold.expected_evidence:
        found = occurrences(observation.pages, target.quote)
        if len(found) != 1:
            diagnostics.append(f"Evidence quote {target.quote!r}: {len(found)} exact occurrences")
    if metrics["expected_status_match"].value == 0:
        diagnostics.append(
            f"Expected status {gold.expected_extraction_status}, observed {observation.status}"
        )
    if artifact:
        for page in artifact.pages:
            if page.status != "text":
                diagnostics.append(
                    f"Page {page.number}: {page.status}; error_type={page.error_type}"
                )
    return CaseResult(
        fixture_id=gold.fixture_id,
        layout_type=gold.layout_type,
        pdf_sha256=sha256(raw).hexdigest(),
        gold_sha256=artifact_id(gold),
        receipt_id=receipt,
        extraction=artifact,
        observation=observation,
        metrics=metrics,
        failures=classify(metrics, observation),
        diagnostics=tuple(diagnostics),
        repeat_fingerprints=tuple(fingerprints),
        runtimes_ms=tuple(timings),
    )


def benchmark(
    output: Path,
    config: BenchmarkConfig | None = None,
    fixtures: tuple[GoldFixture, ...] | None = None,
) -> dict:
    config = config or BenchmarkConfig()
    fixtures = corpus() if fixtures is None else fixtures
    if not fixtures or len({f.fixture_id for f in fixtures}) != len(fixtures):
        raise ValueError("Benchmark requires distinct, nonempty fixtures")
    output.mkdir(parents=True, exist_ok=True)
    # Fresh stores on EVERY invocation. Previous artifacts can never satisfy a new run.
    with tempfile.TemporaryDirectory(prefix=".eval-", dir=output) as work:
        cases = [evaluate_case(gold, Path(work) / gold.fixture_id, config) for gold in fixtures]
        # Preserve inspectable corpus and stores in a unique per-run directory.
        run_dir = output / ("run-" + Path(work).name.removeprefix(".eval-"))
        shutil.copytree(work, run_dir)
    cohort = {
        "corpus_version": CORPUS_VERSION,
        "gold_schema_version": "1",
        "metrics_version": METRICS_VERSION,
        "corpus_sha256": digest(
            [(case.fixture_id, case.pdf_sha256, case.gold_sha256) for case in cases]
        ),
        "generator": generator_metadata(),
        "configuration": config.model_dump(mode="json"),
    }
    metadata = {
        **git_metadata(),
        "timestamp": datetime.now(UTC).isoformat(),
        "parser": "pypdf",
        "parser_version": pypdf.__version__,
        "extractor_version": "1",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "dependencies": {
            name: version(name) for name in ("pydantic", "pypdf", "reportlab", "pillow")
        },
        "artifacts_directory": run_dir.name,
        "evidence_adapter": "gold-assisted-unique-exact-quote-v1",
    }
    return build_report(cases, metadata, cohort)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("datasets/evaluation"))
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-pdf-bytes", type=int, default=20 * 1024 * 1024)
    parser.add_argument("--max-pages", type=int, default=200)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    try:
        config = BenchmarkConfig(
            repeats=args.repeats,
            limits=IngestionLimits(max_pdf_bytes=args.max_pdf_bytes, max_pages=args.max_pages),
        )
        previous = json.loads(args.compare.read_text(encoding="utf-8")) if args.compare else None
        report = benchmark(args.output, config)
        if previous is not None:
            report["comparison"] = compare_reports(previous, report)
        export(report, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Benchmark failed: {exc}\n")
    print(f"{len(report['cases'])} fixtures; report: {args.output / 'report.md'}")
    print(f"Quality fingerprint: {report['quality_sha256']}")
    if any(
        None in case["repeat_fingerprints"] or case["metrics"]["reproducibility"]["value"] != 1
        for case in report["cases"]
    ):
        parser.exit(1, "Some cases could not be evaluated; see diagnostics.\n")


if __name__ == "__main__":
    main()
