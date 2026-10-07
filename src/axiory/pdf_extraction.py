"""Deterministic pypdf adapter; failures are data, never silently dropped pages."""

from hashlib import sha256
from io import BytesIO

import pypdf
from pypdf.generic import ContentStream

from axiory.ingestion_models import (
    ExtractedPage,
    ExtractionArtifact,
    IngestionLimits,
    page_outcome,
)


def _has_images(resources: object, seen: set[int] | None = None) -> bool:
    # Inspect image/form declarations without decoding images or requiring Pillow.
    seen = set() if seen is None else seen
    resources = resources.get_object() if hasattr(resources, "get_object") else resources
    if not resources or id(resources) in seen:
        return False
    seen.add(id(resources))
    xobjects = resources.get("/XObject", {})
    if hasattr(xobjects, "get_object"):
        xobjects = xobjects.get_object()
    for reference in xobjects.values():
        obj = reference.get_object()
        if obj.get("/Subtype") == "/Image":
            return True
        if obj.get("/Subtype") == "/Form" and _has_images(obj.get("/Resources"), seen):
            return True
    return False


class ResourceLimitError(ValueError):
    """An admission rejection, never a successful/partial extraction result."""

    def __init__(self, code: str, actual: int, limit: int):
        self.code = code
        self.actual = actual
        self.limit = limit
        super().__init__(f"{code}: {actual} exceeds {limit}")


def check_pdf_size(size: int, limits: IngestionLimits) -> None:
    if size > limits.max_pdf_bytes:
        raise ResourceLimitError("pdf_size_exceeded", size, limits.max_pdf_bytes)


def extract_pdf(original: bytes, *, limits: IngestionLimits | None = None) -> ExtractionArtifact:
    """Keep unnormalised page text and explicit failures, with no wall clock or OCR."""
    limits = IngestionLimits.model_validate_json(
        (limits if limits is not None else IngestionLimits()).model_dump_json()
    )
    check_pdf_size(len(original), limits)
    common = {"original_sha256": sha256(original).hexdigest(), "parser_version": pypdf.__version__}
    if not original:
        return ExtractionArtifact(**common, status="empty", pages=())
    try:
        reader = pypdf.PdfReader(BytesIO(original), strict=True)
        if reader.is_encrypted:
            return ExtractionArtifact(**common, status="encrypted", pages=())
        count = len(reader.pages)
    except Exception as exc:
        # This catch is intentionally restricted to the parser boundary.
        return ExtractionArtifact(
            **common, status="damaged", pages=(), error_type=type(exc).__name__
        )
    # Outside the parser exception handler: do not turn a policy rejection into damaged.
    if count > limits.max_pages:
        raise ResourceLimitError("page_count_exceeded", count, limits.max_pages)
    pages = []
    for index in range(count):
        try:
            page = reader.pages[index]
            text = page.extract_text(extraction_mode="plain")
            if not isinstance(text, str):
                raise TypeError("Parser did not return text")
            if text.strip():
                status = "text"
            else:
                content = page.get_contents()
                inline_image = content is not None and any(
                    operator == b"INLINE IMAGE"
                    for _, operator in ContentStream(content, reader).operations
                )
                if inline_image or _has_images(page.get("/Resources")):
                    status = "needs_ocr"
                elif content is None or not content.get_data().strip():
                    status = "empty"
                else:
                    status = "not_extractable"
            pages.append(ExtractedPage(number=index + 1, status=status, text=text))
        except Exception as exc:
            pages.append(
                ExtractedPage(
                    number=index + 1, status="error", text="", error_type=type(exc).__name__
                )
            )
    return ExtractionArtifact(**common, status=page_outcome(tuple(pages)), pages=tuple(pages))
