"""Schema-2 store reuses schema-1 originals, identities, versions and evidence."""

from datetime import datetime
from hashlib import sha256

from pydantic import HttpUrl, TypeAdapter

from axiory.ingestion import (
    DocumentStore,
    IntegrityError,
    ParserVersionError,
    artifact_id,
    canonical_bytes,
)
from axiory.ingestion_models import Acquisition, DocumentVersion, LogicalDocument, VersionMetadata
from axiory.parsers.adapters import adapter
from axiory.parsers.models import LayoutArtifact, LayoutReceipt, LayoutStored, ParserConfig
from axiory.pdf_extraction import check_pdf_size


class LayoutStore(DocumentStore):
    def __init__(self, root, *, config=None, experimental=False, limits=None):
        super().__init__(root, limits=limits)
        self.config = ParserConfig.model_validate_json((config or ParserConfig()).model_dump_json())
        self.experimental = experimental
        # Fail before writes if optional parser/license gate is unavailable.
        self.parser = adapter(self.config, experimental=experimental)

    def ingest(
        self,
        original: bytes,
        document: LogicalDocument,
        *,
        metadata: VersionMetadata | None = None,
        source_url: str | None = None,
        retrieved_at: datetime | None = None,
    ) -> str:
        if type(original) is not bytes:
            raise TypeError("original must be exact PDF bytes")
        check_pdf_size(len(original), self.limits)
        document = LogicalDocument.model_validate_json(document.model_dump_json())
        metadata = VersionMetadata.model_validate_json(
            (metadata or VersionMetadata()).model_dump_json()
        )
        url = TypeAdapter(HttpUrl).validate_python(source_url) if source_url is not None else None
        version = DocumentVersion(
            document_id=document.id,
            document_sha256=artifact_id(document),
            original_sha256=sha256(original).hexdigest(),
            **metadata.model_dump(),
        )
        version_hash = artifact_id(version)
        acquisition = Acquisition(
            version_sha256=version_hash, source_url=url, retrieved_at=retrieved_at
        )
        self._check_identity(document, register=True)
        self._put("originals", original, ".pdf")
        self._put("documents", canonical_bytes(document))
        self._put("versions", canonical_bytes(version))
        acquisition_hash = self._put("acquisitions", canonical_bytes(acquisition))
        extraction = self.parser.extract(original, version_hash, self.limits)
        extraction = LayoutArtifact.model_validate_json(extraction.model_dump_json())
        if (
            extraction.original_sha256 != version.original_sha256
            or extraction.version_sha256 != version_hash
            or extraction.config != self.config
            or extraction.parser_version != self.parser.version
        ):
            raise IntegrityError("Adapter returned inconsistent source/configuration")
        extraction_hash = self._put("layout_extractions", canonical_bytes(extraction))
        receipt = LayoutReceipt(
            version_sha256=version_hash,
            acquisition_sha256=acquisition_hash,
            extraction_sha256=extraction_hash,
        )
        return self._put("layout_receipts", canonical_bytes(receipt))

    def load(self, receipt_id: str) -> LayoutStored:
        receipt = self._read("layout_receipts", receipt_id, LayoutReceipt)
        version = self._read("versions", receipt.version_sha256, DocumentVersion)
        document = self._read("documents", version.document_sha256, LogicalDocument)
        acquisition = self._read("acquisitions", receipt.acquisition_sha256, Acquisition)
        extraction = self._read("layout_extractions", receipt.extraction_sha256, LayoutArtifact)
        original = self._bytes("originals", version.original_sha256, ".pdf")
        if (
            document.id != version.document_id
            or acquisition.version_sha256 != receipt.version_sha256
            or extraction.original_sha256 != version.original_sha256
            or extraction.version_sha256 != receipt.version_sha256
        ):
            raise IntegrityError("Document/version/source reference mismatch")
        if extraction.config != self.config:
            raise ParserVersionError("Load with the exact recorded parser configuration")
        if extraction.parser_version != self.parser.version:
            raise ParserVersionError("Install the recorded parser version")
        self._check_identity(document)
        if self.parser.extract(original, receipt.version_sha256, self.limits) != extraction:
            raise IntegrityError("Stored layout extraction cannot be reproduced")
        return LayoutStored(
            receipt=receipt,
            document=document,
            version=version,
            acquisition=acquisition,
            extraction=extraction,
        )
