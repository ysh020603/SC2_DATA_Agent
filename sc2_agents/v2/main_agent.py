"""Tool-isolated MainAgent state machine for V2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .contracts import parse_json_object, validate_main_decision
from .runtime import LLMInvoker


ROOT = Path(__file__).resolve().parent
MAX_MAIN_ROUNDS = 12


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8").strip()


class MainAgent:
    def __init__(
        self,
        invoker: LLMInvoker,
        recorder: Any,
        response_language: str = "English",
    ) -> None:
        self.invoker = invoker
        self.recorder = recorder
        self.response_language = response_language

    def run(
        self,
        user_query: str,
        ask_subagent: Callable[[str, int], dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
        system = "\n\n".join([
            _read("prompts/main_system.md"),
            _read("context/dataset_overview.md"),
            f"Write final_answer in {self.response_language}.",
        ])
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_query},
        ]
        decisions: list[dict[str, Any]] = []
        sessions: list[dict[str, Any]] = []
        asked: set[str] = set()
        for main_round in range(MAX_MAIN_ROUNDS):
            result = self.invoker(f"main_round_{main_round + 1}", messages)
            content = result.get("content", "")
            try:
                decision = validate_main_decision(parse_json_object(content))
            except Exception as first_error:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous reply did not match the required MainAgent JSON contract. "
                        "Return exactly one valid JSON object now."
                    ),
                })
                repair = self.invoker(f"main_round_{main_round + 1}_repair", messages, reasoning=False)
                decision = validate_main_decision(parse_json_object(repair.get("content", "")))
                content = repair.get("content", "")
                self.recorder.record("main_contract_repair", {
                    "main_round": main_round,
                    "first_error": first_error,
                })
            decisions.append(decision)
            self.recorder.record("main_decision", {"main_round": main_round, "decision": decision})
            messages.append({"role": "assistant", "content": content})
            if decision["action"] == "final_answer":
                return str(decision["final_answer"]), decisions, sessions
            question = str(decision["sub_question"]).strip()
            normalized = " ".join(question.lower().split())
            if normalized in asked:
                feedback = {
                    "answer": "This exact subquestion has already been answered. Use the previous facts or ask a narrower follow-up.",
                    "confidence": "low",
                    "evidence_summary": "Duplicate request rejected by the orchestrator.",
                    "limitations": ["Duplicate subquestion."],
                }
            else:
                asked.add(normalized)
                session = ask_subagent(question, main_round)
                sessions.append(session)
                feedback = session["reply"]
            messages.append({
                "role": "user",
                "content": "DataSubAgent reply:\n" + json.dumps(feedback, ensure_ascii=False),
            })
        fallback = (
            "The MainAgent round limit was reached before it produced a complete answer. "
            "The available evidence is incomplete."
        )
        return fallback, decisions, sessions


__all__ = ["MAX_MAIN_ROUNDS", "MainAgent"]

