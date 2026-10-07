import pytest
from pydantic import ValidationError

from axiory.models import Claim, Coverage, Evidence


def test_unknown_is_not_excluded():
    claim = Claim(
        id="unknown",
        product_id="product",
        coverage=Coverage(code="travel.medical", status="unknown"),
        method="synthetic_fixture",
        method_version="1",
        unknown_reason="Not stated",
    )
    assert claim.coverage.status == "unknown"
    assert claim.coverage.limit_amount is None
    assert claim.verification == "unverified"
    assert Claim.model_validate_json(claim.model_dump_json()) == claim


@pytest.mark.parametrize("status", ["covered", "excluded", "unknown"])
def test_claim_cannot_silently_omit_provenance_or_unknown_reason(status):
    with pytest.raises(ValidationError):
        Claim(
            id="claim",
            product_id="product",
            coverage=Coverage(code="travel.medical", status=status),
            method="llm",
            method_version="test",
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"limit_amount": "0", "currency": "CHF", "limit_basis": "per_event"},
        {"limit_amount": "-1", "currency": "CHF", "limit_basis": "per_event"},
        {"limit_amount": "NaN", "currency": "CHF", "limit_basis": "per_event"},
        {"limit_amount": "100"},
        {"currency": "CHF"},
        {
            "status": "excluded",
            "limit_amount": "100",
            "currency": "CHF",
            "limit_basis": "per_event",
        },
        {"status": "unknown", "conditions": ["unsupported"]},
        {"code": "invented.code"},
        {"unexpected": True},
    ],
)
def test_invalid_coverage_rejected(changes):
    with pytest.raises(ValidationError):
        Coverage.model_validate({"code": "travel.medical", "status": "covered", **changes})


@pytest.mark.parametrize(
    "start,end,quote",
    [
        (-1, 2, "abc"),
        (2, 1, "a"),
        (0, 3, "ab"),
        (True, 2, "a"),
        ("0", 1, "a"),
    ],
)
def test_invalid_evidence_offsets(start, end, quote):
    with pytest.raises(ValidationError):
        Evidence(
            id="evidence",
            document_id="doc",
            quote=quote,
            start_char=start,
            end_char=end,
            locator="line:1",
        )
