"""Offline reconstruction from raw replies and verified PDF bytes; imported flags are checked."""

import json
from hashlib import sha256
from pathlib import Path

from pydantic import ValidationError

from axiory.experiments.corpus import load_corpus, render
from axiory.experiments.models import (
    Call,
    CaseRun,
    Corpus,
    Freeze,
    Manifest,
    RequestV2,
    Reservation,
)
from axiory.experiments.pipeline import decode_claim, decode_review
from axiory.experiments.prompts import make_request
from axiory.experiments.report import build_report
from axiory.experiments.runtime import cost_microusd
from axiory.experiments.verification import gates
from axiory.extraction.context import validate_context
from axiory.extraction.providers import Reply
from axiory.extraction.schemas import Context
from axiory.ingestion import DocumentStore, IntegrityError, artifact_id, canonical_bytes
from axiory.parsers.store import LayoutStore


def require(condition, message):
    if not condition:
        raise IntegrityError(message)


def replay(output):
    output = Path(output)
    manifest = Manifest.model_validate_json((output / "manifest.json").read_bytes())
    store = DocumentStore(output / "session")
    require(
        store._read("experiment_manifests", artifact_id(manifest), Manifest) == manifest,
        "Manifest content address mismatch",
    )
    corpus = store._read("experiment_gold", manifest.corpus_sha256, Corpus)
    freeze = store._read("experiment_freezes", manifest.freeze_sha256, Freeze)
    # Repository freeze is a versioned trust anchor, not an imported verification flag.
    trusted_corpus, trusted_freeze = load_corpus()
    require(corpus == trusted_corpus and freeze == trusted_freeze, "Unknown gold freeze")
    ids = tuple(c.source.id for c in corpus.cases)
    require(manifest.selected_ids in (ids, freeze.pilot_ids), "Unrecognized cohort")
    require(
        manifest.measurement != "LIVE" or manifest.selected_ids == freeze.pilot_ids,
        "Live cohort is not the authorized pilot",
    )
    require(
        (store.root / "session-start.json").read_bytes() == canonical_bytes(manifest.config),
        "Session configuration differs from manifest",
    )
    require(
        len(list((store.root / "budget_journal").glob("*.json"))) == len(manifest.reservations),
        "Unaccounted reservation; interrupted sessions cannot be resumed",
    )
    calls = [store._read("experiment_calls", key, Call) for key in manifest.calls]
    reservations = [
        store._read("experiment_reservations", key, Reservation) for key in manifest.reservations
    ]
    require(len(set(manifest.calls)) == len(calls) == len(reservations), "Call/journal mismatch")
    total_tokens = total_cost = 0
    for i, (call, reservation) in enumerate(zip(calls, reservations, strict=True)):
        require(call.run_id == reservation.run_id == manifest.run_id, "Wrong run identity")
        require(
            call.provider == ("openai" if manifest.measurement == "LIVE" else "mock"),
            "Measurement/provider mismatch",
        )
        require(
            reservation.sequence == i
            and reservation.previous_sha256 == (manifest.reservations[i - 1] if i else None),
            "Broken reservation chain",
        )
        require(call.reservation_sha256 == manifest.reservations[i], "Wrong call reservation")
        require(
            call.request_sha256 == reservation.request_sha256 == artifact_id(call.request),
            "Wrong request identity",
        )
        require(
            store._read("experiment_requests", call.request_sha256, RequestV2) == call.request,
            "Request content mismatch",
        )
        journal = sha256(f"{manifest.run_id}:{i}".encode()).hexdigest()
        require(
            store._path("budget_journal", journal).read_bytes() == canonical_bytes(reservation),
            "Journal changed",
        )
        profile = getattr(manifest.config, call.stage)
        reserved = cost_microusd(
            profile, manifest.config.max_input_tokens, manifest.config.max_output_tokens
        )
        require(
            reservation.reserved_microusd == reserved
            and reservation.reserved_tokens
            == manifest.config.max_input_tokens + manifest.config.max_output_tokens,
            "Reservation does not match budget",
        )
        total_tokens += reservation.reserved_tokens
        total_cost += reserved
        estimate = None
        if call.output_sha256:
            reply = store._read("model_outputs", call.output_sha256, Reply)
            if (
                call.provider == "openai"
                and reply.input_tokens is not None
                and reply.output_tokens is not None
            ):
                estimate = cost_microusd(profile, reply.input_tokens, reply.output_tokens)
            if call.error is None:
                require(reply.status == "completed", "Unsuccessful output marked successful")
                require(
                    call.provider != "openai" or reply.model == call.request.model,
                    "Successful reply uses another model",
                )
                require(
                    len(canonical_bytes(reply)) <= manifest.config.max_response_bytes
                    and (reply.input_tokens or 0) <= manifest.config.max_input_tokens
                    and (reply.output_tokens or 0) <= manifest.config.max_output_tokens,
                    "Successful output exceeds limits",
                )
        else:
            require(call.error is not None, "Successful call has no raw reply")
        require(estimate == call.estimated_microusd, "Imported cost estimate mismatch")
    require(
        len(calls) <= manifest.config.max_calls
        and total_tokens <= manifest.config.max_total_tokens
        and total_cost <= manifest.config.max_cost_microusd,
        "Shared budget exceeded",
    )
    by_id = {c.source.id: c for c in corpus.cases}
    runs, flattened = [], []
    expected_ids = [key for key in ids if key in manifest.selected_ids]
    for position, key in enumerate(manifest.case_runs):
        run = store._read("paired_cases", key, CaseRun)
        require(
            position < len(expected_ids) and run.case_id == expected_ids[position],
            "Case sequence/identity mismatch",
        )
        context = store._read("experiment_contexts", run.context_sha256, Context)
        case = by_id[run.case_id]
        require(
            sha256(render(case.source)).hexdigest() == context.original_sha256,
            "Source does not match frozen synthetic document",
        )
        require(
            context.document_id == case.source.id
            and context.product_id == case.source.product_id
            and context.coverage_codes == (case.source.coverage_code,)
            and context.max_chars == manifest.config.max_context_chars,
            "Context identity mismatch",
        )
        case_store = LayoutStore(output / "cases" / run.case_id)
        validate_context(case_store, context)
        stored = case_store.load(context.receipt_sha256)
        claim, verifier, critic, extractor_output = None, None, None, None
        errors = []
        for stage, keys in zip(
            ("extract", "verify", "critic"),
            (run.extract_calls, run.verify_calls, run.critic_calls),
            strict=True,
        ):
            if stage != "extract" and claim is None:
                require(not keys, "Review without validated extractor answer")
                continue
            if not keys:
                require(manifest.stop_reason is not None, "Stage silently omitted")
                errors.append(stage + ":" + manifest.stop_reason)
                continue
            require(len(keys) <= manifest.config.max_retries + 1, "Too many retries")
            request = make_request(
                context,
                manifest.config,
                stage,
                candidate=claim.candidate if claim else None,
                extractor_output=extractor_output,
            )
            require(
                len(canonical_bytes(request)) + 512 <= manifest.config.max_input_tokens,
                "Input exceeds admission bound",
            )
            for retry, call_key in enumerate(keys):
                call = store._read("experiment_calls", call_key, Call)
                require(
                    call.case_id == run.case_id
                    and call.stage == stage
                    and call.request == request
                    and call.retry_count == retry,
                    "Paired request/prompt/response mismatch",
                )
                if retry < len(keys) - 1:
                    require(call.error is not None and call.retryable, "Invalid retry sequence")
            flattened.extend(keys)
            if stage == "extract":
                extractor_output = call.output_sha256
            if call.error:
                error = call.error
                # A retry may be denied before it creates another Call. Transport errors
                # and elapsed-time observations are recorded facts, not model outputs.
                if (
                    call.retryable
                    and len(keys) <= manifest.config.max_retries
                    and manifest.stop_reason
                    in ("cost_budget", "token_budget", "call_or_time_budget")
                ):
                    error = manifest.stop_reason
                errors.append(stage + ":" + error)
                continue
            reply = store._read("model_outputs", call.output_sha256, Reply)
            try:
                if stage == "extract":
                    claim = decode_claim(reply, stored, context)
                elif stage == "verify":
                    verifier = decode_review(reply, stored, context, claim)
                else:
                    critic = decode_review(reply, stored, context, claim)
            except (ValidationError, ValueError):
                errors.append(stage + ":invalid_response")
        require(
            (claim, verifier, critic) == (run.claim, run.verifier, run.critic),
            "Imported claim or verification status differs from raw replay",
        )
        require(
            gates(claim, verifier, critic) == (run.a_released, run.b_released, run.c_released),
            "Imported release flags differ from replay",
        )
        require(
            extractor_output == run.extractor_output_sha256 and tuple(errors) == run.errors,
            "Raw response or error classification differs",
        )
        if run.predecessor_sha256:
            prior = store._read("paired_cases", run.predecessor_sha256, CaseRun)
            require(
                prior.case_id == run.case_id and prior.context_sha256 == run.context_sha256,
                "Invalid correction lineage",
            )
        runs.append(run)
    require(tuple(flattened) == manifest.calls, "Unused or reordered calls")
    require(
        manifest.complete == (len(runs) == len(expected_ids) and manifest.stop_reason is None),
        "Completion status mismatch",
    )
    report = build_report(store, manifest, corpus, runs)
    report["manifest_sha256"] = artifact_id(manifest)
    saved = json.loads((output / "report.json").read_text(encoding="utf-8"))
    require(saved == report, "Report differs from independently recomputed replay")
    return report
