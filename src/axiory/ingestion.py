"""Content-addressed, append-only synthetic PDF store with verified reloads."""

import json
import os
import re
import tempfile
from datetime import datetime
from hashlib import sha256
from pathlib import Path

import pypdf
from pydantic import BaseModel, HttpUrl, TypeAdapter

from axiory.ingestion_models import (
    Acquisition,
    DocumentVersion,
    ExtractionArtifact,
    IngestionReceipt,
    LogicalDocument,
    PdfEvidence,
    StoredIngestion,
    VersionMetadata,
)
from axiory.models import Claim
from axiory.pdf_extraction import extract_pdf


class IntegrityError(ValueError):
    """Stored bytes, metadata or source references do not match."""


class ParserVersionError(IntegrityError):
    """Reproduction requires the recorded parser version."""


def canonical_bytes(model: BaseModel) -> bytes:
    return json.dumps(
        model.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def artifact_id(model: BaseModel) -> str:
    return sha256(canonical_bytes(model)).hexdigest()


class DocumentStore:
    """Single local store. Hashes detect changes; they are not digital signatures."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, collection: str, digest: str, suffix: str = ".json") -> Path:
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise IntegrityError("Invalid artifact identifier")
        path = self.root / collection / f"{digest}{suffix}"
        if not path.resolve().is_relative_to(self.root) or path.is_symlink():
            raise IntegrityError("Artifact path escapes the store or is a symlink")
        return path

    def _put(self, collection: str, data: bytes, suffix: str = ".json") -> str:
        digest = sha256(data).hexdigest()
        path = self._path(collection, digest, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Publish a complete file atomically and exclusively. Never overwrite artifacts.
        fd, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, path)
            except FileExistsError:
                if path.read_bytes() != data:
                    raise IntegrityError(f"Existing {collection} artifact was modified") from None
        finally:
            Path(temporary).unlink(missing_ok=True)
        return digest

    def _bytes(self, collection: str, digest: str, suffix: str = ".json") -> bytes:
        try:
            data = self._path(collection, digest, suffix).read_bytes()
        except OSError as exc:
            raise IntegrityError(f"Missing or unreadable {collection} artifact") from exc
        if sha256(data).hexdigest() != digest:
            raise IntegrityError(f"Hash mismatch in {collection}")
        return data

    def _read[T: BaseModel](self, collection: str, digest: str, model: type[T]) -> T:
        data = self._bytes(collection, digest)
        parsed = model.model_validate_json(data)
        if canonical_bytes(parsed) != data:
            raise IntegrityError(f"Noncanonical {collection} artifact")
        return parsed

    def ingest(
        self,
        original: bytes,
        document: LogicalDocument,
        *,
        metadata: VersionMetadata | None = None,
        source_url: str | None = None,
        retrieved_at: datetime | None = None,
    ) -> str:
        """Return a receipt hash, including for failed extraction. No network fetch."""
        if type(original) is not bytes:
            raise TypeError("original must be exact PDF bytes")
        # Revalidate even model instances; never accept unvalidated model_copy/construct.
        document = LogicalDocument.model_validate_json(document.model_dump_json())
        metadata = VersionMetadata.model_validate_json(
            (metadata if metadata is not None else VersionMetadata()).model_dump_json()
        )
        url = TypeAdapter(HttpUrl).validate_python(source_url) if source_url is not None else None
        document_hash = artifact_id(document)
        version = DocumentVersion(
            document_id=document.id,
            document_sha256=document_hash,
            original_sha256=sha256(original).hexdigest(),
            **metadata.model_dump(),
        )
        acquisition = Acquisition(
            version_sha256=artifact_id(version), source_url=url, retrieved_at=retrieved_at
        )
        # Validate all metadata before writing; preserve raw bytes before running parser.
        self._put("originals", original, ".pdf")
        self._put("documents", canonical_bytes(document))
        version_hash = self._put("versions", canonical_bytes(version))
        acquisition_hash = self._put("acquisitions", canonical_bytes(acquisition))
        extraction = extract_pdf(original)
        extraction_hash = self._put("extractions", canonical_bytes(extraction))
        receipt = IngestionReceipt(
            version_sha256=version_hash,
            acquisition_sha256=acquisition_hash,
            extraction_sha256=extraction_hash,
        )
        return self._put("receipts", canonical_bytes(receipt))

    def load(self, receipt_id: str) -> StoredIngestion:
        """Check every hash/reference and reproduce the extraction from original bytes."""
        receipt = self._read("receipts", receipt_id, IngestionReceipt)
        version = self._read("versions", receipt.version_sha256, DocumentVersion)
        document = self._read("documents", version.document_sha256, LogicalDocument)
        acquisition = self._read("acquisitions", receipt.acquisition_sha256, Acquisition)
        extraction = self._read("extractions", receipt.extraction_sha256, ExtractionArtifact)
        original = self._bytes("originals", version.original_sha256, ".pdf")
        if document.id != version.document_id:
            raise IntegrityError("Logical document reference mismatch")
        if acquisition.version_sha256 != receipt.version_sha256:
            raise IntegrityError("Acquisition version reference mismatch")
        if extraction.original_sha256 != version.original_sha256:
            raise IntegrityError("Extraction source reference mismatch")
        if extraction.parser_version != pypdf.__version__:
            raise ParserVersionError("Install the recorded pypdf version to verify this artifact")
        if extract_pdf(original) != extraction:
            raise IntegrityError("Stored extraction cannot be reproduced from original PDF")
        return StoredIngestion(
            receipt=receipt,
            document=document,
            version=version,
            acquisition=acquisition,
            extraction=extraction,
        )

    def verify_evidence(self, receipt_id: str, evidence: PdfEvidence) -> None:
        """Verify a page span after loading from disk; never trust an imported status."""
        self._verify_evidence(self.load(receipt_id), evidence)

    @staticmethod
    def _verify_evidence(stored: StoredIngestion, evidence: PdfEvidence) -> None:
        evidence = PdfEvidence.model_validate_json(evidence.model_dump_json())
        if (
            evidence.document_id != stored.document.id
            or evidence.version_sha256 != stored.receipt.version_sha256
            or evidence.extraction_sha256 != stored.receipt.extraction_sha256
        ):
            raise IntegrityError("Evidence document/version/extraction mismatch")
        if evidence.page_number > len(stored.extraction.pages):
            raise IntegrityError("Evidence page does not exist")
        page = stored.extraction.pages[evidence.page_number - 1]
        if page.status != "text" or evidence.end_char > len(page.text):
            raise IntegrityError("Evidence requires an extractable page and in-bounds span")
        if page.text[evidence.start_char : evidence.end_char] != evidence.quote:
            raise IntegrityError("Evidence quote does not match page text")

    def verify_claim(self, receipt_id: str, claim: Claim) -> None:
        """Single-version claim check. The supplied verification flag has no authority."""
        claim = Claim.model_validate_json(claim.model_dump_json())
        stored = self.load(receipt_id)
        if claim.product_id != stored.document.product_id or not claim.evidence:
            raise IntegrityError("Claim product mismatch or missing evidence")
        for evidence in claim.evidence:
            if not isinstance(evidence, PdfEvidence):
                raise IntegrityError("Legacy text evidence cannot verify a PDF")
            self._verify_evidence(stored, evidence)
