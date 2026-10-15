"""Experiment-wide admission journal. No retry can silently reset the shared budget."""

import json
import time
from decimal import ROUND_CEILING, Decimal
from hashlib import sha256

from axiory.experiments.models import Call, ExperimentConfig, RequestV2, Reservation, parse_config
from axiory.extraction.providers import ProviderError, Reply
from axiory.ingestion import IntegrityError, artifact_id, canonical_bytes


def cost_microusd(profile, input_tokens, output_tokens):
    # USD/million tokens equals micro-USD/token. Round upwards for reservations.
    amount = (
        Decimal(profile.input_usd_per_million) * input_tokens
        + Decimal(profile.output_usd_per_million) * output_tokens
    )
    return int(amount.to_integral_value(rounding=ROUND_CEILING))


def dry_run(config: ExperimentConfig, count: int):
    stages = (config.extract, config.verify, config.critic)
    attempts = 1 + config.max_retries
    calls = count * 3
    maximum_calls = calls * attempts
    tokens = maximum_calls * (config.max_input_tokens + config.max_output_tokens)
    maximum_cost = (
        count
        * attempts
        * sum(cost_microusd(p, config.max_input_tokens, config.max_output_tokens) for p in stages)
    )
    return {
        "planned_documents": count,
        "profiles": {
            stage: getattr(config, stage).model_dump(mode="json")
            for stage in ("extract", "verify", "critic")
        },
        "configured_cost_limit_usd": config.max_cost_microusd / 1000000,
        "distinct_extractor_calls": count,
        "planned_calls_without_retries": calls,
        "maximum_attempts": maximum_calls,
        "reserved_token_budget": tokens,
        "maximum_estimated_microusd": maximum_cost,
        "maximum_estimated_usd": maximum_cost / 1000000,
        "fits_budget": maximum_calls <= config.max_calls
        and tokens <= config.max_total_tokens
        and maximum_cost <= config.max_cost_microusd,
        "per_document_calls": {"A": 1, "B": 2, "C": 3},
        "note": "Conservative full-input price, no cache discount; not an invoice guarantee",
    }


class Session:
    def __init__(self, store, provider, config, run_id):
        self.store, self.provider = store, provider
        self.config = parse_config(config.model_dump_json())
        self.run_id = run_id
        self.started = time.monotonic()
        self.calls, self.reservations = [], []
        self.reserved_tokens = self.reserved_cost = 0
        self.halted = None
        marker = store.root / "session-start.json"
        if marker.exists():
            raise IntegrityError("Session already exists; replay it, never reset its budget")
        try:
            (store.root / "session.lock").mkdir()
        except FileExistsError:
            raise IntegrityError("Session already exists; never reset its budget") from None
        store._publish(marker, canonical_bytes(self.config))

    def call(self, case_id, stage, request):
        request = RequestV2.model_validate_json(request.model_dump_json())
        b = self.config
        profile = getattr(b, stage)
        if request.model != profile.model or request.temperature != profile.temperature:
            raise IntegrityError("Request does not match frozen provider configuration")
        bound = len(canonical_bytes(request)) + 512
        if bound > b.max_input_tokens or request.max_output_tokens > b.max_output_tokens:
            self.halted = "input_or_output_budget"
            raise ProviderError(self.halted)
        tokens = b.max_input_tokens + b.max_output_tokens
        reserved = cost_microusd(profile, b.max_input_tokens, b.max_output_tokens)
        for retry in range(b.max_retries + 1):
            remaining = b.total_seconds - (time.monotonic() - self.started)
            if self.halted:
                raise ProviderError(self.halted)
            if len(self.reservations) >= b.max_calls or remaining <= 0:
                self.halted = "call_or_time_budget"
            elif self.reserved_tokens + tokens > b.max_total_tokens:
                self.halted = "token_budget"
            elif self.reserved_cost + reserved > b.max_cost_microusd:
                self.halted = "cost_budget"
            if self.halted:
                raise ProviderError(self.halted)
            # Both request and exclusive journal entry exist BEFORE sending to the provider.
            request_hash = self.store._put("experiment_requests", canonical_bytes(request))
            reservation = Reservation(
                run_id=self.run_id,
                sequence=len(self.reservations),
                request_sha256=request_hash,
                previous_sha256=self.reservations[-1] if self.reservations else None,
                reserved_tokens=tokens,
                reserved_microusd=reserved,
            )
            reservation_hash = self.store._put(
                "experiment_reservations", canonical_bytes(reservation)
            )
            journal_key = sha256(f"{self.run_id}:{reservation.sequence}".encode()).hexdigest()
            self.store._publish(
                self.store._path("budget_journal", journal_key), canonical_bytes(reservation)
            )
            self.reservations.append(reservation_hash)
            self.reserved_tokens += tokens
            self.reserved_cost += reserved
            started = time.monotonic()
            output, reply, error, estimated, retryable = None, None, None, None, False
            try:
                reply = self.provider.send(request, min(remaining, b.timeout_seconds))
                reply = Reply.model_validate_json(reply.model_dump_json())
                output = self.store._put("model_outputs", canonical_bytes(reply))
                if len(canonical_bytes(reply)) > b.max_response_bytes:
                    error = "response_size"
                elif time.monotonic() - started > min(remaining, b.timeout_seconds):
                    error = "time_budget"
                elif self.provider.name == "openai" and reply.model != request.model:
                    error = "model_mismatch"
                elif reply.status != "completed":
                    error = reply.status
                elif (reply.input_tokens or 0) > b.max_input_tokens or (
                    reply.output_tokens or 0
                ) > b.max_output_tokens:
                    error = "reported_token_budget"
                if (
                    self.provider.name == "openai"
                    and reply.input_tokens is not None
                    and reply.output_tokens is not None
                ):
                    estimated = cost_microusd(profile, reply.input_tokens, reply.output_tokens)
                    if estimated > reserved:
                        error = "reported_cost_budget"
                if error in (
                    "time_budget",
                    "response_size",
                    "reported_token_budget",
                    "reported_cost_budget",
                    "model_mismatch",
                ):
                    self.halted = error
            except ProviderError as exc:
                error, retryable = exc.code, exc.retryable
            except IntegrityError:
                raise
            except Exception:
                error = "provider_failure"  # Never expose API exception bodies or headers.
            record = Call(
                run_id=self.run_id,
                case_id=case_id,
                stage=stage,
                provider=self.provider.name,
                request=request,
                request_sha256=artifact_id(request),
                reservation_sha256=reservation_hash,
                output_sha256=output,
                latency_seconds=time.monotonic() - started,
                retry_count=retry,
                retryable=retryable,
                error=error,
                estimated_microusd=estimated,
            )
            key = self.store._put("experiment_calls", canonical_bytes(record))
            self.calls.append(key)
            if not error:
                return reply, output
            if not retryable or retry == b.max_retries:
                if error in ("api_status", "provider_failure", "connection", "timeout"):
                    self.halted = error
                raise ProviderError(error)
        raise AssertionError("Bounded loop exhausted")


class OfflineProvider:
    """Gold-blind protocol fixture. Deliberately abstains; never a measured LLM."""

    name = "mock"
    method = "mock"

    def send(self, request, timeout):
        data = json.loads(request.payload)
        context = data["untrusted_document_context"]
        citations = [
            {
                "version_sha256": context["version_sha256"],
                "extraction_sha256": context["extraction_sha256"],
                "page_number": s["page_number"],
                "text": s["text"],
            }
            for s in context["sections"]
        ]
        if request.prompt_version in ("multilingual-extract-1", "multilingual-extract-2"):
            raw = {
                "claims": [
                    {
                        "claim_id": "claim-synthetic",
                        "product_id": context["product_id"],
                        "coverage_code": context["coverage_codes"][0],
                        "coverage_status": "unknown",
                        "limit_amount": None,
                        "currency": None,
                        "limit_basis": None,
                        "conditions": [],
                        "exclusions": [],
                        "sublimits": [],
                        "deductible": None,
                        "evidence_references": citations,
                        "unknown_reason": "Offline protocol fixture; no semantic model assessment",
                    }
                ]
            }
        else:
            raw = {
                "reviews": [
                    {
                        "claim_id": data["untrusted_candidate"]["claim_id"],
                        "decision": "requires_human_review",
                        "reason": "Offline fixture; no LLM judgment",
                        "evidence_references": citations,
                        "counterevidence": [],
                        "alternative_interpretation": None,
                        "checks": [
                            "support",
                            "omissions",
                            "limits",
                            "negation",
                            "contradictions",
                            "unknown",
                        ],
                    }
                ]
            }
        if request.prompt_version == "multilingual-extract-2":
            candidate = raw["claims"][0]
            for key in ("limit_amount", "currency", "limit_basis"):
                candidate.pop(key)
            candidate["limit"] = None
        return Reply(text=json.dumps(raw, ensure_ascii=False), model="offline-protocol-1")
