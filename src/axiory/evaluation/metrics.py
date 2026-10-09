"""Explicit denominators; unsupported structural output is never replaced by text guesses."""

import re
from collections import Counter
from itertools import combinations

from axiory.evaluation.schemas import Failure, GoldFixture, LocatedEvidence, Metric, Observation


def measured(numerator: float, denominator: float, reason: str | None = None) -> Metric:
    if denominator == 0:
        return unavailable("not_evaluable", reason or "Zero applicable reference items")
    return Metric(
        status="measured", numerator=float(numerator), denominator=float(denominator), reason=reason
    )


def unavailable(status: str, reason: str) -> Metric:
    return Metric(status=status, reason=reason)


def normalize(text: str) -> str:
    return " ".join(text.split())


def distance(reference, actual) -> int:
    """Exact Levenshtein distance, O(n*m) time and O(min(n,m)) memory."""
    if len(reference) < len(actual):
        reference, actual = actual, reference
    previous = list(range(len(actual) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(actual, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def occurrences(pages: tuple[str, ...], quote: str) -> list[tuple[int, int]]:
    return [
        (page, match.start())
        for page, text in enumerate(pages, 1)
        for match in re.finditer(f"(?={re.escape(quote)})", text)
    ]


def locate_evidence(gold: GoldFixture, pages: tuple[str, ...]) -> tuple[LocatedEvidence, ...]:
    """Oracle-assisted exact-quote locator baseline, NOT an insurance claim extractor.

    Do not use the gold page as a selection hint. Ambiguous/missing quotes yield no candidate.
    """
    result = []
    for index, target in enumerate(gold.expected_evidence):
        found = occurrences(pages, target.quote)
        if len(found) == 1:
            page, start = found[0]
            result.append(
                LocatedEvidence(
                    target=index,
                    page=page,
                    start=start,
                    end=start + len(target.quote),
                    quote=target.quote,
                )
            )
    return tuple(result)


def evidence_metrics(gold: GoldFixture, observation: Observation) -> dict[str, Metric]:
    valid = 0
    correct_page = 0
    covered = set()
    for item in observation.evidence:
        span_valid = (
            item.page <= len(observation.pages)
            and item.end > item.start
            and item.end <= len(observation.pages[item.page - 1])
            and observation.pages[item.page - 1][item.start : item.end] == item.quote
        )
        valid += span_valid
        if item.target < len(gold.expected_evidence):
            target = gold.expected_evidence[item.target]
            correct_page += item.page == target.page
            if span_valid and item.quote == target.quote and item.page == target.page:
                covered.add(item.target)
    count = len(gold.expected_evidence)
    return {
        "evidence_span_validity": measured(valid, len(observation.evidence)),
        "page_reference_accuracy": measured(correct_page, len(observation.evidence)),
        "missing_evidence_rate": measured(count - len(covered), count),
    }


def score(gold: GoldFixture, observation: Observation) -> dict[str, Metric]:
    expected = normalize("\n".join(gold.expected_text))
    actual = normalize("\n".join(observation.pages))
    reference_chars = Counter(c for c in expected if not c.isspace())
    actual_chars = Counter(c for c in actual if not c.isspace())
    reference_unicode = Counter(c for c in expected if ord(c) > 127)
    actual_unicode = Counter(c for c in actual if ord(c) > 127)
    metrics = {
        "character_error_rate": measured(distance(expected, actual), len(expected)),
        "word_error_rate": measured(
            distance(expected.split(), actual.split()), len(expected.split())
        ),
        "text_completeness": measured(
            sum((reference_chars & actual_chars).values()), sum(reference_chars.values())
        ),
        "unicode_integrity": measured(
            sum((reference_unicode & actual_unicode).values()), sum(reference_unicode.values())
        ),
    }
    by_id = {block.id: block for block in gold.blocks}
    positions = []
    for key in gold.expected_reading_order:
        matches = occurrences(observation.pages, by_id[key].text)
        positions.append(matches[0] if len(matches) == 1 else None)
    pairs = [
        (left, right)
        for left, right in combinations(positions, 2)
        if left is not None and right is not None
    ]
    metrics["reading_order_accuracy"] = measured(
        sum(left < right for left, right in pairs),
        len(pairs),
        "Pairwise order of uniquely located exact source anchors; missing anchors excluded",
    )
    metrics["reading_order_anchor_coverage"] = measured(
        sum(pos is not None for pos in positions), len(positions)
    )
    if not gold.expected_clauses:
        metrics["clause_boundary_accuracy"] = unavailable("not_evaluable", "No annotated clauses")
    elif observation.clauses is None:
        metrics["clause_boundary_accuracy"] = unavailable(
            "unsupported", "pypdf adapter does not output clause boundaries"
        )
    else:
        observed = {clause.id: clause for clause in observation.clauses}
        metrics["clause_boundary_accuracy"] = measured(
            sum(observed.get(clause.id) == clause for clause in gold.expected_clauses),
            len(gold.expected_clauses),
        )
    if not gold.expected_tables:
        for name in ("table_cell_extraction_accuracy", "table_header_value_association"):
            metrics[name] = unavailable("not_evaluable", "No annotated tables")
    elif observation.tables is None:
        for name in ("table_cell_extraction_accuracy", "table_header_value_association"):
            metrics[name] = unavailable("unsupported", "pypdf adapter outputs no table structure")
    else:
        observed = {table.id: table for table in observation.tables}
        correct_cells = correct_links = cell_count = link_count = 0
        for table in gold.expected_tables:
            candidate = observed.get(table.id)
            cells = (
                {(cell.row, cell.column): cell for cell in candidate.cells}
                if (candidate and candidate.page == table.page)
                else {}
            )
            for cell in table.cells:
                cell_count += 1
                correct_cells += cells.get((cell.row, cell.column)) == cell
            links = (
                set(candidate.associations) if candidate and candidate.page == table.page else set()
            )
            expected_cells = {(cell.row, cell.column): cell for cell in table.cells}
            correct_links += sum(
                link in links
                and cells.get(link[:2]) == expected_cells[link[:2]]
                and cells.get(link[2:]) == expected_cells[link[2:]]
                for link in table.associations
            )
            link_count += len(table.associations)
        metrics["table_cell_extraction_accuracy"] = measured(correct_cells, cell_count)
        metrics["table_header_value_association"] = measured(correct_links, link_count)
    metrics.update(evidence_metrics(gold, observation))
    metrics["extraction_failure_rate"] = measured(
        observation.status not in ("success", "partial"), 1
    )
    metrics["partial_extraction_rate"] = measured(observation.status == "partial", 1)
    metrics["expected_status_match"] = measured(
        observation.status == gold.expected_extraction_status, 1
    )
    return metrics


def classify(metrics: dict[str, Metric], observation: Observation) -> tuple[Failure, ...]:
    findings = []
    for metric, kind in (
        ("text_completeness", "missing_text"),
        ("reading_order_accuracy", "incorrect_reading_order"),
        ("clause_boundary_accuracy", "broken_clause_boundary"),
        ("table_cell_extraction_accuracy", "table_structure_lost"),
        ("table_header_value_association", "incorrect_value_association"),
        ("evidence_span_validity", "invalid_evidence_span"),
        ("page_reference_accuracy", "incorrect_page_reference"),
        ("unicode_integrity", "unicode_corruption"),
    ):
        value = metrics[metric]
        if value.status == "measured" and value.value < 1:
            findings.append(
                Failure(kind=kind, basis="measured", detail=f"{metric}={value.value:.6f}")
            )
        elif value.status == "unsupported":
            findings.append(Failure(kind=kind, basis="capability_gap", detail=value.reason))
    if metrics["extraction_failure_rate"].value > 0:
        findings.append(
            Failure(
                kind="extraction_failure",
                basis="measured",
                detail=(
                    f"First extraction state: {observation.status}; "
                    f"failure rate={metrics['extraction_failure_rate'].value:.6f}"
                ),
            )
        )
    return tuple(findings)


def aggregate(cases) -> dict:
    """Micro-average available numerators/denominators, reporting unavailable counts."""
    result = {}
    for name in sorted({name for case in cases for name in case.metrics}):
        values = [case.metrics[name] for case in cases]
        available = [value for value in values if value.status == "measured"]
        result[name] = {
            "metric": measured(
                sum(v.numerator for v in available), sum(v.denominator for v in available)
            ).model_dump(),
            "measured_cases": len(available),
            "unsupported_cases": sum(v.status == "unsupported" for v in values),
            "not_evaluable_cases": sum(v.status == "not_evaluable" for v in values),
        }
        if not available and any(v.status == "unsupported" for v in values):
            result[name]["metric"] = unavailable(
                "unsupported", "No measurable cases; adapter lacks this capability"
            ).model_dump()
    return result
