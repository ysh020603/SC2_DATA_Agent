"""Command-line interface for standalone Agent or plain SC2 QA evaluation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sc2_agent import get_provider_catalog

from .dataset import load_dataset, select_cases
from .experiment import EvaluationExperiment, summarize_existing
from .schemas import ExperimentConfig


def comma_list(value: str | None) -> list[str]:
    return [part.strip() for part in (value or "").split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Experiment JSON configuration file.")
    parser.add_argument("--resume", help="Existing experiment directory to resume.")
    parser.add_argument("--summarize", help="Rebuild reports for an existing experiment directory without API calls.")
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--validate-only", action="store_true", help="Validate config, dataset, filters, and model keys without API calls.")
    parser.add_argument("--mode", choices=["agent", "plain"])
    parser.add_argument("--answer-model-key")
    parser.add_argument("--judge-model-key")
    parser.add_argument("--answer-reasoning", choices=["auto", "on", "off"])
    parser.add_argument("--judge-reasoning", choices=["auto", "on", "off"])
    parser.add_argument("--workers", type=int)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", help="Comma-separated case IDs.")
    parser.add_argument("--races", help="Comma-separated races.")
    parser.add_argument("--hop-counts", help="Comma-separated hop counts.")
    return parser


def load_config(args: argparse.Namespace) -> ExperimentConfig:
    if args.config:
        config = ExperimentConfig.from_file(args.config)
    elif args.resume:
        config = ExperimentConfig.from_file(Path(args.resume) / "run_config.json")
    else:
        raise ValueError("--config is required for a new experiment; use --resume for an existing one")
    overrides = {
        "mode": args.mode,
        "answer_model_key": args.answer_model_key,
        "judge_model_key": args.judge_model_key,
        "answer_reasoning": args.answer_reasoning,
        "judge_reasoning": args.judge_reasoning,
        "workers": args.workers,
        "limit": args.limit,
    }
    for key, value in overrides.items():
        if value is not None:
            setattr(config, key, value)
    if args.ids is not None:
        config.ids = comma_list(args.ids)
    if args.races is not None:
        config.races = comma_list(args.races)
    if args.hop_counts is not None:
        config.hop_counts = [int(value) for value in comma_list(args.hop_counts)]
    config.validate()
    return config


def main() -> int:
    args = build_parser().parse_args()
    if args.summarize:
        summary = summarize_existing(args.summarize)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    config = load_config(args)
    dataset = load_dataset(config.dataset)
    selected = select_cases(dataset, config)
    catalog = get_provider_catalog()
    unknown = [key for key in (config.answer_model_key, config.judge_model_key) if key not in catalog]
    if unknown:
        raise ValueError(f"Unknown model keys: {unknown}")
    if args.validate_only:
        print(json.dumps({
            "status": "valid",
            "mode": config.mode,
            "answer_model_key": config.answer_model_key,
            "judge_model_key": config.judge_model_key,
            "selected_case_count": len(selected),
            "selected_case_ids": [case["id"] for case in selected],
            "dataset_sha256": dataset["_sha256"],
            "answer_input_contract": "exact question only",
        }, ensure_ascii=False, indent=2))
        return 0
    experiment = EvaluationExperiment(
        config,
        run_dir=Path(args.resume).resolve() if args.resume else None,
        retry_failed=args.retry_failed,
    )
    summary = experiment.run()
    print(f"experiment_dir={experiment.recorder.run_dir}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
