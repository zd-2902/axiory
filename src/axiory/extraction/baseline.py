"""Intentionally narrow rules and scripted mock experiment. Neither is an LLM quality estimate."""

import re

from axiory.extraction.evidence import BASIS_TEXT
from axiory.extraction.schemas import (
    Candidate,
    ExtractionResponse,
    Quote,
    Verdict,
    VerificationResponse,
)


def quotes(context):
    return tuple(
        Quote(
            version_sha256=context.version_sha256,
            extraction_sha256=context.extraction_sha256,
            page_number=s.page_number,
            text=s.text,
        )
        for s in context.sections
    )


def rules(context, *, simulated=False):
    text = "\n".join(s.text for s in context.sections)
    ambiguous = any(
        x in text
        for x in ("may apply", "contact information", "not excluded", "except emergency", "|")
    )
    contradictory = "is covered." in text and "is not covered." in text
    unknown = ambiguous or contradictory
    status = (
        "unknown"
        if unknown
        else "excluded"
        if "is not covered" in text
        else "covered"
        if "is covered" in text
        else "unknown"
    )
    # A documented, intentionally fallible mock: overlooks negation, exceptions and conflict.
    if simulated:
        if "not excluded" in text or "is not covered" in text:
            status = "excluded"
        elif "|" in text:
            status = "covered"
    match = re.search(r"Limit CHF (\d+) (per person per trip|per event|per year)", text)
    if simulated and "|" in text:
        match = re.search(r"\| (\d+) \| (per event)", text)
    amount, basis = (
        (match.group(1), {v: k for k, v in BASIS_TEXT.items()}[match.group(2)])
        if match and status == "covered"
        else (None, None)
    )
    # Conservative baseline abstains when it cannot represent sublimits faithfully.
    if not simulated and "sublimit" in text:
        status, amount, basis = "unknown", None, None
    conditions = ("prior approval",) if "prior approval" in text and status == "covered" else ()
    return ExtractionResponse(
        claims=tuple(
            Candidate(
                claim_id=f"claim-{code}",
                product_id=context.product_id,
                coverage_code=code,
                coverage_status=status,
                limit_amount=amount,
                currency="CHF" if amount else None,
                limit_basis=basis,
                conditions=conditions,
                exclusions=(),
                sublimits=(),
                evidence_references=quotes(context),
                unknown_reason="Insufficient or conflicting support under the narrow rules"
                if status == "unknown"
                else None,
            )
            for code in context.coverage_codes
        )
    )


def mock_verification(context, candidates):
    text = "\n".join(s.text for s in context.sections)
    risk = any(x in text for x in ("not excluded", "except emergency", "sublimit")) or (
        "is covered." in text and "is not covered." in text
    )
    return VerificationResponse(
        verdicts=tuple(
            Verdict(
                claim_id=c.claim_id,
                decision="insufficient" if risk else "supported",
                reason="Negation, exception, sublimit or conflict requires review"
                if risk
                else "Scripted lexical fixture check only; not independent semantic confirmation",
                checks=("support", "omissions", "limits", "negation", "overclaim", "unknown"),
                evidence_references=quotes(context),
            )
            for c in candidates
        )
    )
