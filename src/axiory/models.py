"""Validated domain contracts. A claim is an assertion, not an insurance loss."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]*$")]
Status = Literal["covered", "excluded", "unknown"]
CoverageCode = Literal["travel.cancellation", "travel.medical", "travel.baggage"]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class Insurer(DomainModel):
    id: Identifier
    name: Text
    country: Literal["CH"] = "CH"
    synthetic: bool = Field(default=True, strict=True)


class InsuranceProduct(DomainModel):
    id: Identifier
    insurer_id: Identifier
    name: Text
    line_of_business: Literal["travel"] = "travel"
    market: Literal["CH"] = "CH"


class Document(DomainModel):
    id: Identifier
    product_id: Identifier
    title: Text
    source_uri: Text
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    language: Literal["de", "fr", "it", "en"] = "de"
    kind: Literal["policy_conditions", "product_information"]
    version: Text
    synthetic: bool = Field(default=True, strict=True)


class Coverage(DomainModel):
    code: CoverageCode
    ontology_version: Literal["0.1.0"] = "0.1.0"
    status: Status
    limit_amount: Annotated[Decimal, Field(gt=0, allow_inf_nan=False)] | None = None
    currency: Literal["CHF"] | None = None
    limit_basis: Literal["per_person_per_trip", "per_event", "per_year"] | None = None
    conditions: tuple[Text, ...] = ()

    @model_validator(mode="after")
    def consistent_limit(self) -> Self:
        fields = (self.limit_amount, self.currency, self.limit_basis)
        if any(value is not None for value in fields) and not all(
            value is not None for value in fields
        ):
            raise ValueError("A limit requires amount, currency and basis together")
        if self.status != "covered" and any(value is not None for value in fields):
            raise ValueError("Only covered benefits may carry a limit")
        if self.status == "unknown" and self.conditions:
            raise ValueError("Unknown coverage cannot assert conditions")
        return self


class Evidence(DomainModel):
    id: Identifier
    document_id: Identifier
    quote: Text
    start_char: Annotated[int, Field(ge=0, strict=True)]
    end_char: Annotated[int, Field(gt=0, strict=True)]
    locator: Text

    @model_validator(mode="after")
    def valid_span(self) -> Self:
        if self.end_char <= self.start_char:
            raise ValueError("Evidence span must be nonempty")
        if self.end_char - self.start_char != len(self.quote):
            raise ValueError("Evidence span must match quote length")
        return self


class Claim(DomainModel):
    id: Identifier
    product_id: Identifier
    coverage: Coverage
    evidence: tuple[Evidence, ...] = ()
    method: Literal["synthetic_fixture", "human", "llm"]
    method_version: Text
    verification: Literal["unverified", "source_matched", "human_reviewed"] = "unverified"
    unknown_reason: Text | None = None

    @model_validator(mode="after")
    def provenance_required(self) -> Self:
        if self.coverage.status == "unknown":
            if self.unknown_reason is None:
                raise ValueError("Unknown coverage requires an explicit reason")
        elif not self.evidence:
            raise ValueError("An assertion about coverage requires evidence")
        elif self.unknown_reason is not None:
            raise ValueError("Only unknown coverage may have an unknown reason")
        if self.verification != "unverified" and not self.evidence:
            raise ValueError("Verified claims require evidence")
        return self
