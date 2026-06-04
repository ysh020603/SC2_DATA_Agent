#!/usr/bin/env python3
"""Natural-language SC2 search Agent backed by DATA_BASE query tools."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI

from sc2_query_engine import execute_tool
from sc2_search_tools import DEFAULT_DATA_PATH


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR / "skills" / "sc2_data_query"
CONFIG_DIR = SCRIPT_DIR / "config"
CONFIG_FILE = CONFIG_DIR / "provider_config.json"

DEFAULT_PROVIDER = "glm-4.7"
DEFAULT_ENABLE_REASONING = False
PROVIDER_PRESETS: dict[str, dict[str, Any]] = {
    "kimi-k2.5": {
        "model": "kimi-k2.5",
        "api_key": "",
        "base_url": "http://172.18.39.161:19003/v1",
        "temperature": 0.2,
        "top_p": 0.8,
        "max_tokens": 8192,
    },
    "deepseek-v4-flash": {
        "model": "deepseek-v4-flash",
        "api_key": "",
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.2,
        "top_p": 0.8,
        "max_tokens": 8192,
    },
    "glm-4.7": {
        "model": "glm-4.7",
        "api_key": "",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "temperature": 0.2,
        "top_p": 0.8,
        "max_tokens": 8192,
    },
}

ENV_OVERRIDES = {
    "kimi-k2.5": {"api_key": "KIMI_API_KEY", "base_url": "KIMI_BASE_URL"},
    "deepseek-v4-flash": {"api_key": "DEEPSEEK_API_KEY", "base_url": "DEEPSEEK_BASE_URL"},
    "glm-4.7": {"api_key": "GLM_API_KEY", "base_url": "GLM_BASE_URL"},
}


TOOL_SPEC = """
Available tools:

1. filter_attributes_and_resources
Use for resource budgets, numeric fields, race, attributes, boolean flags, sorting, and selected return keys.
Arguments are Query IR:
{
  "sections": ["Unit"|"Ability"|"Upgrade"],
  "name_query": optional string,
  "name_mode": "contains"|"exact"|"fuzzy",
  "numeric_ranges": {"field": {"min": number, "max": number}},
  "tag_filters": {"race": string, "attributes_any": [string], "attributes_all": [string], "booleans": {"field": bool}},
  "combat_filters": optional combat filter object,
  "sort": [{"field": string, "order": "asc"|"desc"}],
  "return_keys": optional list of key paths,
  "limit": integer
}

2. query_tech_tree
Use for tech unlock paths, destroyed-building reverse inference, add-on requirements, or multiple production/morph paths.
Arguments:
{
  "target": optional string,
  "broken_node": optional string,
  "multi_path_min": optional integer,
  "requires_addon": optional "TechLab"|"Reactor",
  "sections": optional list,
  "limit": integer
}

3. query_tactical_profile
Use for spell energy, cast range, cooldown, target type, immediate-cast checks, creep speed, and transforming forms.
Arguments:
{
  "unit_filters": optional field filters,
  "ability_filters": optional field filters,
  "immediate_cast": optional boolean,
  "transforming_only": optional boolean,
  "compare_forms": optional boolean,
  "limit": integer
}

4. search_descriptions
Use when the user describes tactical effects in natural language, such as detector, reveal, cloak, AoE, splash, burrow, armor reduction, harass.
Arguments:
{
  "keywords": [string],
  "mode": "any"|"all",
  "sections": optional list,
  "limit": integer
}

5. strategic_join_analysis
Use for cross-table or derived metric analysis, such as cost efficiency, add-on dependency analysis, and spell target assessment.
Arguments:
{
  "analysis_type": "cost_efficiency"|"addon_dependencies"|"spell_target_check",
  "filters": object,
  "top_n": integer
}
"""


def model_family(model_name: str) -> str:
    name = model_name.lower()
    if "kimi" in name:
        return "kimi"
    if "glm" in name:
        return "glm"
    if "deepseek" in name:
        return "deepseek"
    if "qwen" in name:
        return "qwen"
    return "generic"


def build_inference_config(
    model_name: str,
    enable_reasoning: bool,
    temperature: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {"model": model_name}
    if temperature is not None:
        config["temperature"] = temperature
    if top_p is not None:
        config["top_p"] = top_p
    if max_tokens is not None:
        config["max_tokens"] = max_tokens
    family = model_family(model_name)
    if enable_reasoning:
        if family == "kimi":
            config["temperature"] = 1.0
            config["extra_body"] = {"thinking": {"type": "enabled"}, "chat_template_kwargs": {"thinking": True}}
        elif family in {"glm", "deepseek"}:
            config["extra_body"] = {"thinking": {"type": "enabled"}}
        elif family == "qwen":
            config["extra_body"] = {"enable_thinking": True}
        else:
            config["extra_body"] = {"chat_template_kwargs": {"enable_thinking": True}}
    else:
        if family == "kimi":
            config["temperature"] = 0.6
            config["extra_body"] = {"thinking": {"type": "disabled"}, "chat_template_kwargs": {"thinking": False}}
        elif family in {"glm", "deepseek"}:
            config["extra_body"] = {"thinking": {"type": "disabled"}}
        else:
            config["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
    return config


def load_provider_config_file() -> dict[str, dict[str, Any]]:
    if not CONFIG_FILE.exists():
        return {}
    raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    providers = raw.get("providers", raw)
    return {key: value for key, value in providers.items() if isinstance(value, dict)}


def get_provider_catalog() -> dict[str, dict[str, Any]]:
    catalog = {key: dict(value) for key, value in PROVIDER_PRESETS.items()}
    for provider, cfg in load_provider_config_file().items():
        current = dict(catalog.get(provider, {}))
        current.update(cfg)
        catalog[provider] = current
    for provider, env_map in ENV_OVERRIDES.items():
        if provider not in catalog:
            continue
        for field, env_name in env_map.items():
            if os.environ.get(env_name):
                catalog[provider][field] = os.environ[env_name]
    return catalog


def resolve_provider_config(provider: str = DEFAULT_PROVIDER) -> dict[str, Any]:
    catalog = get_provider_catalog()
    if provider not in catalog:
        raise ValueError(f"Unknown provider: {provider}")
    cfg = dict(catalog[provider])
    if not cfg.get("api_key") or not cfg.get("base_url"):
        raise ValueError(f"Provider {provider} misses api_key or base_url. Configure DATA_BASE/config/provider_config.json.")
    return cfg


def call_llm(
    messages: list[dict[str, str]],
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    enable_reasoning: bool = DEFAULT_ENABLE_REASONING,
) -> str:
    cfg = resolve_provider_config(provider)
    if model:
        cfg["model"] = model
    client = OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
    inference = build_inference_config(
        cfg["model"],
        enable_reasoning=enable_reasoning,
        temperature=cfg.get("temperature"),
        top_p=cfg.get("top_p"),
        max_tokens=cfg.get("max_tokens"),
    )
    completion = client.chat.completions.create(messages=messages, **inference)
    return completion.choices[0].message.content or ""


def load_skill_context() -> str:
    files = [
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "context" / "data_schema.md",
        SKILL_DIR / "context" / "field_dictionary.md",
        SKILL_DIR / "context" / "query_recipes.md",
        SKILL_DIR / "context" / "tech_chain_rules.md",
        SKILL_DIR / "context" / "domain_aliases.md",
    ]
    chunks = []
    for path in files:
        if path.exists():
            chunks.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def planner_prompt(user_query: str, response_language: str = "Chinese") -> list[dict[str, str]]:
    system = f"""
You are an SC2 data query planner. Convert the user's natural-language request into one or more tool calls.

Rules:
- Use only the available tools listed below.
- Return valid JSON only. Do not include Markdown.
- Prefer one combined tool call when possible.
- Use Chinese aliases only as input names; output tool arguments must use internal English field names.
- Do not answer the user directly. Planning only.
- Keep limits modest unless the user asks for exhaustive output.

{TOOL_SPEC}

Skill context:
{load_skill_context()}
"""
    user = f"""
User query:
{user_query}

Return JSON with this schema:
{{
  "language": "{response_language}",
  "tool_calls": [
    {{"tool": "tool_name", "arguments": {{}}}}
  ],
  "notes": ["short planning notes in English"]
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def answer_prompt(
    user_query: str,
    plan: dict[str, Any],
    tool_results: list[dict[str, Any]],
    response_language: str = "Chinese",
) -> list[dict[str, str]]:
    system = """
You are an SC2 data analyst. Use the provided tool results to answer the user's question.

Rules:
- Answer strictly in the requested response language.
- Do not output raw JSON.
- Summarize the useful findings, mention counts, and explain why the results match.
- If the evidence is incomplete or approximate, say so clearly.
- Keep the answer compact but useful.
"""
    user = f"""
Original user query:
{user_query}

Requested response language:
{response_language}

Tool plan:
{json.dumps(plan, ensure_ascii=False, indent=2)}

Tool results:
{json.dumps(compact_tool_results(tool_results), ensure_ascii=False, indent=2)}

Write the final answer now.
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def infer_target_name(user_query: str, fallback: str) -> str:
    aliases = {
        "母舰": "Mothership",
        "控制核心": "CyberneticsCore",
        "兴奋剂": "Stimpack",
        "大和战舰": "Battlecruiser",
        "战列巡航舰": "Battlecruiser",
        "兵营": "Barracks",
        "机场": "Starport",
        "星港": "Starport",
    }
    for alias, name in aliases.items():
        if alias in user_query:
            return name

    lowered = user_query.lower()
    try:
        data = json.loads(Path(DEFAULT_DATA_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback

    names = []
    for rows in data.values():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if isinstance(row, dict) and row.get("name"):
                names.append(str(row["name"]))
    for name in sorted(set(names), key=len, reverse=True):
        if name.lower() in lowered:
            return name
    return fallback


def fallback_plan(user_query: str, response_language: str = "Chinese") -> dict[str, Any]:
    lowered = user_query.lower()
    tech_markers = [
        "tech_chain",
        "tech chain",
        "prerequisite",
        "unlock",
        "build",
        "destroyed",
        "broken",
        "科技链",
        "前置",
        "解锁",
        "建造",
        "摧毁",
        "断掉",
        "多路径",
    ]
    if any(marker in lowered for marker in tech_markers):
        target = user_query
        for marker in [
            "to build",
            "build",
            "unlock",
            "建造",
            "解锁",
            "所需",
            "完整",
            "科技链",
            "。",
            ".",
            "？",
            "?",
        ]:
            target = target.replace(marker, " ")
        target = infer_target_name(user_query, " ".join(target.split()) or user_query)
        if "destroyed" in lowered or "broken" in lowered or "摧毁" in lowered or "断掉" in lowered:
            return {
                "language": response_language,
                "tool_calls": [
                    {
                        "tool": "query_tech_tree",
                        "arguments": {"broken_node": target, "sections": ["Unit", "Upgrade"], "limit": 50},
                    }
                ],
                "notes": ["Fallback plan: reverse tech-chain query."],
            }
        return {
            "language": response_language,
            "tool_calls": [
                {
                    "tool": "query_tech_tree",
                    "arguments": {"target": target, "sections": ["Unit", "Ability", "Upgrade"], "limit": 20},
                }
            ],
            "notes": ["Fallback plan: tech-chain query."],
        }
    return {
        "language": response_language,
        "tool_calls": [
            {
                "tool": "search_descriptions",
                "arguments": {"keywords": [user_query], "mode": "any", "sections": ["Unit", "Ability", "Upgrade"], "limit": 20},
            }
        ],
        "notes": ["Fallback plan: semantic description search."],
    }


def run_agent(
    user_query: str,
    provider: str = DEFAULT_PROVIDER,
    model: str | None = None,
    data_path: str | Path = DEFAULT_DATA_PATH,
    dry_run: bool = False,
    enable_reasoning: bool = DEFAULT_ENABLE_REASONING,
    response_language: str = "Chinese",
) -> dict[str, Any]:
    if dry_run:
        plan = fallback_plan(user_query, response_language=response_language)
    else:
        try:
            plan = parse_json_response(
                call_llm(
                    planner_prompt(user_query, response_language),
                    provider=provider,
                    model=model,
                    enable_reasoning=enable_reasoning,
                )
            )
        except Exception as exc:  # noqa: BLE001
            plan = fallback_plan(user_query, response_language=response_language)
            plan["planner_error"] = repr(exc)

    tool_results = []
    for call in plan.get("tool_calls", []):
        tool = call.get("tool")
        arguments = call.get("arguments") or {}
        try:
            result = execute_tool(tool, arguments, data_path=data_path)
            tool_results.append({"tool": tool, "arguments": arguments, "result": result})
        except Exception as exc:  # noqa: BLE001
            tool_results.append({"tool": tool, "arguments": arguments, "error": repr(exc)})

    if dry_run:
        if response_language == "English":
            answer = "Dry run completed. Tool calls were executed, but no LLM summarization was requested."
        else:
            answer = "试运行已完成。工具调用已经执行，但没有请求 LLM 进行总结。"
    else:
        try:
            answer = call_llm(
                answer_prompt(user_query, plan, tool_results, response_language),
                provider=provider,
                model=model,
                enable_reasoning=enable_reasoning,
            )
        except Exception as exc:  # noqa: BLE001
            answer = fallback_answer(tool_results, exc, response_language=response_language)

    return {"query": user_query, "plan": plan, "tool_results": tool_results, "answer": answer}


def compact_tool_results(tool_results: list[dict[str, Any]], max_items: int = 30) -> list[dict[str, Any]]:
    compacted = []
    for item in tool_results:
        copy = dict(item)
        result = copy.get("result")
        if isinstance(result, dict) and isinstance(result.get("results"), list):
            result = dict(result)
            result["results"] = result["results"][:max_items]
            copy["result"] = result
        compacted.append(copy)
    return compacted


def fallback_answer(tool_results: list[dict[str, Any]], exc: Exception, response_language: str = "Chinese") -> str:
    if response_language == "English":
        lines = [f"LLM summarization failed: {exc!r}", "Brief tool results:"]
    else:
        lines = [f"LLM 总结失败：{exc!r}", "下面是工具检索到的简要结果："]
    for tool_result in tool_results:
        result = tool_result.get("result") or {}
        lines.append(f"- {tool_result.get('tool')}: {result.get('count', 'unknown')} results")
        for row in (result.get("results") or [])[:8]:
            name = row.get("name") or row.get("unit_name") or row.get("ability_name")
            if name:
                lines.append(f"  - {name}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SC2 natural-language search Agent.")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None)
    parser.add_argument("--language", default="Chinese", choices=["Chinese", "English"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reasoning", action="store_true")
    args = parser.parse_args()
    result = run_agent(
        " ".join(args.query),
        provider=args.provider,
        model=args.model,
        dry_run=args.dry_run,
        enable_reasoning=args.reasoning,
        response_language=args.language,
    )
    print(result["answer"])
    print("\n--- Tool trace ---")
    print(json.dumps({"plan": result["plan"], "tool_results": result["tool_results"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
