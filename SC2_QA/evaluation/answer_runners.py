"""Strict Agent and plain answer execution paths."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from API_Tools.llm_caller import call_openai_detailed
from sc2_agent import get_provider_catalog, resolve_reasoning_model_key, run_agent

from .schemas import AnswerInput, ExperimentConfig


def resolve_reasoning_setting(model_key: str, mode: str) -> tuple[str, bool]:
    catalog = get_provider_catalog()
    if model_key not in catalog:
        raise ValueError(f"Unknown model_key: {model_key}")
    enabled = bool(catalog[model_key].get("is_reasoning")) if mode == "auto" else mode == "on"
    return resolve_reasoning_model_key(model_key, enabled), enabled


def run_agent_answer(answer_input: AnswerInput, config: ExperimentConfig, agent_log_root: Path) -> dict[str, Any]:
    _, reasoning_enabled = resolve_reasoning_setting(config.answer_model_key, config.answer_reasoning)
    started = time.perf_counter()
    try:
        result = run_agent(
            answer_input.question,
            provider=config.answer_model_key,
            enable_reasoning=reasoning_enabled,
            response_language="English",
            log_dir=agent_log_root / answer_input.case_id,
        )
        return {
            "status": "completed",
            "mode": "agent",
            "case_id": answer_input.case_id,
            **answer_input.audit_record(),
            "answer_model_key": config.answer_model_key,
            "reasoning_mode": config.answer_reasoning,
            "reasoning_enabled": reasoning_enabled,
            "answer": result.get("answer", ""),
            "reasoning_trace": result.get("reasoning_trace", []),
            "agent_run_id": result.get("run_id"),
            "agent_trace_path": result.get("log_path"),
            "tool_call_count": len(result.get("tool_results") or []),
            "planner_step_count": len((result.get("plan") or {}).get("steps") or []),
            "latency_seconds": round(time.perf_counter() - started, 6),
            "error": "",
        }
    except Exception as exc:
        return {
            "status": "error",
            "mode": "agent",
            "case_id": answer_input.case_id,
            **answer_input.audit_record(),
            "answer_model_key": config.answer_model_key,
            "reasoning_mode": config.answer_reasoning,
            "reasoning_enabled": reasoning_enabled,
            "answer": "",
            "reasoning_trace": [],
            "latency_seconds": round(time.perf_counter() - started, 6),
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_plain_answer(answer_input: AnswerInput, config: ExperimentConfig) -> dict[str, Any]:
    actual_model_key, reasoning_enabled = resolve_reasoning_setting(
        config.answer_model_key, config.answer_reasoning
    )
    messages = [{"role": "user", "content": answer_input.question}]
    started = time.perf_counter()
    result = call_openai_detailed(
        messages=messages,
        model_key=actual_model_key,
        is_reasoning=reasoning_enabled,
    )
    return {
        "status": "error" if result.get("error") else "completed",
        "mode": "plain",
        "case_id": answer_input.case_id,
        **answer_input.audit_record(),
        "messages": messages,
        "answer_model_key": config.answer_model_key,
        "actual_model_key": actual_model_key,
        "model": result.get("model", ""),
        "reasoning_mode": config.answer_reasoning,
        "reasoning_enabled": reasoning_enabled,
        "answer": result.get("content", ""),
        "reasoning": result.get("reasoning", ""),
        "reasoning_available": bool(result.get("reasoning")),
        "reasoning_source": result.get("reasoning_source", "none"),
        "reasoning_extract_mode": result.get("reasoning_extract_mode"),
        "raw_content": result.get("raw_content", ""),
        "raw_message": result.get("raw_message", {}),
        "usage": result.get("usage", {}),
        "finish_reason": result.get("finish_reason", ""),
        "latency_seconds": result.get("latency_seconds") or round(time.perf_counter() - started, 6),
        "error": result.get("error", ""),
    }


def run_answer(answer_input: AnswerInput, config: ExperimentConfig, agent_log_root: Path) -> dict[str, Any]:
    if config.mode == "agent":
        return run_agent_answer(answer_input, config, agent_log_root)
    return run_plain_answer(answer_input, config)
