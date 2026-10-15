"""Synthetic development regressions; these are not an independent quality sample."""

import itertools
import json
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from axiory.experiments.corpus import load_corpus, prepare
from axiory.experiments.models import (
    CandidateV2,
    CaseRun,
    Reflection,
    ReviewV2,
    Source,
    parse_config,
)
from axiory.experiments.pipeline import decode_claim
from axiory.experiments.prompts import make_request
from axiory.experiments.replay import replay
from axiory.experiments.resilience import CHECKS, build_plan
from axiory.experiments.runner import execute, offline_config
from axiory.experiments.runtime import OfflineProvider, dry_run
from axiory.experiments.verification import check_claim, check_review, gates
from axiory.extraction.providers import Reply
from axiory.ingestion import DocumentStore, IntegrityError, artifact_id, canonical_bytes
from axiory.parsers.store import LayoutStore

VERSION = "evidence-plan-3"


def cfg():
    return parse_config(Path("datasets/multilingual/pilot-config-v3.json").read_bytes())


def prepared(tmp_path, pages, code="baggage", language="it"):
    source = Source(
        id="document-resilience",
        product_id="product-resilience",
        language=language,
        coverage_code=code,
        pages=pages,
        synthetic=True,
    )
    store = LayoutStore(tmp_path / "source")
    context = prepare(store, source, max_chars=10000)
    quotes = [
        {
            "version_sha256": context.version_sha256,
            "extraction_sha256": context.extraction_sha256,
            "page_number": s.page_number,
            "text": s.text,
        }
        for s in context.sections
    ]
    data = dict(
        claim_id="claim-resilience",
        product_id=source.product_id,
        coverage_code=code,
        coverage_status="covered",
        limit_amount=None,
        currency=None,
        limit_basis=None,
        conditions=[],
        exclusions=[],
        sublimits=[],
        deductible=None,
        evidence_references=quotes,
        unknown_reason=None,
    )
    return store.load(context.receipt_sha256), context, data


def reflection(context, *, outcome="pass"):
    return Reflection.model_validate_json(
        json.dumps(
            {
                "plan_sha256": artifact_id(build_plan(context)),
                "items": [
                    {
                        "check": check,
                        "outcome": outcome,
                        "evidence_indices": [0],
                        "summary": "Scripted synthetic audit; no model measurement",
                    }
                    for check in CHECKS
                ],
            }
        )
    )


def checked(stored, context, data, audit=None):
    return check_claim(
        stored,
        context,
        CandidateV2.model_validate_json(json.dumps(data)),
        version=VERSION,
        reflection=audit or reflection(context),
    )


def review(stored, context, candidate, audit=None, decision="supported"):
    raw = ReviewV2(
        claim_id=candidate.claim_id,
        decision=decision,
        reason="Synthetic review",
        evidence_references=candidate.evidence_references,
        counterevidence=(),
        alternative_interpretation=None,
        checks=("support", "omissions", "limits", "negation", "contradictions", "unknown"),
    )
    return check_review(
        stored, context, candidate, raw, version=VERSION, reflection=audit or reflection(context)
    )


@pytest.mark.parametrize("order", list(itertools.permutations(range(3))))
@pytest.mark.parametrize("target_first", [True, False])
@pytest.mark.parametrize(
    "language,header,label,basis,other",
    [
        ("de", ("Leistung", "CHF-Limite", "Bezugsgrösse"), "Gepäck", "pro Ereignis", "pro Jahr"),
        ("fr", ("Prestation", "Limite CHF", "Base"), "Bagages", "par événement", "par année"),
        (
            "it",
            ("Voce", "Massimo CHF", "Periodo di riferimento"),
            "Bagaglio",
            "singolo sinistro",
            "anno assicurativo",
        ),
    ],
)
def test_row_binding_survives_column_and_row_permutations(
    tmp_path, order, target_first, language, header, label, basis, other
):
    target = (label, "3'275.50", basis)
    accessory = ("Accessory", "8640", other)
    rows = [target, accessory] if target_first else [accessory, target]
    lines = tuple(" | ".join(row[i] for i in order) for row in [header, *rows])
    stored, context, data = prepared(tmp_path, (lines,), language=language)
    plan = build_plan(context)
    assert plan.table_suspected and len(plan.table_rows) == 2 and not plan.issues
    assert build_plan(type(context).model_validate_json(context.model_dump_json())) == plan
    assert all(
        context.sections[0].start_char
        <= row.cells.start_char
        < row.cells.end_char
        <= context.sections[0].end_char
        for row in plan.table_rows
    )
    data.update(limit_amount="3275.50", currency="CHF", limit_basis="per_event")
    correct = checked(stored, context, data)
    assert not correct.issues
    approved = review(stored, context, correct.candidate)
    assert gates(correct, approved, approved, version=VERSION) == (True, True, True)
    data.update(limit_amount="8640", limit_basis="per_year")
    wrong = checked(stored, context, data)
    assert "table_limit_binding_mismatch" in wrong.issues
    approved = review(stored, context, wrong.candidate)
    assert gates(wrong, approved, approved, version=VERSION) == (False, False, False)


@pytest.mark.parametrize("case_id", ["document-it-1-10", "document-fr-1-14"])
def test_both_observed_escaping_failures_block_even_with_unanimous_approval(tmp_path, case_id):
    source = next(c.source for c in load_corpus()[0].cases if c.source.id == case_id)
    stored, context, data = prepared(tmp_path, source.pages, source.coverage_code, source.language)
    if source.language == "it":
        data.update(
            limit_amount="9000",
            currency="CHF",
            limit_basis="per_year",
            sublimits=[dict(subject="baggage", amount="2125", currency="CHF", basis="per_event")],
        )
        expected = "table_limit_binding_mismatch"
    else:
        data["evidence_references"][0]["text"] = (
            "Le contrat accorde explicitement cette garantie sans montant maximal indiqué ici."
        )
        expected = "incomplete_evidence_context"
    legacy = check_claim(
        stored, context, CandidateV2.model_validate_json(json.dumps(data)), version="pilot-fixes-2"
    )
    assert legacy.source_status == "source_matched"
    wrong = checked(stored, context, data)
    assert expected in wrong.issues
    supported = review(stored, context, wrong.candidate)
    assert gates(wrong, supported, supported, version=VERSION) == (False, False, False)
    # Actual correction is still possible; withholding everything is not the solution.
    if source.language == "it":
        data.update(limit_amount="2125", limit_basis="per_event", sublimits=[])
    else:
        data["evidence_references"][0]["text"] = context.sections[0].text
    assert checked(stored, context, data).source_status == "source_matched"


@pytest.mark.parametrize(
    "body",
    [
        ("Bagaglio", "2070", "per evento"),  # missing headers
        ("Voce", "Massimo CHF", "Periodo di riferimento", "Bagaglio", "2070"),
        ("Voce", "Massimo CHF", "Periodo di riferimento", "Bagaglio", "2070", "not a basis"),
        (
            "Voce",
            "Massimo CHF",
            "Periodo di riferimento",
            "Bagaglio",
            "2070",
            "per evento",
            "footnote",
        ),
        ("Voce", "Massimo CHF", "Periodo di riferimento", "Bagaglio", "2070", "per evento") * 2,
    ],
)
def test_unrecognized_or_ambiguous_table_never_falls_back_to_literal_matching(tmp_path, body):
    stored, context, data = prepared(tmp_path, (body,))
    data.update(limit_amount="2070", currency="CHF", limit_basis="per_event")
    assert build_plan(context).table_suspected
    assert "unsupported_table_layout" in checked(stored, context, data).issues


@pytest.mark.parametrize(
    "mutation", ["duplicate", "unknown_label", "null_limit", "deductible", "sublimit"]
)
def test_unsupported_row_semantics_withheld(tmp_path, mutation):
    rows = ["Voce | Massimo CHF | Base", "Bagaglio | 2070 | per evento"]
    if mutation == "duplicate":
        rows.append("Bagaglio | 2070 | per evento")
    if mutation == "unknown_label":
        rows[1] = "Unrecognized benefit | 2070 | per evento"
    stored, context, data = prepared(tmp_path, (tuple(rows),))
    if mutation != "null_limit":
        data.update(limit_amount="2070", currency="CHF", limit_basis="per_event")
    if mutation == "deductible":
        data["deductible"] = dict(amount="2070", currency="CHF", basis="per_event")
    if mutation == "sublimit":
        data["sublimits"] = [
            dict(subject="baggage", amount="2070", currency="CHF", basis="per_event")
        ]
    assert checked(stored, context, data).source_status == "review_required"


def test_context_coverage_uses_page_spans_and_includes_restricting_pages(tmp_path):
    stored, context, data = prepared(
        tmp_path, (("Bagaglio è assicurato.",), ("Solo previa autorizzazione.",))
    )
    data["conditions"] = ["prior_approval"]
    assert not checked(stored, context, data).issues
    data["evidence_references"] = data["evidence_references"][:1] * 2
    assert "incomplete_evidence_context" in checked(stored, context, data).issues


def test_disjoint_complete_quotes_allowed_but_missing_antecedent_is_not(tmp_path):
    stored, context, data = prepared(
        tmp_path,
        (("Bagages fait partie du contrat.", "Cette garantie est assurée."),),
        language="fr",
    )
    quote = data["evidence_references"][0]
    data["evidence_references"] = [
        dict(quote, text=s)
        for s in ("Bagages fait partie du contrat.", "Cette garantie est assurée.")
    ]
    assert not checked(stored, context, data).issues
    data["evidence_references"].pop(0)
    assert "incomplete_evidence_context" in checked(stored, context, data).issues


@pytest.mark.parametrize(
    "mutation",
    ["plan", "duplicate", "references", "no_reference", "not_applicable", "uncertain", "fail"],
)
def test_reflection_cannot_be_imported_as_approval(tmp_path, mutation):
    stored, context, data = prepared(tmp_path, (("Bagaglio è assicurato.",),))
    audit = reflection(context).model_dump(mode="json")
    if mutation == "plan":
        audit["plan_sha256"] = "0" * 64
    elif mutation == "duplicate":
        audit["items"][1] = audit["items"][0]
    elif mutation == "references":
        audit["items"][0]["evidence_indices"] = [100]
    elif mutation == "no_reference":
        audit["items"][0]["evidence_indices"] = []
    else:
        audit["items"][0]["outcome"] = mutation
    bad = Reflection.model_validate_json(json.dumps(audit))
    claim = checked(stored, context, data, bad)
    assert claim.source_status == "review_required"
    assert not review(stored, context, claim.candidate, bad).source_valid


def test_missing_reflection_and_inconsistent_review_fail_closed(tmp_path):
    stored, context, data = prepared(tmp_path, (("Bagaglio è assicurato.",),))
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    assert "missing_reflection" in check_claim(stored, context, candidate, version=VERSION).issues
    assert (
        "reflection_decision_conflict"
        in review(stored, context, candidate, decision="contradicted").issues
    )
    assert (
        "reflection_decision_conflict"
        in review(stored, context, candidate, reflection(context, outcome="uncertain")).issues
    )
    req = make_request(context, cfg(), "extract")
    raw = json.loads(OfflineProvider().send(req, 1).text)
    del raw["reflection"]
    with pytest.raises(ValidationError):
        decode_claim(Reply(text=json.dumps(raw), model="fixture"), stored, context, version=VERSION)


def test_unknown_remains_unknown_and_supports_explicit_review(tmp_path):
    stored, context, data = prepared(
        tmp_path, (("Für Gepäck ist keine verlässliche Aussage möglich.",),), language="de"
    )
    data.update(coverage_status="unknown", unknown_reason="Source does not resolve coverage")
    claim = checked(stored, context, data)
    accepted = review(stored, context, claim.candidate, decision="supported_unknown")
    assert gates(claim, accepted, accepted, version=VERSION) == (True, True, True)
    assert claim.candidate.coverage_status == "unknown"


def test_prompt_plan_binding_and_frozen_v2_contract(tmp_path):
    _, context, data = prepared(tmp_path, (("Bagaglio è assicurato.",),))
    candidate = CandidateV2.model_validate_json(json.dumps(data))
    contract = json.loads(Path("tests/fixtures/pilot-v2-contract.json").read_text())
    v2 = parse_config(Path("datasets/multilingual/pilot-config-v2.json").read_bytes())
    for stage in ("extract", "verify", "critic"):
        old = make_request(context, v2, stage, candidate=candidate, extractor_output="a" * 64)
        for field in ("system", "output_schema_json"):
            assert sha256(getattr(old, field).encode()).hexdigest() == contract[stage][field]
        new = make_request(context, cfg(), stage, candidate=candidate, extractor_output="a" * 64)
        assert new.prompt_version.endswith("-3")
        payload = json.loads(new.payload)
        assert payload["plan_sha256"] == artifact_id(build_plan(context)) == new.input_hashes[-1]
        assert "expected" not in payload and "PLAN:" in new.system and "REFLECT:" in new.system
        assert len(canonical_bytes(new)) + 512 <= cfg().max_input_tokens
    assert not dry_run(cfg(), 24)[
        "fits_budget"
    ]  # Never silently reset the user's remaining budget.


@pytest.fixture(scope="module")
def run_v3(tmp_path_factory):
    corpus, freeze = load_corpus()
    output = tmp_path_factory.mktemp("resilience") / "run"
    manifest, report = execute(output, corpus, freeze, offline_config(cfg(), 24))
    return output, manifest, report


def test_offline_pipeline_replay_and_forged_approval(run_v3):
    output, manifest, report = run_v3
    assert manifest.complete and len(manifest.calls) == 72
    assert report["live_quality"] is None and replay(output) == report
    store = DocumentStore(output / "session")
    first = store._read("paired_cases", manifest.case_runs[0], CaseRun)
    assert not first.a_released and "reflection_identity_unresolved" in first.claim.issues
    data = first.model_dump(mode="json")
    data["a_released"] = True
    key = store._put("paired_cases", canonical_bytes(CaseRun.model_validate_json(json.dumps(data))))
    data = manifest.model_dump(mode="json")
    data["case_runs"][0] = key
    altered = type(manifest).model_validate_json(json.dumps(data))
    store._put("experiment_manifests", canonical_bytes(altered))
    original = (output / "manifest.json").read_bytes()
    try:
        (output / "manifest.json").write_bytes(canonical_bytes(altered))
        with pytest.raises(IntegrityError, match="release flags"):
            replay(output)
    finally:
        (output / "manifest.json").write_bytes(original)
