#!/usr/bin/env python3
"""Higher-level SC2 query engine for Agent use."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from sc2_search_tools import (
    DEFAULT_DATA_PATH,
    apply_projection,
    combined_search,
    filter_by_numeric_ranges,
    filter_by_tags,
    filter_combat_profile,
    flatten_items,
    get_value,
    load_data,
    normalize_text,
    search_by_name,
)


ADDON_NAMES = {"techlab", "reactor"}
TEXT_EXPANSIONS = {
    "detector": ["detector", "detection", "detect", "reveal", "revealed", "cloak", "cloaked"],
    "reveal": ["reveal", "revealed", "revelation", "detector", "detection"],
    "cloak": ["cloak", "cloaked", "invisible", "stealth", "burrowed"],
    "aoe": ["aoe", "splash", "area of effect", "area damage", "radius"],
    "splash": ["splash", "area of effect", "aoe", "radius"],
    "burrow": ["burrow", "burrowed", "underground"],
    "armor reduction": ["armor reduction", "anti-armor", "anti armor", "armor reduced", "shred"],
    "shred": ["shred", "armor reduction", "anti-armor", "anti armor"],
    "harass": ["harass", "harassment", "worker harassment", "mobility", "mobile"],
}


def all_items(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    return flatten_items(data_path=data_path)


def unit_ability_join(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    data = load_data(data_path)
    ability_by_id = {item["id"]: item for item in data.get("Ability", [])}
    rows: list[dict[str, Any]] = []
    for unit in data.get("Unit", []):
        for ability_ref in unit.get("abilities") or []:
            ability = ability_by_id.get(ability_ref.get("ability"))
            if not ability:
                continue
            rows.append(
                {
                    "unit": unit,
                    "ability": ability,
                    "ability_ref": ability_ref,
                    "unit_name": unit.get("name"),
                    "ability_name": ability.get("name"),
                }
            )
    return rows


def parse_step_name(step_text: str) -> str:
    return re.sub(r"\s*\([^)]*\)\s*", "", step_text).strip()


def parse_tech_chain_text(chain_text: str) -> dict[str, Any]:
    body = chain_text.split(":", 1)[1].strip() if ":" in chain_text else chain_text.strip()
    paths = []
    for match in re.finditer(r"\[([^\]]+)\]", body):
        steps = [parse_step_name(part) for part in match.group(1).split("->")]
        paths.append([step for step in steps if step])
    if not paths and "->" in body:
        parts = [parse_step_name(part) for part in body.split("->")]
        if len(parts) > 1:
            paths = [parts[:-1]]
    target = parse_step_name(body.rsplit("->", 1)[-1])
    return {
        "raw": chain_text,
        "paths": paths,
        "target": target,
        "has_parallel_and": "+" in body and len(paths) > 1,
    }


def tech_chain_contains(chain_text: str, node: str) -> bool:
    wanted = normalize_text(node)
    parsed = parse_tech_chain_text(chain_text)
    for path in parsed["paths"]:
        if any(normalize_text(step) == wanted for step in path):
            return True
    return wanted in normalize_text(chain_text)


def query_tech_tree(
    target: str | None = None,
    broken_node: str | None = None,
    multi_path_min: int | None = None,
    requires_addon: str | None = None,
    sections: list[str] | None = None,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    items = flatten_items(sections=sections, data_path=data_path)
    results = []
    if target:
        matches = search_by_name(target, items=items, mode="exact", limit=limit)
        if not matches:
            matches = search_by_name(target, items=items, mode="fuzzy", limit=limit)
        for item in matches:
            results.append(tech_tree_record(item))
    elif broken_node:
        for item in items:
            matched_chains = [chain for chain in item.get("tech_chain") or [] if tech_chain_contains(chain, broken_node)]
            if matched_chains:
                record = tech_tree_record(item)
                record["matched_chains"] = matched_chains
                record["broken_node"] = broken_node
                results.append(record)
    elif multi_path_min is not None:
        for item in items:
            chains = item.get("tech_chain") or []
            if len(chains) >= multi_path_min:
                results.append(tech_tree_record(item))
    elif requires_addon:
        addon = normalize_text(requires_addon)
        for item in items:
            chains = item.get("tech_chain") or []
            if any(addon in normalize_text(chain) for chain in chains):
                results.append(tech_tree_record(item))
    return {"mode": "tech_tree", "count": len(results[:limit]), "results": results[:limit]}


def tech_tree_record(item: dict[str, Any]) -> dict[str, Any]:
    chains = item.get("tech_chain") or []
    return {
        "_section": item.get("_section"),
        "id": item.get("id"),
        "name": item.get("name"),
        "race": item.get("race"),
        "tech_chain": chains,
        "parsed_tech_chain": [parse_tech_chain_text(chain) for chain in chains],
        "description": first_n(item.get("description") or [], 3),
    }


def query_tactical_profile(
    unit_filters: dict[str, Any] | None = None,
    ability_filters: dict[str, Any] | None = None,
    immediate_cast: bool | None = None,
    transforming_only: bool = False,
    compare_forms: bool = False,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    rows = []
    for row in unit_ability_join(data_path):
        unit = row["unit"]
        ability = row["ability"]
        if not item_matches_simple_filters(unit, unit_filters or {}):
            continue
        if not item_matches_simple_filters(ability, ability_filters or {}):
            continue
        if immediate_cast is not None:
            start_energy = unit.get("start_energy") or 0
            energy_cost = ability.get("energy_cost") or 0
            if (start_energy >= energy_cost) != immediate_cast:
                continue
        rows.append(
            {
                "unit_name": unit.get("name"),
                "unit_id": unit.get("id"),
                "race": unit.get("race"),
                "start_energy": unit.get("start_energy"),
                "max_energy": unit.get("max_energy"),
                "normal_mode": unit.get("normal_mode"),
                "speed": unit.get("speed"),
                "speed_creep_mul": unit.get("speed_creep_mul"),
                "ability_name": ability.get("name"),
                "ability_id": ability.get("id"),
                "energy_cost": ability.get("energy_cost"),
                "cast_range": ability.get("cast_range"),
                "cooldown": ability.get("cooldown"),
                "target": ability.get("target"),
            }
        )

    if transforming_only:
        data = load_data(data_path)
        transforming = [unit for unit in data.get("Unit", []) if unit.get("normal_mode")]
        rows = [form_record(unit, data) for unit in transforming]
        if compare_forms:
            rows = add_form_comparison(rows, data)

    return {"mode": "tactical_profile", "count": len(rows[:limit]), "results": rows[:limit]}


def item_matches_simple_filters(item: dict[str, Any], filters: dict[str, Any]) -> bool:
    for field, condition in filters.items():
        value = get_value(item, field)
        if isinstance(condition, dict):
            op = condition.get("op", "eq")
            expected = condition.get("value")
            if not compare_value(value, op, expected):
                return False
        elif value != condition:
            return False
    return True


def compare_value(value: Any, op: str, expected: Any) -> bool:
    if op == "contains":
        if isinstance(value, list):
            return normalize_text(expected) in {normalize_text(part) for part in value}
        return normalize_text(expected) in normalize_text(value)
    if op == "target_contains":
        return normalize_text(expected) in normalize_text(json.dumps(value, ensure_ascii=False))
    if value is None:
        return False
    if op == "eq":
        return value == expected
    if op == "ne":
        return value != expected
    if op in {"lt", "lte", "gt", "gte"}:
        try:
            left = float(value)
            right = float(expected)
        except (TypeError, ValueError):
            return False
        return {
            "lt": left < right,
            "lte": left <= right,
            "gt": left > right,
            "gte": left >= right,
        }[op]
    return False


def form_record(unit: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": unit.get("name"),
        "id": unit.get("id"),
        "race": unit.get("race"),
        "normal_mode": unit.get("normal_mode"),
        "armor": unit.get("armor"),
        "speed": unit.get("speed"),
        "range": max_weapon_range(unit),
        "is_flying": unit.get("is_flying"),
    }


def add_form_comparison(rows: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    unit_by_id = {unit["id"]: unit for unit in data.get("Unit", [])}
    enriched = []
    for row in rows:
        normal = unit_by_id.get(row.get("normal_mode"))
        item = dict(row)
        if normal:
            item["normal_name"] = normal.get("name")
            item["normal_armor"] = normal.get("armor")
            item["normal_range"] = max_weapon_range(normal)
            item["normal_is_flying"] = normal.get("is_flying")
        enriched.append(item)
    return enriched


def max_weapon_range(unit: dict[str, Any]) -> float | None:
    ranges = [weapon.get("range") for weapon in unit.get("weapons") or [] if isinstance(weapon.get("range"), (int, float))]
    return max(ranges) if ranges else None


def search_descriptions(
    keywords: list[str],
    mode: str = "any",
    sections: list[str] | None = None,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    expanded = expand_keywords(keywords)
    items = flatten_items(sections=sections, data_path=data_path)
    results = []
    for item in items:
        text = " ".join(item.get("description") or [])
        haystack = normalize_text(text)
        hits = [word for word in expanded if normalize_text(word) in haystack]
        if (mode == "all" and len(hits) == len(expanded)) or (mode != "all" and hits):
            results.append(
                {
                    "_section": item.get("_section"),
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "race": item.get("race"),
                    "matched_keywords": sorted(set(hits)),
                    "description": first_n(item.get("description") or [], 4),
                    "tech_chain": first_n(item.get("tech_chain") or [], 2),
                }
            )
    return {"mode": "semantic_search", "keywords": expanded, "count": len(results[:limit]), "results": results[:limit]}


def expand_keywords(keywords: list[str]) -> list[str]:
    expanded: list[str] = []
    for keyword in keywords:
        key = keyword.lower().strip()
        expanded.extend(TEXT_EXPANSIONS.get(key, [keyword]))
    return sorted(set(word for word in expanded if word))


def strategic_join_analysis(
    analysis_type: str,
    filters: dict[str, Any] | None = None,
    top_n: int = 10,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    filters = filters or {}
    if analysis_type == "cost_efficiency":
        items = combined_search(sections=["Unit"], tag_filters=filters.get("tag_filters"), numeric_ranges=filters.get("numeric_ranges"))
        rows = []
        for item in items:
            minerals = item.get("minerals")
            if not isinstance(minerals, (int, float)) or minerals <= 0:
                continue
            rows.append(
                {
                    "name": item.get("name"),
                    "race": item.get("race"),
                    "max_health": item.get("max_health"),
                    "minerals": minerals,
                    "armor": item.get("armor"),
                    "attributes": item.get("attributes"),
                    "health_per_mineral": round((item.get("max_health") or 0) / minerals, 3),
                }
            )
        rows.sort(key=lambda row: row["health_per_mineral"], reverse=True)
        return {"mode": "strategic_join_analysis", "analysis_type": analysis_type, "count": len(rows[:top_n]), "results": rows[:top_n]}

    if analysis_type == "addon_dependencies":
        items = flatten_items(data_path=data_path)
        rows = []
        for item in items:
            chains = item.get("tech_chain") or []
            addons = sorted({addon for addon in ADDON_NAMES if any(addon in normalize_text(chain) for chain in chains)})
            if addons:
                rows.append(
                    {
                        "_section": item.get("_section"),
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "race": item.get("race"),
                        "required_addons": addons,
                        "tech_chain": chains,
                    }
                )
        return {"mode": "strategic_join_analysis", "analysis_type": analysis_type, "count": len(rows[:top_n]), "results": rows[:top_n]}

    if analysis_type == "spell_target_check":
        ability_id = filters.get("ability_id")
        unit_name = filters.get("unit_name")
        data = load_data(data_path)
        ability = next((item for item in data.get("Ability", []) if item.get("id") == ability_id), None)
        unit = next((item for item in data.get("Unit", []) if normalize_text(item.get("name")) == normalize_text(unit_name)), None)
        return {
            "mode": "strategic_join_analysis",
            "analysis_type": analysis_type,
            "ability": ability,
            "unit": unit,
            "assessment": assess_target_compatibility(ability, unit),
        }

    raise ValueError(f"Unsupported analysis_type: {analysis_type}")


def assess_target_compatibility(ability: dict[str, Any] | None, unit: dict[str, Any] | None) -> str:
    if not ability or not unit:
        return "Insufficient data."
    target = ability.get("target")
    if target in ("Unit", "PointOrUnit"):
        return "The ability can target units in general; detailed validator data is not available in this dataset."
    if isinstance(target, dict):
        return "The ability has structured production/research target data rather than a direct combat target validator."
    return f"The ability target type is {target!r}; direct compatibility cannot be proven from this dataset."


def run_query_ir(query_ir: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    results = combined_search(
        name_query=query_ir.get("name_query"),
        name_mode=query_ir.get("name_mode", "contains"),
        numeric_ranges=query_ir.get("numeric_ranges"),
        tag_filters=query_ir.get("tag_filters"),
        combat_filters=query_ir.get("combat_filters"),
        sections=query_ir.get("sections"),
        keys=None,
        limit=query_ir.get("limit", 50),
        data_path=data_path,
    )
    sort_specs = query_ir.get("sort") or []
    for spec in reversed(sort_specs):
        field = spec.get("field")
        reverse = spec.get("order", "asc") == "desc"
        if field:
            results.sort(key=lambda item: safe_sort_value(get_value(item, field)), reverse=reverse)
    return {"mode": "query_ir", "count": len(results), "results": apply_projection(results, query_ir.get("return_keys"))}


def safe_sort_value(value: Any) -> Any:
    if value is None:
        return -math.inf
    return value


def execute_tool(tool_name: str, arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    if tool_name == "run_query_ir":
        return run_query_ir(arguments, data_path=data_path)
    if tool_name == "filter_attributes_and_resources":
        return run_query_ir(arguments, data_path=data_path)
    if tool_name == "query_tech_tree":
        return query_tech_tree(data_path=data_path, **arguments)
    if tool_name == "query_tactical_profile":
        return query_tactical_profile(data_path=data_path, **arguments)
    if tool_name == "search_descriptions":
        return search_descriptions(data_path=data_path, **arguments)
    if tool_name == "strategic_join_analysis":
        return strategic_join_analysis(data_path=data_path, **arguments)
    raise ValueError(f"Unknown tool: {tool_name}")


def first_n(values: list[Any], n: int) -> list[Any]:
    return values[:n]
