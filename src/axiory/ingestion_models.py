"""Strict, immutable contracts for synthetic PDF ingestion (schema 1)."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Nonempty = Annotated[str, Field(min_length=1, pattern=r"\S")]
PositiveInt = Annotated[int, Field(gt=0)]
PageStatus = Literal["text", "empty", "needs_ocr", "not_extractable", "error"]
ExtractionStatus = Literal[
    "success", "partial", "empty", "needs_ocr", "not_extractable", "encrypted", "damaged"
]


class ArtifactModel(BaseModel):
    # Preserve text verbatim: whitespace and Unicode are part of evidence offsets.
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class LogicalDocument(ArtifactModel):
    schema_version: Literal["1"] = "1"
    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
    product_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
    title: Nonempty
    kind: Literal["policy_conditions", "product_information"]
    language: Literal["de", "fr", "it", "en"] | None = None
    synthetic: Literal[True]

    @field_validator("synthetic", mode="before")
    @classmethod
    def synthetic_only(cls, value: object) -> bool:
        if value is not True:
            raise ValueError("Only explicitly declared synthetic documents are supported")
        return True


class VersionMetadata(ArtifactModel):
    declared_version: Nonempty | None = None
    valid_from: date | None = None
    valid_until: date | None = None

    @model_validator(mode="after")
    def ordered_dates(self) -> Self:
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValueError("valid_until precedes valid_from")
        return self


class DocumentVersion(VersionMetadata):
    schema_version: Literal["1"] = "1"
    document_id: Nonempty
    document_sha256: Digest
    original_sha256: Digest


class Acquisition(ArtifactModel):
    schema_version: Literal["1"] = "1"
    version_sha256: Digest
    source_url: HttpUrl | None = None
    retrieved_at: AwareDatetime | None = None


class ExtractedPage(ArtifactModel):
    number: PositiveInt
    status: PageStatus
    text: str
    error_type: Nonempty | None = None

    @model_validator(mode="after")
    def consistent_page(self) -> Self:
        if (self.status == "text") != bool(self.text.strip()):
            raise ValueError("Page text and status disagree")
        if (self.status == "error") != (self.error_type is not None):
            raise ValueError("Only extraction errors carry error_type")
        return self


def page_outcome(pages: tuple[ExtractedPage, ...]) -> ExtractionStatus:
    statuses = {page.status for page in pages}
    if statuses == {"text"}:
        return "success"
    if "text" in statuses:
        return "partial"
    if "error" in statuses:
        return "not_extractable"
    if "needs_ocr" in statuses:
        return "needs_ocr"
    if not statuses or statuses == {"empty"}:
        return "empty"
    return "not_extractable"


class ExtractionArtifact(ArtifactModel):
    schema_version: Literal["1"] = "1"
    original_sha256: Digest
    parser: Literal["pypdf"] = "pypdf"
    parser_version: Nonempty
    extractor_version: Literal["1"] = "1"
    mode: Literal["plain-strict"] = "plain-strict"
    status: ExtractionStatus
    pages: tuple[ExtractedPage, ...]
    error_type: Nonempty | None = None

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if tuple(page.number for page in self.pages) != tuple(range(1, len(self.pages) + 1)):
            raise ValueError("Pages must be contiguous, ordered and one-based")
        if self.error_type is not None:
            if self.pages or self.status not in ("damaged", "not_extractable"):
                raise ValueError("Document-level parser error must be explicit")
        elif self.status == "encrypted":
            if self.pages:
                raise ValueError("Encrypted PDFs cannot have extracted pages")
        elif self.status != page_outcome(self.pages):
            raise ValueError("Extraction status disagrees with pages")
        return self


class IngestionReceipt(ArtifactModel):
    schema_version: Literal["1"] = "1"
    version_sha256: Digest
    acquisition_sha256: Digest
    extraction_sha256: Digest


class PdfEvidence(ArtifactModel):
    schema_version: Literal["pdf-1"] = "pdf-1"
    id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
    document_id: Nonempty
    version_sha256: Digest
    extraction_sha256: Digest
    page_number: PositiveInt
    start_char: Annotated[int, Field(ge=0)]
    end_char: PositiveInt
    quote: Nonempty

    @model_validator(mode="after")
    def valid_span(self) -> Self:
        if self.end_char <= self.start_char or self.end_char - self.start_char != len(self.quote):
            raise ValueError("Evidence requires a nonempty, quote-length character span")
        return self


class StoredIngestion(ArtifactModel):
    receipt: IngestionReceipt
    document: LogicalDocument
    version: DocumentVersion
    acquisition: Acquisition
    extraction: ExtractionArtifact
