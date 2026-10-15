"""Offline structural reassessment only: no new prompts, approvals or LLM-quality score."""

import argparse
import json
from pathlib import Path

from axiory.experiments.models import CaseRun, Manifest
from axiory.experiments.replay import replay
from axiory.experiments.resilience import build_plan, structural_issues
from axiory.extraction.schemas import Context
from axiory.ingestion import DocumentStore, artifact_id


def reassess(source):
    source = Path(source)
    original = replay(source)
    manifest = Manifest.model_validate_json((source / "manifest.json").read_bytes())
    store = DocumentStore(source / "session")
    cases = []
    for key in manifest.case_runs:
        run = store._read("paired_cases", key, CaseRun)
        context = store._read("experiment_contexts", run.context_sha256, Context)
        cases.append(
            {
                "case_id": run.case_id,
                "original_case_sha256": key,
                "candidate_sha256": artifact_id(run.claim.candidate) if run.claim else None,
                "plan_sha256": artifact_id(build_plan(context)),
                "structural_issues": sorted(
                    set(structural_issues(context, run.claim.candidate, run.claim.evidence))
                )
                if run.claim
                else ["no_valid_candidate"],
                "historical_c_released": run.c_released,
            }
        )
    return {
        "schema_version": "structural-reassessment-1",
        "measurement": "OFFLINE_STRUCTURAL_REASSESSMENT",
        "source_manifest_sha256": artifact_id(manifest),
        "source_quality_fingerprint": original["quality_fingerprint"],
        "rules_version": "evidence-plan-3",
        "model_calls": 0,
        "cases": cases,
        "note": "Development diagnostics on already known cases. Original runs remain unchanged. "
        "No v3 reflection is fabricated and no new release or model-quality score is computed. "
        "A full v3 response requires the new schema and reflection.",
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
