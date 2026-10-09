"""Schema 2 adds layout/configuration without changing schema-1 artifacts."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from axiory.ingestion_models import (
    Acquisition,
    ArtifactModel,
    Digest,
    DocumentVersion,
    ExtractedPage,
    ExtractionArtifact,
    ExtractionStatus,
    IngestionReceipt,
    LogicalDocument,
    Nonempty,
    PositiveInt,
)

Finite = Annotated[float, Field(allow_inf_nan=False)]
Capability = Literal["parser", "heuristic", "unsupported"]


class ParserConfig(ArtifactModel):
    schema_version: Literal["1"] = "1"
    adapter_version: Literal["1"] = "1"
    parser: Literal["pypdf", "pymupdf"] = "pypdf"
    sort_text: bool = False
    tables: bool = False

    @model_validator(mode="after")
    def supported(self) -> Self:
        if self.parser == "pypdf" and (self.sort_text or self.tables):
            raise ValueError("pypdf baseline supports plain-strict text only")
        return self


class Box(ArtifactModel):
    x0: Finite
    y0: Finite
    x1: Finite
    y1: Finite

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.x0 < 0 or self.y0 < 0 or self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Invalid bounding box")
        return self


class RawSpan(ArtifactModel):
    start: Annotated[int, Field(ge=0)]
    end: PositiveInt

    @model_validator(mode="after")
    def ordered(self) -> Self:
        if self.end <= self.start:
            raise ValueError("Empty or reversed span")
        return self


class TextElement(ArtifactModel):
    id: Nonempty
    kind: Literal["block", "line"]
    parent_id: str | None = None
    text: str
    bbox: Box
    source: Literal["parser"] = "parser"
    # Offsets in raw_text, never silently mapped into sorted text.
    raw_span: RawSpan | None


class LayoutCell(ArtifactModel):
    row: Annotated[int, Field(ge=0)]
    column: Annotated[int, Field(ge=0)]
    row_span: PositiveInt
    column_span: PositiveInt
    text: str
    bbox: Box
    source: Literal["heuristic"] = "heuristic"


class LayoutTable(ArtifactModel):
    id: Nonempty
    bbox: Box
    cells: tuple[LayoutCell, ...]
    source: Literal["heuristic"] = "heuristic"
    # Parser header guesses are preserved, never promoted to verified relationships.
    header_candidates: tuple[str | None, ...] = ()
    header_associations: None = None


class Capabilities(ArtifactModel):
    blocks: Capability = "unsupported"
    lines: Capability = "unsupported"
    coordinates: Capability = "unsupported"
    reading_order: Capability = "unsupported"
    tables: Capability = "unsupported"
    header_associations: Literal["unsupported"] = "unsupported"
    clauses: Literal["unsupported"] = "unsupported"


class LayoutPage(ExtractedPage):
    raw_text: str
    width: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    height: Annotated[float, Field(gt=0, allow_inf_nan=False)] | None = None
    rotation: Literal[0, 90, 180, 270] = 0
    coordinate_system: Literal["unrotated-cropbox-top-left-points"] = (
        "unrotated-cropbox-top-left-points"
    )
    elements: tuple[TextElement, ...] = ()
    reading_order: tuple[str, ...] = ()
    tables: tuple[LayoutTable, ...] | None = None
    layout_errors: tuple[str, ...] = ()

    @model_validator(mode="after")
    def coherent_layout(self) -> Self:
        if (self.width is None) != (self.height is None):
            raise ValueError("Both page dimensions are required")
        ids = {element.id for element in self.elements}
        if len(ids) != len(self.elements):
            raise ValueError("Duplicate element IDs")
        blocks = {element.id for element in self.elements if element.kind == "block"}
        if any(
            (element.kind == "line" and element.parent_id not in blocks)
            or (element.kind == "block" and element.parent_id is not None)
            for element in self.elements
        ):
            raise ValueError("Invalid block/line hierarchy")
        if len({table.id for table in self.tables or ()}) != len(self.tables or ()):
            raise ValueError("Duplicate table IDs")
        lines = {element.id for element in self.elements if element.kind == "line"}
        if len(self.reading_order) != len(lines) or set(self.reading_order) != lines:
            raise ValueError("Reading order must cover all lines")
        boxes = [element.bbox for element in self.elements]
        for element in self.elements:
            if element.parent_id is not None and element.parent_id not in ids:
                raise ValueError("Missing parent block")
            if element.raw_span:
                span = element.raw_span
                if (
                    span.end > len(self.raw_text)
                    or self.raw_text[span.start : span.end] != element.text
                ):
                    raise ValueError("Raw span does not match element text")
        for table in self.tables or ():
            boxes.append(table.bbox)
            boxes.extend(cell.bbox for cell in table.cells)
            occupied = set()
            for cell in table.cells:
                slots = {
                    (r, c)
                    for r in range(cell.row, cell.row + cell.row_span)
                    for c in range(cell.column, cell.column + cell.column_span)
                }
                if slots & occupied:
                    raise ValueError("Overlapping table cells")
                occupied |= slots
        if boxes and self.width is None:
            raise ValueError("Layout requires page dimensions")
        if any(box.x1 > self.width + 0.01 or box.y1 > self.height + 0.01 for box in boxes):
            raise ValueError("Bounding box outside page")
        return self


class LayoutArtifact(ArtifactModel):
    schema_version: Literal["2"] = "2"
    original_sha256: Digest
    version_sha256: Digest
    parser_version: Nonempty
    config: ParserConfig
    capabilities: Capabilities
    status: ExtractionStatus
    pages: tuple[LayoutPage, ...]
    error_type: Nonempty | None = None

    @model_validator(mode="after")
    def coherent(self) -> Self:
        # Reuse the exact schema-1 outcome contract.
        ExtractionArtifact(
            original_sha256=self.original_sha256,
            parser_version=self.parser_version,
            status=self.status,
            pages=tuple(
                ExtractedPage(
                    number=p.number, text=p.text, status=p.status, error_type=p.error_type
                )
                for p in self.pages
            ),
            error_type=self.error_type,
        )
        return self


class LayoutReceipt(IngestionReceipt):
    schema_version: Literal["2"] = "2"


class LayoutStored(ArtifactModel):
    receipt: LayoutReceipt
    document: LogicalDocument
    version: DocumentVersion
    acquisition: Acquisition
    extraction: LayoutArtifact
