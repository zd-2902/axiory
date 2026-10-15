"""Observable totals and paired metrics, explicitly separated from live model quality."""

import hashlib
import json

from axiory.experiments.metrics import grade, ratio, statistics, stratify
from axiory.experiments.models import Call
from axiory.experiments.runtime import cost_microusd
from axiory.extraction.providers import Reply


def observability(store, manifest, runs):
    records = [store._read("experiment_calls", key, Call) for key in manifest.calls]
    replies = {
        c.output_sha256: store._read("model_outputs", c.output_sha256, Reply)
        for c in records
        if c.output_sha256
    }
    result = {}
    for arm, stages in (
        ("A", ("extract",)),
        ("B", ("extract", "verify")),
        ("C", ("extract", "verify", "critic")),
    ):
        calls = [c for c in records if c.stage in stages]
        measured = [c for c in calls if c.estimated_microusd is not None]
        usages = [
            replies[c.output_sha256]
            for c in calls
            if c.output_sha256
            and replies[c.output_sha256].input_tokens is not None
            and replies[c.output_sha256].output_tokens is not None
        ]
        latency = sum(c.latency_seconds for c in calls)
        cost = sum(c.estimated_microusd for c in measured)
        extra = [c for c in calls if c.stage != "extract"]
        result[arm] = {
            "actual_calls": len(calls),
            "additional_verification_latency_seconds": sum(c.latency_seconds for c in extra),
            "retry_attempts": sum(c.retry_count > 0 for c in calls),
            "errors": sum(c.error is not None for c in calls),
            "latency_seconds_per_attempted_document": ratio(latency, len(runs), len(runs)),
            "recorded_call_latency_seconds": latency,
            "input_tokens_known": sum(r.input_tokens for r in usages) if usages else None,
            "output_tokens_known": sum(r.output_tokens for r in usages) if usages else None,
            "usage_coverage": ratio(len(usages), len(calls), len(runs)),
            "estimated_microusd_known": cost if measured else None,
            "estimated_total_microusd": cost if calls and len(measured) == len(calls) else None,
            "additional_verification_microusd": sum(c.estimated_microusd for c in extra)
            if extra and all(c.estimated_microusd is not None for c in extra)
            else None,
            "cost_coverage": ratio(len(measured), len(calls), len(runs)),
            "human_review_seconds": None,
        }
    return {
        "arms": result,
        "unique_calls": len(records),
        "reserved_cost_microusd": sum(
            cost_microusd(
                getattr(manifest.config, c.stage),
                manifest.config.max_input_tokens,
                manifest.config.max_output_tokens,
            )
            for c in records
        ),
        "reserved_token_upper_bound": len(manifest.reservations)
        * (manifest.config.max_input_tokens + manifest.config.max_output_tokens),
        "note": "Arms share A calls; do not sum arm totals. Unknown timeout usage is not zero. "
        "API-only elapsed times exclude PDF preparation. Offline latencies are not LLM latency.",
    }


def build_report(store, manifest, corpus, runs):
    by_id = {r.case_id: r for r in runs}
    rows = [
        grade(c, by_id.get(c.source.id))
        for c in corpus.cases
        if c.source.id in manifest.selected_ids
    ]
    quality = {
        "rows": rows,
        "metrics": stratify(rows),
        "statistics": statistics(rows, manifest.config),
    }
    fingerprint = hashlib.sha256(
        json.dumps(quality, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "schema_version": "paired-report-1",
        "run_id": manifest.run_id,
        "measurement": manifest.measurement,
        "complete": manifest.complete,
        "stop_reason": manifest.stop_reason,
        "selected_cases": len(rows),
        "attempted_cases": len(runs),
        "quality_fingerprint": fingerprint,
        "live_quality": quality if manifest.measurement == "LIVE" else None,
        "fixture_metrics": quality if manifest.measurement != "LIVE" else None,
        "observability": observability(store, manifest, runs),
        "independent_human_gold_reviews": 0,
        "interpretation": "No empirical comparison without LIVE observations. Separate model "
        "calls are not statistically independent; gold is single-author synthetic.",
    }
