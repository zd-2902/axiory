"""Separate semantic corpus, transparent mock benchmark and explicit synthetic-only live CLI."""

import argparse
import json
import platform
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from pathlib import Path
from typing import Literal

from reportlab.pdfgen.canvas import Canvas

from axiory.evaluation.runner import git_metadata
from axiory.extraction.baseline import mock_verification, rules
from axiory.extraction.context import build_context
from axiory.extraction.evidence import check_candidate
from axiory.extraction.pipeline import replay, review_gate, run
from axiory.extraction.providers import Budget, CallRecord, MockProvider, OpenAIProvider, Reply
from axiory.extraction.schemas import Amount, Basis, Code, Status, Sublimit
from axiory.ingestion import canonical_bytes
from axiory.ingestion_models import ArtifactModel, LogicalDocument, Nonempty
from axiory.parsers.store import LayoutStore


class Annotation(ArtifactModel):
    coverage_status: Status
    limit_amount: Amount | None
    currency: Literal["CHF"] | None
    limit_basis: Basis | None
    conditions: tuple[Nonempty, ...]
    exclusions: tuple[Nonempty, ...]
    sublimits: tuple[Sublimit, ...]
    unknown_reason: Nonempty | None
    support_anchors: tuple[Nonempty, ...]
    rationale: Nonempty


class SemanticCase(ArtifactModel):
    id: Nonempty
    family: Nonempty
    split: Literal["dev", "holdout"]
    scenario: Nonempty
    product_id: Nonempty
    coverage_code: Code
    pages: tuple[tuple[Nonempty, ...], ...]
    annotation: Annotation


class SemanticGold(ArtifactModel):
    schema_version: Literal["semantic-gold-1"]
    synthetic: Literal[True]
    annotation_method: Nonempty
    cases: tuple[SemanticCase, ...]


def load_gold(path=Path("datasets/semantic/gold-v1.json")):
    gold = SemanticGold.model_validate_json(path.read_bytes())
    if len({c.id for c in gold.cases}) != len(gold.cases):
        raise ValueError("Duplicate gold IDs")
    dev = {c.family for c in gold.cases if c.split == "dev"}
    holdout = {c.family for c in gold.cases if c.split == "holdout"}
    if dev & holdout:
        raise ValueError("Family leakage")
    return gold


def pdf(case: SemanticCase) -> bytes:
    output = BytesIO()
    canvas = Canvas(output, pagesize=(595, 842), invariant=1, pageCompression=0)
    for lines in case.pages:
        canvas.setFont("Helvetica", 9)
        canvas.drawString(40, 805, f"SYNTHETIC TEST ONLY - {case.id}")
        for i, line in enumerate(lines):
            if canvas.stringWidth(line, "Helvetica", 9) > 515:
                raise ValueError("Synthetic line exceeds page")
            canvas.drawString(40, 770 - i * 18, line)
        canvas.showPage()
    canvas.save()
    return output.getvalue()


def context_for(store, case):
    receipt = store.ingest(
        pdf(case),
        LogicalDocument(
            id=case.id,
            product_id=case.product_id,
            title="Synthetic semantic test",
            kind="policy_conditions",
            language="en",
            synthetic=True,
        ),
    )
    return build_context(store, receipt, (case.coverage_code,))


def score(case, claim):
    a = case.annotation
    status = claim is not None and claim.coverage_status == a.coverage_status
    limit = claim is not None and (
        claim.limit_amount,
        claim.currency,
        claim.limit_basis,
        claim.sublimits,
    ) == (a.limit_amount, a.currency, a.limit_basis, a.sublimits)
    detail = (
        claim is not None
        and set(claim.conditions) == set(a.conditions)
        and set(claim.exclusions) == set(a.exclusions)
    )
    full = bool(status and limit and detail)
    asserted = claim is not None and claim.coverage_status != "unknown"
    evidence = (
        claim is not None
        and bool(claim.resolved_evidence)
        and not any(
            x in claim.issues
            for x in (
                "wrong_source",
                "wrong_product",
                "missing_quote",
                "ambiguous_quote",
                "quote_outside_context",
                "missing_page",
            )
        )
        and all(
            any(anchor in e.quote for e in claim.resolved_evidence) for anchor in a.support_anchors
        )
    )
    false_exclusion = (
        claim is not None
        and claim.coverage_status == "excluded"
        and a.coverage_status != "excluded"
    )
    critical = asserted and (not status or not limit or not detail or not evidence)
    return {
        "id": case.id,
        "family": case.family,
        "split": case.split,
        "scenario": case.scenario,
        "returned": claim is not None,
        "asserted": asserted,
        "expected_assertion": a.coverage_status != "unknown",
        "full_correct": full,
        "status_correct": bool(status),
        "limit_correct": bool(limit),
        "has_expected_limit": a.limit_amount is not None or bool(a.sublimits),
        "evidence_supported": bool(evidence and full),
        "unsupported": bool(asserted and not (full and evidence)),
        "false_exclusion": bool(false_exclusion),
        "gold_non_excluded": a.coverage_status != "excluded",
        "gold_unknown": a.coverage_status == "unknown",
        "unknown_correct": bool(status and a.coverage_status == "unknown"),
        "critical_error": bool(critical),
    }


def metrics(rows):
    def ratio(n, d):
        return {
            "numerator": n,
            "denominator": d,
            "case_count": len(rows),
            "value": n / d if d else None,
        }

    def count(key):
        return sum(r[key] for r in rows)

    tp = sum(r["asserted"] and r["full_correct"] for r in rows)
    return {
        "claim_precision": ratio(tp, count("asserted")),
        "claim_recall": ratio(tp, count("expected_assertion")),
        "coverage_status_accuracy": ratio(count("status_correct"), len(rows)),
        "limit_extraction_accuracy": ratio(
            sum(r["limit_correct"] and r["has_expected_limit"] for r in rows),
            count("has_expected_limit"),
        ),
        "evidence_support_accuracy": ratio(count("evidence_supported"), count("returned")),
        "unsupported_claim_rate": ratio(count("unsupported"), count("asserted")),
        "false_exclusion_rate": ratio(count("false_exclusion"), count("gold_non_excluded")),
        "unknown_recall": ratio(count("unknown_correct"), count("gold_unknown")),
        "critical_error_rate": ratio(count("critical_error"), len(rows)),
    }


def observability(calls, case_count):
    records = [store._read("model_calls", k, CallRecord) for store, k in calls]
    replies = [
        store._read("model_outputs", r.output_sha256, Reply)
        for (store, _), r in zip(calls, records, strict=True)
        if r.output_sha256
    ]

    def measured(values, expected):
        return {
            "numerator": sum(values) if values else None,
            "denominator": expected,
            "measured_count": len(values),
            "case_count": case_count,
            "complete": len(values) == expected and expected > 0,
        }

    return {
        "calls": len(records),
        "latency_seconds": measured([r.latency_seconds for r in records], len(records)),
        "input_tokens": measured(
            [r.input_tokens for r in replies if r.input_tokens is not None], len(records)
        ),
        "output_tokens": measured(
            [r.output_tokens for r in replies if r.output_tokens is not None], len(records)
        ),
        "estimated_cost_usd": measured(
            [r.estimated_cost_usd for r in records if r.estimated_cost_usd is not None],
            len(records),
        ),
        "human_review_minutes": measured([], case_count),
    }


def benchmark(output: Path, gold_path: Path):
    gold = load_gold(gold_path)
    rows = {mode: [] for mode in ("rules", "mock_extractor", "mock_verifier_gate")}
    calls = {mode: [] for mode in rows}
    runs = []
    for case in gold.cases:
        store = LayoutStore(output / "cases" / case.id / "store")
        context = context_for(store, case)
        baseline = rules(context).claims[0]
        baseline = check_candidate(
            store.load(context.receipt_sha256),
            context,
            baseline,
            method="rules",
            model="rules-1",
            prompt="rules-1",
        )
        rows["rules"].append(score(case, baseline))
        extraction = rules(context, simulated=True)
        verification = mock_verification(context, extraction.claims)
        key, single = run(store, context, MockProvider([extraction.model_dump_json()]))
        verified_key, verified = run(
            store,
            context,
            MockProvider([extraction.model_dump_json(), verification.model_dump_json()]),
            verify=True,
        )
        replay_key, replayed = replay(store, verified_key)
        if (replayed.claims, replayed.verdicts, replayed.errors) != (
            verified.claims,
            verified.verdicts,
            verified.errors,
        ):
            raise ValueError("Offline replay differs")
        claim = single.claims[0] if single.claims else None
        rows["mock_extractor"].append(score(case, claim))
        # Experimental release gate WITHHOLDS; never edits or turns absence into exclusion.
        eligible = review_gate(verified)
        rows["mock_verifier_gate"].append(score(case, eligible[0] if eligible else None))
        calls["mock_extractor"].extend((store, call) for call in single.calls)
        calls["mock_verifier_gate"].extend((store, call) for call in verified.calls)
        runs.append(
            {
                "case": case.id,
                "single": key,
                "verified": verified_key,
                "replay": replay_key,
                "claims_unchanged": single.claims == verified.claims,
            }
        )
    quality = {
        mode: {
            split: metrics([r for r in values if split == "all" or r["split"] == split])
            for split in ("all", "dev", "holdout")
        }
        for mode, values in rows.items()
    }
    stable = {
        "quality": quality,
        "cases": rows,
        "gold_sha256": sha256(canonical_bytes(gold)).hexdigest(),
    }
    fingerprint = sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    report = {
        "schema_version": "semantic-report-1",
        "measurement": "OFFLINE_SCRIPTED_MOCK",
        "metadata": {
            **git_metadata(),
            "python": platform.python_version(),
            "pypdf": version("pypdf"),
            "pydantic": version("pydantic"),
            "reportlab": version("reportlab"),
        },
        "paid_api_calls": 0,
        "live_llm_quality_measured": False,
        "quality_fingerprint": fingerprint,
        **stable,
        "observability": {m: observability(cs, len(gold.cases)) for m, cs in calls.items()},
        "runs": runs,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "measurement": report["measurement"],
                "cases": len(gold.cases),
                "fingerprint": fingerprint,
                "report": str(output / "report.json"),
            }
        )
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("datasets/evaluation-semantic"))
    parser.add_argument("--gold", type=Path, default=Path("datasets/semantic/gold-v1.json"))
    parser.add_argument(
        "--live", action="store_true", help="Explicit opt-in to paid synthetic calls"
    )
    parser.add_argument("--case", help="Exactly one bundled synthetic case for a live pilot")
    parser.add_argument("--model")
    parser.add_argument("--budget", type=Path, help="Strict Budget JSON with explicit pricing")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.live:
        benchmark(args.output, args.gold)
        return
    if not args.case or not args.model or not args.budget:
        parser.error("--live requires --case, --model and --budget")
    # Live CLI accepts only the committed synthetic corpus, never a user PDF or custom gold.
    if args.gold != Path("datasets/semantic/gold-v1.json"):
        parser.error("Live mode accepts only the bundled synthetic corpus")
    cases = [c for c in load_gold().cases if c.id == args.case]
    if len(cases) != 1:
        parser.error("Unknown synthetic case")
    store = LayoutStore(args.output / "store")
    context = context_for(store, cases[0])
    budget = Budget.model_validate_json(args.budget.read_bytes())
    key, result = run(
        store,
        context,
        OpenAIProvider(allow_live=True),
        model=args.model,
        budget=budget,
        verify=args.verify,
    )
    candidate = result.claims[0] if result.claims else None
    baseline = check_candidate(
        store.load(context.receipt_sha256),
        context,
        rules(context).claims[0],
        method="rules",
        model="rules-1",
        prompt="rules-1",
    )
    eligible = review_gate(result)
    report = {
        "measurement": "LIVE_SINGLE_SYNTHETIC_PILOT",
        "case_count": 1,
        "run": key,
        "case": cases[0].id,
        "model": args.model,
        "errors": result.errors,
        "quality": {
            "rules": metrics([score(cases[0], baseline)]),
            "extractor": metrics([score(cases[0], candidate)]),
            "verifier_gate": metrics([score(cases[0], eligible[0] if eligible else None)])
            if args.verify
            else None,
        },
        "observability": observability([(store, k) for k in result.calls], 1),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "live-report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run": key, "errors": result.errors, "claims": len(result.claims)}))
    if result.errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
