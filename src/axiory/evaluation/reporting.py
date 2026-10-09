"""JSON/Markdown export, stable quality fingerprints and compatible-run comparison."""

import json
from hashlib import sha256
from pathlib import Path

from axiory.evaluation.metrics import aggregate
from axiory.evaluation.schemas import CaseResult

REPORT_SCHEMA = "1"


def digest(value) -> str:
    return sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def stable_payload(report: dict) -> dict:
    """Remove observations that necessarily vary with time/machine/checkout metadata."""
    result = json.loads(json.dumps(report))
    result.pop("metadata", None)
    result.pop("quality_sha256", None)
    result.pop("comparison", None)
    for case in result["cases"]:
        case.pop("runtimes_ms", None)
        case["metrics"].pop("runtime_per_document_ms", None)
    for group in [result["aggregate"], *result["by_layout"].values()]:
        group.pop("runtime_per_document_ms", None)
    return result


def build_report(cases, metadata: dict, cohort: dict) -> dict:
    report = {
        "report_schema_version": REPORT_SCHEMA,
        "metadata": metadata,
        "comparison_key": digest(cohort),
        "cohort": cohort,
        "cases": [case.model_dump(mode="json") for case in cases],
        "aggregate": aggregate(cases),
        "by_layout": {
            layout: aggregate([case for case in cases if case.layout_type == layout])
            for layout in sorted({case.layout_type for case in cases})
        },
    }
    report["quality_sha256"] = digest(stable_payload(report))
    return report


def compare_reports(previous: dict, current: dict) -> dict:
    if not isinstance(previous, dict):
        raise ValueError("Invalid previous report: expected an object")
    if previous.get("report_schema_version") != REPORT_SCHEMA:
        return {"comparable": False, "reason": "Different report schema", "deltas": {}}
    try:
        cases = [CaseResult.model_validate_json(json.dumps(case)) for case in previous["cases"]]
        if not cases or len({case.fixture_id for case in cases}) != len(cases):
            raise ValueError("Missing or duplicate cases")
        if previous["comparison_key"] != digest(previous["cohort"]):
            raise ValueError("Invalid cohort fingerprint")
        if previous["quality_sha256"] != digest(stable_payload(previous)):
            raise ValueError("Invalid quality fingerprint")
        if previous["aggregate"] != aggregate(cases):
            raise ValueError("Aggregate disagrees with cases")
        expected_layouts = {
            layout: aggregate([case for case in cases if case.layout_type == layout])
            for layout in {case.layout_type for case in cases}
        }
        if previous["by_layout"] != expected_layouts:
            raise ValueError("Layout aggregates disagree with cases")
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid previous report: {exc}") from exc
    if previous.get("comparison_key") != current["comparison_key"]:
        return {
            "comparable": False,
            "reason": "Corpus/metric definitions/configuration differ",
            "deltas": {},
        }
    deltas = {}
    for name, current_summary in current["aggregate"].items():
        if name == "runtime_per_document_ms":
            continue  # Performance needs a controlled machine, not an arbitrary saved report.
        before = previous["aggregate"].get(name, {}).get("metric", {})
        after = current_summary["metric"]
        if before.get("status") == after["status"] == "measured":
            deltas[name] = after["value"] - before["value"]
    return {
        "comparable": True,
        "reason": "Same cohort; deltas are current minus previous",
        "deltas": deltas,
    }


def markdown(report: dict) -> str:
    meta = report["metadata"]
    lines = [
        "# Axiory: synthetischer Layout-Benchmark",
        "",
        "**Kein Benchmark realer AVB und keine semantische Versicherungsbewertung.**",
        "",
        f"Parser: {meta['parser']} {meta['parser_version']}; "
        f"Git: {meta['git_commit'] or 'unknown'}.",
        f"Gold-/Evaluationsschema: 1; Corpus: {report['cohort']['corpus_sha256']}.",
        f"Zeitpunkt: {meta['timestamp']}; Dirty: {meta['git_dirty']}.",
        f"Stabiler Qualitätsfingerprint: {report['quality_sha256']}.",
        "",
        "CER/WER verwenden ausschliesslich Whitespace-Normalisierung. Reading Order misst",
        "eindeutige Textanker im serialisierten Text, keine rekonstruierte Layoutstruktur.",
        "Evidence nutzt einen goldgestützten exakten Zitat-Locator, keine autonome Extraktion.",
        "unsupported ist keine gemessene Null. Capability gaps sind getrennt von Messfehlern.",
        "",
        "| Metrik | Wert/Status | Zähler | Nenner | messbar / unsupported / n.a. |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name, summary in report["aggregate"].items():
        metric = summary["metric"]
        value = f"{metric['value']:.6f}" if metric["status"] == "measured" else metric["status"]
        counts = (
            f"{summary['measured_cases']} / {summary['unsupported_cases']} / "
            f"{summary['not_evaluable_cases']}"
        )
        lines.append(
            f"| {name} | {value} | {metric['numerator']} | {metric['denominator']} | {counts} |"
        )
    lines += [
        "",
        "## Layoutvergleich",
        "",
        "| Layout | Fälle | CER | Completeness | Reading Order |",
        "| --- | --- | --- | --- | --- |",
    ]
    for layout, group in report["by_layout"].items():

        def show(name, group=group):
            m = group[name]["metric"]
            return f"{m['value']:.4f}" if m["status"] == "measured" else m["status"]

        count = sum(case["layout_type"] == layout for case in report["cases"])
        lines.append(
            f"| {layout} | {count} | {show('character_error_rate')} | "
            f"{show('text_completeness')} | {show('reading_order_accuracy')} |"
        )
    lines += ["", "## Fälle und Fehleranalyse", ""]
    for case in report["cases"]:
        lines += [
            f"### {case['fixture_id']}",
            "",
            f"Status: {case['observation']['status']}; "
            f"Status-Erwartung erfüllt: {case['metrics']['expected_status_match']['value']}.",
            f"Originalhash: {case['pdf_sha256']}; Receipt: {case['receipt_id']}.",
            "",
        ]
        for finding in case["failures"]:
            lines.append(f"- {finding['kind']} ({finding['basis']}): {finding['detail']}")
        for diagnostic in case["diagnostics"]:
            lines.append(f"- Diagnose: {diagnostic}")
        if not case["failures"] and not case["diagnostics"]:
            lines.append("- Keine Abweichung in den messbaren Dimensionen.")
        lines.append("")
    lines += [
        "## Grenzen",
        "",
        f"{len(report['cases'])} kontrollierte Fälle sind keine repräsentative Stichprobe. "
        "Fehlende OCR und",
        "fehlende Tabellen-/Klauselstruktur werden sichtbar, nicht nachträglich repariert.",
        "Zeiten umfassen Ingestion und verifizierten Reload, nicht PDF-Erzeugung/Metriken.",
        "Keine harten CPU-/RAM-/Zeitlimits; dafür ist ein isolierter Worker erforderlich.",
        "Rohtexte, Evidenzkandidaten, Goldstandard, Konfiguration und Laufzeitumgebung",
        "stehen in den JSON-Artefakten. Fehlende/mehrdeutige Anker werden ausgewiesen.",
    ]
    if "comparison" in report:
        lines += ["", "## Vergleich", "", json.dumps(report["comparison"], ensure_ascii=False)]
    return "\n".join(lines) + "\n"


def export(report: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (destination / "report.md").write_text(markdown(report), encoding="utf-8")
