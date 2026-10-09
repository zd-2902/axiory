"""Deterministic source checks and explicit gates, separate from semantic/human approval."""

import re
from decimal import Decimal

from axiory.experiments.models import CheckedClaim, CheckedReview
from axiory.extraction.evidence import resolve
from axiory.ingestion import IntegrityError


def check_claim(stored, context, candidate):
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
    amounts = [candidate.limit_amount] + [s.amount for s in candidate.sublimits]
    if candidate.deductible:
        amounts.append(candidate.deductible.amount)
    if any(a is not None and (Decimal(a) not in numbers or "CHF" not in text) for a in amounts):
        issues.append("amount_not_literal")
    return CheckedClaim(
        candidate=candidate,
        evidence=tuple(evidence),
        source_status="review_required" if issues else "source_matched",
        issues=tuple(sorted(set(issues))),
    )


def check_review(stored, context, candidate, review):
    issues = []
    if review.claim_id != candidate.claim_id:
        issues.append("wrong_claim")
    if (
        set(review.checks)
        != {"support", "omissions", "limits", "negation", "contradictions", "unknown"}
        or len(review.checks) != 6
    ):
        issues.append("incomplete_checks")
    if not review.evidence_references:
        issues.append("missing_review_evidence")
    for i, quote in enumerate(review.evidence_references + review.counterevidence):
        try:
            resolve(stored, context, quote, i)
        except IntegrityError as exc:
            issues.append(str(exc))
    return CheckedReview(review=review, source_valid=not issues, issues=tuple(issues))


def gates(claim, verifier, critic):
    a = claim is not None and claim.source_status == "source_matched"
    b = (
        a
        and verifier is not None
        and verifier.source_valid
        and verifier.review.decision == "supported"
    )
    c = b and critic is not None and critic.source_valid and critic.review.decision == "supported"
    return bool(a), bool(b), bool(c)
