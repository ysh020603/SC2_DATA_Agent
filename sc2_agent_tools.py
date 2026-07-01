#!/usr/bin/env python3
"""Agent-facing wrappers around the SC2 query engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sc2_query_engine import (
    execute_tool,
    get_subontology,
    list_subontology_members,
    query_ability_unlocks,
    query_combat_synergy,
    query_counter_relations,
    query_garrison_relations,
    query_morph_enablers,
    query_relation_evidence,
    query_relations,
    query_stat_bonuses,
    query_tactical_profile,
    query_tech_tree,
    search_descriptions,
    search_markdown,
    strategic_join_analysis,
)
from sc2_search_tools import DEFAULT_DATA_PATH


def filter_attributes_and_resources(query_ir: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Filter by resources, numeric ranges, tags, booleans, combat fields, sorting, and selected return keys."""
    return execute_tool("filter_attributes_and_resources", query_ir, data_path=data_path)


def infer_tech_tree(arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Forward or reverse tech-chain inference."""
    return query_tech_tree(data_path=data_path, **arguments)


def assess_tactical_profile(arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Join units and abilities for energy, range, cooldown, target, and transformation questions."""
    return query_tactical_profile(data_path=data_path, **arguments)


def semantic_feature_search(arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Search descriptions for tactical effects and feature phrases."""
    return search_descriptions(data_path=data_path, **arguments)


def strategic_decision_support(arguments: dict[str, Any], data_path: str | Path = DEFAULT_DATA_PATH) -> dict[str, Any]:
    """Run derived metrics and cross-table strategic analysis."""
    return strategic_join_analysis(data_path=data_path, **arguments)


def query_unit_counters(arguments, data_path=None):
    """Query the 2026-07-01 graph's unified counter relations."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_counter_relations(data_path=data_path, **arguments)

def query_unit_synergy(arguments, data_path=None):
    """Query which units synergize with a given unit."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_combat_synergy(data_path=data_path, **arguments)

def query_garrison_transport(arguments, data_path=None):
    """Query garrison, loading, and transport relations."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_garrison_relations(data_path=data_path, **arguments)

def query_upgrade_stat_bonuses(arguments, data_path=None):
    """Query which upgrades grant stat bonuses to a unit, or which units an upgrade affects."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_stat_bonuses(data_path=data_path, **arguments)

def query_upgrade_unlocks(arguments, data_path=None):
    """Query which upgrades unlock new abilities for a unit."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_ability_unlocks(data_path=data_path, **arguments)

def query_morph_unlocks(arguments, data_path=None):
    """Query which upgrades enable morph/transform capabilities."""
    if data_path is None:
        from sc2_search_tools import DEFAULT_DATA_PATH as dp
        data_path = dp
    return query_morph_enablers(data_path=data_path, **arguments)


def query_ontology(arguments, data_path=None):
    """Fetch a SubOntology definition or expand its canonical Unit members."""
    data_path = data_path or DEFAULT_DATA_PATH
    if arguments.get("include_members", True):
        payload = dict(arguments)
        payload.pop("include_members", None)
        return list_subontology_members(data_path=data_path, **payload)
    return get_subontology(data_path=data_path, name=arguments["name"])


def query_typed_relations(arguments, data_path=None):
    """Query typed graph edges while retaining descriptions, sources, and facts."""
    return query_relations(data_path=data_path or DEFAULT_DATA_PATH, **arguments)


def retrieve_relation_evidence(arguments, data_path=None):
    """Retrieve one relation or fact by stable identifier."""
    return query_relation_evidence(data_path=data_path or DEFAULT_DATA_PATH, **arguments)


def semantic_markdown_search(arguments, data_path=None):
    """Search the copied release Markdown corpus."""
    return search_markdown(data_path=data_path or DEFAULT_DATA_PATH, **arguments)
