#!/usr/bin/env python3
"""Agent-facing wrappers around the SC2 query engine."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sc2_query_engine import (
    execute_tool,
    query_ability_unlocks,
    query_combat_synergy,
    query_counter_relations,
    query_garrison_relations,
    query_morph_enablers,
    query_stat_bonuses,
    query_tactical_profile,
    query_tech_tree,
    search_descriptions,
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
    """Query which units hard-counter or soft-counter a given unit."""
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
