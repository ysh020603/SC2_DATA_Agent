"""Single-mode experiment orchestration and resumable case execution."""

from __future__ import annotations

import hashlib
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sc2_agent import MAX_AGENT_STEPS, get_provider_catalog
from sc2_agents.v2.main_agent import MAX_MAIN_ROUNDS as V2_MAX_MAIN_ROUNDS
from sc2_agents.v2.sub_agent import MAX_SUB_TOOL_ROUNDS as V2_MAX_SUB_TOOL_ROUNDS
from sc2_agents.v2_1.main_agent import MAX_MAIN_ROUNDS as V2_1_MAX_MAIN_ROUNDS
from sc2_agents.v2_1.sub_agent import MAX_SUB_TOOL_ROUNDS as V2_1_MAX_SUB_TOOL_ROUNDS
from API_Tools.rate_limiter import DEFAULT_KIMI_RPM, KIMI_PROVIDER_MAX_RPM

from .answer_runners import run_answer
from .dataset import load_dataset, select_cases
from .judge import judge_answer, zero_judgment
from .recorder import DEFAULT_LOG_ROOT, EvaluationRecorder, slug
from .reporting import write_reports
from .schemas import AnswerInput, ExperimentConfig, JudgeInput


REPO_ROOT = Path(__file__).resolve().parents[2]


def git_metadata() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            completed = subprocess.run(
                ["git", *args], cwd=REPO_ROOT, check=False, capture_output=True, text=True, timeout=10
            )
            return completed.stdout.strip()
        except Exception:
            return ""
    status = run("status", "--short")
    return {"commit": run("rev-parse", "HEAD"), "branch": run("branch", "--show-current"), "dirty": bool(status), "status": status}


def make_experiment_id(config: ExperimentConfig) -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fingerprint = hashlib.sha256(
        json.dumps(config.to_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:8]
    return "_".join([
        now,
        config.mode,
        config.agent_version if config.mode == "agent" else "plain",
        slug(config.answer_model_key),
        slug(config.judge_model_key),
        fingerprint,
    ])


class EvaluationExperiment:
    def __init__(
        self,
        config: ExperimentConfig,
        run_dir: str | Path | None = None,
        retry_failed: bool = False,
    ) -> None:
        config.validate()
        catalog = get_provider_catalog()
        missing_models = [key for key in (config.answer_model_key, config.judge_model_key) if key not in catalog]
        if missing_models:
            raise ValueError(f"Unknown model keys: {missing_models}")
        self.config = config
        self.dataset = load_dataset(config.dataset)
        self.cases = select_cases(self.dataset, config)
        self.experiment_id = Path(run_dir).name if run_dir else make_experiment_id(config)
        self.recorder = EvaluationRecorder(self.experiment_id, run_dir=run_dir)
        self.retry_failed = retry_failed

    def initialize(self) -> None:
        config_path = self.recorder.run_dir / "run_config.json"
        manifest_path = self.recorder.run_dir / "manifest.json"
        if not config_path.exists():
            self.recorder.write_json(config_path, self.config.to_dict())
        if not manifest_path.exists():
            self.recorder.write_json(manifest_path, {
                "experiment_id": self.experiment_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "dataset_path": self.dataset["_resolved_path"],
                "dataset_sha256": self.dataset["_sha256"],
                "selected_case_count": len(self.cases),
                "input_contract": {
                    "answer_input_source": "question",
                    "extra_answer_guidance": False,
                    "plain_messages": [{"role": "user", "content": "<exact dataset question>"}],
                    "agent_user_input": "<exact dataset question>",
                },
                "agent_max_steps": MAX_AGENT_STEPS,
                "agent_version": self.config.agent_version,
                "agent_limits": {
                    "v1_planner_steps": MAX_AGENT_STEPS,
                    "v2_main_rounds": V2_MAX_MAIN_ROUNDS,
                    "v2_sub_tool_rounds": V2_MAX_SUB_TOOL_ROUNDS,
                    "v2_1_main_rounds": V2_1_MAX_MAIN_ROUNDS,
                    "v2_1_sub_tool_rounds": V2_1_MAX_SUB_TOOL_ROUNDS,
                },
                "provider_rate_limits": {
                    "kimi_default_rpm": DEFAULT_KIMI_RPM,
                    "kimi_hard_max_rpm": KIMI_PROVIDER_MAX_RPM,
                    "shared_across_processes": True,
                },
                "git": git_metadata(),
            })
        self.recorder.event("experiment_started", {
            "experiment_id": self.experiment_id,
            "mode": self.config.mode,
            "agent_version": self.config.agent_version,
            "case_count": len(self.cases),
        })

    def should_skip(self, case: dict[str, Any]) -> bool:
        existing = self.recorder.read_case(str(case["id"]))
        if existing is None:
            return False
        if self.retry_failed and existing.get("status") != "completed":
            return False
        return True

    def process_case(self, case: dict[str, Any]) -> dict[str, Any]:
        case_id = str(case["id"])
        self.recorder.event("case_started", {"case_id": case_id})
        answer_input = AnswerInput.from_case(case)
        answer: dict[str, Any] | None = None
        answer_attempts = []
        for attempt_index in range(self.config.answer_retries + 1):
            if self.config.request_delay_seconds > 0:
                time.sleep(self.config.request_delay_seconds)
            answer = run_answer(answer_input, self.config, self.recorder.agent_traces_dir)
            answer_attempts.append({
                "attempt": attempt_index + 1,
                "status": answer.get("status"),
                "error": answer.get("error", ""),
                "latency_seconds": answer.get("latency_seconds"),
                "agent_trace_path": answer.get("agent_trace_path"),
            })
            if answer.get("status") == "completed" and str(answer.get("answer") or "").strip():
                break
            if attempt_index < self.config.answer_retries and self.config.retry_backoff_seconds > 0:
                time.sleep(self.config.retry_backoff_seconds)
        if answer is None:
            raise RuntimeError("Answer runner did not produce a result")
        answer["attempts"] = answer_attempts
        answer["retry_count"] = max(0, len(answer_attempts) - 1)

        judge_input = JudgeInput.from_case(case, str(answer.get("answer") or ""))
        if answer.get("status") != "completed" or not judge_input.candidate_answer.strip():
            judgment = zero_judgment(judge_input, "Answer generation failed or returned an empty answer.")
            status = "answer_error"
        else:
            judgment = judge_answer(judge_input, self.config)
            status = "completed" if judgment.get("status") == "completed" else "judge_error"

        record = {
            "status": status,
            "experiment_id": self.experiment_id,
            "mode": self.config.mode,
            "case": case,
            "answer": answer,
            "judgment": judgment,
        }
        path = self.recorder.write_case(case_id, record)
        self.recorder.event("case_finished", {
            "case_id": case_id,
            "status": status,
            "earned_points": judgment.get("earned_points"),
            "max_points": judgment.get("max_points"),
            "case_path": path,
        })
        return record

    def run(self) -> dict[str, Any]:
        self.initialize()
        pending = [case for case in self.cases if not self.should_skip(case)]
        skipped = len(self.cases) - len(pending)
        self.recorder.event("resume_scan", {"pending": len(pending), "skipped": skipped})
        if self.config.workers == 1:
            for case in pending:
                self.process_case(case)
        else:
            with ThreadPoolExecutor(max_workers=self.config.workers) as executor:
                futures = {executor.submit(self.process_case, case): case for case in pending}
                for future in as_completed(futures):
                    case = futures[future]
                    try:
                        future.result()
                    except Exception as exc:
                        self.recorder.event("case_unhandled_error", {"case_id": case["id"], "error": exc})
        summary = write_reports(self.recorder.run_dir)
        self.recorder.event("experiment_finished", {"summary": summary})
        return summary


def summarize_existing(run_dir: str | Path) -> dict[str, Any]:
    return write_reports(Path(run_dir).resolve())
