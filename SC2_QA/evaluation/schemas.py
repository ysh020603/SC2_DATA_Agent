"""Validated data contracts for SC2 QA experiments."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


VALID_MODES = {"agent", "plain"}
VALID_REASONING_MODES = {"auto", "on", "off"}


@dataclass(frozen=True)
class AnswerInput:
    """The complete and intentionally minimal input visible to an answer model."""

    case_id: str
    question: str

    @classmethod
    def from_case(cls, case: dict[str, Any]) -> "AnswerInput":
        return cls(case_id=str(case["id"]), question=str(case["question"]))

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.question.encode("utf-8")).hexdigest()

    def audit_record(self) -> dict[str, Any]:
        return {
            "answer_input_source": "question",
            "answer_input_text": self.question,
            "answer_input_sha256": self.sha256,
            "extra_answer_guidance": False,
        }


@dataclass(frozen=True)
class JudgeInput:
    case_id: str
    question: str
    candidate_answer: str
    standard_answer: str
    scoring: dict[str, Any]

    @classmethod
    def from_case(cls, case: dict[str, Any], candidate_answer: str) -> "JudgeInput":
        return cls(
            case_id=str(case["id"]),
            question=str(case["question"]),
            candidate_answer=candidate_answer,
            standard_answer=str(case["standard_answer"]),
            scoring=dict(case["scoring"]),
        )


@dataclass
class ExperimentConfig:
    experiment_name: str
    mode: str
    answer_model_key: str
    judge_model_key: str
    dataset: str = "qa_multihop_sc2_60.json"
    answer_reasoning: str = "auto"
    agent_version: str = "v2"
    judge_reasoning: str = "auto"
    workers: int = 1
    answer_retries: int = 2
    judge_retries: int = 2
    retry_backoff_seconds: float = 3.0
    request_delay_seconds: float = 0.0
    races: list[str] = field(default_factory=list)
    hop_counts: list[int] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)
    limit: int | None = None

    def validate(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {sorted(VALID_MODES)}, got {self.mode!r}")
        if self.answer_reasoning not in VALID_REASONING_MODES:
            raise ValueError(f"Invalid answer_reasoning: {self.answer_reasoning}")
        if self.agent_version not in {"v1", "v2"}:
            raise ValueError(f"Invalid agent_version: {self.agent_version}")
        if self.judge_reasoning not in VALID_REASONING_MODES:
            raise ValueError(f"Invalid judge_reasoning: {self.judge_reasoning}")
        if not self.answer_model_key or not self.judge_model_key:
            raise ValueError("answer_model_key and judge_model_key are required")
        if self.workers < 1:
            raise ValueError("workers must be at least 1")
        if self.answer_retries < 0 or self.judge_retries < 0:
            raise ValueError("retry counts cannot be negative")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_file(cls, path: str | Path) -> "ExperimentConfig":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        config = cls(**raw)
        config.validate()
        return config
