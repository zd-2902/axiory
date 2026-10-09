"""Bounded extractor + optional independent verifier; immutable runs, explicit corrections."""

import json

from pydantic import ValidationError

from axiory.extraction import prompts
from axiory.extraction.context import build_context, validate_context
from axiory.extraction.evidence import check_candidate, resolve
from axiory.extraction.providers import Budget, Caller, ProviderError, ReplayProvider, Request
from axiory.extraction.schemas import (
    Context,
    ExtractionResponse,
    PipelineResult,
    VerificationResponse,
    VerifiedVerdict,
)
from axiory.ingestion import IntegrityError, artifact_id, canonical_bytes


def request(context, model, budget, *, candidates=None):
    schema = ExtractionResponse if candidates is None else VerificationResponse
    return Request(
        model=model,
        prompt_version=prompts.EXTRACT_VERSION if candidates is None else prompts.VERIFY_VERSION,
        system=prompts.EXTRACT if candidates is None else prompts.VERIFY,
        payload=prompts.payload(context, candidates),
        output_schema_json=json.dumps(schema.model_json_schema(), sort_keys=True),
        input_hashes=(
            artifact_id(context),
            context.version_sha256,
            context.original_sha256,
            context.extraction_sha256,
        ),
        max_output_tokens=budget.max_output_tokens,
    )


def run(store, context, provider, *, model="mock-1", verify=False, budget=None, predecessor=None):
    validate_context(store, context)
    if predecessor is not None:
        old = store._read("semantic_runs", predecessor, PipelineResult)
        if old.context_sha256 != artifact_id(context):
            raise IntegrityError("Correction must retain the original context")
    context_hash = store._put("semantic_contexts", canonical_bytes(context))
    caller = Caller(store, provider, budget or Budget())
    claims, verdicts, errors = (), (), []
    stored = store.load(context.receipt_sha256)
    try:
        answer = caller.call(request(context, model, caller.budget))
        parsed = ExtractionResponse.model_validate_json(answer.text)
        if {c.coverage_code for c in parsed.claims} != set(context.coverage_codes):
            raise ValueError("coverage_set")
        claims = tuple(
            check_candidate(
                stored,
                context,
                c,
                method=provider.method,
                model=answer.model,
                prompt=prompts.EXTRACT_VERSION,
            )
            for c in parsed.claims
        )
    except ProviderError as exc:
        errors.append(exc.code)
    except IntegrityError:
        raise
    except (ValidationError, ValueError):
        errors.append("invalid_extraction_response")
    if verify and claims:
        try:
            # Same original context, a separate call and prompt; no extractor chain of thought.
            answer = caller.call(request(context, model, caller.budget, candidates=parsed.claims))
            verification = VerificationResponse.model_validate_json(answer.text)
            if len(verification.verdicts) != len(claims) or {
                v.claim_id for v in verification.verdicts
            } != {c.claim_id for c in claims}:
                raise ValueError("verdict_set")
            checked = []
            for v in verification.verdicts:
                issues = []
                if (
                    set(v.checks)
                    != {"support", "omissions", "limits", "negation", "overclaim", "unknown"}
                    or len(v.checks) != 6
                ):
                    issues.append("incomplete_verifier_checks")
                if not v.evidence_references:
                    issues.append("missing_verifier_evidence")
                for i, q in enumerate(v.evidence_references):
                    try:
                        resolve(stored, context, q, i)
                    except IntegrityError as exc:
                        issues.append(str(exc))
                checked.append(
                    VerifiedVerdict(
                        **v.model_dump(), evidence_valid=not issues, issues=tuple(issues)
                    )
                )
            verdicts = tuple(checked)
        except ProviderError as exc:
            errors.append("verifier_" + exc.code)
        except IntegrityError:
            raise
        except (ValidationError, ValueError):
            errors.append("invalid_verifier_response")
    result = PipelineResult(
        context_sha256=context_hash,
        budget=caller.budget,
        verifier_enabled=verify,
        calls=tuple(caller.calls),
        claims=claims,
        verdicts=verdicts,
        errors=tuple(errors),
        predecessor_sha256=predecessor,
    )
    key = store._put("semantic_runs", canonical_bytes(result))
    return key, result


def replay(store, result_hash, *, budget=None):
    from axiory.extraction.providers import CallRecord

    result = store._read("semantic_runs", result_hash, PipelineResult)
    context = store._read("semantic_contexts", result.context_sha256, Context)
    validate_context(store, context)
    if not result.calls:
        raise IntegrityError("No recorded provider call to replay")
    first = store._read("model_calls", result.calls[0], CallRecord)
    if first.provider == "replay":
        raise IntegrityError("Replay from the original run, not a replay record")
    method = "llm" if first.provider == "openai" else "mock"
    provider = ReplayProvider(store, result.calls, method=method)
    # Replay validates current prompt/schema/model/input against each recorded request.
    replay_key, rebuilt = run(
        store,
        context,
        provider,
        model=first.request.model,
        verify=result.verifier_enabled,
        budget=budget or result.budget,
        predecessor=result.predecessor_sha256,
    )
    if provider.used != len(result.calls):
        raise IntegrityError("Replay left unconsumed call records")
    if (rebuilt.claims, rebuilt.verdicts, rebuilt.errors) != (
        result.claims,
        result.verdicts,
        result.errors,
    ):
        raise IntegrityError("Stored semantic result disagrees with revalidated raw responses")
    return replay_key, rebuilt


def verified_context(store, receipt, codes, **kwargs):
    return build_context(store, receipt, codes, **kwargs)


def review_gate(result):
    """Experimental eligible subset; the full immutable result always retains every claim."""
    if result.errors:
        return ()
    verdicts = {v.claim_id: v for v in result.verdicts}
    return tuple(
        c
        for c in result.claims
        if c.verification_status == "source_matched"
        and c.claim_id in verdicts
        and verdicts[c.claim_id].evidence_valid
        and verdicts[c.claim_id].decision == "supported"
    )
