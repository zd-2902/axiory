"""Official SDK exercised through an in-memory HTTP transport, never the live API."""

import json

import pytest

from axiory.evaluation.semantic import context_for, load_gold
from axiory.extraction.baseline import rules
from axiory.extraction.pipeline import run
from axiory.extraction.providers import Budget, CallRecord, OpenAIProvider, Reply
from axiory.parsers.store import LayoutStore


def test_official_sdk_request_and_response(tmp_path):
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    store = LayoutStore(tmp_path)
    context = context_for(store, load_gold().cases[0])
    raw = rules(context).model_dump_json()
    requests = []

    def handler(request):
        data = json.loads(request.content)
        requests.append(data)
        assert data["store"] is False
        assert data["text"]["format"]["strict"] is True
        assert "tools" not in data
        assert [x["role"] for x in data["input"]] == ["system", "user"]
        return httpx.Response(
            200,
            json={
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": "fixture-model-snapshot",
                "output": [
                    {
                        "type": "message",
                        "id": "msg_synthetic",
                        "role": "assistant",
                        "status": "completed",
                        "content": [{"type": "output_text", "text": raw, "annotations": []}],
                    }
                ],
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150,
                    "input_tokens_details": {"cached_tokens": 0},
                    "output_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    client = openai.OpenAI(
        api_key="synthetic-test-not-a-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    provider = OpenAIProvider(allow_live=True, client=client)
    _, result = run(
        store,
        context,
        provider,
        model="fixture-model",
        budget=Budget(input_usd_per_million=1.0, output_usd_per_million=2.0),
    )
    assert not result.errors and len(requests) == 1
    assert result.claims[0].model_version == "fixture-model-snapshot"
    record = store._read("model_calls", result.calls[0], CallRecord)
    assert record.estimated_cost_usd == pytest.approx(0.0002)
    reply = store._read("model_outputs", record.output_sha256, Reply)
    assert reply.input_tokens == 100 and reply.output_tokens == 50
    assert reply.envelope and reply.text == raw
    assert "synthetic-test-not-a-secret" not in record.model_dump_json()


@pytest.mark.parametrize("status,attempts", [(429, 2), (500, 2), (400, 1)])
def test_sdk_retries_owned_by_caller(tmp_path, status, attempts):
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    store = LayoutStore(tmp_path)
    context = context_for(store, load_gold().cases[0])
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={"error": {"message": "synthetic error"}})

    client = openai.OpenAI(
        api_key="synthetic-test-not-a-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    _, result = run(
        store,
        context,
        OpenAIProvider(allow_live=True, client=client),
        budget=Budget(input_usd_per_million=1.0, output_usd_per_million=2.0),
    )
    assert len(calls) == attempts
    assert result.errors == ("api_status",)


def test_official_sdk_timeout_is_bounded_and_redacted(tmp_path):
    httpx = pytest.importorskip("httpx")
    openai = pytest.importorskip("openai")
    store = LayoutStore(tmp_path)
    context = context_for(store, load_gold().cases[0])
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("SECRET ERROR DETAILS", request=request)

    client = openai.OpenAI(
        api_key="synthetic-test-not-a-secret",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    _, result = run(
        store,
        context,
        OpenAIProvider(allow_live=True, client=client),
        budget=Budget(input_usd_per_million=1.0, output_usd_per_million=2.0),
    )
    assert len(calls) == 2 and result.errors == ("timeout",)
    for key in result.calls:
        record = store._read("model_calls", key, CallRecord)
        assert "SECRET ERROR DETAILS" not in record.model_dump_json()
        assert record.output_sha256 is None
