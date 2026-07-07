"""Public V2 MainAgent plus DataSubAgent entry point."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from API_Tools.llm_caller import load_agent_pool
from sc2_data_store import get_dataset_store
from sc2_search_tools import DEFAULT_DATA_PATH

from .main_agent import MainAgent
from .runtime import LLMInvoker, V2TraceRecorder
from .sub_agent import DataSubAgent


DEFAULT_PROVIDER = "DeepSeek-V4-flash"
DEFAULT_ENABLE_REASONING = False


def get_provider_catalog() -> dict[str, dict[str, Any]]:
    pool = load_agent_pool().get("llm_agents_pool") or {}
    return {key: dict(value) for key, value in pool.items() if isinstance(value, dict)}


def run_agent(
    user_query: str,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    data_path: str | Path = DEFAULT_DATA_PATH,
    dry_run: bool = False,
    enable_reasoning: bool = DEFAULT_ENABLE_REASONING,
    response_language: str = "English",
    log_dir: str | Path | None = None,
) -> dict[str, Any]:
    if dry_run:
        from sc2_agents.v1.agent import run_agent as run_v1

        result = run_v1(
            user_query,
            provider=provider,
            model=model,
            data_path=data_path,
            dry_run=True,
            enable_reasoning=enable_reasoning,
            response_language=response_language,
            log_dir=log_dir,
        )
        result["agent_version"] = "v1-dry-run"
        return result

    recorder = V2TraceRecorder(user_query, log_dir=log_dir)
    result: dict[str, Any] | None = None
    try:
        dataset_metadata = get_dataset_store(data_path).metadata()
        recorder.record("dataset_loaded", dataset_metadata)
        invoker = LLMInvoker(recorder, provider, model, enable_reasoning)
        subagent = DataSubAgent(invoker, recorder, data_path=data_path)
        mainagent = MainAgent(invoker, recorder, response_language=response_language)
        answer, decisions, sessions = mainagent.run(user_query, subagent.run)
        tool_results = [item for session in sessions for item in session["observations"]]
        plan = {
            "steps": decisions,
            "observations": [
                {
                    "session_id": session["session_id"],
                    "question": session["question"],
                    "selected_tools": session["selected_tools"],
                    "reply": session["reply"],
                }
                for session in sessions
            ],
        }
        result = {
            "agent_version": "v2",
            "run_id": recorder.run_id,
            "log_path": str(recorder.trace_path),
            "query": user_query,
            "provider": provider,
            "reasoning_enabled": enable_reasoning,
            "dataset": dataset_metadata,
            "routing": {"agent_version": "v2", "strategy": "main_subagent"},
            "plan": plan,
            "tool_results": tool_results,
            "reasoning_trace": invoker.trace,
            "main_decisions": decisions,
            "subagent_sessions": sessions,
            "answer": answer,
        }
        recorder.finalize(result, status="completed")
        return result
    except Exception as exc:
        recorder.finalize(result, status="failed", error=exc)
        raise


__all__ = ["DEFAULT_ENABLE_REASONING", "DEFAULT_PROVIDER", "get_provider_catalog", "run_agent"]
