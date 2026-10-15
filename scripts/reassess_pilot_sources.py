"""Recheck saved candidates with v2 literal rules; never call a model or rewrite a run."""

import argparse
import json
from pathlib import Path

from axiory.experiments.models import CaseRun, Manifest
from axiory.experiments.replay import replay
from axiory.experiments.verification import check_claim
from axiory.extraction.schemas import Context
from axiory.ingestion import DocumentStore, artifact_id
from axiory.parsers.store import LayoutStore


def reassess(source):
    source = Path(source)
    original = replay(source)  # validates originals, replies, prompts, gates and report
    manifest = Manifest.model_validate_json((source / "manifest.json").read_bytes())
    store = DocumentStore(source / "session")
    cases = []
    for key in manifest.case_runs:
        run = store._read("paired_cases", key, CaseRun)
        if run.claim is None:
            cases.append(
                {
                    "case_id": run.case_id,
                    "original_case_sha256": key,
                    "status": "no_valid_candidate",
                    "before": None,
                    "after": None,
                }
            )
            continue
        context = store._read("experiment_contexts", run.context_sha256, Context)
        stored = LayoutStore(source / "cases" / run.case_id).load(context.receipt_sha256)
        checked = check_claim(stored, context, run.claim.candidate, version="pilot-fixes-2")
        cases.append(
            {
                "case_id": run.case_id,
                "original_case_sha256": key,
                "candidate_sha256": artifact_id(run.claim.candidate),
                "status": "rechecked",
                "before": {"status": run.claim.source_status, "issues": run.claim.issues},
                "after": {"status": checked.source_status, "issues": checked.issues},
            }
        )
    return {
        "schema_version": "source-reassessment-1",
        "measurement": "OFFLINE_SOURCE_REASSESSMENT",
        "source_manifest_sha256": artifact_id(manifest),
        "source_quality_fingerprint": original["quality_fingerprint"],
        "protocol_version": "pilot-fixes-2",
        "model_calls": 0,
        "cases": cases,
        "note": "Existing canonical candidates only. Invalid replies are not repaired. "
        "Reviews are not reinterpreted; no v2 model-quality claim or gate score.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; never overwrite an evaluation artifact")
    report = reassess(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(json.dumps({"output": str(args.output), "model_calls": 0, "cases": len(report["cases"])}))


if __name__ == "__main__":
    main()
