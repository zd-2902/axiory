"""Deterministic source checks and explicit gates, separate from semantic/human approval."""

import re
from decimal import Decimal

from axiory.experiments.models import CheckedClaim, CheckedReview, Review
from axiory.experiments.money import literal_amounts
from axiory.experiments.resilience import evidence_issues, reflection_issues, structural_issues
from axiory.extraction.evidence import resolve
from axiory.ingestion import IntegrityError


def check_claim(stored, context, candidate, *, version="pilot-1", reflection=None):
    _version(version)
    evidence, issues = [], []
    if candidate.product_id != context.product_id:
        issues.append("wrong_product")
    if candidate.coverage_code not in context.coverage_codes:
        issues.append("wrong_coverage")
    for i, quote in enumerate(candidate.evidence_references):
        try:
            evidence.append(resolve(stored, context, quote, i))
        except IntegrityError as exc:
            issues.append(str(exc))
    if not evidence:
        issues.append("missing_evidence")
    if context.truncated or context.incomplete_source:
        issues.append("incomplete_context")
    text = "\n".join(e.quote for e in evidence)
    numbers = {
        Decimal(x.replace(",", "."))
        for x in re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?(?![\w.])", text)
    }
    if version in ("pilot-fixes-2", "evidence-plan-3"):
        numbers = literal_amounts(text)
    amounts = [candidate.limit_amount] + [s.amount for s in candidate.sublimits]
    if candidate.deductible:
        amounts.append(candidate.deductible.amount)
    if any(a is not None and (Decimal(a) not in numbers or "CHF" not in text) for a in amounts):
        issues.append("amount_not_literal")
    if version == "evidence-plan-3":
        issues.extend(structural_issues(context, candidate, evidence))
        if reflection is None:
            issues.append("missing_reflection")
        else:
            issues.extend(reflection_issues(context, reflection, candidate.evidence_references))
    return CheckedClaim(
        candidate=candidate,
        evidence=tuple(evidence),
        source_status="review_required" if issues else "source_matched",
        issues=tuple(sorted(set(issues))),
    )


def check_review(stored, context, candidate, review, *, version="pilot-1", reflection=None):
    _version(version)
    issues = []
    if review.claim_id != candidate.claim_id:
        issues.append("wrong_claim")
    if (
        set(review.checks)
        != {"support", "omissions", "limits", "negation", "contradictions", "unknown"}
        or len(review.checks) != 6
    ):
        issues.append("incomplete_checks")
    if version in ("pilot-fixes-2", "evidence-plan-3"):
        if (review.decision == "supported_unknown" and candidate.coverage_status != "unknown") or (
            review.decision == "supported" and candidate.coverage_status == "unknown"
        ):
            issues.append("wrong_assessment_status")
    if not review.evidence_references:
        issues.append("missing_review_evidence")
    evidence = []
    for i, quote in enumerate(review.evidence_references + review.counterevidence):
        try:
            evidence.append(resolve(stored, context, quote, i))
        except IntegrityError as exc:
            issues.append(str(exc))
    if version == "evidence-plan-3":
        issues.extend(evidence_issues(context, evidence))
        if reflection is None:
            issues.append("missing_reflection")
        else:
            issues.extend(
                reflection_issues(
                    context,
                    reflection,
                    review.evidence_references + review.counterevidence,
                    decision=review.decision,
                )
            )
    if review.decision != "supported_unknown":
        review = Review.model_validate_json(review.model_dump_json())
    return CheckedReview(review=review, source_valid=not issues, issues=tuple(issues))


def _version(version):
    if version not in ("pilot-1", "pilot-fixes-2", "evidence-plan-3"):
        raise ValueError("Unknown verification protocol")


def gates(claim, verifier, critic, *, version="pilot-1"):
    _version(version)
    a = claim is not None and claim.source_status == "source_matched"
    decision = "supported"
    if (
        version in ("pilot-fixes-2", "evidence-plan-3")
        and claim
        and claim.candidate.coverage_status == "unknown"
    ):
        decision = "supported_unknown"
    b = (
        a
        and verifier is not None
        and verifier.source_valid
        and verifier.review.decision == decision
    )
    c = b and critic is not None and critic.source_valid and critic.review.decision == decision
    return bool(a), bool(b), bool(c)
