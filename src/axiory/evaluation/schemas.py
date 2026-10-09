"""Versioned, parser-independent source annotations and evaluation contracts."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from axiory.ingestion_models import ArtifactModel, Digest, ExtractionArtifact, IngestionLimits

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]*$")]
Positive = Annotated[int, Field(gt=0)]
Text = Annotated[str, Field(min_length=1)]
FailureClass = Literal[
    "missing_text",
    "incorrect_reading_order",
    "table_structure_lost",
    "incorrect_value_association",
    "broken_clause_boundary",
    "invalid_evidence_span",
    "incorrect_page_reference",
    "unicode_corruption",
    "extraction_failure",
]


class SourceBlock(ArtifactModel):
    id: Identifier
    page: Positive
    text: Text
    x: Annotated[float, Field(ge=20, le=570)] = 45.0
    y: Annotated[float, Field(ge=20, le=820)] = 740.0
    font_size: Annotated[float, Field(ge=5, le=24)] = 10.0
    rendering: Literal["text", "image", "outline"] = "text"


class TextAnchor(ArtifactModel):
    page: Positive
    quote: Text


class GoldClause(ArtifactModel):
    id: Identifier
    parts: tuple[TextAnchor, ...] = Field(min_length=1)


class TableCell(ArtifactModel):
    row: Annotated[int, Field(ge=0)]
    column: Annotated[int, Field(ge=0)]
    text: Text
    row_span: Positive = 1
    column_span: Positive = 1
    header: bool = False


class GoldTable(ArtifactModel):
    id: Identifier
    page: Positive
    cells: tuple[TableCell, ...] = Field(min_length=1)
    # Each tuple: header row, header column, value row, value column.
    associations: tuple[tuple[int, int, int, int], ...] = ()

    @model_validator(mode="after")
    def valid_cells(self) -> Self:
        keys = {(cell.row, cell.column): cell for cell in self.cells}
        occupied = set()
        for cell in self.cells:
            area = {
                (r, c)
                for r in range(cell.row, cell.row + cell.row_span)
                for c in range(cell.column, cell.column + cell.column_span)
            }
            if area & occupied:
                raise ValueError("Overlapping table cells")
            occupied |= area
        for hr, hc, vr, vc in self.associations:
            if (hr, hc) not in keys or (vr, vc) not in keys or not keys[hr, hc].header:
                raise ValueError("Invalid header/value association")
        return self


class GoldFixture(ArtifactModel):
    schema_version: Literal["1"] = "1"
    fixture_id: Identifier
    document_version: Literal["1"] = "1"
    language: Literal["de", "fr", "it"]
    layout_type: Identifier
    page_count: Positive
    blocks: tuple[SourceBlock, ...]
    # Page texts in intended source reading order, NOT parser outputs.
    expected_text: tuple[str, ...]
    expected_clauses: tuple[GoldClause, ...] = ()
    expected_tables: tuple[GoldTable, ...] = ()
    expected_evidence: tuple[TextAnchor, ...] = ()
    expected_reading_order: tuple[Identifier, ...]
    # Separately author-defined operational expectation, not a quality target.
    expected_extraction_status: Literal[
        "success", "partial", "empty", "needs_ocr", "not_extractable"
    ]
    # PDF paint order is intentionally independent of the intended reading order.
    paint_order: tuple[Identifier, ...]
    interpretation_status: Literal["not_evaluated"] = "not_evaluated"

    @model_validator(mode="after")
    def coherent_source(self) -> Self:
        blocks = {block.id: block for block in self.blocks}
        if len(blocks) != len(self.blocks):
            raise ValueError("Duplicate block IDs")
        for order in (self.paint_order, self.expected_reading_order):
            if len(order) != len(blocks) or set(order) != set(blocks):
                raise ValueError("Orders must cover every block exactly once")
        if any(block.page > self.page_count for block in self.blocks):
            raise ValueError("Block page out of bounds")
        expected = tuple(
            "\n".join(
                blocks[key].text for key in self.expected_reading_order if blocks[key].page == page
            )
            for page in range(1, self.page_count + 1)
        )
        if self.expected_text != expected:
            raise ValueError("Expected text disagrees with authored source blocks")
        anchors = [
            *self.expected_evidence,
            *(part for clause in self.expected_clauses for part in clause.parts),
        ]
        for anchor in anchors:
            if anchor.page > self.page_count or anchor.quote not in expected[anchor.page - 1]:
                raise ValueError("Annotation is not in the intended source text")
        if len({c.id for c in self.expected_clauses}) != len(self.expected_clauses):
            raise ValueError("Duplicate clause IDs")
        if len({t.id for t in self.expected_tables}) != len(self.expected_tables):
            raise ValueError("Duplicate table IDs")
        for table in self.expected_tables:
            if table.page > self.page_count or any(
                cell.text not in expected[table.page - 1] for cell in table.cells
            ):
                raise ValueError("Table content is absent from the source")
        return self


class Metric(ArtifactModel):
    status: Literal["measured", "unsupported", "not_evaluable"]
    numerator: float | None = Field(default=None, allow_inf_nan=False)
    denominator: float | None = Field(default=None, allow_inf_nan=False)
    reason: str | None = None
    value: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def valid_fraction(self) -> Self:
        if self.status == "measured":
            if (
                self.numerator is None
                or self.numerator < 0
                or self.denominator is None
                or self.denominator <= 0
            ):
                raise ValueError("Measured metrics require numerator >= 0 and denominator > 0")
        elif self.numerator is not None or self.denominator is not None or not self.reason:
            raise ValueError("Unavailable metrics require a reason and no score")
        expected = self.numerator / self.denominator if self.status == "measured" else None
        if self.value is not None and self.value != expected:
            raise ValueError("Score disagrees with numerator/denominator")
        object.__setattr__(self, "value", expected)
        return self


class LocatedEvidence(ArtifactModel):
    target: Annotated[int, Field(ge=0)]
    page: Positive
    start: Annotated[int, Field(ge=0)]
    end: Positive
    quote: Text


class Observation(ArtifactModel):
    status: Literal[
        "success",
        "partial",
        "empty",
        "needs_ocr",
        "not_extractable",
        "encrypted",
        "damaged",
        "error",
    ]
    pages: tuple[str, ...]
    evidence: tuple[LocatedEvidence, ...] = ()
    clauses: tuple[GoldClause, ...] | None = None
    tables: tuple[GoldTable, ...] | None = None


class Failure(ArtifactModel):
    kind: FailureClass
    basis: Literal["measured", "capability_gap"]
    detail: str


class BenchmarkConfig(ArtifactModel):
    repeats: Annotated[int, Field(ge=2, le=10)] = 2
    limits: IngestionLimits = IngestionLimits()


class CaseResult(ArtifactModel):
    fixture_id: Identifier
    layout_type: Identifier
    pdf_sha256: Digest
    gold_sha256: Digest
    receipt_id: Digest | None
    extraction: ExtractionArtifact | None
    observation: Observation
    metrics: dict[str, Metric]
    failures: tuple[Failure, ...]
    diagnostics: tuple[str, ...]
    repeat_fingerprints: tuple[str | None, ...]
    runtimes_ms: tuple[float, ...]
