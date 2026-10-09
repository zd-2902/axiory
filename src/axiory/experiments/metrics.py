"""Predeclared paired metrics. Missing values are null; withholding is not unknown."""

import random
from collections import defaultdict
from decimal import Decimal
from statistics import mean


def normalize(text):
    return " ".join(text.split())


def grade(case, run):
    gold = case.expected
    claim = run.claim if run else None
    c = claim.candidate if claim else None
    status = c is not None and c.coverage_status == gold.status

    def monetary(amount, currency, basis, sublimits, deductible):
        return (
            Decimal(amount) if amount is not None else None,
            currency,
            basis,
            sorted((v.subject, Decimal(v.amount), v.currency, v.basis) for v in sublimits),
            (Decimal(deductible.amount), deductible.currency, deductible.basis)
            if deductible
            else None,
        )

    money = c is not None and monetary(
        c.limit_amount, c.currency, c.limit_basis, c.sublimits, c.deductible
    ) == monetary(gold.amount, gold.currency, gold.basis, gold.sublimits, gold.deductible)
    atoms = (
        c is not None
        and set(c.conditions) == set(gold.conditions)
        and set(c.exclusions) == set(gold.exclusions)
    )
    full = bool(
        status
        and money
        and atoms
        and c.product_id == case.source.product_id
        and c.coverage_code == case.source.coverage_code
    )
    cited = " ".join(normalize(e.quote) for e in claim.evidence) if claim else ""
    anchors = all(normalize(anchor) in cited for anchor in gold.anchors)
    evidence = claim is not None and claim.source_status == "source_matched" and anchors
    hallucination = claim is not None and any(
        x in claim.issues
        for x in (
            "missing_quote",
            "ambiguous_quote",
            "wrong_source",
            "missing_page",
            "quote_outside_context",
        )
    )
    row = {
        "case_id": case.source.id,
        "family": case.family,
        "language": case.source.language,
        "coverage_code": case.source.coverage_code,
        "scenario": case.scenario,
        "difficulty": case.difficulty,
        "split": case.split,
        "baseline_present": c is not None,
        "baseline_correct": full,
        "baseline_error": c is not None and not (full and evidence),
        "gold_asserted": gold.status != "unknown",
        "gold_unknown": gold.status == "unknown",
        "gold_nonexcluded": gold.status != "excluded",
        "has_limit": gold.amount is not None or bool(gold.sublimits),
        "has_deductible": gold.deductible is not None,
        "hallucinated_evidence": hallucination,
        "source_supported": bool(evidence),
        "errors": list(run.errors) if run else ["not_attempted"],
        "arms": {},
    }
    for arm, released in zip(
        ("A", "B", "C"),
        (run.a_released, run.b_released, run.c_released) if run else (False,) * 3,
        strict=True,
    ):
        asserted = released and c.coverage_status != "unknown"
        row["arms"][arm] = {
            "released": released,
            "asserted": asserted,
            "correct_assertion": bool(asserted and full and evidence),
            "status_correct": bool(released and status),
            "money_correct": bool(released and money),
            "full_correct": bool(released and full),
            "evidence_supported": bool(released and full and evidence),
            "unknown_correct": bool(released and status and gold.status == "unknown"),
            "unsupported": bool(asserted and not (full and evidence)),
            "false_exclusion": bool(
                released and c.coverage_status == "excluded" and gold.status != "excluded"
            ),
            "critical_error": bool(asserted and not (full and evidence)),
            "false_rejection": bool(full and evidence and not released),
            "missed_error": bool(row["baseline_error"] and released),
            "withheld": c is not None and not released,
        }
    return row


def ratio(n, d, cases):
    return {"numerator": n, "denominator": d, "case_count": cases, "value": n / d if d else None}


def summarize(rows, arm):
    n = len(rows)

    def count(key):
        return sum(r["arms"][arm][key] for r in rows)

    def source(key):
        return sum(r[key] for r in rows)

    correct_eligible = sum(r["baseline_correct"] and r["source_supported"] for r in rows)
    return {
        "claim_precision": ratio(count("correct_assertion"), count("asserted"), n),
        "claim_recall": ratio(count("correct_assertion"), source("gold_asserted"), n),
        "coverage_status_accuracy": ratio(count("status_correct"), n, n),
        "limit_accuracy": ratio(
            sum(r["has_limit"] and r["arms"][arm]["money_correct"] for r in rows),
            source("has_limit"),
            n,
        ),
        "deductible_accuracy": ratio(
            sum(r["has_deductible"] and r["arms"][arm]["money_correct"] for r in rows),
            source("has_deductible"),
            n,
        ),
        "evidence_support_accuracy": ratio(count("evidence_supported"), count("released"), n),
        "unknown_recall": ratio(count("unknown_correct"), source("gold_unknown"), n),
        "false_exclusion_rate": ratio(count("false_exclusion"), source("gold_nonexcluded"), n),
        "unsupported_claim_rate": ratio(count("unsupported"), count("asserted"), n),
        "critical_error_rate": ratio(count("critical_error"), n, n),
        "hallucinated_evidence_rate": ratio(
            source("hallucinated_evidence"), source("baseline_present"), n
        ),
        "verifier_false_rejection_rate": ratio(count("false_rejection"), correct_eligible, n)
        if arm != "A"
        else ratio(0, 0, n),
        "verifier_missed_error_rate": ratio(count("missed_error"), source("baseline_error"), n)
        if arm != "A"
        else ratio(0, 0, n),
        "withheld_claim_rate": ratio(count("withheld"), source("baseline_present"), n),
    }


def stratify(rows):
    result = {"all": {a: summarize(rows, a) for a in "ABC"}}
    for key in ("language", "coverage_code", "scenario", "difficulty", "split"):
        result[key] = {
            value: {a: summarize([r for r in rows if r[key] == value], a) for a in "ABC"}
            for value in sorted({r[key] for r in rows})
        }
    return result


def paired_bootstrap(rows, arm, *, metric="critical_error", seed=1729, repeats=1000):
    groups = defaultdict(list)
    for row in rows:
        groups[row["family"]].append(row)
    families = sorted(groups)

    def delta(sample):
        return mean(float(r["arms"][arm][metric]) - float(r["arms"]["A"][metric]) for r in sample)

    estimate = delta(rows) if rows else None
    common = {
        "contrast": arm + "-A",
        "metric": metric,
        "estimate": estimate,
        "case_count": len(rows),
        "family_count": len(families),
        "replicates": repeats,
        "seed": seed,
        "confidence": 0.95,
        "method": "paired_family_percentile_bootstrap",
        "small_sample": len(families) < 10,
        "significance_claim": False,
    }
    if len(families) < 2:
        return {**common, "interval": None, "reason": "fewer_than_two_families"}
    rng = random.Random(seed)
    samples = sorted(
        delta([r for f in rng.choices(families, k=len(families)) for r in groups[f]])
        for _ in range(repeats)
    )
    low, high = int((repeats - 1) * 0.025), int((repeats - 1) * 0.975)
    return {**common, "interval": [samples[low], samples[high]], "reason": None}


def statistics(rows, config):
    result = {}
    for split in ("all", "dev", "holdout"):
        subset = [r for r in rows if split == "all" or r["split"] == split]
        result[split] = {
            arm: {
                metric: paired_bootstrap(
                    subset,
                    arm,
                    metric=metric,
                    seed=config.seed,
                    repeats=config.bootstrap_replicates,
                )
                for metric in ("critical_error", "status_correct", "withheld")
            }
            for arm in "BC"
        }
    complete = [r for r in rows if r["baseline_present"] and not r["errors"]]
    return {
        "paired": result,
        "sensitivity_complete_cases": {
            "case_count": len(complete),
            "metrics": {a: summarize(complete, a) for a in "ABC"},
        },
        "caution": "Family bootstrap is descriptive; small cohorts, template dependence and "
        "single-author annotation do not justify significance or population claims.",
    }
