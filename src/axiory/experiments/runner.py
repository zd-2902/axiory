"""Explicit offline, dry-run, live-pilot and replay entry points."""

import argparse
import json
import os
import subprocess
from pathlib import Path
from uuid import uuid4

from axiory.experiments.corpus import ROOT, load_corpus
from axiory.experiments.models import Manifest, parse_config
from axiory.experiments.pipeline import evaluate_case
from axiory.experiments.report import build_report
from axiory.experiments.runtime import OfflineProvider, Session, dry_run
from axiory.extraction.providers import OpenAIProvider
from axiory.ingestion import DocumentStore, artifact_id, canonical_bytes
from axiory.parsers.store import LayoutStore


def git_metadata():
    try:
        command = ["git", "-c", "safe.directory=" + Path.cwd().as_posix()]
        head = subprocess.check_output(
            command + ["rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        dirty = bool(
            subprocess.check_output(
                command + ["status", "--porcelain"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        )
        return head, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def offline_config(config, count):
    """Explicit simulation admission; never applied to a live provider."""
    plan = dry_run(config, count)
    data = config.model_dump(mode="json")
    data.update(
        max_calls=plan["maximum_attempts"],
        max_total_tokens=plan["reserved_token_budget"],
        max_cost_microusd=plan["maximum_estimated_microusd"],
    )
    return parse_config(json.dumps(data))


def execute(output, corpus, freeze, config, *, provider=None, pilot=True, allow_live=False):
    provider = provider or OfflineProvider()
    live = provider.name == "openai"
    if live and (allow_live is not True or not pilot):
        raise ValueError("Live requires explicit opt-in and is limited to the frozen 24-case pilot")
    trusted_corpus, trusted_freeze = load_corpus()
    if corpus != trusted_corpus or freeze != trusted_freeze:
        raise ValueError("Only the committed synthetic corpus and freeze are admitted")
    if live:
        for stage in ("extract", "verify", "critic"):
            profile = getattr(config, stage)
            if profile.model != "gpt-4.1-mini-2025-04-14" or (
                profile.input_usd_per_million != "0.40" or profile.output_usd_per_million != "1.60"
            ):
                raise ValueError(
                    "Pilot requires the reviewed snapshot and explicit price assumptions"
                )
    ids = freeze.pilot_ids if pilot else tuple(c.source.id for c in corpus.cases)
    if not dry_run(config, len(ids))["fits_budget"]:
        raise ValueError("Dry-run exceeds shared admission budgets")
    if live and config.max_cost_microusd > 2000000:
        raise ValueError("Current live pilot authorization is capped at USD 2")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    store = DocumentStore(output / "session")
    run_id = "run-" + uuid4().hex
    session = Session(store, provider, config, run_id)
    corpus_hash = store._put("experiment_gold", canonical_bytes(corpus))
    freeze_hash = store._put("experiment_freezes", canonical_bytes(freeze))
    commit, dirty = git_metadata()
    keys, runs = [], []
    for case in corpus.cases:
        if case.source.id not in ids:
            continue
        key, run = evaluate_case(
            LayoutStore(output / "cases" / case.source.id), session, case.source
        )
        keys.append(key)
        runs.append(run)
        if session.halted:
            break
    manifest = Manifest(
        run_id=run_id,
        measurement="LIVE" if live else "OFFLINE_PROTOCOL_TEST",
        git_commit=commit,
        git_dirty=dirty,
        config=config,
        corpus_sha256=corpus_hash,
        freeze_sha256=freeze_hash,
        selected_ids=ids,
        case_runs=tuple(keys),
        calls=tuple(session.calls),
        reservations=tuple(session.reservations),
        complete=len(runs) == len(ids) and not session.halted,
        stop_reason=session.halted,
    )
    store._put("experiment_manifests", canonical_bytes(manifest))
    (output / "manifest.json").write_bytes(canonical_bytes(manifest))
    report = build_report(store, manifest, corpus, runs)
    report["manifest_sha256"] = artifact_id(manifest)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--replay", type=Path)
    parser.add_argument("--all-offline", action="store_true", help="Exercise all 120; never live")
    parser.add_argument("--config", type=Path, default=ROOT / "pilot-config-v2.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.replay:
        from axiory.experiments.replay import replay

        report = replay(args.replay)
        print(
            json.dumps(
                {"replayed": str(args.replay), "quality_fingerprint": report["quality_fingerprint"]}
            )
        )
        return
    corpus, freeze = load_corpus()
    config = parse_config(args.config.read_bytes())
    if args.live and args.all_offline:
        parser.error("--all-offline cannot be combined with --live")
    if args.all_offline:
        config = offline_config(config, len(corpus.cases))
    plan = dry_run(config, len(corpus.cases) if args.all_offline else len(freeze.pilot_ids))
    print(json.dumps(plan, indent=2))
    if args.dry_run:
        return
    if not plan["fits_budget"]:
        parser.error("Dry-run exceeds shared budgets")
    provider = None
    if args.live:
        if not os.environ.get("OPENAI_API_KEY"):
            parser.error(
                "OPENAI_API_KEY is unavailable; set it through a secret environment variable"
            )
        provider = OpenAIProvider(allow_live=True)
    output = args.output or Path("datasets/evaluation-real") / ("run-" + uuid4().hex)
    manifest, report = execute(
        output,
        corpus,
        freeze,
        config,
        provider=provider,
        pilot=not args.all_offline,
        allow_live=args.live,
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "measurement": manifest.measurement,
                "complete": manifest.complete,
                "stop_reason": manifest.stop_reason,
                "quality_fingerprint": report["quality_fingerprint"],
            },
            indent=2,
        )
    )
    if not manifest.complete:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
