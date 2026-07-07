"""Tool-isolated MainAgent state machine for V2.1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .contracts import parse_json_object, validate_main_decision
from .runtime import LLMInvoker


ROOT = Path(__file__).resolve().parent
MAX_MAIN_ROUNDS = 20


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
            _read("context/reasoning_policy.md"),
            _read("context/field_mapping.md"),
            _read("context/graph_traversal_policy.md"),
            _read("context/entity_canonicalization.md"),
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
        messages.append({
            "role": "user",
            "content": (
                "The maximum number of MainAgent rounds has now been reached. "
                "Do not ask another subquestion. Return one valid MainAgent JSON object with action "
                "`final_answer`. Use the accumulated DataSubAgent evidence to provide the best "
                "supported answer. If the wording is ambiguous or evidence is incomplete, include "
                "the defensible candidates and limitations in the final_answer."
            ),
        })
        try:
            result = self.invoker("main_round_limit_best_effort_final", messages)
            decision = validate_main_decision(parse_json_object(result.get("content", "")))
            if decision["action"] == "final_answer":
                decisions.append(decision)
                self.recorder.record("main_decision", {
                    "main_round": MAX_MAIN_ROUNDS,
                    "decision": decision,
                    "best_effort": True,
                })
                return str(decision["final_answer"]), decisions, sessions
        except Exception as exc:
            self.recorder.record("main_best_effort_final_failed", {"error": f"{type(exc).__name__}: {exc}"})
        fallback = self._evidence_fallback_answer(sessions)
        return fallback, decisions, sessions

    @staticmethod
    def _evidence_fallback_answer(sessions: list[dict[str, Any]]) -> str:
        replies = [session.get("reply") or {} for session in sessions]
        useful = [reply for reply in replies if str(reply.get("answer") or "").strip()]
        if not useful:
            return (
                "The available evidence is insufficient to produce a supported answer. "
                "No conclusive DataSubAgent reply was available."
            )
        parts = [
            "The available evidence did not converge to one fully supported endpoint before the round limit. "
            "Best supported facts gathered:"
        ]
        for index, reply in enumerate(useful[-5:], start=1):
            parts.append(f"{index}. {reply.get('answer')}")
            candidates = reply.get("candidate_entities") or []
            if candidates:
                compact = []
                for candidate in candidates[:5]:
                    name = candidate.get("name", "")
                    role = candidate.get("role", "")
                    fields = candidate.get("fields", {})
                    compact.append(f"{name} ({role}, fields={fields})")
                parts.append("   Candidates: " + "; ".join(compact))
        parts.append("Limitations: evidence is partial, so ambiguous candidates should be treated explicitly.")
        return "\n".join(parts)


__all__ = ["MAX_MAIN_ROUNDS", "MainAgent"]
