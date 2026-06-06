#!/usr/bin/env python3
"""Deterministic smoke tests for bilingual multi-hop SC2 query cases."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sc2_query_engine import execute_tool  # noqa: E402


CASES: list[dict[str, Any]] = [
    {
        "id": "01_barracks_outputs",
        "zh": "兵营能生产哪些单位？这些单位分别多少矿、气、人口？",
        "en": "What units can Barracks produce, and how many minerals, gas, and supply do they cost?",
        "tool": "query_production_outputs",
        "arguments": {"producer_name": "Barracks", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Marine", "Marauder", "Reaper", "Ghost"],
    },
    {
        "id": "02_factory_addon_branches",
        "zh": "重工厂挂 Tech Lab 后能生产哪些单位？不挂 Tech Lab 又能生产哪些？",
        "en": "What can Factory produce with a Tech Lab, and what can it produce without a Tech Lab?",
        "tool": "query_addon_branches",
        "arguments": {"producer_name": "Factory", "return_keys": ["name", "minerals", "gas", "supply", "time"]},
        "contains": ["Hellion", "SiegeTank", "Thor"],
    },
    {
        "id": "03_starport_addon_branches",
        "zh": "星港挂 Reactor 后能双产哪些单位？哪些必须 Tech Lab？",
        "en": "Which Starport units are Reactor-compatible, and which require a Tech Lab?",
        "tool": "query_addon_branches",
        "arguments": {"producer_name": "Starport", "return_keys": ["name", "minerals", "gas", "supply", "time"]},
        "contains": ["Medivac", "VikingFighter", "Banshee", "Raven"],
    },
    {
        "id": "04_battlecruiser_tech",
        "zh": "要造战列巡航舰，需要哪些建筑和前置？",
        "en": "What buildings and prerequisites are needed to build a Battlecruiser?",
        "tool": "query_tech_tree",
        "arguments": {"target": "Battlecruiser", "sections": ["Unit"], "limit": 10},
        "contains": ["FusionCore", "Starport", "Battlecruiser"],
    },
    {
        "id": "05_barracks_dependency",
        "zh": "如果兵营被打掉，会影响哪些单位、建筑、升级？",
        "en": "If Barracks is destroyed, which units, buildings, and upgrades are affected?",
        "tool": "query_dependency_impact",
        "arguments": {"node_name": "Barracks", "sections": ["Unit", "Upgrade"], "limit": 100},
        "contains": ["Factory", "Stimpack"],
    },
    {
        "id": "06_ghost_academy_dependency",
        "zh": "如果 Ghost Academy 没有建好，哪些技能或单位不可用？",
        "en": "If Ghost Academy is not built, which abilities or units are unavailable?",
        "tool": "query_dependency_impact",
        "arguments": {"node_name": "GhostAcademy", "sections": ["Unit", "Ability", "Upgrade"], "limit": 100},
        "contains": ["Ghost"],
    },
    {
        "id": "07_engineering_bay_upgrade_effects",
        "zh": "兵营里的哪些单位受步兵攻防升级影响？",
        "en": "Which Barracks units are affected by infantry weapon and armor upgrades?",
        "tool": "query_upgrade_effects",
        "arguments": {"research_producer_name": "EngineeringBay", "race": "Terran", "limit": 50},
        "contains": ["Marine", "Marauder", "Ghost", "Reaper"],
    },
    {
        "id": "08_stimpack_effects",
        "zh": "Stimpack 解锁后影响哪些单位？这些单位的成本、人口和生产建筑是什么？",
        "en": "Which units are affected by Stimpack, and what are their costs, supply, and production sources?",
        "tool": "query_upgrade_effects",
        "arguments": {"upgrade_name": "Stimpack", "race": "Terran", "include_sources": True, "limit": 20},
        "contains": ["Marine", "Marauder", "Barracks"],
    },
    {
        "id": "09_techlab_research",
        "zh": "哪些人族升级需要 Tech Lab？分别挂在哪个建筑上？",
        "en": "Which Terran upgrades require a Tech Lab, and which building are they attached to?",
        "tool": "query_research_outputs",
        "arguments": {"race": "Terran", "required_addon": "TechLab", "return_keys": ["name", "cost"], "limit": 100},
        "contains": ["Stimpack", "BansheeCloak"],
    },
    {
        "id": "10_terran_energy_abilities",
        "zh": "哪些人族单位有消耗能量的技能？技能能量够不够开局立刻释放？",
        "en": "Which Terran units have energy-based abilities, and can they cast immediately when spawned?",
        "tool": "query_unit_abilities",
        "arguments": {"race": "Terran", "only_energy": True, "limit": 100},
        "contains": ["Ghost", "Raven"],
    },
    {
        "id": "11_ghost_abilities",
        "zh": "Ghost 有哪些技能？每个技能的能量、射程、冷却、目标类型是什么？",
        "en": "What abilities does Ghost have, with energy, range, cooldown, and target type?",
        "tool": "query_unit_abilities",
        "arguments": {"unit_name": "Ghost", "limit": 100},
        "contains": ["EMP_EMP", "EFFECT_GHOSTSNIPE"],
    },
    {
        "id": "12_raven_abilities",
        "zh": "Raven 的技能能影响哪些目标类型？这些技能的能量成本是多少？",
        "en": "What target types can Raven abilities affect, and what are their energy costs?",
        "tool": "query_unit_abilities",
        "arguments": {"unit_name": "Raven", "limit": 100},
        "contains": ["EFFECT_ANTIARMORMISSILE", "BUILDAUTOTURRET_AUTOTURRET"],
    },
    {
        "id": "13_all_addon_producers",
        "zh": "所有人族建筑中，哪些能挂 Tech Lab / Reactor？挂了以后分别新增什么生产项？",
        "en": "Among all Terran structures, which can attach Tech Lab or Reactor, and what outputs do they unlock?",
        "tool": "query_addon_producers",
        "arguments": {"race": "Terran", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Barracks", "Factory", "Starport", "Marauder", "SiegeTank", "Banshee"],
    },
    {
        "id": "14_barracks_techlab_research",
        "zh": "Barracks Tech Lab 解锁了哪些单位或升级？",
        "en": "What units or upgrades does the Barracks Tech Lab unlock?",
        "tool": "query_research_outputs",
        "arguments": {"producer_name": "BarracksTechLab", "return_keys": ["name", "cost"], "limit": 50},
        "contains": ["Stimpack", "ShieldWall", "PunisherGrenades"],
    },
    {
        "id": "15_reactor_double_production",
        "zh": "Reactor 能让哪些建筑双产？这些建筑各自能双产哪些单位？",
        "en": "Which buildings can use Reactor for double production, and which units are Reactor-compatible?",
        "tool": "query_addon_producers",
        "arguments": {"race": "Terran", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Marine", "Hellion", "Medivac"],
    },
    {
        "id": "16_marauder_source",
        "zh": "一个 Marauder 是从哪个建筑生产的？需要什么插件？成本是多少？",
        "en": "Where is a Marauder produced, what add-on does it require, and what does it cost?",
        "tool": "query_reverse_production_sources",
        "arguments": {"produced_name": "Marauder", "producer_race": "Terran", "return_keys": ["name", "race"], "limit": 20},
        "contains": ["Barracks", "TechLab"],
    },
    {
        "id": "17_siegetank_source",
        "zh": "一个 SiegeTank 需要哪些建筑和插件？由哪个技能训练出来？",
        "en": "What buildings and add-on does a Siege Tank require, and which ability trains it?",
        "tool": "query_reverse_production_sources",
        "arguments": {"produced_name": "SiegeTank", "producer_race": "Terran", "return_keys": ["name", "race", "tech_chain"], "limit": 20},
        "contains": ["Factory", "TechLab", "FACTORYTRAIN_SIEGETANK"],
    },
    {
        "id": "18_factory_dependency",
        "zh": "哪些人族单位最终依赖 Factory？它们成本、人口和生产建筑分别是什么？",
        "en": "Which Terran units ultimately depend on Factory, and what are their costs, supply, and production buildings?",
        "tool": "query_dependency_impact",
        "arguments": {"node_name": "Factory", "sections": ["Unit"], "race": "Terran", "limit": 100},
        "contains": ["SiegeTank", "Starport"],
    },
    {
        "id": "19_barracks_antiair",
        "zh": "只用兵营科技线，能生产哪些对空单位？成本和射程是多少？",
        "en": "Using only the Barracks tech line, which anti-air units can be produced, and what are their costs and ranges?",
        "tool": "query_combat_production_options",
        "arguments": {"producer_name": "Barracks", "can_attack_air": True, "limit": 50},
        "contains": ["Marine"],
    },
    {
        "id": "20_fastest_without_techlab",
        "zh": "在没有 Tech Lab 的情况下，人族能最快生产哪些战斗单位？",
        "en": "Without a Tech Lab, what are the fastest Terran combat units to produce?",
        "tool": "query_combat_production_options",
        "arguments": {"race": "Terran", "require_no_addon": True, "sort_by": "time", "limit": 20},
        "contains": ["Marine"],
    },
    {
        "id": "21_gas_units_sources",
        "zh": "找出所有需要气体的人族单位，并说明它们来自哪个建筑、是否需要插件、科技链是什么。",
        "en": "Find all Terran units that cost gas and explain their production source, add-on requirement, and tech chain.",
        "tool": "query_gas_units_with_sources",
        "arguments": {"race": "Terran", "limit": 100},
        "contains": ["Reaper", "Marauder", "Starport"],
    },
    {
        "id": "22_protoss_gateway_outputs",
        "zh": "神族传送门能生产哪些单位？这些单位分别多少矿、气、人口？",
        "en": "What units can a Protoss Gateway produce, and what are their mineral, gas, and supply costs?",
        "tool": "query_production_outputs",
        "arguments": {"producer_name": "Gateway", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Zealot", "Stalker", "HighTemplar"],
    },
    {
        "id": "23_protoss_stargate_outputs",
        "zh": "神族星门能生产哪些空军单位？成本和人口是多少？",
        "en": "What air units can a Protoss Stargate produce, and what are their costs and supply?",
        "tool": "query_production_outputs",
        "arguments": {"producer_name": "Stargate", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Phoenix", "Carrier", "Tempest"],
    },
    {
        "id": "24_protoss_cybernetics_research",
        "zh": "神族控制核心能研究哪些升级？",
        "en": "Which upgrades can the Protoss Cybernetics Core research?",
        "tool": "query_research_outputs",
        "arguments": {"producer_name": "CyberneticsCore", "return_keys": ["name", "cost"], "limit": 50},
        "contains": ["WarpGateResearch", "ProtossAirWeaponsLevel1"],
    },
    {
        "id": "25_protoss_cybernetics_dependency",
        "zh": "如果神族控制核心被打掉，会影响哪些单位和升级？",
        "en": "If the Protoss Cybernetics Core is destroyed, which units and upgrades are affected?",
        "tool": "query_dependency_impact",
        "arguments": {"node_name": "CyberneticsCore", "sections": ["Unit", "Upgrade"], "race": "Protoss", "limit": 100},
        "contains": ["Stalker", "Mothership", "WarpGateResearch"],
    },
    {
        "id": "26_protoss_oracle_abilities",
        "zh": "先知有哪些技能？这些技能的目标类型和射程是什么？",
        "en": "What abilities does the Oracle have, and what are their target types and ranges?",
        "tool": "query_unit_abilities",
        "arguments": {"unit_name": "Oracle", "limit": 50},
        "contains": ["ORACLEREVELATION_ORACLEREVELATION", "BUILD_STASISTRAP"],
    },
    {
        "id": "27_protoss_gas_units_sources",
        "zh": "找出所有需要气体的神族单位，并说明它们来自哪个建筑和科技链。",
        "en": "Find all Protoss units that cost gas and explain their production source and tech chain.",
        "tool": "query_gas_units_with_sources",
        "arguments": {"race": "Protoss", "limit": 100},
        "contains": ["Colossus", "Mothership", "RoboticsFacility"],
    },
    {
        "id": "28_zerg_larva_outputs",
        "zh": "虫族幼虫能变成哪些单位？这些单位分别多少矿、气、人口？",
        "en": "What units can Zerg Larva morph into, and what are their mineral, gas, and supply costs?",
        "tool": "query_production_outputs",
        "arguments": {"producer_name": "Larva", "return_keys": ["name", "minerals", "gas", "supply"], "limit": 50},
        "contains": ["Drone", "Zergling", "Roach", "Hydralisk"],
    },
    {
        "id": "29_zerg_spawning_pool_research",
        "zh": "虫族血池能研究哪些升级？",
        "en": "Which upgrades can the Zerg Spawning Pool research?",
        "tool": "query_research_outputs",
        "arguments": {"producer_name": "SpawningPool", "return_keys": ["name", "cost"], "limit": 50},
        "contains": ["zerglingmovementspeed", "zerglingattackspeed"],
    },
    {
        "id": "30_zerg_spawning_pool_dependency",
        "zh": "如果虫族血池被打掉，会影响哪些单位和升级？",
        "en": "If the Zerg Spawning Pool is destroyed, which units and upgrades are affected?",
        "tool": "query_dependency_impact",
        "arguments": {"node_name": "SpawningPool", "sections": ["Unit", "Upgrade"], "race": "Zerg", "limit": 100},
        "contains": ["Baneling", "Roach", "zerglingmovementspeed"],
    },
    {
        "id": "31_zerg_infestor_abilities",
        "zh": "感染者有哪些技能？这些技能的目标类型和射程是什么？",
        "en": "What abilities does the Infestor have, and what are their target types and ranges?",
        "tool": "query_unit_abilities",
        "arguments": {"unit_name": "Infestor", "limit": 50},
        "contains": ["FUNGALGROWTH_FUNGALGROWTH", "NEURALPARASITE_NEURALPARASITE"],
    },
    {
        "id": "32_zerg_gas_units_sources",
        "zh": "找出所有需要气体的虫族单位，并说明它们来自哪个生产来源和科技链。",
        "en": "Find all Zerg units that cost gas and explain their production source and tech chain.",
        "tool": "query_gas_units_with_sources",
        "arguments": {"race": "Zerg", "limit": 100},
        "contains": ["Baneling", "Hydralisk", "Mutalisk"],
    },
    {
        "id": "33_protoss_stalker_source",
        "zh": "追猎者从哪个建筑生产？需要什么前置？",
        "en": "Where is a Stalker produced, and what prerequisite does it require?",
        "tool": "query_reverse_production_sources",
        "arguments": {"produced_name": "Stalker", "producer_race": "Protoss", "return_keys": ["name", "race"], "limit": 20},
        "contains": ["Gateway", "CyberneticsCore"],
    },
    {
        "id": "34_zerg_roach_source",
        "zh": "蟑螂从哪里生产？需要什么前置？",
        "en": "Where is a Roach produced, and what prerequisite does it require?",
        "tool": "query_reverse_production_sources",
        "arguments": {"produced_name": "Roach", "producer_race": "Zerg", "return_keys": ["name", "race"], "limit": 20},
        "contains": ["Larva", "RoachWarren"],
    },
    {
        "id": "35_zerg_upgrade_effects",
        "zh": "虫族小狗移速升级影响哪些单位？这些单位来源是什么？",
        "en": "Which units are affected by Zergling movement speed, and what are their production sources?",
        "tool": "query_upgrade_effects",
        "arguments": {"upgrade_name": "zerglingmovementspeed", "race": "Zerg", "include_sources": True, "limit": 20},
        "contains": ["Zergling", "Larva"],
    },
]


def run_case(case: dict[str, Any]) -> tuple[bool, str]:
    result = execute_tool(case["tool"], case["arguments"])
    payload = json.dumps(result, ensure_ascii=False)
    missing = [needle for needle in case.get("contains", []) if needle not in payload]
    count = result.get("count", 0)
    if missing:
        return False, f"{case['id']} missing {missing}; count={count}"
    if isinstance(count, int) and count <= 0:
        return False, f"{case['id']} returned no results"
    return True, f"{case['id']} ok; count={count}"


def main() -> int:
    failures = []
    for case in CASES:
        ok, message = run_case(case)
        print(message)
        print(f"  zh: {case['zh']}")
        print(f"  en: {case['en']}")
        if not ok:
            failures.append(message)
    if failures:
        print("\nFAILURES:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(f"\nAll {len(CASES)} bilingual multi-hop cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
