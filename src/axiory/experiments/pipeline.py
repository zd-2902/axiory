"""One extractor answer, then two bounded, separately prompted review calls."""

import time

from pydantic import ValidationError

from axiory.experiments.corpus import prepare
from axiory.experiments.models import (
    Call,
    CaseRun,
    ExtractResponse,
    ExtractResponseV2,
    ReviewResponse,
    ReviewResponseV2,
    protocol,
)
from axiory.experiments.prompts import make_request
from axiory.experiments.verification import check_claim, check_review, gates
from axiory.extraction.providers import ProviderError
from axiory.ingestion import IntegrityError, canonical_bytes


def decode_claim(reply, stored, context, *, version="pilot-1"):
    schema = ExtractResponseV2 if version == "pilot-fixes-2" else ExtractResponse
    response = schema.model_validate_json(reply.text)
    if len(response.claims) != 1:
        raise ValueError("Exactly one requested claim")
    candidate = response.claims[0]
    if version == "pilot-fixes-2":
        candidate = candidate.candidate()
    return check_claim(stored, context, candidate, version=version)


def decode_review(reply, stored, context, claim, *, version="pilot-1"):
    schema = ReviewResponseV2 if version == "pilot-fixes-2" else ReviewResponse
    response = schema.model_validate_json(reply.text)
    if len(response.reviews) != 1:
        raise ValueError("Exactly one review required")
    return check_review(stored, context, claim.candidate, response.reviews[0], version=version)


def evaluate_case(case_store, session, source, *, predecessor=None):
    version = protocol(session.config)
    context = prepare(case_store, source, max_chars=session.config.max_context_chars)
    stored = case_store.load(context.receipt_sha256)
    context_hash = session.store._put("experiment_contexts", canonical_bytes(context))
    if predecessor:
        previous = session.store._read("paired_cases", predecessor, CaseRun)
        if previous.case_id != source.id or previous.context_sha256 != context_hash:
            raise IntegrityError("Correction must retain its document context")
    claim, verifier, critic, output = None, None, None, None
    errors, latencies, stages = [], [], []
    for stage in ("extract", "verify", "critic"):
        started, offset = time.monotonic(), len(session.calls)
        if stage != "extract" and claim is None:
            latencies.append(0.0)
            stages.append(())
            continue
        try:
            req = make_request(
                context,
                session.config,
                stage,
                candidate=claim.candidate if claim else None,
                extractor_output=output,
            )
            reply, response_hash = session.call(source.id, stage, req)
            if stage == "extract":
                output = response_hash
                claim = decode_claim(reply, stored, context, version=version)
            elif stage == "verify":
                verifier = decode_review(reply, stored, context, claim, version=version)
            else:
                critic = decode_review(reply, stored, context, claim, version=version)
        except ProviderError as exc:
            errors.append(stage + ":" + exc.code)
        except IntegrityError:
            raise
        except (ValidationError, ValueError):
            errors.append(stage + ":invalid_response")
        calls = tuple(session.calls[offset:])
        if stage == "extract" and calls:
            output = session.store._read("experiment_calls", calls[-1], Call).output_sha256
        stages.append(calls)
        latencies.append(time.monotonic() - started)
    a, b, c = gates(claim, verifier, critic, version=version)
    result = CaseRun(
        case_id=source.id,
        context_sha256=context_hash,
        extractor_output_sha256=output,
        extract_calls=stages[0],
        verify_calls=stages[1],
        critic_calls=stages[2],
        claim=claim,
        verifier=verifier,
        critic=critic,
        a_released=a,
        b_released=b,
        c_released=c,
        errors=tuple(errors),
        stage_latency_seconds=tuple(latencies),
        predecessor_sha256=predecessor,
    )
    return session.store._put("paired_cases", canonical_bytes(result)), result
