"""Post-pilot development regressions; not independent model-quality measurements."""

import json
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from axiory.experiments.corpus import load_corpus, prepare
from axiory.experiments.models import (
    CandidateV2,
    CaseRun,
    ExtractResponseV2,
    ReviewV2,
    parse_config,
)
from axiory.experiments.money import literal_amounts
from axiory.experiments.pipeline import decode_claim
from axiory.experiments.prompts import make_request
from axiory.experiments.replay import replay
from axiory.experiments.runner import execute
from axiory.experiments.verification import check_claim, check_review, gates
from axiory.extraction.providers import Reply
from axiory.ingestion import DocumentStore, IntegrityError, artifact_id, canonical_bytes
from axiory.parsers.store import LayoutStore

VERSION = "pilot-fixes-2"
CHECKS = ["support", "omissions", "limits", "negation", "contradictions", "unknown"]


def config(version=2):
    name = "pilot-config-v2.json" if version == 2 else "pilot-config.json"
    return parse_config((Path("datasets/multilingual") / name).read_bytes())


@pytest.mark.parametrize(
    "token",
    [
        "1875.",
        "1875,",
        "(1875)",
        "1875.00.",
        "1875,00;",
        "1'875.",
        "1’875",
        "1 875",
        "1\u00a0875",
        "1\u202f875",
        "1'875.00",
        "1875!",
    ],
)
def test_complete_money_literals(token):
    assert literal_amounts("CHF " + token) == {Decimal("1875")}


@pytest.mark.parametrize(
    "token",
    [
        "1.875",
        "1,875",
        "18'75",
        "18 75",
        "01",
        "1875.001",
        "1.875,00",
        "1875x",
        "x1875",
        "1875.9x",
        "-1875",
        "−1875",
        "+1875",
        "1/875",
        "1875-2000",
        "10.10.2026",
        "12:30",
        "1'875’000",
        "1875e3",
    ],
)
def test_never_match_partial_or_ambiguous_amounts(token):
    assert not literal_amounts("CHF " + token)


@pytest.fixture
def prepared(tmp_path):
    corpus, _ = load_corpus()
    source = next(c.source for c in corpus.cases if c.source.id == "document-it-1-00")
    store = LayoutStore(tmp_path / "source")
    context = prepare(store, source, max_chars=10000)
    quote = {
        "version_sha256": context.version_sha256,
        "extraction_sha256": context.extraction_sha256,
        "page_number": 1,
        "text": context.sections[0].text,
    }
    data = {
        "claim_id": "claim-test",
        "product_id": source.product_id,
        "coverage_code": source.coverage_code,
        "coverage_status": "covered",
        "limit_amount": "1875",
        "currency": "CHF",
        "limit_basis": "per_event",
        "conditions": [],
        "exclusions": [],
        "sublimits": [],
        "deductible": None,
        "evidence_references": [quote],
        "unknown_reason": None,
    }
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    return store.load(context.receipt_sha256), context, candidate


def wire(candidate):
    data = candidate.model_dump(mode="json")
    amount, currency, basis = (data.pop(k) for k in ("limit_amount", "currency", "limit_basis"))
    data["limit"] = {"amount": amount, "currency": currency, "basis": basis} if amount else None
    return data


def test_sentence_period_fix_and_legacy_preserved(prepared):
    stored, context, candidate = prepared
    before = artifact_id(candidate)
    assert check_claim(stored, context, candidate).issues == ("amount_not_literal",)
    fixed = check_claim(stored, context, candidate, version=VERSION)
    assert fixed.source_status == "source_matched" and not fixed.issues
    assert artifact_id(candidate) == before
    assert all(e.quote == context.sections[0].text for e in fixed.evidence)


@pytest.mark.parametrize("status", ["covered", "excluded", "unknown"])
def test_atomic_money_null_roundtrip(prepared, status):
    stored, context, candidate = prepared
    data = wire(candidate)
    data.update(
        coverage_status=status,
        limit=None,
        unknown_reason="Unresolved source" if status == "unknown" else None,
    )
    checked = decode_claim(
        Reply(text=json.dumps({"claims": [data]}), model="fixture"),
        stored,
        context,
        version=VERSION,
    )
    assert checked.candidate.limit_amount is None and checked.candidate.currency is None
    assert checked.candidate.limit_basis is None and checked.candidate.coverage_status == status


@pytest.mark.parametrize(
    "mutation",
    [
        "currency_only",
        "missing_basis",
        "unknown_money",
        "excluded_money",
        "legacy_currency",
        "zero",
    ],
)
def test_atomic_money_rejects_inconsistent_objects(prepared, mutation):
    _, _, candidate = prepared
    data = wire(candidate)
    if mutation == "currency_only":
        data["limit"] = {"currency": "CHF"}
    if mutation == "missing_basis":
        del data["limit"]["basis"]
    if mutation == "unknown_money":
        data.update(coverage_status="unknown", unknown_reason="Conflict")
    if mutation == "excluded_money":
        data["coverage_status"] = "excluded"
    if mutation == "legacy_currency":
        data["currency"] = "CHF"
    if mutation == "zero":
        data["limit"]["amount"] = "0"
    with pytest.raises(ValidationError):
        response = ExtractResponseV2.model_validate_json(json.dumps({"claims": [data]}))
        response.claims[0].candidate()


def reviewed(stored, context, candidate, decision, *, checks=None, quote=None):
    data = {
        "claim_id": candidate.claim_id,
        "decision": decision,
        "reason": "Synthetic check",
        "evidence_references": [quote]
        if quote
        else candidate.model_dump(mode="json")["evidence_references"],
        "counterevidence": [],
        "alternative_interpretation": None,
        "checks": CHECKS if checks is None else checks,
    }
    raw = ReviewV2.model_validate_json(json.dumps(data))
    return check_review(stored, context, candidate, raw, version=VERSION)


@pytest.mark.parametrize("status", ["covered", "unknown", "excluded"])
@pytest.mark.parametrize(
    "decision",
    [
        "supported",
        "supported_unknown",
        "insufficient_evidence",
        "unsupported",
        "contradicted",
        "requires_human_review",
    ],
)
def test_unknown_requires_explicit_justified_assessment(prepared, status, decision):
    stored, context, original = prepared
    data = original.model_dump(mode="json")
    data.update(
        coverage_status=status,
        limit_amount=None,
        currency=None,
        limit_basis=None,
        unknown_reason="Synthetic unknown" if status == "unknown" else None,
    )
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    claim = check_claim(stored, context, candidate, version=VERSION)
    review = reviewed(stored, context, candidate, decision)
    allowed = decision == ("supported_unknown" if status == "unknown" else "supported")
    assert gates(claim, review, review, version=VERSION) == (True, allowed, allowed)
    assert claim.candidate == candidate and claim.human_status == "not_reviewed"
    if decision == "supported_unknown":
        assert not gates(claim, review, review)[1]  # legacy gates never accept new verdict


def test_new_unknown_verdict_cannot_bypass_evidence_or_checks(prepared):
    stored, context, original = prepared
    data = original.model_dump(mode="json")
    data.update(
        coverage_status="unknown",
        limit_amount=None,
        currency=None,
        limit_basis=None,
        unknown_reason="Synthetic unknown",
    )
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    claim = check_claim(stored, context, candidate, version=VERSION)
    quote = candidate.evidence_references[0].model_dump(mode="json")
    quote["text"] = "invented source"
    for review in (
        reviewed(stored, context, candidate, "supported_unknown", checks=["support"] * 6),
        reviewed(stored, context, candidate, "supported_unknown", quote=quote),
    ):
        assert not review.source_valid
        assert not gates(claim, review, review, version=VERSION)[1]


def test_legacy_prompt_schema_contract_and_v2_pairing(prepared):
    _, context, candidate = prepared
    expected = json.loads(Path("tests/fixtures/pilot-v1-contract.json").read_text())
    for stage in ("extract", "verify", "critic"):
        old = make_request(
            context, config(1), stage, candidate=candidate, extractor_output="a" * 64
        )
        assert old.prompt_version == expected[stage]["prompt_version"]
        for field in ("system", "output_schema_json"):
            assert sha256(getattr(old, field).encode()).hexdigest() == expected[stage][field]
        new = make_request(context, config(), stage, candidate=candidate, extractor_output="a" * 64)
        assert new.prompt_version.endswith("-2") and old != new
        assert len(canonical_bytes(new)) + 512 < config().max_input_tokens
        assert "expected" not in json.loads(new.payload)
    b = make_request(context, config(), "verify", candidate=candidate, extractor_output="a" * 64)
    c = make_request(context, config(), "critic", candidate=candidate, extractor_output="a" * 64)
    assert b.payload == c.payload and b.input_hashes == c.input_hashes
    assert "supported_unknown" in b.system and "table row" in b.system


@pytest.fixture(scope="module")
def v2_run(tmp_path_factory):
    corpus, freeze = load_corpus()
    output = tmp_path_factory.mktemp("v2") / "run"
    manifest, report = execute(output, corpus, freeze, config())
    return output, manifest, report


def test_version_two_roundtrip_and_imported_gate_rejected(v2_run):
    output, manifest, report = v2_run
    assert manifest.config.schema_version == "experiment-config-2"
    assert manifest.complete and len(manifest.calls) == 72
    assert report["live_quality"] is None and replay(output) == report
    store = DocumentStore(output / "session")
    first = store._read("paired_cases", manifest.case_runs[0], CaseRun)
    data = first.model_dump(mode="json")
    data["b_released"] = True
    forged = CaseRun.model_validate_json(json.dumps(data))
    key = store._put("paired_cases", canonical_bytes(forged))
    data = manifest.model_dump(mode="json")
    data["case_runs"][0] = key
    altered = type(manifest).model_validate_json(json.dumps(data))
    store._put("experiment_manifests", canonical_bytes(altered))
    path = output / "manifest.json"
    original = path.read_bytes()
    try:
        path.write_bytes(canonical_bytes(altered))
        with pytest.raises(IntegrityError, match="release flags"):
            replay(output)
    finally:
        path.write_bytes(original)


@pytest.mark.parametrize("case_id", ["document-it-1-10", "document-it-1-15"])
def test_table_and_condition_errors_need_semantic_review(tmp_path, case_id):
    from types import SimpleNamespace

    from axiory.experiments.metrics import grade

    corpus, _ = load_corpus()
    case = next(c for c in corpus.cases if c.source.id == case_id)
    store = LayoutStore(tmp_path / "pdf")
    context = prepare(store, case.source, max_chars=10000)
    g = case.expected
    data = {
        "claim_id": "claim-test",
        "product_id": case.source.product_id,
        "coverage_code": case.source.coverage_code,
        "coverage_status": g.status,
        "limit_amount": g.amount,
        "currency": g.currency,
        "limit_basis": g.basis,
        "conditions": list(g.conditions),
        "exclusions": list(g.exclusions),
        "sublimits": [],
        "deductible": None,
        "unknown_reason": None,
        "evidence_references": [
            {
                "version_sha256": context.version_sha256,
                "extraction_sha256": context.extraction_sha256,
                "page_number": 1,
                "text": context.sections[0].text,
            }
        ],
    }
    if case.scenario == "table":
        data.update(limit_amount="9000", limit_basis="per_year")
        data["sublimits"] = [
            {"subject": "baggage", "amount": "2125", "currency": "CHF", "basis": "per_event"}
        ]
    else:
        data["conditions"].remove("emergency")
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    stored = store.load(context.receipt_sha256)
    claim = check_claim(stored, context, candidate, version=VERSION)
    assert claim.source_status == "source_matched"  # literal matching is not semantics
    supported = reviewed(stored, context, candidate, "supported")
    a, b, c = gates(claim, supported, supported, version=VERSION)
    row = grade(
        case, SimpleNamespace(claim=claim, a_released=a, b_released=b, c_released=c, errors=())
    )
    assert row["arms"]["C"]["critical_error"]  # never hide the known blind spot
    rejected = reviewed(stored, context, candidate, "unsupported")
    assert gates(claim, rejected, supported, version=VERSION) == (True, False, False)
    assert gates(claim, supported, rejected, version=VERSION) == (True, True, False)


def test_v2_supported_unknown_record_is_reloadable_and_forgery_is_detected(prepared, tmp_path):
    stored, context, original = prepared
    data = original.model_dump(mode="json")
    data.update(
        coverage_status="unknown",
        limit_amount=None,
        currency=None,
        limit_basis=None,
        unknown_reason="Synthetic unknown",
    )
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    review = reviewed(stored, context, candidate, "supported_unknown")
    from axiory.experiments.models import CheckedReview

    store = DocumentStore(tmp_path / "records")
    key = store._put("reviews", canonical_bytes(review))
    assert store._read("reviews", key, CheckedReview) == review
    data = review.model_dump(mode="json")
    data["source_valid"] = False
    store._path("reviews", key).write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(IntegrityError):
        store._read("reviews", key, CheckedReview)
