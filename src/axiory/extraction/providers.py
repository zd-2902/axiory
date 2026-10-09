"""One optional official provider, deterministic mock, and recorded-response replay."""

import time
from typing import Annotated, Literal, Protocol
from uuid import uuid4

from pydantic import Field

from axiory.ingestion import DocumentStore, IntegrityError, artifact_id, canonical_bytes
from axiory.ingestion_models import ArtifactModel, Digest, Nonempty


class Budget(ArtifactModel):
    max_input_tokens: Annotated[int, Field(gt=0)] = 40000
    max_output_tokens: Annotated[int, Field(ge=16)] = 4000
    max_total_tokens: Annotated[int, Field(gt=0)] = 176000
    max_calls: Annotated[int, Field(gt=0, le=20)] = 4
    max_retries: Annotated[int, Field(ge=0, le=3)] = 1
    timeout_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 30.0
    total_seconds: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 120.0
    max_cost_usd: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 1.0
    input_usd_per_million: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    output_usd_per_million: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None = None
    max_response_bytes: Annotated[int, Field(gt=0)] = 1048576


class Request(ArtifactModel):
    model: Nonempty
    prompt_version: Nonempty
    system: Nonempty
    payload: Nonempty
    output_schema_json: Nonempty
    input_hashes: tuple[Digest, ...]
    max_output_tokens: Annotated[int, Field(ge=16)]


class Reply(ArtifactModel):
    text: str
    model: Nonempty
    status: Literal["completed", "refused", "incomplete"] = "completed"
    input_tokens: Annotated[int, Field(ge=0)] | None = None
    output_tokens: Annotated[int, Field(ge=0)] | None = None
    envelope: str | None = None


class CallRecord(ArtifactModel):
    schema_version: Literal["llm-call-1"] = "llm-call-1"
    run_id: Nonempty
    provider: Literal["mock", "openai", "replay"]
    request: Request
    request_sha256: Digest
    output_sha256: Digest | None
    latency_seconds: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    retry_count: Annotated[int, Field(ge=0)]
    error: str | None
    estimated_cost_usd: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    reserved_cost_usd: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    input_token_upper_bound: Annotated[int, Field(gt=0)]


class ProviderError(Exception):
    def __init__(self, code: str, *, retryable=False):
        self.code = code
        self.retryable = retryable
        super().__init__(code)


class Provider(Protocol):
    name: str
    method: str

    def send(self, request: Request, timeout: float) -> Reply: ...


class MockProvider:
    name = "mock"
    method = "mock"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def send(self, request: Request, timeout: float) -> Reply:
        self.calls += 1
        response = next(self.responses)
        if isinstance(response, Exception):
            raise response
        return (
            response if isinstance(response, Reply) else Reply(text=response, model=request.model)
        )


class OpenAIProvider:
    name = "openai"
    method = "llm"

    def __init__(self, *, allow_live: bool = False, client=None):
        if allow_live is not True:
            raise ValueError("Live calls require explicit allow_live=True")
        if client is None:
            from openai import OpenAI

            # SDK reads OPENAI_API_KEY; no key is accepted in configuration or logs.
            client = OpenAI(max_retries=0)
        self.client = client

    def send(self, request: Request, timeout: float) -> Reply:
        import json

        from openai import APIConnectionError, APIStatusError, APITimeoutError

        try:
            response = self.client.with_options(timeout=timeout, max_retries=0).responses.create(
                model=request.model,
                store=False,
                max_output_tokens=request.max_output_tokens,
                input=[
                    {"role": "system", "content": request.system},
                    {"role": "user", "content": request.payload},
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "axiory_response",
                        "strict": True,
                        "schema": json.loads(request.output_schema_json),
                    }
                },
            )
        except APITimeoutError:
            raise ProviderError("timeout", retryable=True) from None
        except APIConnectionError:
            raise ProviderError("connection", retryable=True) from None
        except APIStatusError as exc:
            raise ProviderError(
                "api_status", retryable=exc.status_code == 429 or exc.status_code >= 500
            ) from None
        refusal = any(
            getattr(c, "type", None) == "refusal"
            for o in response.output
            for c in getattr(o, "content", [])
        )
        usage = response.usage
        return Reply(
            text=response.output_text,
            model=response.model,
            status="refused"
            if refusal
            else "completed"
            if response.status == "completed"
            else "incomplete",
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
            envelope=response.model_dump_json(),
        )


class ReplayProvider:
    name = "replay"

    def __init__(self, store: DocumentStore, calls: tuple[str, ...], *, method: str):
        self.store = store
        self.records = iter(calls)
        self.method = method

    def send(self, request: Request, timeout: float) -> Reply:
        record = self.store._read("model_calls", next(self.records), CallRecord)
        if record.request_sha256 != artifact_id(record.request) or record.request != request:
            raise IntegrityError("Replay request/model/prompt/input mismatch")
        if record.error is not None or record.output_sha256 is None:
            raise ProviderError(
                record.error or "recorded_error",
                retryable=record.error in ("timeout", "connection", "api_status"),
            )
        return self.store._read("model_outputs", record.output_sha256, Reply)


class Caller:
    """Per-run admission budgets. Timeouts are transport controls, not worker isolation."""

    def __init__(self, store: DocumentStore, provider: Provider, budget: Budget):
        self.store, self.provider = store, provider
        self.budget = Budget.model_validate_json(budget.model_dump_json())
        if provider.name == "openai" and (
            budget.input_usd_per_million is None or budget.output_usd_per_million is None
        ):
            raise ValueError("Live calls require explicit current pricing")
        self.started = time.monotonic()
        self.run_id = str(uuid4())
        self.calls = []
        self.reserved_tokens = 0
        self.reserved_cost = 0.0

    def call(self, request: Request) -> Reply:
        request = Request.model_validate_json(request.model_dump_json())
        b = self.budget
        if request.max_output_tokens > b.max_output_tokens:
            raise ProviderError("output_budget")
        # UTF-8 byte count plus framing reserve: conservative admission, not a tokenizer.
        upper = len(canonical_bytes(request)) + 512
        tokens = upper + request.max_output_tokens
        cost = (
            upper * (b.input_usd_per_million or 0)
            + request.max_output_tokens * (b.output_usd_per_million or 0)
        ) / 1000000
        if self.provider.name != "openai":
            cost = 0.0
        for retry in range(b.max_retries + 1):
            remaining = b.total_seconds - (time.monotonic() - self.started)
            if upper > b.max_input_tokens or self.reserved_tokens + tokens > b.max_total_tokens:
                raise ProviderError("token_budget")
            if len(self.calls) >= b.max_calls or remaining <= 0:
                raise ProviderError("call_or_time_budget")
            if self.reserved_cost + cost > b.max_cost_usd:
                raise ProviderError("cost_budget")
            self.reserved_tokens += tokens
            self.reserved_cost += cost  # Never release reservations after ambiguous timeouts.
            started = time.monotonic()
            reply = None
            error = None
            retryable = False
            output = None
            estimate = None
            try:
                reply = self.provider.send(request, min(remaining, b.timeout_seconds))
                reply = Reply.model_validate_json(reply.model_dump_json())
                # Retain raw replies, including malformed JSON/refusals, BEFORE parsing claims.
                output = self.store._put("model_outputs", canonical_bytes(reply))
                if len(canonical_bytes(reply)) > b.max_response_bytes:
                    error = "response_size"
                elif time.monotonic() - started > min(remaining, b.timeout_seconds):
                    error = "time_budget"
                elif reply.status != "completed":
                    error = reply.status
                elif (reply.input_tokens or 0) > min(upper, b.max_input_tokens) or (
                    reply.output_tokens or 0
                ) > request.max_output_tokens:
                    error = "reported_token_budget"
                if (
                    self.provider.name == "openai"
                    and reply.input_tokens is not None
                    and reply.output_tokens is not None
                ):
                    estimate = (
                        reply.input_tokens * b.input_usd_per_million
                        + reply.output_tokens * b.output_usd_per_million
                    ) / 1000000
                    self.reserved_cost += max(0.0, estimate - cost)
                    if self.reserved_cost > b.max_cost_usd:
                        error = "reported_cost_budget"
                actual_tokens = (reply.input_tokens or 0) + (reply.output_tokens or 0)
                self.reserved_tokens += max(0, actual_tokens - tokens)
            except ProviderError as exc:
                error, retryable = exc.code, exc.retryable
            except IntegrityError:
                raise
            except Exception:
                error = "provider_failure"  # Never log exception bodies, keys or HTTP headers.
            record = CallRecord(
                run_id=self.run_id,
                provider=self.provider.name,
                request=request,
                request_sha256=artifact_id(request),
                output_sha256=output,
                latency_seconds=time.monotonic() - started,
                retry_count=retry,
                error=error,
                estimated_cost_usd=estimate,
                reserved_cost_usd=cost,
                input_token_upper_bound=upper,
            )
            self.calls.append(self.store._put("model_calls", canonical_bytes(record)))
            if not error:
                return reply
            if not retryable or retry == b.max_retries:
                raise ProviderError(error)
        raise AssertionError("bounded retry loop exhausted")
