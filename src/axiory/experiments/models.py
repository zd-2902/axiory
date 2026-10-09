"""Additive Sprint-6 contracts. Legacy schema and hashes remain unchanged."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from axiory.extraction.providers import Request
from axiory.extraction.schemas import Amount, Basis, Candidate, Code, Quote, Sublimit
from axiory.ingestion_models import ArtifactModel, Digest, Nonempty, PdfEvidence

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
Language = Literal["de", "fr", "it"]
Stage = Literal["extract", "verify", "critic"]
Condition = Literal[
    "prior_approval", "police_report", "emergency", "medical_certificate", "immediate_notification"
]
Exclusion = Literal["non_emergency", "unattended_items", "intentional_events"]
Decision = Literal[
    "supported", "unsupported", "contradicted", "insufficient_evidence", "requires_human_review"
]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Deductible(ArtifactModel):
    amount: Amount
    currency: Literal["CHF"]
    basis: Basis


class CandidateV2(Candidate):
    conditions: tuple[Condition, ...]
    exclusions: tuple[Exclusion, ...]
    deductible: Deductible | None

    @model_validator(mode="after")
    def details(self) -> Self:
        if self.coverage_status != "covered" and self.deductible is not None:
            raise ValueError("Only covered claims may carry a deductible")
        if len(set(self.conditions)) != len(self.conditions) or len(set(self.exclusions)) != len(
            self.exclusions
        ):
            raise ValueError("Repeated semantic atoms")
        return self


class ExtractResponse(ArtifactModel):
    claims: Annotated[tuple[CandidateV2, ...], Field(min_length=1, max_length=5)]


class Review(ArtifactModel):
    claim_id: Identifier
    decision: Decision
    reason: Nonempty
    evidence_references: tuple[Quote, ...]
    counterevidence: tuple[Quote, ...]
    alternative_interpretation: str | None
    checks: tuple[
        Literal["support", "omissions", "limits", "negation", "contradictions", "unknown"], ...
    ]


class ReviewResponse(ArtifactModel):
    reviews: tuple[Review, ...]


class Source(ArtifactModel):
    id: Identifier
    product_id: Identifier
    language: Language
    coverage_code: Code
    pages: Annotated[tuple[tuple[Nonempty, ...], ...], Field(min_length=1)]
    synthetic: Literal[True]


class Expected(ArtifactModel):
    status: Literal["covered", "excluded", "unknown"]
    amount: Amount | None
    currency: Literal["CHF"] | None
    basis: Basis | None
    conditions: tuple[Condition, ...]
    exclusions: tuple[Exclusion, ...]
    sublimits: tuple[Sublimit, ...]
    deductible: Deductible | None
    anchors: tuple[Nonempty, ...]
    rationale: Nonempty

    @model_validator(mode="after")
    def consistent(self) -> Self:
        triple = self.amount, self.currency, self.basis
        if any(x is not None for x in triple) != all(x is not None for x in triple):
            raise ValueError("Incomplete gold limit")
        if self.amount is not None and Decimal(self.amount) <= 0:
            raise ValueError("Gold limit must be positive")
        if self.status != "covered" and (self.amount or self.sublimits or self.deductible):
            raise ValueError("Non-covered gold cannot assert monetary coverage")
        return self


class Case(ArtifactModel):
    source: Source
    family: Identifier
    template: Identifier
    split: Literal["dev", "holdout"]
    scenario: Literal[
        "clear",
        "exclusion",
        "negation",
        "exception",
        "conditional",
        "sublimit",
        "deductible",
        "basis",
        "ambiguity",
        "contradiction",
        "table",
        "cross_page",
    ]
    difficulty: Literal["simple", "moderate", "hard"]
    expected: Expected


class Corpus(ArtifactModel):
    schema_version: Literal["multilingual-gold-1"] = "multilingual-gold-1"
    annotation_status: Literal["single_author_synthetic_not_independently_reviewed"]
    cases: tuple[Case, ...]


class Freeze(ArtifactModel):
    schema_version: Literal["gold-freeze-1"] = "gold-freeze-1"
    corpus_sha256: Digest
    file_sha256: Digest
    case_count: int
    pilot_ids: tuple[Identifier, ...]
    frozen_before_live: Literal[True]
    independent_review_count: Literal[0]


class Profile(ArtifactModel):
    model: Nonempty
    temperature: Annotated[float, Field(ge=0, le=2, allow_inf_nan=False)] | None
    input_usd_per_million: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]{1,6})?$")]
    output_usd_per_million: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]{1,6})?$")]
    pricing_source: Literal["https://developers.openai.com/api/docs/models/gpt-4.1-mini"]
    pricing_checked_on: Literal["2026-10-09"]


class ExperimentConfig(ArtifactModel):
    schema_version: Literal["experiment-config-1"] = "experiment-config-1"
    extract: Profile
    verify: Profile
    critic: Profile
    max_cost_microusd: Annotated[int, Field(gt=0)] = 2000000
    max_calls: Annotated[int, Field(gt=0, le=10000)] = 144
    max_input_tokens: Annotated[int, Field(gt=0)] = 20000
    max_output_tokens: Annotated[int, Field(ge=16)] = 2000
    max_total_tokens: Annotated[int, Field(gt=0)] = 3168000
    max_retries: Annotated[int, Field(ge=0, le=3)] = 1
    timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 45.0
    total_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1800.0
    max_response_bytes: Annotated[int, Field(gt=0)] = 1048576
    max_context_chars: Annotated[int, Field(gt=0)] = 10000
    bootstrap_replicates: Annotated[int, Field(ge=100, le=10000)] = 1000
    seed: int = 1729


class RequestV2(Request):
    schema_version: Literal["llm-request-2"] = "llm-request-2"
    temperature: Annotated[float, Field(ge=0, le=2, allow_inf_nan=False)] | None
    service_tier: Literal["default"] = "default"


class Reservation(ArtifactModel):
    run_id: Identifier
    sequence: Annotated[int, Field(ge=0)]
    request_sha256: Digest
    previous_sha256: Digest | None
    reserved_tokens: Annotated[int, Field(gt=0)]
    reserved_microusd: Annotated[int, Field(ge=0)]


class Call(ArtifactModel):
    schema_version: Literal["experiment-call-1"] = "experiment-call-1"
    run_id: Identifier
    case_id: Identifier
    stage: Stage
    provider: Literal["mock", "openai"]
    request: RequestV2
    request_sha256: Digest
    reservation_sha256: Digest
    output_sha256: Digest | None
    latency_seconds: Nonnegative
    retry_count: Annotated[int, Field(ge=0)]
    retryable: bool
    error: str | None
    estimated_microusd: Annotated[int, Field(ge=0)] | None


class CheckedClaim(ArtifactModel):
    schema_version: Literal["semantic-2"] = "semantic-2"
    ontology_version: Literal["travel-2"] = "travel-2"
    candidate: CandidateV2
    evidence: tuple[PdfEvidence, ...]
    source_status: Literal["source_matched", "review_required"]
    issues: tuple[str, ...]
    human_status: Literal["not_reviewed"] = "not_reviewed"


class CheckedReview(ArtifactModel):
    review: Review
    source_valid: bool
    issues: tuple[str, ...]
    human_status: Literal["not_reviewed"] = "not_reviewed"


class CaseRun(ArtifactModel):
    schema_version: Literal["paired-case-1"] = "paired-case-1"
    case_id: Identifier
    context_sha256: Digest
    extractor_output_sha256: Digest | None
    extract_calls: tuple[Digest, ...]
    verify_calls: tuple[Digest, ...]
    critic_calls: tuple[Digest, ...]
    claim: CheckedClaim | None
    verifier: CheckedReview | None
    critic: CheckedReview | None
    a_released: bool
    b_released: bool
    c_released: bool
    errors: tuple[str, ...]
    stage_latency_seconds: tuple[Nonnegative, Nonnegative, Nonnegative]
    predecessor_sha256: Digest | None = None


class Manifest(ArtifactModel):
    schema_version: Literal["paired-run-1"] = "paired-run-1"
    run_id: Identifier
    measurement: Literal["LIVE", "OFFLINE_PROTOCOL_TEST"]
    git_commit: Digest | Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")] | None
    git_dirty: bool | None
    config: ExperimentConfig
    corpus_sha256: Digest
    freeze_sha256: Digest
    selected_ids: tuple[Identifier, ...]
    case_runs: tuple[Digest, ...]
    calls: tuple[Digest, ...]
    reservations: tuple[Digest, ...]
    complete: bool
    stop_reason: str | None
