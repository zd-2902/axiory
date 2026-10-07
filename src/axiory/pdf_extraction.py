"""Deterministic pypdf adapter; failures are data, never silently dropped pages."""

from hashlib import sha256
from io import BytesIO

import pypdf
from pypdf.generic import ContentStream

from axiory.ingestion_models import ExtractedPage, ExtractionArtifact, page_outcome


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


def extract_pdf(original: bytes) -> ExtractionArtifact:
    """Keep unnormalised page text and explicit failures, with no wall clock or OCR."""
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
