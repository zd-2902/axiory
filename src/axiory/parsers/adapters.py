"""Version-pinned parser adapters. No OCR, network calls or implicit optional imports."""

from hashlib import sha256
from typing import Protocol

import pypdf

from axiory.ingestion_models import IngestionLimits, page_outcome
from axiory.parsers.models import (
    Box,
    Capabilities,
    LayoutArtifact,
    LayoutCell,
    LayoutPage,
    LayoutTable,
    ParserConfig,
    RawSpan,
    TextElement,
)
from axiory.pdf_extraction import ResourceLimitError, check_pdf_size, extract_pdf


class ParserProtocol(Protocol):
    config: ParserConfig

    @property
    def version(self) -> str: ...

    def extract(
        self, original: bytes, version_sha256: str, limits: IngestionLimits
    ) -> LayoutArtifact: ...


class PypdfAdapter:
    def __init__(self, config: ParserConfig | None = None):
        self.config = ParserConfig.model_validate_json((config or ParserConfig()).model_dump_json())
        if self.config.parser != "pypdf":
            raise ValueError("Wrong parser configuration")

    @property
    def version(self) -> str:
        return pypdf.__version__

    def extract(self, original, version_sha256, limits):
        old = extract_pdf(original, limits=limits)
        return LayoutArtifact(
            original_sha256=old.original_sha256,
            version_sha256=version_sha256,
            parser_version=self.version,
            config=self.config,
            capabilities=Capabilities(),
            status=old.status,
            error_type=old.error_type,
            pages=tuple(LayoutPage(**p.model_dump(), raw_text=p.text) for p in old.pages),
        )


def box(rect) -> Box:
    return Box(x0=float(rect[0]), y0=float(rect[1]), x1=float(rect[2]), y1=float(rect[3]))


def raw_span(text, raw):
    start = raw.find(text) if text else -1
    if start < 0 or raw.find(text, start + 1) >= 0:
        return None  # No invented mapping for repeated/missing text.
    return RawSpan(start=start, end=start + len(text))


def text_elements(page, raw):
    elements = []
    for index, block in enumerate(page.get_text("dict", sort=False)["blocks"]):
        if block["type"] != 0:
            continue
        block_id = f"block-{index}"
        lines = []
        for number, line in enumerate(block["lines"]):
            text = "".join(span["text"] for span in line["spans"])
            element = TextElement(
                id=f"{block_id}-line-{number}",
                kind="line",
                parent_id=block_id,
                text=text,
                bbox=box(line["bbox"]),
                raw_span=raw_span(text, raw),
            )
            lines.append(element)
        block_text = "\n".join(line.text for line in lines)
        elements.append(
            TextElement(
                id=block_id,
                kind="block",
                text=block_text,
                bbox=box(block["bbox"]),
                raw_span=raw_span(block_text, raw),
            )
        )
        elements.extend(lines)
    return tuple(elements)


def tables(page):
    result = []
    # Native library's geometric detector is heuristic, not tagged-PDF truth.
    found = sorted(page.find_tables().tables, key=lambda t: (t.bbox[1], t.bbox[0]))
    for index, table in enumerate(found):
        matrix = table.extract()
        rects = [rect for row in table.rows for rect in row.cells if rect is not None]
        xs = sorted({round(rect[i], 3) for rect in rects for i in (0, 2)})
        ys = sorted({round(rect[i], 3) for rect in rects for i in (1, 3)})
        cells = []
        seen = set()
        for row, native_row in enumerate(table.rows):
            for col, rect in enumerate(native_row.cells):
                if rect is None or tuple(rect) in seen:
                    continue
                seen.add(tuple(rect))
                x0, y0, x1, y1 = (round(value, 3) for value in rect)
                cells.append(
                    LayoutCell(
                        row=ys.index(y0),
                        column=xs.index(x0),
                        row_span=ys.index(y1) - ys.index(y0),
                        column_span=xs.index(x1) - xs.index(x0),
                        text=matrix[row][col] or "",
                        bbox=box(rect),
                    )
                )
        result.append(
            LayoutTable(
                id=f"table-{index}",
                bbox=box(table.bbox),
                cells=tuple(cells),
                header_candidates=tuple(table.header.names),
            )
        )
    return tuple(result)


class PyMuPDFAdapter:
    """Explicit experiment gate is required even when the extra is installed."""

    def __init__(self, config: ParserConfig | None = None, *, experimental: bool = False):
        if not experimental:
            raise ValueError("PyMuPDF requires experimental=True and a reviewed license strategy")
        self.config = ParserConfig.model_validate_json(
            (
                config or ParserConfig(parser="pymupdf", sort_text=True, tables=True)
            ).model_dump_json()
        )
        if self.config.parser != "pymupdf":
            raise ValueError("Wrong parser configuration")
        try:
            import pymupdf
        except ImportError as exc:
            raise ValueError("Install the experimental-pymupdf extra explicitly") from exc
        self.library = pymupdf

    @property
    def version(self):
        return self.library.VersionBind

    def extract(self, original, version_sha256, limits):
        check_pdf_size(len(original), limits)
        common = dict(
            original_sha256=sha256(original).hexdigest(),
            version_sha256=version_sha256,
            parser_version=self.version,
            config=self.config,
            capabilities=Capabilities(
                blocks="parser",
                lines="parser",
                coordinates="parser",
                reading_order="heuristic",
                tables="heuristic" if self.config.tables else "unsupported",
            ),
        )
        try:
            document = self.library.open(stream=original, filetype="pdf")
        except Exception as exc:
            return LayoutArtifact(
                **common, status="damaged", pages=(), error_type=type(exc).__name__
            )
        with document:
            if document.is_encrypted or (document.metadata or {}).get("encryption"):
                return LayoutArtifact(**common, status="encrypted", pages=())
            if document.is_repaired:
                return LayoutArtifact(
                    **common, status="damaged", pages=(), error_type="RepairedPdfRejected"
                )
            if document.page_count > limits.max_pages:
                raise ResourceLimitError(
                    "page_count_exceeded", document.page_count, limits.max_pages
                )
            pages = []
            for number in range(document.page_count):
                raw = text = ""
                try:
                    page = document[number]
                    raw = page.get_text("text", sort=False)
                    text = page.get_text("text", sort=self.config.sort_text)
                    status = (
                        "text"
                        if text.strip()
                        else (
                            "needs_ocr"
                            if page.get_image_info()
                            else "not_extractable"
                            if page.get_drawings()
                            else "empty"
                        )
                    )
                    errors = []
                    elements = ()
                    extracted_tables = None
                    try:
                        elements = text_elements(page, raw)
                    except Exception as exc:
                        errors.append("elements:" + type(exc).__name__)
                    if self.config.tables:
                        try:
                            extracted_tables = tables(page)
                        except Exception as exc:
                            errors.append("tables:" + type(exc).__name__)
                    order = tuple(
                        e.id
                        for e in sorted(
                            (e for e in elements if e.kind == "line"),
                            key=lambda e: (e.bbox.y0, e.bbox.x0, e.id),
                        )
                    )
                    pages.append(
                        LayoutPage(
                            number=number + 1,
                            status=status,
                            text=text,
                            raw_text=raw,
                            width=float(page.cropbox.width),
                            height=float(page.cropbox.height),
                            rotation=page.rotation,
                            elements=elements,
                            reading_order=order,
                            tables=extracted_tables,
                            layout_errors=tuple(errors),
                        )
                    )
                except Exception as exc:
                    # Preserve already extracted text even if layout validation fails.
                    if raw.strip() or text.strip():
                        pages.append(
                            LayoutPage(
                                number=number + 1,
                                status="text",
                                text=text or raw,
                                raw_text=raw,
                                layout_errors=("layout:" + type(exc).__name__,),
                            )
                        )
                    else:
                        pages.append(
                            LayoutPage(
                                number=number + 1,
                                status="error",
                                text="",
                                raw_text=raw,
                                error_type=type(exc).__name__,
                            )
                        )
            return LayoutArtifact(**common, pages=tuple(pages), status=page_outcome(tuple(pages)))


def adapter(config: ParserConfig, *, experimental=False) -> ParserProtocol:
    config = ParserConfig.model_validate_json(config.model_dump_json())
    if config.parser == "pypdf":
        return PypdfAdapter(config)
    return PyMuPDFAdapter(config, experimental=experimental)
