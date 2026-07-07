"""Point-by-point LLM judging with local score recomputation."""

from __future__ import annotations

import json
import re
import time
from typing import Any

from API_Tools.llm_caller import call_openai_detailed

from .answer_runners import resolve_reasoning_setting
from .schemas import ExperimentConfig, JudgeInput


JUDGE_SYSTEM_PROMPT = """You are an atomic answer grader. Grade only the atomic criteria supplied by the user.

Rules:
- Each criterion is independent and atomic. Award either 0 or its full point value; never partial credit.
- Credit a point only when the candidate answer explicitly states the required fact or an unambiguously equivalent value.
- Numeric forms such as 150 and 150.0 are equivalent when they express the same requested quantity.
- Use containment-based grading: if the candidate answer contains the complete required fact anywhere, award the point even if the answer also lists other candidates, marks the correct candidate as an alternative, hedges about ambiguity, or does not present the correct endpoint as the sole final answer.
- For endpoint_name criteria, award the point when the exact expected endpoint name appears as a candidate answer or explicitly named entity. Do not require it to be the first, primary, or unique endpoint.
- For attribute criteria such as mineral_cost, gas_cost, maximum_health, armor, or research_time, award the point when the expected value is stated for the expected endpoint, or when the candidate clearly gives a complete candidate block for the expected endpoint containing that value.
- Do not withhold an attribute point merely because another candidate block has different values. Grade the expected endpoint's facts if they are present.
- Do not award an attribute point when the expected value appears only for a different entity and the expected endpoint is absent or lacks that attribute.
- Do not infer missing facts from correct intermediate reasoning.
- Do not award points for facts outside the supplied criteria.
- Do not deduct points for style, verbosity, or harmless additional information.
- Additional incorrect candidates are harmless unless they make the required fact impossible to identify.
- The reference answer and evidence fields define the grading target.
- Return one result for every point_id exactly once.
- Return valid JSON only, with no Markdown fences or commentary outside the JSON object.
"""


def build_judge_messages(judge_input: JudgeInput, repair: dict[str, str] | None = None) -> list[dict[str, str]]:
    criteria = judge_input.scoring.get("criteria") or []
    output_shape = {
        "case_id": judge_input.case_id,
        "point_results": [
            {
                "point_id": item["point_id"],
                "awarded_points": f"0 or {item['points']}",
                "max_points": item["points"],
                "candidate_evidence": "short excerpt from candidate answer, or empty string",
                "reason": "brief grading reason",
            }
            for item in criteria
        ],
        "overall_comment": "brief overall assessment",
    }
    payload: dict[str, Any] = {
        "question": judge_input.question,
        "candidate_answer": judge_input.candidate_answer,
        "standard_answer": judge_input.standard_answer,
        "max_points": judge_input.scoring.get("max_points"),
        "criteria": criteria,
        "required_output_shape": output_shape,
    }
    if repair:
        payload["repair_previous_output"] = repair["output"]
        payload["repair_validation_error"] = repair["error"]
        payload["repair_instruction"] = "Return a corrected complete JSON object."
    return [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, indent=2)},
    ]


def parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s*```$", "", value)
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start, end = value.find("{"), value.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Judge output does not contain a JSON object")
        parsed = json.loads(value[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Judge output must be a JSON object")
    return parsed


def validate_and_score(parsed: dict[str, Any], judge_input: JudgeInput) -> dict[str, Any]:
    criteria = judge_input.scoring.get("criteria") or []
    expected = {str(item["point_id"]): item for item in criteria}
    raw_results = parsed.get("point_results")
    if not isinstance(raw_results, list):
        raise ValueError("point_results must be a list")
    actual_ids = [str(item.get("point_id")) for item in raw_results if isinstance(item, dict)]
    if len(actual_ids) != len(set(actual_ids)):
        raise ValueError("point_results contains duplicate point_id values")
    if set(actual_ids) != set(expected):
        raise ValueError(f"point_id mismatch: expected {sorted(expected)}, got {sorted(actual_ids)}")

    validated = []
    for raw in raw_results:
        point_id = str(raw["point_id"])
        maximum = float(expected[point_id]["points"])
        try:
            awarded = float(raw.get("awarded_points", 0))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid awarded_points for {point_id}") from exc
        if awarded not in {0.0, maximum}:
            raise ValueError(f"{point_id} must award either 0 or {maximum}")
        validated.append({
            "point_id": point_id,
            "awarded_points": int(awarded) if awarded.is_integer() else awarded,
            "max_points": int(maximum) if maximum.is_integer() else maximum,
            "candidate_evidence": str(raw.get("candidate_evidence") or ""),
            "reason": str(raw.get("reason") or ""),
            "criterion": expected[point_id].get("criterion"),
            "expected_answer": expected[point_id].get("expected_answer"),
        })
    ordering = {str(item["point_id"]): index for index, item in enumerate(criteria)}
    validated.sort(key=lambda item: ordering[item["point_id"]])
    earned = sum(float(item["awarded_points"]) for item in validated)
    maximum = sum(float(item["max_points"]) for item in validated)
    return {
        "status": "completed",
        "case_id": judge_input.case_id,
        "point_results": validated,
        "earned_points": int(earned) if earned.is_integer() else earned,
        "max_points": int(maximum) if maximum.is_integer() else maximum,
        "accuracy": earned / maximum if maximum else 0.0,
        "full_credit": earned == maximum,
        "overall_comment": str(parsed.get("overall_comment") or ""),
    }


def zero_judgment(judge_input: JudgeInput, reason: str) -> dict[str, Any]:
    criteria = judge_input.scoring.get("criteria") or []
    maximum = sum(float(item.get("points", 0)) for item in criteria)
    return {
        "status": "not_judged",
        "case_id": judge_input.case_id,
        "point_results": [
            {
                "point_id": item["point_id"],
                "awarded_points": 0,
                "max_points": item["points"],
                "candidate_evidence": "",
                "reason": reason,
                "criterion": item.get("criterion"),
                "expected_answer": item.get("expected_answer"),
            }
            for item in criteria
        ],
        "earned_points": 0,
        "max_points": int(maximum) if maximum.is_integer() else maximum,
        "accuracy": 0.0,
        "full_credit": False,
        "overall_comment": reason,
        "attempts": [],
    }


def judge_answer(judge_input: JudgeInput, config: ExperimentConfig) -> dict[str, Any]:
    actual_model_key, reasoning_enabled = resolve_reasoning_setting(
        config.judge_model_key, config.judge_reasoning
    )
    attempts = []
    repair: dict[str, str] | None = None
    last_error = ""
    started = time.perf_counter()
    for attempt_index in range(config.judge_retries + 1):
        messages = build_judge_messages(judge_input, repair=repair)
        result = call_openai_detailed(
            messages=messages,
            model_key=actual_model_key,
            is_reasoning=reasoning_enabled,
        )
        attempt = {
            "attempt": attempt_index + 1,
            "messages": messages,
            "model_key": actual_model_key,
            "model": result.get("model"),
            "content": result.get("content", ""),
            "reasoning": result.get("reasoning", ""),
            "reasoning_source": result.get("reasoning_source"),
            "reasoning_extract_mode": result.get("reasoning_extract_mode"),
            "usage": result.get("usage", {}),
            "finish_reason": result.get("finish_reason", ""),
            "latency_seconds": result.get("latency_seconds", 0.0),
            "rate_limit_wait_seconds": result.get("rate_limit_wait_seconds", 0.0),
            "error": result.get("error", ""),
        }
        attempts.append(attempt)
        if result.get("error"):
            last_error = result["error"]
        else:
            try:
                judgment = validate_and_score(parse_json_object(result.get("content", "")), judge_input)
                judgment.update({
                    "judge_model_key": config.judge_model_key,
                    "actual_judge_model_key": actual_model_key,
                    "judge_reasoning_mode": config.judge_reasoning,
                    "judge_reasoning_enabled": reasoning_enabled,
                    "attempts": attempts,
                    "latency_seconds": round(time.perf_counter() - started, 6),
                    "error": "",
                })
                return judgment
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                repair = {"output": result.get("content", ""), "error": last_error}
        if attempt_index < config.judge_retries and config.retry_backoff_seconds > 0:
            time.sleep(config.retry_backoff_seconds)

    maximum = float(judge_input.scoring.get("max_points", 0))
    return {
        "status": "judge_error",
        "case_id": judge_input.case_id,
        "point_results": [],
        "earned_points": None,
        "max_points": int(maximum) if maximum.is_integer() else maximum,
        "accuracy": None,
        "full_credit": False,
        "judge_model_key": config.judge_model_key,
        "actual_judge_model_key": actual_model_key,
        "judge_reasoning_mode": config.judge_reasoning,
        "judge_reasoning_enabled": reasoning_enabled,
        "attempts": attempts,
        "latency_seconds": round(time.perf_counter() - started, 6),
        "error": last_error or "Judge failed without a parseable result",
    }
