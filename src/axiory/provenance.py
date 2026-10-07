"""Mechanical source checks, never a semantic or legal verification."""

from hashlib import sha256

from axiory.models import Claim, Document, Evidence


def verify_source(claim: Claim, document: Document, source: bytes) -> None:
    """Raise ValueError on a broken product, document, hash or exact text reference.

    Demo offsets refer to Unicode characters in UTF-8 decoded source bytes.
    PDF ingestion will need a separate versioned extraction artifact.
    """
    if any(not isinstance(item, Evidence) for item in claim.evidence):
        raise ValueError("PDF evidence requires DocumentStore.verify_claim")
    if not claim.evidence:
        raise ValueError("No evidence to verify")
    if document.product_id != claim.product_id:
        raise ValueError("Document belongs to another product")
    if sha256(source).hexdigest() != document.sha256:
        raise ValueError("Source hash mismatch")
    text = source.decode("utf-8")
    for evidence in claim.evidence:
        if evidence.document_id != document.id:
            raise ValueError("Evidence belongs to another document")
        if text[evidence.start_char : evidence.end_char] != evidence.quote:
            raise ValueError("Quote does not match source span")
