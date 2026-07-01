"""Dataset loading, validation, filtering, and fingerprinting."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .schemas import ExperimentConfig


QA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = QA_DIR / "qa_multihop_sc2_60.json"


def resolve_dataset_path(value: str | Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = QA_DIR / path
    return path.resolve()


def load_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    resolved = resolve_dataset_path(path)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    questions = payload.get("questions")
    if not isinstance(questions, list) or not questions:
        raise ValueError("Dataset must contain a non-empty questions list")
    seen: set[str] = set()
    for index, case in enumerate(questions):
        missing = {"id", "race", "question", "standard_answer", "scoring", "reasoning_path", "metadata"} - set(case)
        if missing:
            raise ValueError(f"Question {index} is missing fields: {sorted(missing)}")
        case_id = str(case["id"])
        if case_id in seen:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        scoring = case["scoring"]
        criteria = scoring.get("criteria") or []
        if not criteria or sum(float(item.get("points", 0)) for item in criteria) != float(scoring.get("max_points", 0)):
            raise ValueError(f"Invalid scoring points for {case_id}")
    payload["_resolved_path"] = str(resolved)
    payload["_sha256"] = hashlib.sha256(resolved.read_bytes()).hexdigest()
    return payload


def select_cases(dataset: dict[str, Any], config: ExperimentConfig) -> list[dict[str, Any]]:
    cases = list(dataset["questions"])
    if config.ids:
        wanted = set(config.ids)
        cases = [case for case in cases if case["id"] in wanted]
    if config.races:
        wanted_races = {race.casefold() for race in config.races}
        cases = [case for case in cases if str(case["race"]).casefold() in wanted_races]
    if config.hop_counts:
        wanted_hops = set(config.hop_counts)
        cases = [case for case in cases if int(case["metadata"]["hop_count"]) in wanted_hops]
    if config.limit is not None:
        cases = cases[: config.limit]
    if not cases:
        raise ValueError("No cases match the configured filters")
    return cases
