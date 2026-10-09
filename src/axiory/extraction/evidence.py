"""Exact source resolution and conservative lexical checks, never semantic certification."""

import re
from decimal import Decimal

from axiory.extraction.schemas import Candidate, ClaimRecord, Context, Quote
from axiory.ingestion import IntegrityError
from axiory.ingestion_models import PdfEvidence

BASIS_TEXT = {
    "per_person_per_trip": "per person per trip",
    "per_event": "per event",
    "per_year": "per year",
    "per_item": "per item",
}


def resolve(stored, context: Context, quote: Quote, index: int) -> PdfEvidence:
    if (
        quote.version_sha256 != context.version_sha256
        or quote.extraction_sha256 != context.extraction_sha256
    ):
        raise IntegrityError("wrong_source")
    if quote.page_number > len(stored.extraction.pages):
        raise IntegrityError("missing_page")
    text = stored.extraction.pages[quote.page_number - 1].text
    positions = [m.start() for m in re.finditer("(?=" + re.escape(quote.text) + ")", text)]
    if len(positions) != 1:
        raise IntegrityError("ambiguous_quote" if positions else "missing_quote")
    start = positions[0]
    end = start + len(quote.text)
    if not any(
        s.page_number == quote.page_number and s.start_char <= start and s.end_char >= end
        for s in context.sections
    ):
        raise IntegrityError("quote_outside_context")
    return PdfEvidence(
        id=f"evidence-{index}",
        document_id=context.document_id,
        version_sha256=context.version_sha256,
        extraction_sha256=context.extraction_sha256,
        page_number=quote.page_number,
        start_char=start,
        end_char=end,
        quote=quote.text,
    )


def check_candidate(stored, context, candidate: Candidate, *, method, model, prompt):
    issues = []
    evidence = []
    if candidate.product_id != context.product_id:
        issues.append("wrong_product")
    if candidate.coverage_code not in context.coverage_codes:
        issues.append("unrequested_coverage")
    for i, quote in enumerate(candidate.evidence_references):
        try:
            evidence.append(resolve(stored, context, quote, i))
        except IntegrityError as exc:
            issues.append(str(exc))
    if context.truncated or context.incomplete_source:
        issues.append("incomplete_context")
    if not evidence:
        issues.append("no_resolved_evidence")
    text = "\n".join(e.quote for e in evidence)
    amounts = {Decimal(m) for m in re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", text)}
    limits = [(candidate.limit_amount, candidate.currency, candidate.limit_basis)]
    limits += [(s.amount, s.currency, s.basis) for s in candidate.sublimits]
    for amount, currency, basis in limits:
        if amount is not None and (
            Decimal(amount) not in amounts or currency not in text or BASIS_TEXT[basis] not in text
        ):
            issues.append("limit_not_literal_in_evidence")
    # Only vocabulary supported by the synthetic English grammar; other languages need review.
    if candidate.coverage_status == "covered" and "not covered" in text.lower():
        issues.append("negation_or_exception_requires_review")
    return ClaimRecord(
        **candidate.model_dump(),
        extraction_method=method,
        model_version=model,
        prompt_version=prompt,
        resolved_evidence=tuple(evidence),
        verification_status="review_required" if issues else "source_matched",
        issues=tuple(sorted(set(issues))),
    )
