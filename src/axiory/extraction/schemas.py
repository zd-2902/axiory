"""Untrusted model DTOs and immutable application records; no legacy schema changes."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from axiory.extraction.providers import Budget
from axiory.ingestion_models import ArtifactModel, Digest, Nonempty, PdfEvidence
from axiory.parsers.models import ParserConfig

Code = Literal[
    "cancellation", "interruption", "baggage", "medical_assistance", "rental_car_deductible"
]
Status = Literal["covered", "excluded", "unknown"]
Basis = Literal["per_person_per_trip", "per_event", "per_year", "per_item"]
Amount = Annotated[str, Field(pattern=r"^(0|[1-9][0-9]{0,11})(\.[0-9]{1,2})?$")]


class Quote(ArtifactModel):
    version_sha256: Digest
    extraction_sha256: Digest
    page_number: Annotated[int, Field(gt=0)]
    text: Nonempty


class Sublimit(ArtifactModel):
    subject: Nonempty
    amount: Amount
    currency: Literal["CHF"]
    basis: Basis


class Candidate(ArtifactModel):
    claim_id: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
    product_id: Nonempty
    coverage_code: Code
    coverage_status: Status
    limit_amount: Amount | None
    currency: Literal["CHF"] | None
    limit_basis: Basis | None
    conditions: tuple[Nonempty, ...]
    exclusions: tuple[Nonempty, ...]
    sublimits: tuple[Sublimit, ...]
    evidence_references: tuple[Quote, ...]
    unknown_reason: Nonempty | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        fields = (self.limit_amount, self.currency, self.limit_basis)
        if any(x is not None for x in fields) != all(x is not None for x in fields):
            raise ValueError("A limit requires amount, currency and basis together")
        if self.limit_amount is not None and Decimal(self.limit_amount) <= 0:
            raise ValueError("Zero is not a coverage limit")
        if any(Decimal(x.amount) <= 0 for x in self.sublimits):
            raise ValueError("Sublimits must be positive")
        if self.coverage_status != "covered" and (self.limit_amount or self.sublimits):
            raise ValueError("Only covered claims may carry limits")
        if (self.coverage_status == "unknown") != (self.unknown_reason is not None):
            raise ValueError("Unknown requires an explicit reason, never an exclusion")
        if self.coverage_status != "unknown" and not self.evidence_references:
            raise ValueError("Positive and negative claims require evidence")
        return self


class ExtractionResponse(ArtifactModel):
    claims: Annotated[tuple[Candidate, ...], Field(min_length=1, max_length=100)]

    @model_validator(mode="after")
    def unique(self) -> Self:
        if len({x.claim_id for x in self.claims}) != len(self.claims):
            raise ValueError("Duplicate claim IDs")
        if len({x.coverage_code for x in self.claims}) != len(self.claims):
            raise ValueError("One consolidated claim per requested coverage")
        return self


class Section(ArtifactModel):
    page_number: Annotated[int, Field(gt=0)]
    start_char: Annotated[int, Field(ge=0)]
    end_char: Annotated[int, Field(gt=0)]
    text: Nonempty

    @model_validator(mode="after")
    def span(self) -> Self:
        if self.end_char - self.start_char != len(self.text):
            raise ValueError("Context span mismatch")
        return self


class Context(ArtifactModel):
    schema_version: Literal["context-1"] = "context-1"
    ontology_version: Literal["travel-1"] = "travel-1"
    receipt_sha256: Digest
    document_id: Nonempty
    product_id: Nonempty
    version_sha256: Digest
    original_sha256: Digest
    extraction_sha256: Digest
    parser_config: ParserConfig
    parser_version: Nonempty
    coverage_codes: tuple[Code, ...]
    sections: tuple[Section, ...]
    max_chars: Annotated[int, Field(gt=0)]
    truncated: bool
    omitted_chars: Annotated[int, Field(ge=0)]
    incomplete_source: bool
    synthetic: Literal[True] = True


class ClaimRecord(Candidate):
    schema_version: Literal["semantic-1"] = "semantic-1"
    ontology_version: Literal["travel-1"] = "travel-1"
    extraction_method: Literal["llm", "mock", "rules"]
    model_version: Nonempty
    prompt_version: Nonempty
    verification_status: Literal["source_matched", "review_required"]
    semantic_status: Literal["not_professionally_verified"] = "not_professionally_verified"
    resolved_evidence: tuple[PdfEvidence, ...]
    issues: tuple[str, ...]


class Verdict(ArtifactModel):
    claim_id: Nonempty
    decision: Literal["supported", "contradicted", "insufficient"]
    reason: Nonempty
    checks: tuple[
        Literal["support", "omissions", "limits", "negation", "overclaim", "unknown"], ...
    ]
    evidence_references: tuple[Quote, ...]


class VerificationResponse(ArtifactModel):
    verdicts: tuple[Verdict, ...]


class VerifiedVerdict(Verdict):
    evidence_valid: bool
    issues: tuple[str, ...]
    experimental: Literal[True] = True


class PipelineResult(ArtifactModel):
    schema_version: Literal["semantic-run-1"] = "semantic-run-1"
    context_sha256: Digest
    budget: Budget
    verifier_enabled: bool
    calls: tuple[Digest, ...]
    claims: tuple[ClaimRecord, ...]
    verdicts: tuple[VerifiedVerdict, ...]
    errors: tuple[str, ...]
    predecessor_sha256: Digest | None = None
