"""Deterministic paragraph-preserving prefix context; reloaded originals are authoritative."""

import re

from axiory.extraction.schemas import Code, Context, Section
from axiory.ingestion import IntegrityError
from axiory.parsers.store import LayoutStore


def build_context(
    store: LayoutStore, receipt: str, codes: tuple[Code, ...], *, max_chars: int = 24000
) -> Context:
    if type(max_chars) is not int or max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if not codes or len(set(codes)) != len(codes):
        raise ValueError("Request distinct coverage codes")
    stored = store.load(receipt)
    pages = stored.extraction.pages
    if not any(p.text for p in pages):
        raise IntegrityError("No extractable context")
    sections = []
    remaining = max_chars
    stopped = False
    for page in pages:
        # Keep paragraph separators and original Unicode offsets. Never remove headers.
        for match in re.finditer(r".+?(?:\n\s*\n|\Z)", page.text, re.DOTALL):
            text = match.group()
            if stopped:
                continue
            if len(text) > remaining:
                stopped = True  # Do not silently cut a clause or jump over exceptions.
                continue
            if text.strip():
                sections.append(
                    Section(
                        page_number=page.number,
                        start_char=match.start(),
                        end_char=match.end(),
                        text=text,
                    )
                )
                remaining -= len(text)
    omitted = sum(len(p.text) for p in pages) - sum(len(s.text) for s in sections)
    return Context(
        receipt_sha256=receipt,
        document_id=stored.document.id,
        product_id=stored.document.product_id,
        version_sha256=stored.receipt.version_sha256,
        original_sha256=stored.version.original_sha256,
        extraction_sha256=stored.receipt.extraction_sha256,
        parser_config=stored.extraction.config,
        parser_version=stored.extraction.parser_version,
        coverage_codes=codes,
        sections=tuple(sections),
        max_chars=max_chars,
        truncated=omitted > 0,
        omitted_chars=omitted,
        incomplete_source=stored.extraction.status != "success",
    )


def validate_context(store: LayoutStore, context: Context) -> None:
    context = Context.model_validate_json(context.model_dump_json())
    if (
        build_context(
            store, context.receipt_sha256, context.coverage_codes, max_chars=context.max_chars
        )
        != context
    ):
        raise IntegrityError("Context differs from verified source")
