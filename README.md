# SC2 DATA Search & Natural-Language Agent

A structured, searchable database and query system for StarCraft II: Legacy of the Void units, buildings, abilities, and upgrades.

## Database

Core data file:

``text
data_base_add_graph.json
``

It is built from the raw data.json plus tech-chain and description sources, containing three top-level sections:

| Section   | Content | Count |
|-----------|---------|------:|
| Ability | Skills, actions, and commands (train, build, research, cast, move, attack, etc.) | 683 |
| Unit    | Units and buildings across Terran, Protoss, and Zerg, including transformed variants | 204 |
| Upgrade | Technologies and upgrades (weapon/armor tiers, ability unlocks, special research) | 124 |

Every object retains searchable original fields from data.json with internal numeric IDs replaced by readable names, plus three added fields:

| Key           | Type              | Purpose |
|---------------|-------------------|---------|
| 	ech_chain  | list<string>    | Tech-tree unlock paths, supporting single paths, multi-path alternatives, and parallel AND dependencies ([path A] + [path B] -> target). |
| description | list<string>    | Natural-language descriptions of the unit, ability, or upgrade. |
| elations   | list<object>    | Inter-entity relationship graph edges (counter, synergy, production, morph, garrison, stat bonuses, ability locks). 345 Abilities, 180 Units, and 72 Upgrades carry non-empty relations. |

Full schema details are in [DATA_BASE_STRUCTURE.md](DATA_BASE_STRUCTURE.md).

## Query Engine

The tools are organized across three layers:

### Layer 1 — Core search/filter (sc2_search_tools.py)

Reusable Python functions that can be called standalone or wrapped as Agent tools.

| Function                   | Purpose |
|----------------------------|---------|
| search_by_name           | Search by name with exact, contains, or fuzzy matching. |
| ilter_by_numeric_ranges | Filter by any numeric field (max_health, weapons.range, cost.gas, etc.). |
| ilter_by_tags           | Filter by race, attributes (Armored, Light, ...), and boolean flags (is_flying, 
eeds_power, ...). |
| ilter_combat_profile    | Filter by weapon properties: air/ground target, range, damage, DPS, bonus damage type. |
| combined_search          | Compose all four filters in one pass. |
| pply_projection         | Return only selected key paths instead of the full record. |

### Layer 2 — Higher-level query engine (sc2_query_engine.py)

Domain-aware functions that perform cross-table joins, tech-chain parsing, and relation-graph traversal.

**Entity lookup:**

| Tool                       | Purpose |
|----------------------------|---------|
| esolve_entity_key       | Resolve user-facing names (including Chinese aliases) to canonical database keys. |
| get_entity               | Fetch one full entity record by section and name. |

**Production joins:**

| Tool                              | Purpose |
|-----------------------------------|---------|
| query_production_outputs        | Given a producer, return everything it can train/build/morph, with cost/supply/time. |
| query_reverse_production_sources | Given a unit or upgrade, return which buildings produce it and under what add-on conditions. |
| query_addon_branches            | Show TechLab-only, Reactor-compatible, and no-addon production branches for a given structure. |
| query_addon_producers           | List all Terran structures that accept add-ons and their branch breakdowns. |
| query_research_outputs          | Given a research building, return all upgrades it can research. |

**Unit-ability and dependency analysis:**

| Tool                       | Purpose |
|----------------------------|---------|
| query_unit_abilities     | Join unit → ability with energy cost, range, cooldown, and target-type details. |
| query_dependency_impact  | Reverse-impact analysis: what breaks if a given building or upgrade is destroyed/missing. |
| query_upgrade_effects    | Infer which units an upgrade affects by name-substring matching. |
| query_gas_units_with_sources | Return all gas-costing units with their production sources and tech chains. |
| query_combat_production_options | Combine production-source and combat-profile filters in one call. |

**Tech-tree analysis:**

| Tool              | Purpose |
|-------------------|---------|
| query_tech_tree | Forward or reverse tech-chain lookup, add-on requirements, multi-path detection. |

**Tactical and semantic:**

| Tool                      | Purpose |
|---------------------------|---------|
| query_tactical_profile  | Unit × ability join with energy, range, cooldown, immediate-cast checks, creep speed, and transforming forms. |
| search_descriptions     | Keyword search of description text for tactical effects (detector, cloak, splash, burrow, harass, etc.). |

**Strategic analysis:**

| Tool                       | Purpose |
|----------------------------|---------|
| strategic_join_analysis  | Derived-metric analysis: cost efficiency rankings, add-on dependency reports, spell target compatibility. |

### Layer 3 — Relation graph queries (sc2_query_engine.py)

Query the elations edges in data_base_add_graph.json:

| Tool                       | Relation queried | Purpose |
|----------------------------|------------------|---------|
| query_counter_relations  | hard_counters, soft_counters | What counters Marine? What does Archon hard-counter? |
| query_combat_synergy     | synergizes_with | What units work well with SiegeTank? |
| query_garrison_relations | garrisons_in    | What units can enter Bunker? Can SiegeTank load into Medivac? |
| query_stat_bonuses       | grants_stat_bonus | What upgrades improve MissileTurret? What does HiSecAutoTracking affect? |
| query_ability_unlocks    | unlocks_unit_ability | What does Stimpack unlock? What upgrades give Marine new abilities? |
| query_morph_enablers     | enables_morph   | What upgrade lets Hellion transform? What does SmartServos enable? |

## Natural-Language Agent

The Agent (sc2_agent.py) performs multi-step, tool-calling retrieval:

1. User enters a natural-language question.
2. A context router picks relevant skill modules and race dictionaries.
3. The LLM plans one or more tool calls from the available catalog.
4. Deterministic query functions execute the retrieval.
5. The LLM summarizes the evidence into a natural-language answer.

Agent supports both Chinese and English I/O modes, with an optional reasoning toggle.

Run from the project root:

``powershell
python sc2_agent.py "Retrieve the complete tech_chain to build a Mothership." --language English
python sc2_agent.py "What counters a Battlecruiser?" --language English
python sc2_agent.py "Which upgrades from the EngineeringBay affect Marines?" --language English
``

Dry-run mode executes tools without LLM calls:

``powershell
python sc2_agent.py "What does a Barracks produce?" --dry-run
``

### Agent tools catalog

The Agent has access to 20+ deterministic tools through sc2_agent_tools.py. The full tool spec with argument schemas is defined in sc2_agent.py (the TOOL_SPEC constant). Each tool can be independently invoked with the standard execute_tool(tool_name, arguments) interface from sc2_query_engine.py.

### Provider configuration

API settings are stored in config/provider_config.json (gitignored). See config/provider_config.example.json for the format. Supported providers:

| Provider           | Model              |
|--------------------|--------------------|
| glm-4.7          | glm-4.7            |
| kimi-k2.5        | kimi-k2.5          |
| deepseek-v4-flash| deepseek-v4-flash  |

Environment variable overrides:

``text
GLM_API_KEY / GLM_BASE_URL
KIMI_API_KEY / KIMI_BASE_URL
DEEPSEEK_API_KEY / DEEPSEEK_BASE_URL
``

## Streamlit UI

Run from the project root:

``powershell
streamlit run streamlit_search_app.py --server.port 8501
``

Then open http://localhost:8501.

The app includes:
- **Main Search page**: manually compose name, numeric, tag/attribute, and combat filters with a sortable results table.
- **Agent Search subpage** (pages/1_Agent_Search.py): enter a natural-language instruction and let the Agent plan and execute retrieval automatically, with expandable tool-trace panels.

## Key Files

| File | Purpose |
|------|---------|
| data_base_add_graph.json | Core structured database with tech chains, descriptions, and relations. |
| uild_data_base.py | Build script that generates the database from raw sources. |
| sc2_search_tools.py | Low-level search/filter functions. |
| sc2_query_engine.py | Higher-level query engine with cross-table joins and relation graphs. |
| sc2_agent_tools.py | Agent-facing wrappers around the query engine. |
| sc2_agent.py | Natural-language Agent with LLM planning, routing, and summarization. |
| streamlit_search_app.py | Streamlit main search UI. |
| pages/1_Agent_Search.py | Streamlit Agent subpage. |
| config/provider_config.example.json | API configuration example. |
| DATA_BASE_STRUCTURE.md | Full database schema documentation. |
