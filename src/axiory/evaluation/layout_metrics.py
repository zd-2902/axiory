"""Exact multiset precision/recall: extra and duplicate cells count as false positives."""

from collections import Counter

from axiory.evaluation.metrics import classify, measured, unavailable
from axiory.evaluation.schemas import Failure


def cell_metrics(gold, extraction):
    names = ("table_cell_precision", "table_cell_recall")
    if extraction.capabilities.tables == "unsupported":
        return {name: unavailable("unsupported", "Adapter has no table output") for name in names}
    if any(page.tables is None for page in extraction.pages) or not extraction.pages:
        return {
            name: unavailable("not_evaluable", "Table extraction unavailable/failed")
            for name in names
        }
    reference = Counter()
    # Match tables by physical page and top-left ordinal, never by text or gold IDs.
    by_page = {}
    for table in gold.expected_tables:
        ordinal = by_page.get(table.page, 0)
        by_page[table.page] = ordinal + 1
        for cell in table.cells:
            reference[
                (
                    table.page,
                    ordinal,
                    cell.row,
                    cell.column,
                    cell.row_span,
                    cell.column_span,
                    cell.text,
                )
            ] += 1
    actual = Counter()
    for page in extraction.pages:
        for ordinal, table in enumerate(page.tables):
            for cell in table.cells:
                actual[
                    (
                        page.number,
                        ordinal,
                        cell.row,
                        cell.column,
                        cell.row_span,
                        cell.column_span,
                        cell.text,
                    )
                ] += 1
    correct = sum((reference & actual).values())
    return {
        "table_cell_precision": measured(correct, sum(actual.values())),
        "table_cell_recall": measured(correct, sum(reference.values())),
    }


def association_metrics(reference, actual):
    """None means unavailable, () supported but no relations. Duplicates count."""
    names = ("header_association_precision", "header_association_recall")
    if actual is None:
        return {
            name: unavailable("unsupported", "No reliable header/value relations") for name in names
        }
    wanted, found = Counter(reference), Counter(actual)
    correct = sum((wanted & found).values())
    return {
        names[0]: measured(correct, sum(found.values())),
        names[1]: measured(correct, sum(wanted.values())),
    }


def findings(metrics, observation, extraction):
    result = list(classify(metrics, observation))
    if extraction and extraction.capabilities.tables != "unsupported":
        # Lack of legacy header flags does not imply lack of geometrically detected cells.
        result = [item for item in result if item.kind != "table_structure_lost"]
        for name in ("table_cell_precision", "table_cell_recall"):
            metric = metrics[name]
            if metric.status == "measured" and metric.value < 1:
                result.append(
                    Failure(
                        kind="table_structure_lost",
                        basis="measured",
                        detail=f"{name}={metric.value:.6f}",
                    )
                )
    return tuple(result)
