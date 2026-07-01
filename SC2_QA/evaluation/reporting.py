"""Single-mode aggregate metrics and human-readable reports."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _merge_usage(target: dict[str, float], usage: Any) -> None:
    if not isinstance(usage, dict):
        return
    for key, value in usage.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            target[str(key)] = target.get(str(key), 0.0) + float(value)


def _usage_totals(records: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, float]]:
    answer_usage: dict[str, float] = {}
    judge_usage: dict[str, float] = {}
    for record in records:
        answer = record.get("answer", {})
        _merge_usage(answer_usage, answer.get("usage"))
        for trace in answer.get("reasoning_trace") or []:
            _merge_usage(answer_usage, trace.get("usage"))
        for attempt in record.get("judgment", {}).get("attempts") or []:
            _merge_usage(judge_usage, attempt.get("usage"))
    return answer_usage, judge_usage


def _group_metrics(records: list[dict[str, Any]], key_fn) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[str(key_fn(record))].append(record)
    return {key: score_metrics(values) for key, values in sorted(groups.items())}


def score_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    scoreable = [record for record in records if record.get("judgment", {}).get("earned_points") is not None]
    earned = sum(float(record["judgment"]["earned_points"]) for record in scoreable)
    maximum = sum(float(record["judgment"]["max_points"]) for record in scoreable)
    accuracies = [float(record["judgment"]["accuracy"]) for record in scoreable]
    return {
        "case_count": len(records),
        "scoreable_case_count": len(scoreable),
        "earned_points": earned,
        "max_points": maximum,
        "micro_accuracy": earned / maximum if maximum else None,
        "macro_accuracy": sum(accuracies) / len(accuracies) if accuracies else None,
        "full_credit_count": sum(bool(record["judgment"].get("full_credit")) for record in scoreable),
        "full_credit_rate": (
            sum(bool(record["judgment"].get("full_credit")) for record in scoreable) / len(scoreable)
            if scoreable else None
        ),
    }


def build_summary(records: list[dict[str, Any]], run_config: dict[str, Any]) -> dict[str, Any]:
    answer_errors = sum(record.get("answer", {}).get("status") != "completed" for record in records)
    judge_errors = sum(record.get("judgment", {}).get("status") == "judge_error" for record in records)
    answer_latencies = [float(record.get("answer", {}).get("latency_seconds") or 0) for record in records]
    judge_latencies = [float(record.get("judgment", {}).get("latency_seconds") or 0) for record in records]
    criteria: dict[str, dict[str, float]] = defaultdict(lambda: {"earned_points": 0.0, "max_points": 0.0, "occurrences": 0})
    for record in records:
        for point in record.get("judgment", {}).get("point_results") or []:
            bucket = criteria[str(point["point_id"])]
            bucket["earned_points"] += float(point.get("awarded_points", 0))
            bucket["max_points"] += float(point.get("max_points", 0))
            bucket["occurrences"] += 1
    for bucket in criteria.values():
        bucket["accuracy"] = bucket["earned_points"] / bucket["max_points"] if bucket["max_points"] else None
    answer_usage, judge_usage = _usage_totals(records)
    return {
        "experiment_name": run_config.get("experiment_name"),
        "mode": run_config.get("mode"),
        "answer_model_key": run_config.get("answer_model_key"),
        "judge_model_key": run_config.get("judge_model_key"),
        "overall": score_metrics(records),
        "by_race": _group_metrics(records, lambda record: record["case"]["race"]),
        "by_hop_count": _group_metrics(records, lambda record: record["case"]["metadata"]["hop_count"]),
        "by_criterion": dict(sorted(criteria.items())),
        "answer_error_count": answer_errors,
        "judge_error_count": judge_errors,
        "average_answer_latency_seconds": sum(answer_latencies) / len(answer_latencies) if answer_latencies else None,
        "average_judge_latency_seconds": sum(judge_latencies) / len(judge_latencies) if judge_latencies else None,
        "answer_usage": answer_usage,
        "judge_usage": judge_usage,
    }


def write_reports(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    records = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((run_dir / "cases").glob("*.json"))]
    summary = build_summary(records, config)
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (run_dir / "summary.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        fieldnames = ["case_id", "race", "hop_count", "status", "earned_points", "max_points", "accuracy", "full_credit", "answer_latency_seconds", "judge_latency_seconds"]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            judgment = record.get("judgment", {})
            writer.writerow({
                "case_id": record["case"]["id"],
                "race": record["case"]["race"],
                "hop_count": record["case"]["metadata"]["hop_count"],
                "status": record.get("status"),
                "earned_points": judgment.get("earned_points"),
                "max_points": judgment.get("max_points"),
                "accuracy": judgment.get("accuracy"),
                "full_credit": judgment.get("full_credit"),
                "answer_latency_seconds": record.get("answer", {}).get("latency_seconds"),
                "judge_latency_seconds": judgment.get("latency_seconds"),
            })

    overall = summary["overall"]
    lines = [
        f"# Evaluation Report: {summary['experiment_name']}", "",
        f"- Mode: `{summary['mode']}`",
        f"- Answer model: `{summary['answer_model_key']}`",
        f"- Judge model: `{summary['judge_model_key']}`",
        f"- Cases: {overall['case_count']}",
        f"- Earned points: {overall['earned_points']} / {overall['max_points']}",
        f"- Micro accuracy: {format_ratio(overall['micro_accuracy'])}",
        f"- Macro accuracy: {format_ratio(overall['macro_accuracy'])}",
        f"- Full-credit rate: {format_ratio(overall['full_credit_rate'])}",
        f"- Answer errors: {summary['answer_error_count']}",
        f"- Judge errors: {summary['judge_error_count']}", "",
        f"- Answer token usage: `{json.dumps(summary['answer_usage'], ensure_ascii=False)}`",
        f"- Judge token usage: `{json.dumps(summary['judge_usage'], ensure_ascii=False)}`", "",
        "## By race", "",
    ]
    for key, metrics in summary["by_race"].items():
        lines.append(f"- {key}: {metrics['earned_points']} / {metrics['max_points']} ({format_ratio(metrics['micro_accuracy'])})")
    lines.extend(["", "## By hop count", ""])
    for key, metrics in summary["by_hop_count"].items():
        lines.append(f"- {key} hops: {metrics['earned_points']} / {metrics['max_points']} ({format_ratio(metrics['micro_accuracy'])})")
    lines.extend(["", "## By scoring criterion", ""])
    for key, metrics in summary["by_criterion"].items():
        lines.append(f"- {key}: {metrics['earned_points']} / {metrics['max_points']} ({format_ratio(metrics['accuracy'])})")
    (run_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def format_ratio(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2%}"
