# SC2 Search Tools

This workspace provides layered search and query capabilities for data_base_add_graph.json.

## Data Source

Default data file:

``text
data_base_add_graph.json
``

It contains three top-level sections: Ability, Unit, Upgrade. Every returned item includes _section when searched. Internal numeric IDs are replaced with readable names; relationships use fields like bility_name, produces_name, upgrade_name, and 
ormal_mode_name.

## Module: sc2_search_tools.py — Core Search & Filter

Low-level, composable Python functions usable standalone or as Agent tools.

### search_by_name

Search by 
ame field.

Modes: exact, contains, uzzy.

``python
from sc2_search_tools import search_by_name

rows = search_by_name(
    "Battlecruiser",
    sections=["Unit"],
    mode="exact",
    keys=["_section", "name", "race", "tech_chain"],
)
``

### ilter_by_numeric_ranges

Filter by any numeric field path, including nested fields.

Supported field paths:

``text
max_health, armor, sight, speed, supply, minerals, gas, time
cast_range, energy_cost, cooldown
cost.minerals, cost.gas, cost.time
weapons.range, weapons.damage_per_hit, weapons.cooldown, weapons.dps, weapons.bonuses.damage
``

``python
from sc2_search_tools import filter_by_numeric_ranges

rows = filter_by_numeric_ranges(
    {"max_health": {"min": 300}, "weapons.range": {"min": 6}},
    sections=["Unit"],
    keys=["_section", "name", "race", "max_health"],
)
``

### ilter_by_tags

Filter by race, attributes, and boolean flags.

``python
from sc2_search_tools import filter_by_tags

rows = filter_by_tags(
    race="Zerg",
    attributes_any=["Armored"],
    booleans={"is_flying": False},
    sections=["Unit"],
    keys=["_section", "name", "race", "attributes", "is_flying"],
)
``

### ilter_combat_profile

Filter Unit records by weapon/combat configuration.

``python
from sc2_search_tools import filter_combat_profile

rows = filter_combat_profile(
    can_attack_air=True,
    min_range=5,
    bonus_against="Armored",
    keys=["_section", "name", "race", "weapons"],
)
``

### combined_search

Compose all four filters in a single pass.

``python
from sc2_search_tools import combined_search

rows = combined_search(
    name_query="viking",
    name_mode="fuzzy",
    sections=["Unit"],
    tag_filters={"race": "Terran"},
    combat_filters={"can_attack_air": True},
    keys=["_section", "name", "race", "weapons"],
    limit=10,
)
``

### pply_projection

Return only selected key paths instead of full records.

``python
keys=["_section", "name", "race", "tech_chain"]
``

Nested key paths are supported:

``python
keys=["name", "cost.minerals", "cost.gas", "cost.time"]
``

## Module: sc2_query_engine.py — Higher-Level Query Engine

Domain-aware functions for cross-table joins, tech-chain parsing, and relation-graph traversal. These are the functions the Agent calls through execute_tool().

### Entity Lookup

#### esolve_entity_key

Resolve a user-facing mention (including Chinese aliases) to a canonical Unit, Ability, or Upgrade name.

``python
from sc2_query_engine import resolve_entity_key

result = resolve_entity_key("Factory", expected_section="Unit")
# Returns top matches with confidence scores and candidate list.
``

#### get_entity

Fetch a single canonical entity record by section and name.

``python
from sc2_query_engine import get_entity

result = get_entity("Unit", "Marine", keys=["name", "race", "max_health", "minerals", "tech_chain"])
``

### Production Joins

#### query_production_outputs

Given a producer, return everything it can train/build/morph, with cost, supply, and time.

``python
from sc2_query_engine import query_production_outputs

result = query_production_outputs(
    "Barracks",
    output_sections=["Unit"],
    target_types=["Train"],
    return_keys=["name", "race", "minerals", "gas", "supply", "time"],
)
``

#### query_reverse_production_sources

Given a unit or upgrade, find which buildings produce it and under what add-on conditions.

``python
result = query_reverse_production_sources(
    "Marauder",
    produced_section="Unit",
    include_requirements=True,
)
``

#### query_addon_branches

Show TechLab-only, Reactor-compatible, and no-addon production branches for a Terran structure.

``python
result = query_addon_branches("Factory")
``

#### query_addon_producers

List all add-on-capable Terran structures and their branch breakdowns.

``python
result = query_addon_producers(race="Terran")
``

#### query_research_outputs

Given a research building, return all upgrades it can research.

``python
result = query_research_outputs(
    producer_name="EngineeringBay",
    race="Terran",
    include_requirements=True,
)
``

### Unit-Ability & Dependency

#### query_unit_abilities

Join a unit to its abilities with energy cost, range, cooldown, and target type.

``python
result = query_unit_abilities(unit_name="Ghost")
``

#### query_dependency_impact

Reverse-impact analysis: what breaks if a given building or upgrade is destroyed or missing.

``python
result = query_dependency_impact(node_name="Factory")
``

#### query_upgrade_effects

Infer which units an upgrade affects, optionally scoped by research producer.

``python
result = query_upgrade_effects(upgrade_name="Stimpack", race="Terran")
``

#### query_gas_units_with_sources

Return all gas-costing units with their production sources and tech chains.

``python
result = query_gas_units_with_sources(race="Terran", min_gas=50)
``

#### query_combat_production_options

Combine production-source and combat-profile filters in one call.

``python
result = query_combat_production_options(
    producer_name="Barracks",
    can_attack_air=True,
)
``

### Tech Tree

#### query_tech_tree

Forward or reverse tech-chain lookup, add-on requirements, multi-path detection.

``python
result = query_tech_tree(target="Mothership")
# Returns parsed tech chain: [Pylon -> Gateway -> CyberneticsCore -> Stargate -> FleetBeacon] + [Nexus] -> Mothership

# Reverse: what is affected if a node is destroyed?
result = query_tech_tree(broken_node="Factory")

# Find multi-path items:
result = query_tech_tree(multi_path_min=2)

# Find items requiring a specific add-on:
result = query_tech_tree(requires_addon="TechLab")
``

### Tactical & Semantic

#### query_tactical_profile

Unit × ability join with energy, range, cooldown, immediate-cast checks, and transforming forms.

``python
result = query_tactical_profile(
    unit_filters={"race": "Protoss"},
    immediate_cast=True,
)
``

#### search_descriptions

Keyword search of description text for tactical effects.

Supported expanded keywords: detector, reveal, cloak, AoE/splash, burrow, armor reduction/shred, harass.

``python
from sc2_query_engine import search_descriptions

result = search_descriptions(
    keywords=["detector"],
    mode="any",
    sections=["Unit", "Ability"],
)
``

### Strategic Analysis

#### strategic_join_analysis

Derived-metric analysis with three modes:

``python
# Cost efficiency ranking (health per mineral):
result = strategic_join_analysis("cost_efficiency", filters={"tag_filters": {"race": "Zerg"}}, top_n=10)

# Add-on dependency report:
result = strategic_join_analysis("addon_dependencies", top_n=50)

# Spell target compatibility check:
result = strategic_join_analysis("spell_target_check", filters={
    "ability_name": "Feedback",
    "unit_name": "Ghost",
})
``

### Relation Graph Queries

Query the elations edges built into data_base_add_graph.json.

#### query_counter_relations

What counters or is countered by a given unit.

``python
from sc2_query_engine import query_counter_relations

result = query_counter_relations("Marine", counter_type="all")
# Returns both hard_counters and soft_counters in both directions.
``

#### query_combat_synergy

What units synergize with a given unit.

``python
from sc2_query_engine import query_combat_synergy

result = query_combat_synergy("SiegeTank")
``

#### query_garrison_relations

What units can garrison in what transports or structures.

``python
from sc2_query_engine import query_garrison_relations

result = query_garrison_relations("Marine")       # what can Marine enter?
result = query_garrison_relations("Bunker")       # what can enter Bunker?
``

#### query_stat_bonuses

Which upgrades grant stat bonuses to a unit, or which units an upgrade affects.

``python
from sc2_query_engine import query_stat_bonuses

result = query_stat_bonuses("MissileTurret")      # upgrades affecting MissileTurret
result = query_stat_bonuses("HiSecAutoTracking")  # units affected by this upgrade
``

#### query_ability_unlocks

Which upgrades unlock new abilities for a unit.

``python
from sc2_query_engine import query_ability_unlocks

result = query_ability_unlocks("Stimpack")        # what Stimpack unlocks
result = query_ability_unlocks("Marine")          # what upgrades give Marine abilities
``

#### query_morph_enablers

Which upgrades enable morph/transform capabilities.

``python
from sc2_query_engine import query_morph_enablers

result = query_morph_enablers("Hellion")          # what enables Hellion to transform
result = query_morph_enablers("SmartServos")      # what SmartServos enables
``

## Streamlit UI

Run from the project root:

``powershell
python -m streamlit run streamlit_search_app.py --server.port 8501
``

Then open http://localhost:8501.

The app has two pages:
- **Main Search**: manually compose name, numeric, tag/attribute, and combat filters.
- **Agent Search** (pages/1_Agent_Search.py): enter a natural-language instruction and let the Agent plan and execute retrieval automatically. Expand trace panels to inspect tool calls and raw results.

## Natural-Language Agent

Run from the project root:

``powershell
python sc2_agent.py "Retrieve the complete tech_chain to build a Mothership." --language English
python sc2_agent.py "What counters a Battlecruiser?" --language English
``

The Agent uses OpenAI-compatible API settings from config/provider_config.json (gitignored). See config/provider_config.example.json for the format.

Environment variable overrides:

``text
GLM_API_KEY / GLM_BASE_URL
KIMI_API_KEY / KIMI_BASE_URL
DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL
``

Enable reasoning mode:

``powershell
python sc2_agent.py "Retrieve the complete tech_chain to build a Mothership." --reasoning
``
