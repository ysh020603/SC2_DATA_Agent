# SC2 Search Tools

This workspace provides two search entry points:

- `sc2_search_tools.py`: reusable Python search/filter functions for Agent tools.
- `streamlit_search_app.py`: Streamlit UI for interactive search.
- `sc2_query_engine.py`: higher-level deterministic query engine for tech-chain, tactical, semantic, and strategic analysis.
- `sc2_agent.py`: natural-language Agent that plans tool calls, executes retrieval, and asks an LLM to summarize the evidence.
- `pages/1_Agent_Search.py`: Streamlit subpage for natural-language Agent search.

## Data Source

Default data file when running the tools from this folder:

```text
data_base.json
```

The file contains three top-level sections:

```text
Ability
Unit
Upgrade
```

Every returned item includes `_section` when searched through the tool module.
Internal numeric ids are removed from the searchable database; relationships use fields such as `ability_name`, `produces_name`, `upgrade_name`, and `normal_mode_name`.

## Tool Functions

### `search_by_name`

Search by `name`.

Modes:

- `exact`
- `contains`
- `fuzzy`

```python
from sc2_search_tools import search_by_name

rows = search_by_name(
    "Battlecruiser",
    sections=["Unit"],
    mode="exact",
    keys=["_section", "name", "race", "tech_chain"],
)
```

### `filter_by_numeric_ranges`

Filter by numeric fields or nested numeric fields.

Supported examples:

```text
max_health
armor
sight
speed
minerals
gas
time
cost.minerals
cost.gas
cost.time
weapons.range
weapons.damage_per_hit
weapons.dps
weapons.bonuses.damage
```

```python
from sc2_search_tools import filter_by_numeric_ranges

rows = filter_by_numeric_ranges(
    {
        "max_health": {"min": 300},
        "weapons.range": {"min": 6},
    },
    sections=["Unit"],
    keys=["_section", "name", "race", "max_health"],
)
```

### `filter_by_tags`

Filter by race, attributes and boolean flags.

```python
from sc2_search_tools import filter_by_tags

rows = filter_by_tags(
    race="Zerg",
    attributes_any=["Armored"],
    booleans={"is_flying": False},
    sections=["Unit"],
    keys=["_section", "name", "race", "attributes", "is_flying"],
)
```

### `filter_combat_profile`

Filter Unit records by weapon/combat profile.

```python
from sc2_search_tools import filter_combat_profile

rows = filter_combat_profile(
    can_attack_air=True,
    min_range=5,
    bonus_against="Armored",
    keys=["_section", "name", "race", "weapons"],
)
```

### `combined_search`

Compose all filters.

```python
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
```

## Return Projection

All functions return full records by default.

Pass `keys=[...]` to return only selected fields:

```python
keys=["_section", "name", "race", "tech_chain"]
```

Nested key paths are supported:

```python
keys=["name", "cost.minerals", "cost.gas", "cost.time"]
```

## Streamlit UI

Run:

```powershell
python -m streamlit run DATA_BASE\streamlit_search_app.py --server.port 8501
```

Then open:

```text
http://localhost:8501
```

The Streamlit app has an Agent subpage. Use it to enter a natural-language instruction, run the Agent, read the final answer, and expand the trace panels to inspect tool calls and raw tool results.

## Natural-Language Agent

Run from the project root:

```powershell
python DATA_BASE\sc2_agent.py "Retrieve the complete tech_chain to build a Mothership"
```

Run from inside `DATA_BASE`:

```powershell
python sc2_agent.py "Find all flying units that cost gas but do not need Protoss power."
```

The Agent uses OpenAI-compatible API settings loaded from:

```text
DATA_BASE/config/provider_config.json
```

This real config file is ignored by `DATA_BASE/.gitignore` because it contains API keys. Use this tracked sample to describe the required format:

```text
DATA_BASE/config/provider_config.example.json
```

The default provider is `glm-4.7`. Reasoning is not stored in config; it is controlled per request from the Streamlit Agent page or with the CLI flag:

```powershell
python DATA_BASE\sc2_agent.py "Retrieve the complete tech_chain to build a Mothership" --reasoning
```

Environment variables can override keys and endpoints:

```text
GLM_API_KEY
GLM_BASE_URL
KIMI_API_KEY
KIMI_BASE_URL
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
```
