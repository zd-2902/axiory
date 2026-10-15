"""Versioned, gold-blind evidence planning and conservative release obligations.

The small row-major grammar is a synthetic adapter, not recovered PDF geometry.
Unsupported or ambiguous structures never silently fall back to number matching.
"""

import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field

from axiory.experiments.money import literal_amounts
from axiory.extraction.schemas import Amount, Basis, Code
from axiory.ingestion import artifact_id
from axiory.ingestion_models import ArtifactModel, Digest, Nonempty

CHECKS = (
    "identity",
    "evidence_completeness",
    "table_binding",
    "semantic_atoms",
    "contradictions",
    "unknown",
)
BANNER = "SYNTHETIC / SYNTHETISCH / SYNTHETIQUE / SINTETICO"
# Explicit, versioned language vocabulary, independent of case IDs and gold labels.
LABELS = {
    "cancellation": ("annullierung", "annulation", "annullamento"),
    "interruption": ("reiseabbruch", "interruption du voyage", "interruzione del viaggio"),
    "baggage": ("gepäck", "bagages", "bagaglio"),
    "medical_assistance": ("medizinische assistance", "assistance médicale", "assistenza medica"),
    "rental_car_deductible": (
        "mietwagen-selbstbehalt",
        "franchise voiture de location",
        "franchigia auto a noleggio",
    ),
}
HEADERS = {
    "label": {"leistung", "position", "prestation", "prestazione", "voce"},
    "amount": {"chf-limite", "maximalbetrag chf", "limite chf", "maximum chf", "massimo chf"},
    "basis": {
        "bezugsgrösse",
        "bezugszeitraum",
        "base",
        "période de référence",
        "periodo di riferimento",
    },
}
BASES = {
    "per_event": {
        "pro ereignis",
        "einzelnes ereignis",
        "par événement",
        "sinistre individuel",
        "per evento",
        "singolo sinistro",
    },
    "per_year": {
        "pro jahr",
        "versicherungsjahr",
        "par année",
        "année d'assurance",
        "per anno",
        "anno assicurativo",
    },
    "per_item": {"pro gegenstand", "par objet", "per oggetto"},
    "per_person_per_trip": {
        "pro person und reise",
        "par personne et par voyage",
        "per persona e per viaggio",
    },
}
TABLE_MARKERS = re.compile(r"\b(tabelle|erstattungsplan|tableau|barème|tabella|prospetto)\b", re.I)
CELL_AMOUNT = re.compile(r"(?:CHF\s*)?[0-9][0-9'’., \u00a0\u202f]*", re.I)


class Span(ArtifactModel):
    page_number: Annotated[int, Field(gt=0)]
    start_char: Annotated[int, Field(ge=0)]
    end_char: Annotated[int, Field(gt=0)]


class TableRow(ArtifactModel):
    header: Span
    cells: Span
    label: Nonempty
    coverage_code: Code | None
    amount: Amount
    currency: Literal["CHF"] = "CHF"
    basis: Basis


class EvidencePlan(ArtifactModel):
    schema_version: Literal["evidence-plan-1"] = "evidence-plan-1"
    context_sha256: Digest
    coverage_policy: Literal["all_context_nonwhitespace_except_synthetic_banner"] = (
        "all_context_nonwhitespace_except_synthetic_banner"
    )
    required_spans: tuple[Span, ...]
    table_suspected: bool
    table_rows: tuple[TableRow, ...]
    issues: tuple[str, ...]
    checks: tuple[str, ...] = CHECKS


def _lines(section):
    lines, offset = [], section.start_char
    for raw in section.text.splitlines(keepends=True):
        text = raw.strip()
        if text and text != BANNER:
            start = offset + len(raw) - len(raw.lstrip())
            lines.append((text, start, start + len(text)))
        offset += len(raw)
    return lines


def _span(page, lines):
    return Span(page_number=page, start_char=lines[0][1], end_char=lines[-1][2])


def build_plan(context):
    """No expected labels or model judgments are accepted as input."""
    spans, rows, issues = [], [], []
    suspected = False
    for section in context.sections:
        lines = _lines(section)
        if not lines:
            continue
        spans.append(_span(section.page_number, lines))
        tokens = [x[0].casefold() for x in lines]
        page_table = (
            bool(TABLE_MARKERS.search(section.text))
            or any(t in words for t in tokens for words in HEADERS.values())
            or any(CELL_AMOUNT.fullmatch(t) or "|" in t or "\t" in t for t in tokens)
        )
        suspected |= page_table
        if not page_table:
            continue
        starts = []
        for i in range(len(lines) - 2):
            roles = [
                next((role for role, words in HEADERS.items() if t in words), None)
                for t in tokens[i : i + 3]
            ]
            if set(roles) == set(HEADERS):
                starts.append((i, roles))
        if len(starts) != 1:
            issues.append("unsupported_table_layout")
            continue
        start, roles = starts[0]
        body = lines[start + 3 :]
        if not body or len(body) % 3:
            issues.append("unsupported_table_layout")
            continue
        page_rows = []
        for index in range(0, len(body), 3):
            chunk = body[index : index + 3]
            cells = dict(zip(roles, (line[0] for line in chunk), strict=True))
            amounts = literal_amounts(cells["amount"])
            basis = next(
                (b for b, words in BASES.items() if cells["basis"].casefold() in words), None
            )
            if not CELL_AMOUNT.fullmatch(cells["amount"]) or len(amounts) != 1 or basis is None:
                issues.append("unsupported_table_layout")
                break
            amount = next(iter(amounts))
            if amount <= 0 or amount >= Decimal("1000000000000"):
                issues.append("unsupported_table_layout")
                break
            label = cells["label"]
            code = next((c for c, aliases in LABELS.items() if label.casefold() in aliases), None)
            page_rows.append(
                TableRow(
                    header=_span(section.page_number, lines[start : start + 3]),
                    cells=_span(section.page_number, chunk),
                    label=label,
                    coverage_code=code,
                    amount=format(amount, "f"),
                    basis=basis,
                )
            )
        else:
            rows.extend(page_rows)
    if context.truncated or context.incomplete_source:
        issues.append("incomplete_context")
    if not spans:
        issues.append("empty_evidence_plan")
    return EvidencePlan(
        context_sha256=artifact_id(context),
        required_spans=tuple(spans),
        table_suspected=suspected,
        table_rows=tuple(rows),
        issues=tuple(sorted(set(issues))),
    )


def evidence_issues(context, evidence):
    """Cover every non-whitespace source character using resolved page intervals.

    No concatenated quote search: fragments on another page cannot fill a gap.
    This deliberately broad policy avoids guessing which antecedents or exceptions matter.
    """
    for section in context.sections:
        intervals = sorted(
            (e.start_char, e.end_char) for e in evidence if e.page_number == section.page_number
        )
        for _, start, end in _lines(section):
            cursor = start
            for a, b in intervals:
                if b <= cursor or a >= end:
                    continue
                if (
                    a > cursor
                    and section.text[
                        cursor - section.start_char : min(a, end) - section.start_char
                    ].strip()
                ):
                    return ["incomplete_evidence_context"]
                cursor = max(cursor, b)
                if cursor >= end:
                    break
            if (
                cursor < end
                and section.text[cursor - section.start_char : end - section.start_char].strip()
            ):
                return ["incomplete_evidence_context"]
    return []


def structural_issues(context, candidate, evidence):
    plan = build_plan(context)
    issues = list(plan.issues) + evidence_issues(context, evidence)
    if plan.table_suspected and candidate.coverage_status != "unknown":
        target = [r for r in plan.table_rows if r.coverage_code == candidate.coverage_code]
        if len(target) != 1:
            issues.append("ambiguous_target_table_row")
        else:
            row = target[0]
            if (
                candidate.coverage_status != "covered"
                or candidate.limit_amount is None
                or Decimal(candidate.limit_amount) != Decimal(row.amount)
                or candidate.currency != row.currency
                or candidate.limit_basis != row.basis
            ):
                issues.append("table_limit_binding_mismatch")
        # Flat three-column rows cannot prove hierarchical monetary relationships.
        if candidate.sublimits or candidate.deductible:
            issues.append("unsupported_table_monetary_hierarchy")
    return issues


def reflection_issues(context, reflection, quotes, *, decision=None):
    plan = build_plan(context)
    issues = []
    if reflection.plan_sha256 != artifact_id(plan):
        issues.append("reflection_wrong_plan")
    if set(i.check for i in reflection.items) != set(CHECKS) or len(reflection.items) != len(
        CHECKS
    ):
        issues.append("reflection_incomplete_checks")
    positive = True
    for item in reflection.items:
        if len(set(item.evidence_indices)) != len(item.evidence_indices) or any(
            i >= len(quotes) for i in item.evidence_indices
        ):
            issues.append("reflection_invalid_reference")
        applicable = not (item.check == "table_binding" and not plan.table_suspected)
        acceptable = item.outcome == "pass" or (not applicable and item.outcome == "not_applicable")
        if not acceptable:
            positive = False
            issues.append("reflection_" + item.check + "_unresolved")
        if item.outcome == "pass" and not item.evidence_indices:
            issues.append("reflection_missing_reference")
    if decision is not None and (decision in ("supported", "supported_unknown")) != positive:
        issues.append("reflection_decision_conflict")
    return issues
