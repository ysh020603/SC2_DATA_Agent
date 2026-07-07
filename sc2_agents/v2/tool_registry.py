"""Catalog, schema generation, validation, and dispatch for V2 tools."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

import sc2_query_engine as query_engine
from sc2_query_engine import execute_tool
from sc2_search_tools import DEFAULT_DATA_PATH


CATALOG: dict[str, str] = {
    "resolve_entity_key": "Resolve a user-facing name or alias to a canonical Unit, Ability, Upgrade, or SubOntology key.",
    "get_entity": "Fetch selected fields or the complete record for one canonical entity.",
    "filter_attributes_and_resources": "Filter entities by names, numeric ranges, race, tags, booleans, combat fields, and sorting.",
    "query_production_outputs": "Follow a producer to Units or Upgrades it trains, builds, morphs, or researches.",
    "query_reverse_production_sources": "Find the structures or units that produce a specified Unit or Upgrade.",
    "query_addon_branches": "Inspect TechLab, Reactor, and no-add-on production branches for one Terran producer.",
    "query_addon_producers": "List add-on-capable Terran structures and their production branches.",
    "query_research_outputs": "Find upgrades researched by a structure or filtered by race and add-on requirement.",
    "query_unit_abilities": "Join Units to Ability records, including energy, range, cooldown, targets, and requirements.",
    "query_dependency_impact": "Find entities affected by a missing prerequisite or technology node.",
    "query_upgrade_effects": "Find units affected by an upgrade, optionally scoped by research structure.",
    "query_gas_units_with_sources": "Find gas-costing units with production sources and technology evidence.",
    "query_combat_production_options": "Combine production constraints with combat properties such as anti-air or speed.",
    "query_tech_tree": "Query prerequisite paths, missing-node impact, add-on requirements, and multiple paths.",
    "query_tactical_profile": "Query spell, transformation, movement, range, cooldown, and target properties.",
    "search_descriptions": "Search semantic descriptions using tactical keywords.",
    "strategic_join_analysis": "Run supported derived analyses for cost, add-on dependency, or spell targets.",
    "query_counter_relations": "Traverse the unified counters relation for a canonical unit.",
    "query_combat_synergy": "Traverse synergizes_with relations for a canonical unit.",
    "query_garrison_relations": "Traverse transport and garrison compatibility relations.",
    "query_stat_bonuses": "Traverse upgrade-to-unit stat bonus relations.",
    "query_ability_unlocks": "Traverse upgrade-to-unit ability unlock relations.",
    "query_morph_enablers": "Find an Upgrade or structure that enables a morph; do not use it to find the source Unit that morphs into another Unit.",
    "query_relations": "Traverse typed graph relations with configurable direction and endpoint type; use reverse morphs_into traversal to find which Unit morphs into a result Unit.",
    "get_subontology": "Fetch one canonical SubOntology class definition and members.",
    "list_subontology_members": "List concrete Units in a SubOntology class.",
    "query_unit_classes": "Find SubOntology classes that contain a Unit.",
    "filter_units_by_subontology": "Filter concrete Units by a canonical class and optional race.",
    "query_relation_evidence": "Retrieve provenance for a known relation ID or fact ID.",
    "resolve_markdown_documents": "Map an entity to release-relative Markdown documents.",
    "read_markdown_evidence": "Read an allowed line range from a release Markdown document.",
    "search_markdown": "Search release Markdown for semantic evidence not represented by structured fields.",
}

FUNCTION_ALIASES = {"filter_attributes_and_resources": "run_query_ir"}
REQUIRED_OVERRIDES = {
    "query_counter_relations": ["entity_name"],
    "query_combat_synergy": ["entity_name"],
    "query_garrison_relations": ["entity_name"],
    "query_stat_bonuses": ["entity_name"],
    "query_ability_unlocks": ["entity_name"],
    "query_morph_enablers": ["entity_name"],
}
SPECIAL_SCHEMAS: dict[str, dict[str, Any]] = {
    "filter_attributes_and_resources": {
        "type": "object",
        "properties": {
            "sections": {"type": "array", "items": {"type": "string"}},
            "name_query": {"type": "string"},
            "name_mode": {"type": "string", "enum": ["contains", "exact", "fuzzy"]},
            "numeric_ranges": {"type": "object"},
            "tag_filters": {"type": "object"},
            "combat_filters": {"type": "object"},
            "sort": {"type": "array", "items": {"type": "object"}},
            "return_keys": {"type": "array", "items": {"type": "string"}},
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
        },
        "required": ["sections"],
        "additionalProperties": False,
    }
}


def _schema_for_annotation(annotation: Any) -> dict[str, Any]:
    text = str(annotation).lower()
    if "list" in text:
        return {"type": "array", "items": {"type": "string"}}
    if "dict" in text:
        return {"type": "object"}
    if "bool" in text:
        return {"type": "boolean"}
    if "int" in text:
        return {"type": "integer"}
    if "float" in text:
        return {"type": "number"}
    return {"type": "string"}


def _function_schema(tool_name: str) -> dict[str, Any]:
    if tool_name in SPECIAL_SCHEMAS:
        return SPECIAL_SCHEMAS[tool_name]
    function_name = FUNCTION_ALIASES.get(tool_name, tool_name)
    function = getattr(query_engine, function_name)
    signature = inspect.signature(function)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for name, parameter in signature.parameters.items():
        if name in {"data_path", "query_ir"}:
            continue
        schema = _schema_for_annotation(parameter.annotation)
        if name == "limit":
            schema.update({"minimum": 1, "maximum": 500})
        properties[name] = schema
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
    required = REQUIRED_OVERRIDES.get(tool_name, required)
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


class ToolRegistry:
    def names(self) -> list[str]:
        return list(CATALOG)

    def catalog_text(self) -> str:
        return "\n".join(f"- {name}: {summary}" for name, summary in CATALOG.items())

    def validate_selection(self, names: list[str], maximum: int = 4) -> list[str]:
        selected: list[str] = []
        for name in names:
            if name in CATALOG and name not in selected:
                selected.append(name)
        if not selected:
            raise ValueError("No valid tools were selected.")
        return selected[:maximum]

    def openai_tools(self, names: list[str]) -> list[dict[str, Any]]:
        selected = self.validate_selection(names)
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": CATALOG[name],
                    "parameters": _function_schema(name),
                },
            }
            for name in selected
        ]

    def validate_arguments(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name not in CATALOG:
            raise ValueError(f"Unknown V2 tool: {name}")
        if not isinstance(arguments, dict):
            raise TypeError("Tool arguments must be a JSON object.")
        schema = _function_schema(name)
        unknown = set(arguments) - set(schema.get("properties", {}))
        missing = set(schema.get("required", [])) - set(arguments)
        if unknown:
            raise ValueError(f"Unsupported arguments for {name}: {sorted(unknown)}")
        if missing:
            raise ValueError(f"Missing required arguments for {name}: {sorted(missing)}")
        validated = dict(arguments)
        if "limit" in validated:
            validated["limit"] = max(1, min(int(validated["limit"]), 500))
        return validated

    def execute(self, name: str, arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
        return execute_tool(name, self.validate_arguments(name, arguments), data_path=data_path)

    def fallback_selection(self, question: str, maximum: int = 4) -> list[str]:
        lowered = question.lower()
        scores: list[tuple[int, str]] = []
        for name, summary in CATALOG.items():
            tokens = set(re.findall(r"[a-z_]+", f"{name} {summary}".lower()))
            score = sum(1 for token in tokens if len(token) > 3 and token in lowered)
            scores.append((score, name))
        ranked = [name for score, name in sorted(scores, reverse=True) if score > 0]
        defaults = ["resolve_entity_key", "get_entity", "query_relations", "query_tech_tree"]
        return (ranked + [name for name in defaults if name not in ranked])[:maximum]


def dispatcher_tool_names() -> set[str]:
    source = inspect.getsource(query_engine.execute_tool)
    return set(re.findall(r'if tool_name == "([^"]+)"', source)) - {"run_query_ir"}


__all__ = ["CATALOG", "ToolRegistry", "dispatcher_tool_names"]
