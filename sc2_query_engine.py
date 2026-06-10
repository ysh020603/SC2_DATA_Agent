#!/usr/bin/env python3
"""Higher-level SC2 query engine for Agent use."""

from __future__ import annotations

import json
import math
import re
import inspect
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

ENTITY_ALIASES = {
    "\u5175\u8425": "Barracks",
    "\u91cd\u5de5\u5382": "Factory",
    "\u5de5\u5382": "Factory",
    "\u661f\u6e2f": "Starport",
    "\u673a\u573a": "Starport",
    "\u6307\u6325\u4e2d\u5fc3": "CommandCenter",
    "\u5e7d\u7075\u519b\u6821": "GhostAcademy",
    "\u5de5\u7a0b\u7ad9": "EngineeringBay",
    "\u519b\u68b0\u5e93": "Armory",
    "\u79d1\u6280\u5b9e\u9a8c\u5ba4": "TechLab",
    "\u53cd\u5e94\u5806": "Reactor",
    "\u673a\u67aa\u5175": "Marine",
    "\u6d77\u9646": "Marauder",
    "\u52ab\u63a0\u8005": "Reaper",
    "\u5e7d\u7075": "Ghost",
    "\u5766\u514b": "SiegeTank",
    "\u96f7\u795e": "Thor",
    "\u533b\u7597\u8fd0\u8f93\u673a": "Medivac",
    "\u5973\u5996": "Banshee",
    "\u89e3\u653e\u8005": "Liberator",
    "\u6218\u5217\u5de1\u822a\u8230": "Battlecruiser",
    "\u5927\u548c\u6218\u8230": "Battlecruiser",
}

PRODUCTION_TARGET_TYPES = {"Train", "TrainPlace", "Build", "BuildInstant", "BuildOnUnit", "Morph", "MorphPlace"}
OUTPUT_TARGET_TYPES = PRODUCTION_TARGET_TYPES | {"Research"}


def all_items(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    return flatten_items(data_path=data_path)


def entity_indexes(data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, dict[str, dict[str, Any]]]:
    data = load_data(data_path)
    indexes: dict[str, dict[str, dict[str, Any]]] = {}
    for section in ("Ability", "Unit", "Upgrade"):
        indexes[section] = {normalize_text(item.get("name")): item for item in data.get(section, []) if item.get("name")}
    return indexes


def resolve_entity_key(
    mention: str,
    expected_section: str | None = None,
    sections: list[str] | None = None,
    race: str | None = None,
    limit: int = 5,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    """Resolve a user-facing mention to canonical database keys."""
    wanted_sections = sections or ([expected_section] if expected_section else ["Unit", "Ability", "Upgrade"])
    alias = ENTITY_ALIASES.get(mention.strip(), mention)
    items = flatten_items(sections=wanted_sections, data_path=data_path)
    if race:
        items = [item for item in items if normalize_text(item.get("race", "")) == normalize_text(race)]

    exact = [item for item in items if normalize_text(item.get("name")) == normalize_text(alias)]
    if not exact and alias != mention:
        exact = [item for item in items if normalize_text(item.get("name")) == normalize_text(mention)]
    matches = exact or search_by_name(alias, items=items, mode="fuzzy", limit=limit)
    candidates = [
        {
            "section": item.get("_section"),
            "name": item.get("name"),
            "race": item.get("race"),
        }
        for item in matches[:limit]
    ]
    best = candidates[0] if candidates else None
    return {
        "mode": "entity_key_resolution",
        "mention": mention,
        "normalized_mention": alias,
        "resolved": best,
        "confidence": 1.0 if exact else (0.65 if best else 0.0),
        "candidates": candidates,
    }


def get_entity(
    section: str,
    name: str,
    keys: list[str] | None = None,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    indexes = entity_indexes(data_path)
    item = indexes.get(section, {}).get(normalize_text(name))
    if not item:
        resolved = resolve_entity_key(name, expected_section=section, data_path=data_path)
        candidate = resolved.get("resolved") or {}
        item = indexes.get(candidate.get("section", ""), {}).get(normalize_text(candidate.get("name")))
    if not item:
        return {"mode": "get_entity", "count": 0, "results": []}
    row = dict(item)
    row["_section"] = section
    return {"mode": "get_entity", "count": 1, "results": [project_entity(row, keys)]}


def project_entity(item: dict[str, Any], keys: list[str] | None = None) -> dict[str, Any]:
    return apply_projection([item], keys)[0] if keys else item


def unit_ability_join(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    data = load_data(data_path)
    ability_by_name = {normalize_text(item.get("name")): item for item in data.get("Ability", [])}
    ability_by_id = {item.get("id"): item for item in data.get("Ability", []) if item.get("id") is not None}
    rows: list[dict[str, Any]] = []
    for unit in data.get("Unit", []):
        for ability_ref in unit.get("abilities") or []:
            ability_name = ability_ref.get("ability_name")
            ability = ability_by_name.get(normalize_text(ability_name)) if ability_name else None
            if not ability:
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
        "name": item.get("name"),
        "race": item.get("race"),
        "tech_chain": chains,
        "parsed_tech_chain": [parse_tech_chain_text(chain) for chain in chains],
        "description": first_n(item.get("description") or [], 3),
    }


def extract_produces(target: Any, target_types: set[str] | None = None) -> list[dict[str, Any]]:
    target_types = target_types or PRODUCTION_TARGET_TYPES
    if not isinstance(target, dict):
        return []
    produced = []
    for target_type, payload in target.items():
        if target_type not in target_types or not isinstance(payload, dict):
            continue
        if payload.get("produces_name"):
            produced.append({"target_type": target_type, "section": "Unit", "name": payload.get("produces_name")})
        if payload.get("upgrade_name"):
            produced.append({"target_type": target_type, "section": "Upgrade", "name": payload.get("upgrade_name")})
    return produced


def requirement_summary(ability_ref: dict[str, Any]) -> list[dict[str, Any]]:
    requirements = []
    for requirement in ability_ref.get("requirements") or []:
        requirements.append(
            {
                key: value
                for key, value in requirement.items()
                if key.endswith("_name") or key in {"addon_name", "building_name", "upgrade_name"}
            }
        )
    return requirements


def requirement_matches(requirements: list[dict[str, Any]], field: str, value: str) -> bool:
    wanted = normalize_text(value)
    return any(normalize_text(requirement.get(field, "")) == wanted for requirement in requirements)


def has_addon_requirement(requirements: list[dict[str, Any]], addon_name: str | None = None) -> bool:
    if addon_name is None:
        return any(requirement.get("addon_name") or requirement.get("addon_to_name") for requirement in requirements)
    wanted = normalize_text(addon_name)
    return any(
        normalize_text(requirement.get("addon_name", "")) == wanted
        or normalize_text(requirement.get("addon_to_name", "")) == wanted
        for requirement in requirements
    )


def get_addon_requirement(requirements: list[dict[str, Any]]) -> str | None:
    for requirement in requirements:
        addon = requirement.get("addon_name") or requirement.get("addon_to_name")
        if addon:
            return addon
    return None


def requirements_pass(
    requirements: list[dict[str, Any]],
    required_addon: str | None = None,
    excluded_addon: str | None = None,
    require_no_addon: bool = False,
    required_building: str | None = None,
    required_upgrade: str | None = None,
) -> bool:
    if required_addon and not has_addon_requirement(requirements, required_addon):
        return False
    if excluded_addon and has_addon_requirement(requirements, excluded_addon):
        return False
    if require_no_addon and has_addon_requirement(requirements):
        return False
    if required_building and not requirement_matches(requirements, "building_name", required_building):
        return False
    if required_upgrade and not requirement_matches(requirements, "upgrade_name", required_upgrade):
        return False
    return True


def production_edges(data_path: str | Path = DEFAULT_DATA_PATH) -> list[dict[str, Any]]:
    indexes = entity_indexes(data_path)
    ability_index = indexes.get("Ability", {})
    edges = []
    for producer in load_data(data_path).get("Unit", []):
        for ability_ref in producer.get("abilities") or []:
            ability = ability_index.get(normalize_text(ability_ref.get("ability_name")))
            if not ability:
                continue
            requirements = requirement_summary(ability_ref)
            for produced in extract_produces(ability.get("target"), OUTPUT_TARGET_TYPES):
                produced_item = indexes.get(produced["section"], {}).get(normalize_text(produced["name"]))
                if not produced_item:
                    continue
                edges.append(
                    {
                        "producer": producer,
                        "ability_ref": ability_ref,
                        "ability": ability,
                        "requirements": requirements,
                        "required_addon": get_addon_requirement(requirements),
                        "target_type": produced["target_type"],
                        "produced_section": produced["section"],
                        "produced_name": produced["name"],
                        "produced_item": produced_item,
                    }
                )
    return edges


def row_max_weapon_range(unit: dict[str, Any]) -> float | None:
    return max_weapon_range(unit)


def can_attack(unit: dict[str, Any], target: str) -> bool:
    wanted = normalize_text(target)
    for weapon in unit.get("weapons") or []:
        weapon_target = normalize_text(weapon.get("target_type", ""))
        if wanted == "air" and weapon_target in {"air", "any"}:
            return True
        if wanted == "ground" and weapon_target in {"ground", "any"}:
            return True
    return False


def query_production_outputs(
    producer_name: str,
    producer_section: str = "Unit",
    output_sections: list[str] | None = None,
    target_types: list[str] | None = None,
    return_keys: list[str] | None = None,
    required_addon: str | None = None,
    excluded_addon: str | None = None,
    require_no_addon: bool = False,
    required_building: str | None = None,
    required_upgrade: str | None = None,
    include_requirements: bool = True,
    include_ability: bool = True,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    """Return records produced by a Unit through its ability list."""
    indexes = entity_indexes(data_path)
    resolved = resolve_entity_key(producer_name, expected_section=producer_section, data_path=data_path)
    producer_info = resolved.get("resolved") or {}
    producer = indexes.get(producer_info.get("section") or producer_section, {}).get(normalize_text(producer_info.get("name") or producer_name))
    if not producer:
        return {"mode": "production_outputs", "producer": producer_name, "count": 0, "results": [], "resolution": resolved}

    output_filter = set(output_sections or ["Unit"])
    default_target_types = ["Research"] if output_filter == {"Upgrade"} else ["Train"]
    if not target_types and normalize_text(producer.get("name")) == "larva":
        default_target_types = ["Train", "Morph"]
    target_type_filter = set(target_types or default_target_types)
    ability_index = indexes.get("Ability", {})
    rows = []
    seen = set()
    for ability_ref in producer.get("abilities") or []:
        requirements = requirement_summary(ability_ref)
        if not requirements_pass(
            requirements,
            required_addon=required_addon,
            excluded_addon=excluded_addon,
            require_no_addon=require_no_addon,
            required_building=required_building,
            required_upgrade=required_upgrade,
        ):
            continue
        ability_name = ability_ref.get("ability_name")
        ability = ability_index.get(normalize_text(ability_name))
        if not ability:
            continue
        for produced in extract_produces(ability.get("target"), target_type_filter):
            if produced["section"] not in output_filter:
                continue
            produced_item = indexes.get(produced["section"], {}).get(normalize_text(produced["name"]))
            if not produced_item:
                continue
            dedupe_key = (produced["section"], produced["name"], ability.get("name"))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            projected = project_entity(dict(produced_item), return_keys)
            row = {
                "producer_name": producer.get("name"),
                "producer_section": producer_info.get("section") or producer_section,
                "target_type": produced["target_type"],
                "produced_section": produced["section"],
                "produced": projected,
            }
            if include_ability:
                row["ability"] = {
                    "name": ability.get("name"),
                    "target": ability.get("target"),
                }
            if include_requirements:
                row["requirements"] = requirements
                row["required_addon"] = get_addon_requirement(requirements)
            rows.append(row)
            if len(rows) >= limit:
                break
        if len(rows) >= limit:
            break

    return {
        "mode": "production_outputs",
        "producer": {"section": producer_info.get("section") or producer_section, "name": producer.get("name"), "race": producer.get("race")},
        "count": len(rows),
        "results": rows,
        "resolution": resolved,
    }


def query_reverse_production_sources(
    produced_name: str,
    produced_section: str = "Unit",
    producer_race: str | None = None,
    target_types: list[str] | None = None,
    return_keys: list[str] | None = None,
    required_addon: str | None = None,
    excluded_addon: str | None = None,
    require_no_addon: bool = False,
    include_requirements: bool = True,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    """Return producers whose abilities create the requested Unit or Upgrade."""
    indexes = entity_indexes(data_path)
    resolved = resolve_entity_key(produced_name, expected_section=produced_section, data_path=data_path)
    produced_info = resolved.get("resolved") or {}
    target_name = produced_info.get("name") or produced_name
    target_type_filter = set(target_types or list(OUTPUT_TARGET_TYPES))
    output_filter = {produced_info.get("section") or produced_section}
    rows = []

    for edge in production_edges(data_path):
        producer = edge["producer"]
        if producer_race and normalize_text(producer.get("race", "")) != normalize_text(producer_race):
            continue
        requirements = edge["requirements"]
        if not requirements_pass(
            requirements,
            required_addon=required_addon,
            excluded_addon=excluded_addon,
            require_no_addon=require_no_addon,
        ):
            continue
        if edge["target_type"] not in target_type_filter:
            continue
        if edge["produced_section"] not in output_filter:
            continue
        if normalize_text(edge["produced_name"]) != normalize_text(target_name):
            continue
        producer_row = dict(producer)
        producer_row["_section"] = "Unit"
        row = {
            "produced": {"section": edge["produced_section"], "name": target_name},
            "producer": project_entity(producer_row, return_keys),
            "target_type": edge["target_type"],
            "ability": {"name": edge["ability"].get("name"), "target": edge["ability"].get("target")},
        }
        if include_requirements:
            row["requirements"] = requirements
            row["required_addon"] = edge["required_addon"]
        rows.append(row)
        if len(rows) >= limit:
            return {
                "mode": "reverse_production_sources",
                "produced": produced_info or {"section": produced_section, "name": produced_name},
                "count": len(rows),
                "results": rows,
                "resolution": resolved,
            }

    return {
        "mode": "reverse_production_sources",
        "produced": produced_info or {"section": produced_section, "name": produced_name},
        "count": len(rows),
        "results": rows,
        "resolution": resolved,
    }


def query_addon_branches(
    producer_name: str,
    return_keys: list[str] | None = None,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    branches = {
        "no_addon_required": query_production_outputs(
            producer_name,
            require_no_addon=True,
            return_keys=return_keys,
            limit=limit,
            data_path=data_path,
        ).get("results", []),
        "techlab_required": query_production_outputs(
            producer_name,
            required_addon="TechLab",
            return_keys=return_keys,
            limit=limit,
            data_path=data_path,
        ).get("results", []),
        "reactor_required": query_production_outputs(
            producer_name,
            required_addon="Reactor",
            return_keys=return_keys,
            limit=limit,
            data_path=data_path,
        ).get("results", []),
    }
    reactor_compatible = []
    for row in branches["no_addon_required"]:
        if row.get("target_type") == "Train":
            item = dict(row)
            item["reactor_compatible"] = True
            reactor_compatible.append(item)
    branches["reactor_compatible"] = reactor_compatible
    count = sum(len(rows) for rows in branches.values())
    return {"mode": "addon_branches", "producer_name": producer_name, "count": count, "results": branches}


def query_addon_producers(
    race: str | None = None,
    return_keys: list[str] | None = None,
    limit: int = 50,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    rows = []
    for unit in load_data(data_path).get("Unit", []):
        if not unit.get("accepts_addon"):
            continue
        if race and normalize_text(unit.get("race", "")) != normalize_text(race):
            continue
        branches = query_addon_branches(unit.get("name"), return_keys=return_keys, limit=100, data_path=data_path)
        rows.append(
            {
                "producer": {"name": unit.get("name"), "race": unit.get("race")},
                "accepts_addon": True,
                "branches": branches.get("results"),
            }
        )
        if len(rows) >= limit:
            break
    return {"mode": "addon_producers", "count": len(rows), "results": rows}


def query_research_outputs(
    producer_name: str | None = None,
    race: str | None = None,
    required_addon: str | None = None,
    return_keys: list[str] | None = None,
    include_requirements: bool = True,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    indexes = entity_indexes(data_path)
    ability_index = indexes.get("Ability", {})
    upgrade_index = indexes.get("Upgrade", {})
    producers = load_data(data_path).get("Unit", [])
    if producer_name:
        resolved = resolve_entity_key(producer_name, expected_section="Unit", data_path=data_path)
        resolved_name = (resolved.get("resolved") or {}).get("name")
        producers = [producer for producer in producers if normalize_text(producer.get("name")) == normalize_text(resolved_name or producer_name)]
    if race:
        producers = [producer for producer in producers if normalize_text(producer.get("race", "")) == normalize_text(race)]

    rows = []
    for producer in producers:
        for ability_ref in producer.get("abilities") or []:
            requirements = requirement_summary(ability_ref)
            producer_is_required_addon = required_addon and normalize_text(required_addon) in normalize_text(producer.get("name", ""))
            if required_addon and not producer_is_required_addon and not has_addon_requirement(requirements, required_addon):
                continue
            ability = ability_index.get(normalize_text(ability_ref.get("ability_name")))
            if not ability:
                continue
            for produced in extract_produces(ability.get("target"), {"Research"}):
                upgrade = upgrade_index.get(normalize_text(produced["name"]))
                if not upgrade:
                    continue
                row = {
                    "producer": {"name": producer.get("name"), "race": producer.get("race")},
                    "upgrade": project_entity(dict(upgrade), return_keys),
                    "ability": {"name": ability.get("name"), "target": ability.get("target")},
                }
                if include_requirements:
                    row["requirements"] = requirements
                    row["required_addon"] = get_addon_requirement(requirements)
                rows.append(row)
                if len(rows) >= limit:
                    return {"mode": "research_outputs", "count": len(rows), "results": rows}
    return {"mode": "research_outputs", "count": len(rows), "results": rows}


def query_unit_abilities(
    unit_name: str | None = None,
    race: str | None = None,
    only_energy: bool = False,
    include_passive_commands: bool = False,
    ability_return_keys: list[str] | None = None,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    rows = []
    resolved_unit_name = None
    if unit_name:
        resolved_unit_name = (resolve_entity_key(unit_name, "Unit", data_path=data_path).get("resolved") or {}).get("name") or unit_name
    for row in unit_ability_join(data_path):
        unit = row["unit"]
        ability = row["ability"]
        if resolved_unit_name and normalize_text(unit.get("name")) != normalize_text(resolved_unit_name):
            continue
        if race and normalize_text(unit.get("race", "")) != normalize_text(race):
            continue
        unit_has_energy_pool = isinstance(unit.get("max_energy"), (int, float)) or isinstance(unit.get("start_energy"), (int, float))
        ability_has_energy_cost = isinstance(ability.get("energy_cost"), (int, float)) and ability.get("energy_cost", 0) > 0
        if only_energy and not (ability_has_energy_cost or unit_has_energy_pool):
            continue
        if not include_passive_commands and normalize_text(ability.get("name", "")) in {"smart", "stopstop", "movemove", "patrolpatrol", "holdpositionhold", "attackattack"}:
            continue
        energy_cost = ability.get("energy_cost") or 0
        start_energy = unit.get("start_energy") or 0
        rows.append(
            {
                "unit": {
                    "name": unit.get("name"),
                    "race": unit.get("race"),
                    "start_energy": unit.get("start_energy"),
                    "max_energy": unit.get("max_energy"),
                },
                "ability": project_entity(dict(ability), ability_return_keys)
                if ability_return_keys
                else {
                    "name": ability.get("name"),
                    "energy_cost": ability.get("energy_cost"),
                    "cast_range": ability.get("cast_range"),
                    "cooldown": ability.get("cooldown"),
                    "target": ability.get("target"),
                },
                "requirements": requirement_summary(row["ability_ref"]),
                "can_cast_immediately": bool(start_energy >= energy_cost) if energy_cost else None,
            }
        )
        if len(rows) >= limit:
            break
    return {"mode": "unit_abilities", "count": len(rows), "results": rows}


def query_dependency_impact(
    node_name: str,
    sections: list[str] | None = None,
    race: str | None = None,
    include_requirements: bool = True,
    include_tech_chain: bool = True,
    limit: int = 200,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    resolved = resolve_entity_key(node_name, sections=["Unit", "Upgrade"], data_path=data_path)
    node = (resolved.get("resolved") or {}).get("name") or node_name
    wanted_sections = sections or ["Unit", "Ability", "Upgrade"]
    rows = []
    for item in flatten_items(sections=wanted_sections, data_path=data_path):
        if race and item.get("race") and normalize_text(item.get("race")) != normalize_text(race):
            continue
        matched_chains = [chain for chain in item.get("tech_chain") or [] if tech_chain_contains(chain, node)]
        matched_requirements = []
        if include_requirements and item.get("_section") == "Unit":
            for ability_ref in item.get("abilities") or []:
                for requirement in requirement_summary(ability_ref):
                    if any(normalize_text(value) == normalize_text(node) for value in requirement.values()):
                        matched_requirements.append({"ability_name": ability_ref.get("ability_name"), "requirement": requirement})
        if not matched_chains and not matched_requirements:
            continue
        row = {
            "_section": item.get("_section"),
            "name": item.get("name"),
            "race": item.get("race"),
            "matched_requirements": matched_requirements,
        }
        if include_tech_chain:
            row["matched_chains"] = matched_chains
        rows.append(row)
        if len(rows) >= limit:
            break
    return {"mode": "dependency_impact", "node": node, "count": len(rows), "results": rows, "resolution": resolved}


def extract_names_from_descriptions(item: dict[str, Any], unit_names: set[str]) -> list[str]:
    text = " ".join(item.get("description") or [])
    normalized_text = normalize_text(text)
    return sorted(name for name in unit_names if normalize_text(name) in normalized_text)


def query_upgrade_effects(
    upgrade_name: str | None = None,
    research_producer_name: str | None = None,
    race: str | None = None,
    include_sources: bool = True,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    data = load_data(data_path)
    unit_by_name = {unit.get("name"): unit for unit in data.get("Unit", []) if unit.get("name")}
    unit_names = set(unit_by_name)
    upgrades = data.get("Upgrade", [])
    if upgrade_name:
        resolved = resolve_entity_key(upgrade_name, expected_section="Upgrade", data_path=data_path)
        resolved_name = (resolved.get("resolved") or {}).get("name") or upgrade_name
        upgrades = [upgrade for upgrade in upgrades if normalize_text(upgrade.get("name")) == normalize_text(resolved_name)]
    if research_producer_name:
        research_rows = query_research_outputs(research_producer_name, race=race, limit=500, data_path=data_path).get("results", [])
        names = {row.get("upgrade", {}).get("name") for row in research_rows}
        upgrades = [upgrade for upgrade in upgrades if upgrade.get("name") in names]

    rows = []
    for upgrade in upgrades:
        affected_names = extract_names_from_descriptions(upgrade, unit_names)
        affected = []
        for name in affected_names:
            unit = unit_by_name[name]
            if race and normalize_text(unit.get("race", "")) != normalize_text(race):
                continue
            item = {
                "name": unit.get("name"),
                "race": unit.get("race"),
                "minerals": unit.get("minerals"),
                "gas": unit.get("gas"),
                "supply": unit.get("supply"),
                "attributes": unit.get("attributes"),
            }
            if include_sources:
                item["production_sources"] = query_reverse_production_sources(name, producer_race=race, return_keys=["name", "race"], limit=10, data_path=data_path).get("results", [])
            affected.append(item)
        if affected:
            rows.append(
                {
                    "upgrade": {
                        "name": upgrade.get("name"),
                        "cost": upgrade.get("cost"),
                        "description": upgrade.get("description"),
                    },
                    "affected_units": affected,
                }
            )
        if len(rows) >= limit:
            break
    return {"mode": "upgrade_effects", "count": len(rows), "results": rows}


def query_gas_units_with_sources(
    race: str | None = None,
    min_gas: float = 0,
    include_tech_chain: bool = True,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    rows = []
    sources_by_name: dict[str, list[dict[str, Any]]] = {}
    for edge in production_edges(data_path):
        producer = edge["producer"]
        if race and normalize_text(producer.get("race", "")) != normalize_text(race):
            continue
        if edge["produced_section"] != "Unit":
            continue
        producer_row = dict(producer)
        producer_row["_section"] = "Unit"
        sources_by_name.setdefault(normalize_text(edge["produced_name"]), []).append(
            {
                "produced": {"section": "Unit", "name": edge["produced_name"]},
                "producer": project_entity(producer_row, ["name", "race"]),
                "target_type": edge["target_type"],
                "ability": {"name": edge["ability"].get("name"), "target": edge["ability"].get("target")},
                "requirements": edge["requirements"],
                "required_addon": edge["required_addon"],
            }
        )
    for unit in load_data(data_path).get("Unit", []):
        gas = unit.get("gas")
        if not isinstance(gas, (int, float)) or gas <= min_gas:
            continue
        if race and normalize_text(unit.get("race", "")) != normalize_text(race):
            continue
        row = {
            "unit": {
                "name": unit.get("name"),
                "race": unit.get("race"),
                "minerals": unit.get("minerals"),
                "gas": unit.get("gas"),
                "supply": unit.get("supply"),
                "time": unit.get("time"),
            },
            "production_sources": sources_by_name.get(normalize_text(unit.get("name")), []),
        }
        if include_tech_chain:
            row["tech_chain"] = unit.get("tech_chain") or []
        rows.append(row)
        if len(rows) >= limit:
            break
    return {"mode": "gas_units_with_sources", "count": len(rows), "results": rows}


def query_combat_production_options(
    producer_name: str | None = None,
    race: str | None = None,
    can_attack_air: bool | None = None,
    require_no_addon: bool = False,
    required_addon: str | None = None,
    sort_by: str | None = None,
    limit: int = 100,
    data_path: str | Path = DEFAULT_DATA_PATH,
) -> dict[str, Any]:
    rows = []
    resolved_producer = None
    if producer_name:
        resolved_producer = (resolve_entity_key(producer_name, expected_section="Unit", data_path=data_path).get("resolved") or {}).get("name") or producer_name
    seen = set()
    for edge in production_edges(data_path):
        producer = edge["producer"]
        produced = edge["produced_item"]
        if edge["target_type"] != "Train" or edge["produced_section"] != "Unit":
            continue
        if resolved_producer and normalize_text(producer.get("name")) != normalize_text(resolved_producer):
            continue
        if required_addon and not has_addon_requirement(edge["requirements"], required_addon):
            continue
        if require_no_addon and has_addon_requirement(edge["requirements"]):
            continue
        if race and normalize_text(produced.get("race", "")) != normalize_text(race):
            continue
        if can_attack_air is not None and can_attack(produced, "Air") != can_attack_air:
            continue
        dedupe_key = (producer.get("name"), produced.get("name"), edge["ability"].get("name"))
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        item = {
            "producer_name": producer.get("name"),
            "name": produced.get("name"),
            "race": produced.get("race"),
            "minerals": produced.get("minerals"),
            "gas": produced.get("gas"),
            "supply": produced.get("supply"),
            "time": produced.get("time"),
            "range": row_max_weapon_range(produced),
            "can_attack_air": can_attack(produced, "Air"),
            "required_addon": edge["required_addon"],
            "requirements": edge["requirements"],
        }
        rows.append(item)
    if sort_by:
        rows.sort(key=lambda item: safe_sort_value(item.get(sort_by)))
    return {"mode": "combat_production_options", "count": len(rows[:limit]), "results": rows[:limit]}


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
                "race": unit.get("race"),
                "start_energy": unit.get("start_energy"),
                "max_energy": unit.get("max_energy"),
                "normal_mode_name": unit.get("normal_mode_name"),
                "speed": unit.get("speed"),
                "speed_creep_mul": unit.get("speed_creep_mul"),
                "ability_name": ability.get("name"),
                "energy_cost": ability.get("energy_cost"),
                "cast_range": ability.get("cast_range"),
                "cooldown": ability.get("cooldown"),
                "target": ability.get("target"),
            }
        )

    if transforming_only:
        data = load_data(data_path)
        transforming = [unit for unit in data.get("Unit", []) if unit.get("normal_mode_name") or unit.get("normal_mode")]
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
        "race": unit.get("race"),
        "normal_mode_name": unit.get("normal_mode_name"),
        "armor": unit.get("armor"),
        "speed": unit.get("speed"),
        "range": max_weapon_range(unit),
        "is_flying": unit.get("is_flying"),
    }


def add_form_comparison(rows: list[dict[str, Any]], data: dict[str, Any]) -> list[dict[str, Any]]:
    unit_by_name = {normalize_text(unit.get("name")): unit for unit in data.get("Unit", [])}
    unit_by_id = {unit.get("id"): unit for unit in data.get("Unit", []) if unit.get("id") is not None}
    enriched = []
    for row in rows:
        normal_name = row.get("normal_mode_name")
        normal = unit_by_name.get(normalize_text(normal_name)) if normal_name else None
        if not normal:
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
                        "name": item.get("name"),
                        "race": item.get("race"),
                        "required_addons": addons,
                        "tech_chain": chains,
                    }
                )
        return {"mode": "strategic_join_analysis", "analysis_type": analysis_type, "count": len(rows[:top_n]), "results": rows[:top_n]}

    if analysis_type == "spell_target_check":
        ability_name = filters.get("ability_name")
        ability_id = filters.get("ability_id")
        unit_name = filters.get("unit_name")
        data = load_data(data_path)
        ability = next(
            (item for item in data.get("Ability", []) if normalize_text(item.get("name")) == normalize_text(ability_name)),
            None,
        )
        if ability is None and ability_id is not None:
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


def _build_relations_index(data):
    by_subject = {}
    by_object = {}
    for entity_type, entities in data.items():
        for entity in entities:
            for rel in entity.get("relations", []):
                relation = rel.get("relation", "")
                subj = rel.get("subject_name", "")
                obj = rel.get("object_name", "")
                desc = rel.get("description", "")
                key_s = (relation, subj)
                if key_s not in by_subject:
                    by_subject[key_s] = []
                by_subject[key_s].append({"object_type": entity_type, "object_name": obj, "description": desc})
                key_o = (relation, obj)
                if key_o not in by_object:
                    by_object[key_o] = []
                by_object[key_o].append({"subject_type": entity_type, "subject_name": subj, "description": desc})
    for k in list(by_subject):
        seen = set()
        deduped = []
        for item in by_subject[k]:
            sig = (item["object_type"], item["object_name"], item["description"])
            if sig not in seen:
                seen.add(sig)
                deduped.append(item)
        by_subject[k] = deduped
    for k in list(by_object):
        seen = set()
        deduped = []
        for item in by_object[k]:
            sig = (item["subject_type"], item["subject_name"], item["description"])
            if sig not in seen:
                seen.add(sig)
                deduped.append(item)
        by_object[k] = deduped
    return {"by_subject": by_subject, "by_object": by_object}


def _query_relation(data, relation_names, entity_name, direction="both"):
    idx = _build_relations_index(data)
    results = []
    for rel_name in relation_names:
        if direction in ("forward", "both"):
            for item in idx["by_subject"].get((rel_name, entity_name), []):
                results.append({
                    "subject_name": entity_name, "relation": rel_name,
                    "object_type": item["object_type"], "object_name": item["object_name"],
                    "description": item["description"], "direction": "forward"
                })
        if direction in ("reverse", "both"):
            for item in idx["by_object"].get((rel_name, entity_name), []):
                results.append({
                    "subject_type": item["subject_type"], "subject_name": item["subject_name"],
                    "relation": rel_name, "object_name": entity_name,
                    "description": item["description"], "direction": "reverse"
                })
    return {"count": len(results), "results": results}


def query_counter_relations(entity_name, counter_type="all", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    relations = []
    if counter_type in ("hard", "all"):
        relations.append("hard_counters")
    if counter_type in ("soft", "all"):
        relations.append("soft_counters")
    return _query_relation(data, relations, entity_name, direction="both")

def query_combat_synergy(entity_name, direction="both", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    return _query_relation(data, ["synergizes_with"], entity_name, direction=direction)

def query_garrison_relations(entity_name, direction="both", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    return _query_relation(data, ["garrisons_in"], entity_name, direction=direction)

def query_stat_bonuses(entity_name, direction="both", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    return _query_relation(data, ["grants_stat_bonus"], entity_name, direction=direction)

def query_ability_unlocks(entity_name, direction="both", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    return _query_relation(data, ["unlocks_unit_ability"], entity_name, direction=direction)

def query_morph_enablers(entity_name, direction="both", data_path=None):
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    data = load_data(data_path)
    return _query_relation(data, ["enables_morph"], entity_name, direction=direction)



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


def call_query_function(func: Any, arguments: dict[str, Any], data_path: str | Path) -> dict[str, Any]:
    signature = inspect.signature(func)
    accepts_var_kwargs = any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values())
    if accepts_var_kwargs:
        filtered_arguments = dict(arguments)
    else:
        allowed = {
            name
            for name, param in signature.parameters.items()
            if param.kind in {inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY}
        }
        filtered_arguments = {key: value for key, value in arguments.items() if key in allowed}
    return func(data_path=data_path, **filtered_arguments)


def execute_tool(tool_name: str, arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    if tool_name == "resolve_entity_key":
        return call_query_function(resolve_entity_key, arguments, data_path)
    if tool_name == "get_entity":
        return call_query_function(get_entity, arguments, data_path)
    if tool_name == "run_query_ir":
        return run_query_ir(arguments, data_path=data_path)
    if tool_name == "filter_attributes_and_resources":
        return run_query_ir(arguments, data_path=data_path)
    if tool_name == "query_production_outputs":
        return call_query_function(query_production_outputs, arguments, data_path)
    if tool_name == "query_reverse_production_sources":
        return call_query_function(query_reverse_production_sources, arguments, data_path)
    if tool_name == "query_addon_branches":
        return call_query_function(query_addon_branches, arguments, data_path)
    if tool_name == "query_addon_producers":
        return call_query_function(query_addon_producers, arguments, data_path)
    if tool_name == "query_research_outputs":
        return call_query_function(query_research_outputs, arguments, data_path)
    if tool_name == "query_unit_abilities":
        return call_query_function(query_unit_abilities, arguments, data_path)
    if tool_name == "query_dependency_impact":
        return call_query_function(query_dependency_impact, arguments, data_path)
    if tool_name == "query_upgrade_effects":
        return call_query_function(query_upgrade_effects, arguments, data_path)
    if tool_name == "query_gas_units_with_sources":
        return call_query_function(query_gas_units_with_sources, arguments, data_path)
    if tool_name == "query_combat_production_options":
        return call_query_function(query_combat_production_options, arguments, data_path)
    if tool_name == "query_tech_tree":
        return call_query_function(query_tech_tree, arguments, data_path)
    if tool_name == "query_tactical_profile":
        return call_query_function(query_tactical_profile, arguments, data_path)
    if tool_name == "search_descriptions":
        return call_query_function(search_descriptions, arguments, data_path)
    if tool_name == "strategic_join_analysis":
        return call_query_function(strategic_join_analysis, arguments, data_path)
    if tool_name == "query_counter_relations":
        return call_query_function(query_counter_relations, arguments, data_path)
    if tool_name == "query_combat_synergy":
        return call_query_function(query_combat_synergy, arguments, data_path)
    if tool_name == "query_garrison_relations":
        return call_query_function(query_garrison_relations, arguments, data_path)
    if tool_name == "query_stat_bonuses":
        return call_query_function(query_stat_bonuses, arguments, data_path)
    if tool_name == "query_ability_unlocks":
        return call_query_function(query_ability_unlocks, arguments, data_path)
    if tool_name == "query_morph_enablers":
        return call_query_function(query_morph_enablers, arguments, data_path)
        raise ValueError(f"Unknown tool: {tool_name}")


def first_n(values: list[Any], n: int) -> list[Any]:
    return values[:n]
