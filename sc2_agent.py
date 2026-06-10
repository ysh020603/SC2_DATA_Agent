#!/usr/bin/env python3
"""Natural-language SC2 search Agent backed by DATA_BASE query tools."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from openai import OpenAI
except ModuleNotFoundError:  # pragma: no cover - dry-run and deterministic tests do not need the SDK.
    OpenAI = None

from sc2_query_engine import ENTITY_ALIASES, execute_tool
from sc2_search_tools import DEFAULT_DATA_PATH


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR / "skills" / "sc2_data_query"
MAIN_AGENT_SKILL_DIR = SCRIPT_DIR / "skills" / "main_agent"
CONFIG_DIR = SCRIPT_DIR / "config"
OPTIONAL_SKILLS_DIR = SCRIPT_DIR / "skills" / "optional_skills"
CONFIG_FILE = CONFIG_DIR / "provider_config.json"
MAX_AGENT_STEPS = 4

DEFAULT_PROVIDER = "glm-4.7"
DEFAULT_ENABLE_REASONING = False
DEFAULT_LLM_TIMEOUT_SECONDS = 180.0
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

0. resolve_entity_key
Use as the entity-key resolver subagent. It resolves user mentions or aliases into canonical Unit, Ability, or Upgrade names.
Arguments:
{
  "mention": string,
  "expected_section": optional "Unit"|"Ability"|"Upgrade",
  "sections": optional list,
  "race": optional string,
  "limit": integer
}

0b. get_entity
Use to fetch one canonical entity record by section/name.
Arguments:
{
  "section": "Unit"|"Ability"|"Upgrade",
  "name": string,
  "keys": optional list of key paths
}

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

1b. query_production_outputs
Use for producer-to-output multi-hop joins, such as "what units can Barracks train and what are their costs/supply?"
This tool follows Unit.abilities[*].ability_name -> Ability.target.*.produces_name/upgrade_name -> Unit/Upgrade.
Arguments:
{
  "producer_name": string,
  "producer_section": optional "Unit",
  "output_sections": optional ["Unit"|"Upgrade"],
  "target_types": optional list such as ["Train"], ["Research"], or ["Train","Build","Morph"],
  "return_keys": optional list of produced entity key paths,
  "required_addon": optional string,
  "excluded_addon": optional string,
  "require_no_addon": optional boolean,
  "required_building": optional string,
  "required_upgrade": optional string,
  "include_requirements": optional boolean,
  "include_ability": optional boolean,
  "limit": integer
}

1c. query_reverse_production_sources
Use for output-to-producer joins, such as "where is Marauder produced and what add-on is required?"
Arguments:
{
  "produced_name": string,
  "produced_section": optional "Unit"|"Upgrade",
  "producer_race": optional string,
  "target_types": optional list,
  "return_keys": optional producer key paths,
  "required_addon": optional string,
  "excluded_addon": optional string,
  "require_no_addon": optional boolean,
  "include_requirements": optional boolean,
  "limit": integer
}

1d. query_addon_branches
Use for add-on condition branches, e.g. Factory or Starport with TechLab, without TechLab, or Reactor-compatible outputs.
Arguments:
{
  "producer_name": string,
  "return_keys": optional list of produced Unit key paths,
  "limit": integer
}

1d2. query_addon_producers
Use for all add-on-capable structures and their TechLab/Reactor-compatible production branches.
Arguments:
{
  "race": optional string,
  "return_keys": optional list of produced Unit key paths,
  "limit": integer
}

1e. query_research_outputs
Use for producer-to-upgrade joins, e.g. EngineeringBay researches which upgrades, or which Terran upgrades require TechLab.
Arguments:
{
  "producer_name": optional string,
  "race": optional string,
  "required_addon": optional string,
  "return_keys": optional list of Upgrade key paths,
  "include_requirements": optional boolean,
  "limit": integer
}

1f. query_unit_abilities
Use for Unit -> Ability joins, energy-cost skills, cast range, cooldown, and target-type questions.
Arguments:
{
  "unit_name": optional string,
  "race": optional string,
  "only_energy": optional boolean,
  "include_passive_commands": optional boolean,
  "ability_return_keys": optional list of Ability key paths,
  "limit": integer
}

1g. query_dependency_impact
Use for reverse dependency impact across tech_chain and requirements, e.g. if Factory or GhostAcademy is missing.
Arguments:
{
  "node_name": string,
  "sections": optional list,
  "race": optional string,
  "include_requirements": optional boolean,
  "include_tech_chain": optional boolean,
  "limit": integer
}

1h. query_upgrade_effects
Use for Upgrade -> affected Unit inference from descriptions, optionally scoped by research producer.
Arguments:
{
  "upgrade_name": optional string,
  "research_producer_name": optional string,
  "race": optional string,
  "include_sources": optional boolean,
  "limit": integer
}

1i. query_gas_units_with_sources
Use for units costing gas plus reverse production source and tech-chain evidence.
Arguments:
{
  "race": optional string,
  "min_gas": optional number,
  "include_tech_chain": optional boolean,
  "limit": integer
}

1j. query_combat_production_options
Use for combined production and combat questions, such as Barracks-tech anti-air units or fastest units without TechLab.
Arguments:
{
  "producer_name": optional string,
  "race": optional string,
  "can_attack_air": optional boolean,
  "require_no_addon": optional boolean,
  "required_addon": optional string,
  "sort_by": optional string,
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
6. query_counter_relations
Use for hard/soft counter questions: "what counters Marine?", "what does Archon hard-counter?"
Arguments:
{
  "entity_name": string (canonical unit name),
  "counter_type": optional "hard"|"soft"|"all"
}

7. query_combat_synergy
Use for synergy/composition questions: "what units work well with SiegeTank?"
Arguments:
{
  "entity_name": string (canonical unit name),
  "direction": optional "forward"|"reverse"|"both"
}

8. query_garrison_relations
Use for garrison/transport questions: "what units can enter Bunker?", "can SiegeTank load into Medivac?"
Arguments:
{
  "entity_name": string (canonical unit/structure name),
  "direction": optional "forward"|"reverse"|"both"
}

9. query_stat_bonuses
Use for upgrade stat bonus questions: "what upgrades improve MissileTurret?", "what units does HiSecAutoTracking affect?"
Arguments:
{
  "entity_name": string (canonical upgrade or unit name),
  "direction": optional "forward"|"reverse"|"both"
}

10. query_ability_unlocks
Use for upgrade ability unlock questions: "what does Stimpack unlock?", "what upgrades give Marine new abilities?"
Arguments:
{
  "entity_name": string (canonical upgrade or unit name),
  "direction": optional "forward"|"reverse"|"both"
}

11. query_morph_enablers
Use for morph/transform unlock questions: "what upgrade lets Hellion transform?", "what does SmartServos enable?"
Arguments:
{
  "entity_name": string (canonical upgrade or unit name),
  "direction": optional "forward"|"reverse"|"both"
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
    if OpenAI is None:
        raise RuntimeError("The openai package is not installed in this Python environment.")
    cfg = resolve_provider_config(provider)
    if model:
        cfg["model"] = model
    client = OpenAI(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        timeout=float(cfg.get("timeout", DEFAULT_LLM_TIMEOUT_SECONDS)),
    )
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



def load_main_agent_context(selected_skills: list[str], selected_races: list[str]) -> str:
    files = [
        MAIN_AGENT_SKILL_DIR / "SKILL.md",
        MAIN_AGENT_SKILL_DIR / "routing.md",
        SCRIPT_DIR / "skills" / "subagents" / "entity_key_resolver" / "SKILL.md",
    ]

    # 1. Dynamically load Optional Skills selected by LLM
    skills_index_path = OPTIONAL_SKILLS_DIR / "index.json"
    if skills_index_path.exists():
        skills_index = json.loads(skills_index_path.read_text(encoding="utf-8"))
        for skill_id in selected_skills:
            if skill_id in skills_index:
                files.append(OPTIONAL_SKILLS_DIR / skills_index[skill_id]["file"])

    # 2. Dynamically load race dictionaries selected by LLM
    for race in selected_races:
        race_dir = race.lower()
        if race_dir in ["terran", "protoss", "zerg"]:
            entity_context = SCRIPT_DIR / "skills" / "subagents" / "entity_key_resolver" / "context" / race_dir
            files.append(entity_context / "units.md")
            files.append(entity_context / "abilities.md")
            files.append(entity_context / "upgrades.md")

    chunks = []
    for path in files:
        if path.exists():
            chunks.append(f"# {path.name}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(chunks)


def router_prompt(user_query: str) -> list[dict[str, str]]:
    """Build Context Router prompt so the LLM picks Skills and race dictionaries from the user query."""
    skills_index_path = OPTIONAL_SKILLS_DIR / "index.json"
    skills_summary: dict[str, dict[str, str]] = {}
    if skills_index_path.exists():
        skills_summary = json.loads(skills_index_path.read_text(encoding="utf-8"))

    skills_text = "\n".join([f"- {skill_id}: {info['description']}" for skill_id, info in skills_summary.items()])

    system = f"""
You are a Context Router for a StarCraft II Agent. Your task is to analyze the user's query and decide which optional skills and race-specific data dictionaries should be loaded into the working memory.

Available Optional Skills (Summaries):
{skills_text}

Available Race Dictionaries:
- Terran
- Protoss
- Zerg

Rules:
1. Select skills ONLY if their description matches the user's intent. Leave empty if none match.
2. Select a race ONLY if the query implies or mentions units/mechanics of that race.
3. Return valid JSON only.

Output Schema:
{{
  "selected_skills": ["skill_id_1"],
  "selected_races": ["Terran"]
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user_query}]


def llm_context_router(user_query: str, provider: str, model: str | None) -> dict[str, list[str]]:
    """Call LLM to decide which contexts to load."""
    try:
        response = call_llm(
            router_prompt(user_query),
            provider=provider,
            model=model,
            enable_reasoning=False,
        )
        return parse_json_response(response)
    except Exception as e:
        print(f"Router failed: {e}. Falling back to empty context.")
        return {"selected_skills": [], "selected_races": []}

def planner_prompt(
    user_query: str,
    context_text: str,
    state: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    state = state or {"observations": [], "step": 0}
    system = f"""
You are the main SC2 multi-hop data query orchestrator. Plan the next retrieval step, observe tool results, and decide when the evidence is sufficient.

Rules:
- Use only the available tools listed below.
- Return valid JSON only. Do not include Markdown.
- Prefer deterministic tools over guessing from descriptions.
- For multi-hop questions, call tools step by step. Use observations from previous steps before planning the next step.
- Use resolve_entity_key when a user-facing name may need canonical Unit/Ability/Upgrade keys.
- Use query_production_outputs or query_reverse_production_sources for production joins instead of trying to compose this with generic filters.
- Do not answer the user directly. Planning only.
- Keep limits modest unless the user asks for exhaustive output.
- If enough evidence has been collected, return status "final" with no tool calls.

{TOOL_SPEC}

Core skill context:
{load_skill_context()}

Selected main-agent skill context:
{context_text}
"""
    user = f"""
User query:
{user_query}

Current state:
{json.dumps(compact_agent_state(state), ensure_ascii=False, indent=2)}

Return JSON with this schema:
{{
  "status": "need_tools"|"final",
  "tool_calls": [
    {{"tool": "tool_name", "arguments": {{}}}}
  ],
  "notes": [string]
}}
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def answer_prompt(
    user_query: str,
    plan: dict[str, Any],
    tool_results: list[dict[str, Any]],
) -> list[dict[str, str]]:
    system = """
You are an SC2 data analyst. Use the provided tool results to answer the user's question. Respond in English.

Rules:
- Do not output raw JSON.
- Summarize the useful findings, mention counts, and explain why the results match.
- If the evidence is incomplete or approximate, say so clearly.
- Keep the answer compact but useful.
"""
    user = f"""
Original user query:
{user_query}

Tool plan:
{json.dumps(plan, ensure_ascii=False, indent=2)}

Tool results:
{json.dumps(compact_tool_results(tool_results), ensure_ascii=False, indent=2)}

Write the final answer now.
"""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def compact_agent_state(state: dict[str, Any], max_observations: int = 6, max_rows: int = 8) -> dict[str, Any]:
    compacted = dict(state)
    observations = []
    for observation in compacted.get("observations", [])[-max_observations:]:
        copy = dict(observation)
        result = copy.get("result")
        if isinstance(result, dict) and isinstance(result.get("results"), list):
            result = dict(result)
            result["results"] = result["results"][:max_rows]
            copy["result"] = result
        observations.append(copy)
    compacted["observations"] = observations
    return compacted


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


def detect_query_race(user_query: str) -> str | None:
    lowered = user_query.lower()
    race_aliases = {
        "Terran": ["terran", "human", "人族", "人类"],
        "Protoss": ["protoss", "神族", "星灵"],
        "Zerg": ["zerg", "虫族", "异虫"],
    }
    for race, aliases in race_aliases.items():
        if any(alias in lowered or alias in user_query for alias in aliases):
            return race
    return None


def infer_target_name(user_query: str, fallback: str) -> str:
    aliases = dict(ENTITY_ALIASES)
    aliases.update({
    })
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

def fallback_plan(user_query: str, ) -> dict[str, Any]:
    lowered = user_query.lower()
    race_hint = detect_query_race(user_query)
    if any(marker in lowered for marker in ["research", "upgrades", "upgrade", "\u7814\u7a76", "\u5347\u7ea7"]) and not any(
        marker in lowered for marker in ["tech lab", "techlab", "\u79d1\u6280\u5b9e\u9a8c\u5ba4"]
    ):
        producer = infer_target_name(user_query, None)
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_research_outputs",
                    "arguments": {
                        "producer_name": producer,
                        "race": race_hint,
                        "return_keys": ["name", "cost", "tech_chain", "description"],
                        "include_requirements": True,
                        "limit": 100,
                    },
                }
            ],
            "notes": ["Fallback plan: generic research-output query."],
        }
    if any(marker in lowered for marker in ["addon", "tech lab", "techlab", "reactor", "without tech lab", "\u6302", "\u79d1\u6280\u5b9e\u9a8c\u5ba4", "\u53cd\u5e94\u5806", "\u4e0d\u6302", "\u53cc\u4ea7"]):
        if any(marker in lowered for marker in ["all", "which structures", "\u6240\u6709", "\u54ea\u4e9b\u5efa\u7b51", "\u54ea\u4e9b\u80fd\u6302"]):
            return {
                    "status": "need_tools",
                "tool_calls": [
                    {
                        "tool": "query_addon_producers",
                        "arguments": {"race": race_hint or "Terran", "return_keys": ["name", "race", "minerals", "gas", "supply", "time"], "limit": 50},
                    }
                ],
                "notes": ["Fallback plan: all add-on-capable producers."],
            }
        if any(marker in lowered for marker in ["factory", "\u91cd\u5de5\u5382", "\u5de5\u5382"]):
            producer = "Factory"
        elif any(marker in lowered for marker in ["starport", "\u661f\u6e2f", "\u673a\u573a"]):
            producer = "Starport"
        elif any(marker in lowered for marker in ["barracks", "\u5175\u8425"]):
            producer = "Barracks"
        else:
            producer = infer_target_name(user_query, user_query)
        if any(marker in lowered for marker in ["which upgrades", "upgrades", "research", "\u54ea\u4e9b\u5347\u7ea7", "\u5347\u7ea7", "\u7814\u7a76"]):
            return {
                    "status": "need_tools",
                "tool_calls": [
                    {
                        "tool": "query_research_outputs",
                        "arguments": {"race": race_hint or "Terran", "required_addon": "TechLab", "return_keys": ["name", "cost", "tech_chain"], "limit": 100},
                    }
                ],
                "notes": ["Fallback plan: research outputs requiring TechLab."],
            }
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_addon_branches",
                    "arguments": {"producer_name": producer, "return_keys": ["name", "race", "minerals", "gas", "supply", "time"], "limit": 100},
                }
            ],
            "notes": ["Fallback plan: add-on branch production query."],
        }

    if any(marker in lowered for marker in ["from which", "where is", "source", "produced from", "\u4ece\u54ea\u4e2a\u5efa\u7b51", "\u54ea\u4e2a\u5efa\u7b51\u751f\u4ea7", "\u4ece\u54ea\u6765"]):
        target = infer_target_name(user_query, user_query)
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_reverse_production_sources",
                    "arguments": {
                        "produced_name": target,
                        "produced_section": "Unit",
                        "producer_race": race_hint,
                        "return_keys": ["name", "race", "tech_chain"],
                        "include_requirements": True,
                        "limit": 50,
                    },
                }
            ],
            "notes": ["Fallback plan: reverse production source query."],
        }

    if any(marker in lowered for marker in ["abilities", "spells", "energy", "cast range", "cooldown", "target type", "\u6280\u80fd", "\u80fd\u91cf", "\u5c04\u7a0b", "\u51b7\u5374", "\u76ee\u6807\u7c7b\u578b"]):
        unit = infer_target_name(user_query, None)
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_unit_abilities",
                    "arguments": {
                        "unit_name": unit,
                        "race": race_hint if unit is None else None,
                        "only_energy": any(marker in lowered for marker in ["energy", "\u80fd\u91cf"]),
                        "include_passive_commands": False,
                        "limit": 100,
                    },
                }
            ],
            "notes": ["Fallback plan: unit-to-ability tactical join."],
        }

    if any(marker in lowered for marker in ["destroyed", "missing", "not built", "dependency", "depend", "\u88ab\u6253\u6389", "\u6ca1\u6709\u5efa\u597d", "\u4e0d\u53ef\u7528", "\u4f9d\u8d56", "\u5f71\u54cd"]):
        node = infer_target_name(user_query, user_query)
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_dependency_impact",
                    "arguments": {"node_name": node, "sections": ["Unit", "Ability", "Upgrade"], "race": race_hint, "limit": 200},
                }
            ],
            "notes": ["Fallback plan: dependency impact query."],
        }

    if any(marker in lowered for marker in ["engineeringbay", "engineering bay", "infantry weapons", "infantry armor", "\u5de5\u7a0b\u7ad9", "\u6b65\u5175\u653b\u9632", "\u6b65\u5175\u5347\u7ea7"]):
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_upgrade_effects",
                    "arguments": {"research_producer_name": "EngineeringBay", "race": "Terran", "include_sources": True, "limit": 100},
                }
            ],
            "notes": ["Fallback plan: EngineeringBay upgrade effects."],
        }

    if any(marker in lowered for marker in ["stimpack", "\u5174\u594b\u5242"]):
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_upgrade_effects",
                    "arguments": {"upgrade_name": "Stimpack", "race": "Terran", "include_sources": True, "limit": 20},
                }
            ],
            "notes": ["Fallback plan: upgrade effects query."],
        }

    if any(marker in lowered for marker in ["gas units", "cost gas", "vespene", "\u9700\u8981\u6c14", "\u8017\u6c14", "\u6c14\u4f53"]):
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_gas_units_with_sources",
                    "arguments": {"race": race_hint, "min_gas": 0, "limit": 100},
                }
            ],
            "notes": ["Fallback plan: gas units with reverse production sources."],
        }

    if any(marker in lowered for marker in ["anti-air", "attack air", "\u5bf9\u7a7a"]):
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_combat_production_options",
                    "arguments": {
                        "producer_name": infer_target_name(user_query, None),
                        "race": race_hint,
                        "can_attack_air": True,
                        "limit": 100,
                    },
                }
            ],
            "notes": ["Fallback plan: production plus anti-air combat filter."],
        }

    if any(marker in lowered for marker in ["fastest", "without techlab", "without tech lab", "\u6700\u5feb", "\u6ca1\u6709 tech lab", "\u6ca1\u6709\u79d1\u6280\u5b9e\u9a8c\u5ba4"]):
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_combat_production_options",
                    "arguments": {"race": race_hint or "Terran", "require_no_addon": True, "sort_by": "time", "limit": 100},
                }
            ],
            "notes": ["Fallback plan: fastest no-TechLab production options."],
        }

    production_markers = [
        "produce",
        "train",
        "morph",
        "morph into",
        "spawn",
        "\u751f\u4ea7",
        "\u8bad\u7ec3",
        "\u80fd\u9020",
        "\u80fd\u751f\u4ea7",
        "\u53d8\u6210",
        "\u53d8\u4e3a",
        "\u5b75\u5316",
    ]
    if any(marker in lowered for marker in production_markers):
        producer = infer_target_name(user_query, user_query)
        target_types = ["Train", "Morph"] if producer == "Larva" else ["Train"]
        return {
            "status": "need_tools",
            "tool_calls": [
                {
                    "tool": "query_production_outputs",
                    "arguments": {
                        "producer_name": producer,
                        "producer_section": "Unit",
                        "output_sections": ["Unit"],
                        "target_types": target_types,
                        "return_keys": ["name", "race", "minerals", "gas", "supply", "time"],
                        "include_requirements": True,
                        "include_ability": True,
                        "limit": 50,
                    },
                }
            ],
            "notes": ["Fallback plan: production-output multi-hop query."],
        }
    tech_markers = [
        "tech_chain",
        "tech chain",
        "prerequisite",
        "unlock",
        "build",
        "destroyed",
        "broken",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
    ]
    if any(marker in lowered for marker in tech_markers):
        target = user_query
        for marker in [
            "to build",
            "build",
            "unlock",
            "",
            "",
            "",
            "",
            "",
            "",
            ".",
            "",
            "?",
        ]:
            target = target.replace(marker, " ")
        target = infer_target_name(user_query, " ".join(target.split()) or user_query)
        if "destroyed" in lowered or "broken" in lowered or "" in lowered or "" in lowered:
            return {
                    "tool_calls": [
                    {
                        "tool": "query_tech_tree",
                        "arguments": {"broken_node": target, "sections": ["Unit", "Upgrade"], "limit": 50},
                    }
                ],
                "notes": ["Fallback plan: reverse tech-chain query."],
            }
        return {
            "tool_calls": [
                {
                    "tool": "query_tech_tree",
                    "arguments": {"target": target, "sections": ["Unit", "Ability", "Upgrade"], "limit": 20},
                }
            ],
            "notes": ["Fallback plan: tech-chain query."],
        }
    return {
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
    response_language: str = "English",
) -> dict[str, Any]:

    # === Phase 1: LLM Context Routing ===
    if dry_run:
        routing_decision: dict[str, list[str]] = {"selected_skills": [], "selected_races": []}
    else:
        routing_decision = llm_context_router(user_query, provider, model)

    context_text = load_main_agent_context(
        routing_decision.get("selected_skills", []),
        routing_decision.get("selected_races", []),
    )
    # ===================================

    state: dict[str, Any] = {"step": 0, "observations": []}
    plans = []
    tool_results = []
    planner_error: Exception | None = None

    for step in range(MAX_AGENT_STEPS):
        state["step"] = step
        planner_failed = False
        if dry_run:
            plan = fallback_plan(user_query)
        else:
            try:
                plan = parse_json_response(
                    call_llm(
                        planner_prompt(user_query, context_text, state=state),
                        provider=provider,
                        model=model,
                        enable_reasoning=enable_reasoning,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                planner_error = exc
                planner_failed = True
                plan = fallback_plan(user_query)
                plan["planner_error"] = repr(exc)
        plans.append(plan)

        calls = plan.get("tool_calls") or []
        if plan.get("status") == "final" or not calls:
            break

        for call in calls:
            tool = call.get("tool")
            arguments = call.get("arguments") or {}
            observation = {"step": step, "tool": tool, "arguments": arguments}
            try:
                observation["result"] = execute_tool(tool, arguments, data_path=data_path)
            except Exception as exc:  # noqa: BLE001
                observation["error"] = repr(exc)
            tool_results.append(observation)
            state["observations"].append(observation)

        if dry_run or planner_failed:
            break

    plan_bundle = {"steps": plans, "observations": state["observations"]}
    if dry_run:
        answer = dry_run_answer(tool_results)
    elif planner_error is not None:
        answer = fallback_answer(tool_results, planner_error)
    else:
        try:
            answer = call_llm(
                answer_prompt(user_query, plan_bundle, tool_results),
                provider=provider,
                model=model,
                enable_reasoning=enable_reasoning,
            )
        except Exception as exc:  # noqa: BLE001
            answer = fallback_answer(tool_results, exc)

    return {"query": user_query, "plan": plan_bundle, "tool_results": tool_results, "answer": answer}


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


def dry_run_answer(tool_results: list[dict[str, Any]]) -> str:
    lines = ["Dry run completed. Tool calls were executed without LLM summarization."]
    for tool_result in tool_results:
        result = tool_result.get("result") or {}
        lines.append(f"- {tool_result.get('tool')}: {result.get('count', 'unknown')} results")
        for row in (result.get("results") or [])[:10]:
            produced = row.get("produced") if isinstance(row, dict) else None
            if isinstance(produced, dict):
                name = produced.get("name")
                minerals = produced.get("minerals")
                gas = produced.get("gas")
                supply = produced.get("supply")
                time = produced.get("time")
                parts = [str(name)]
                if minerals is not None:
                    parts.append(f"minerals={minerals}")
                if gas is not None:
                    parts.append(f"gas={gas}")
                if supply is not None:
                    parts.append(f"supply={supply}")
                if time is not None:
                    parts.append(f"time={time}")
                lines.append(f"  - {', '.join(parts)}")
                continue
            name = (row.get("name") or row.get("unit_name") or row.get("ability_name")) if isinstance(row, dict) else None
            if name:
                lines.append(f"  - {name}")
    return "\n".join(lines)


def fallback_answer(tool_results: list[dict[str, Any]], exc: Exception) -> str:
    lines = [f"LLM planning or summarization failed: {exc!r}", "Deterministic retrieval summary:"]
    summary = dry_run_answer(tool_results).splitlines()
    return "\n".join(lines + summary[1:])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the SC2 natural-language search Agent.")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--model", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reasoning", action="store_true")
    args = parser.parse_args()
    result = run_agent(
        " ".join(args.query),
        provider=args.provider,
        model=args.model,
        dry_run=args.dry_run,
        enable_reasoning=args.reasoning,
        
    )
    print(result["answer"])
    print("\n--- Tool trace ---")
    print(json.dumps({"plan": result["plan"], "tool_results": result["tool_results"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()