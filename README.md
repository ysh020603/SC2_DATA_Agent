# StarCraft II Data Agent

StarCraft II Data Agent is an evidence-aware natural-language retrieval system for the **2026-07-01 StarCraft II: Legacy of the Void dataset release**. It combines deterministic Python query tools, a typed relationship graph, hierarchical Unit SubOntologies, file-addressable Markdown evidence, and an OpenAI-compatible multi-model agent.

The application can answer questions about units, structures, abilities, upgrades, production, research, technology dependencies, tactical properties, counters, synergy, transport rules, ontology classes, and supporting source passages. Every question is written to a durable local trace whether it is submitted from the command line, Streamlit, or Python.

## Key capabilities

- Searches 683 Abilities, 204 Units, 124 Upgrades, and 109 SubOntology classes.
- Traverses 6,503 typed relations with stable relation IDs and provenance.
- Uses the unified `counters` relation introduced by the 2026-07-01 release.
- Expands semantic assertions over canonical SubOntology members.
- Routes entities and relations to 116 copied Markdown documents.
- Retrieves exact one-based source line ranges and evidence text.
- Supports production, reverse production, research, add-on, morph, ability, and technology-chain joins.
- Calls DeepSeek, Kimi, Gemini, Qwen, or other OpenAI-compatible endpoints through a configurable model pool.
- Extracts provider-visible reasoning from separate fields or embedded thinking tags.
- Persists prompts, routing decisions, plans, tool calls, reasoning, answers, errors, timing, and usage metadata for every run.

## Agent versions

The repository now contains three selectable Agent implementations:

- **V1** preserves the original context-router, planner, deterministic retrieval, and final-answer pipeline. Its explicit entry point is `sc2_agents.v1.run_agent`.
- **V2** uses a tool-isolated MainAgent and a fresh DataSubAgent session for every focused subquestion. MainAgent never receives tool schemas or raw tool results. DataSubAgent first selects a small tool set from an English catalog, then uses native OpenAI-compatible tool calls with full schemas.
- **V2.1** is an isolated copy of V2 under `sc2_agents.v2_1` with stronger English context for candidate roles, weakly constrained questions, field mapping, production-output coverage, and best-effort answers. It raises the MainAgent limit to 20 rounds while leaving V1 and V2 unchanged.

All static V2 and V2.1 prompts, contexts, and tool descriptions are English. The answer language remains configurable. See [docs/AGENT_VERSIONS.md](docs/AGENT_VERSIONS.md) for architecture and test commands.

## Repository layout

```text
SC2_DATA_Agent/
├── API_config/
│   ├── config.example.json
│   └── config.json                 # local secrets; ignored by Git
├── API_Tools/
│   ├── llm_caller.py               # model-pool OpenAI-compatible caller
│   ├── reasoning_extractor.py      # reasoning response-shape extraction
│   ├── reasoning_extractors.md
│   └── probe_reasoning_extraction.py
├── data_sc2_260701/
│   ├── data_base_sc2_260701.json   # active entity and relation database
│   ├── BUILD_MANIFEST.json
│   ├── DATA_STRUCTURE.md
│   ├── SUB_ONTOLOGY.md
│   ├── markdown/{Terran,Protoss,Zerg}/*.md
│   └── relations/entity_expanded_relations.json
├── skills/                         # agent routing and schema guidance
├── sc2_agents/
│   ├── v1/                         # preserved V1 entry point and manifest
│   └── v2/                         # MainAgent, DataSubAgent, contracts, prompts, and tool registry
├── tests/                          # local V2 protocol and isolation tests
├── archive/legacy_v1/              # inactive pre-2026-07-01 files
├── sc2_data_store.py               # version-aware data and evidence indexes
├── sc2_search_tools.py             # low-level filters and projections
├── sc2_query_engine.py             # joins, graph, ontology, and evidence tools
├── sc2_agent_tools.py              # agent-facing convenience wrappers
├── sc2_trace.py                    # durable per-question logging
├── sc2_agent.py                    # router, planner, tool loop, and answerer
└── streamlit_search_app.py         # interactive interface
```

The legacy archive is retained for reference only. Nothing under `archive/legacy_v1` participates in the current runtime.

## Active dataset

The default database is:

```text
data_sc2_260701/data_base_sc2_260701.json
```

The release contains four top-level collections:

| Collection | Count | Purpose |
|---|---:|---|
| `Ability` | 683 | Commands, casts, production, research, movement, and morph actions |
| `Unit` | 204 | Units, structures, transformed forms, summons, and temporary entities |
| `Upgrade` | 124 | Technologies, unlocks, and stat improvements |
| `SubOntology` | 109 | Canonical Unit classes and race/class intersections |

`Unit` records retain the original combat, cost, movement, weapon, ability, requirement, and technology-chain fields. The current release also adds:

- `attack_type`: `None`, `Ground`, `Air`, or `Both`.
- `dimension_a_classes`: membership in the 28 primary Unit classes.

The dataset location can be overridden by passing `--data-path` to the CLI or a path to `run_agent(..., data_path=...)`. `sc2_data_store.DatasetStore` also accepts a release directory and selects its `data_base_sc2_*.json` file.

## SubOntology model

SubOntologies are classes over canonical Units; they are not additional game units.

The hierarchy contains:

- 28 Dimension A classes, including `GroundUnits`, `AirUnits`, `Spellcasters`, `Detectors`, `Workers`, `Harassers`, and `TransportUnits`.
- 3 race classes: `Protoss`, `Terran`, and `Zerg`.
- 78 non-empty race/class intersections such as `Terran_Spellcasters` and `Zerg_GroundUnits`.

Each SubOntology record contains `name`, `entity_type`, `level`, `parents`, `members`, `description`, and `relations`. `GroundUnits` and `AirUnits` form a complete, disjoint partition of all 204 Units.

Source semantic assertions may use a SubOntology endpoint. The release expands those assertions to concrete member relations. Expanded relations retain the original class names, member binding, descriptions, source facts, and `source.kind = subontology_expansion` metadata.

## Unified relation graph

Every relation uses the same structure:

```json
{
  "relation_id": "stable SHA-256 identifier",
  "subject_name": "Marine",
  "subject_type": "Unit",
  "relation": "counters",
  "object_name": "Zergling",
  "object_type": "Unit",
  "description": ["Retained relation descriptions"],
  "source": [{"kind": "markdown_semantic_extraction"}],
  "fact": [{"document": "markdown/Terran/marine.md", "line_start": 91, "line_end": 91}]
}
```

`description`, `source`, and `fact` are always lists. The supported derivation kinds are:

- `structured_data_direct`
- `structured_data_inference`
- `markdown_semantic_extraction`
- `subontology_expansion`
- `pending_postprocess`

The semantic graph uses these relation names:

| Relation | Meaning |
|---|---|
| `counters` | A tactical or matchup advantage |
| `synergizes_with` | Useful unit or strategy interaction |
| `garrisons_in` | Loading, transport, or garrison compatibility |
| `grants_stat_bonus` | Upgrade-to-Unit stat effect |
| `enables_morph` | Upgrade or structure enabling a morph |

The former `hard_counters` and `soft_counters` relation names are not present in the active release. Compatibility calls that pass a hard/soft selector return the unified results with a migration note.

Structured relations additionally cover abilities, requirements, action results, production, research, spawning, morphing, and ability unlocks.

## Markdown evidence

The release includes 116 Markdown files copied from the extraction corpus:

| Race | Documents |
|---|---:|
| Protoss | 38 |
| Terran | 36 |
| Zerg | 42 |

Semantic facts contain:

- a release-relative document path;
- document entity and race;
- heading path;
- one-based start and end lines;
- block ID and fact ID;
- exact evidence text.

The runtime never accepts arbitrary Markdown filesystem paths. `DatasetStore.safe_markdown_path` restricts reads to the active release's `markdown` directory.

## Query tools

### Entity and low-level search

- `resolve_entity_key`
- `get_entity`
- `run_query_ir`
- `filter_attributes_and_resources`
- `search_by_name`
- `filter_by_numeric_ranges`
- `filter_by_tags`
- `filter_combat_profile`
- `combined_search`

### Production and technology

- `query_production_outputs`
- `query_reverse_production_sources`
- `query_addon_branches`
- `query_addon_producers`
- `query_research_outputs`
- `query_unit_abilities`
- `query_dependency_impact`
- `query_upgrade_effects`
- `query_gas_units_with_sources`
- `query_combat_production_options`
- `query_tech_tree`
- `query_tactical_profile`
- `search_descriptions`
- `strategic_join_analysis`

### Typed graph

- `query_relations`
- `query_counter_relations`
- `query_combat_synergy`
- `query_garrison_relations`
- `query_stat_bonuses`
- `query_ability_unlocks`
- `query_morph_enablers`
- `query_relation_evidence`

### SubOntology and evidence

- `get_subontology`
- `list_subontology_members`
- `query_unit_classes`
- `filter_units_by_subontology`
- `resolve_markdown_documents`
- `read_markdown_evidence`
- `search_markdown`

All Agent tools are dispatched through `sc2_query_engine.execute_tool(tool_name, arguments, data_path=...)`.

## Installation

Python 3.11 or later is recommended.

```powershell
cd C:\code\SC2_DATA_Agent
python -m pip install -r requirements.txt
```

The deterministic tools do not require an API connection. Natural-language routing, planning, and answer generation require the `openai` package and at least one configured model entry. The interactive interface additionally requires Streamlit.

## API configuration

Copy the example configuration:

```powershell
Copy-Item API_config\config.example.json API_config\config.json
```

The real `API_config/config.json` is ignored by Git. It contains a `llm_agents_pool` object keyed by user-facing model keys.

Important fields include:

| Field | Purpose |
|---|---|
| `api_url` | OpenAI-compatible base URL |
| `api_key` | Local credential; never written to traces |
| `api_key_env` | Optional environment-variable override |
| `model_name` | Model identifier sent to the endpoint |
| `temperature`, `top_p`, `max_tokens` | Generation controls |
| `timeout_seconds` | Client timeout |
| `is_reasoning` | Whether this entry represents reasoning mode |
| `reasoning_extract_mode` | Response shape used to separate reasoning and answer |
| `reasoning_extra_body` | Request body merged when reasoning is enabled |
| `non_reasoning_extra_body` | Request body merged when reasoning is disabled |

The caller gives explicit function arguments priority over model-pool values. If `api_key_env` is configured and present, its value overrides the file credential.

Kimi requests are protected by a shared rolling-window limiter. All Kimi model variants, answer calls, Judge calls, and retries share a default 58-RPM bucket below the provider's 60-RPM ceiling. The limiter coordinates evaluator threads and sequential Python processes through `logs/.rate_limits/requests.sqlite3`. Non-Kimi providers are not rate-limited by this mechanism. Set `SC2_KIMI_RPM` to a value from 1 through 60 to override the default.

## Reasoning extraction

The API layer can extract provider-visible reasoning from several OpenAI-compatible response shapes:

| Mode | Source |
|---|---|
| `none` | No reasoning extraction |
| `auto` | Separated fields first, then embedded tags |
| `field_reasoning_content` | `message.reasoning_content` |
| `field_reasoning` | `message.reasoning` |
| `field_reasoning_details` | `message.reasoning_details` |
| `content_think_tags` | `<think>...</think>` inside content |
| `content_redacted_thinking_tags` | `<redacted_thinking>...</redacted_thinking>` inside content |

Only reasoning returned by the configured provider can be recorded. If an endpoint does not expose a reasoning field or tag, the trace records `reasoning_available: false` and the detected source instead of manufacturing a chain of thought.

Model keys ending in `_think` can be paired with a non-thinking entry of the same base name. The CLI and UI can select the paired key when reasoning is switched on or off.

To inspect a configured response shape manually:

```powershell
python API_Tools\probe_reasoning_extraction.py `
  --model-key Qwen3-8b_think `
  --mode auto `
  --prompt "Which is larger, 9.11 or 9.8? Answer briefly."
```

Probe reports are local and ignored by Git.

## Command-line usage

Basic question:

```powershell
python sc2_agent.py "What counters a Marine, and which source lines support the answer?"
```

Choose a model and enable reasoning:

```powershell
python sc2_agent.py "List the members of Terran_Spellcasters." `
  --model-key DeepSeek-V4-flash `
  --reasoning-mode on `
  --language English
```

Display the provider-visible reasoning trace in the terminal:

```powershell
python sc2_agent.py "Explain the production path for a Battlecruiser." `
  --reasoning-mode on `
  --show-reasoning
```

Run deterministic retrieval without any API call:

```powershell
python sc2_agent.py "What counters Marine?" --dry-run
```

Useful CLI options:

```text
--provider / --model-key     key from API_config/config.json
--model                      optional underlying model-name override
--reasoning                  compatibility shortcut for reasoning on
--reasoning-mode             auto, on, or off
--language                   answer language
--data-path                  database file or dataset release path
--dry-run                    deterministic tools only
--show-reasoning             print the captured reasoning trace
--show-tools                 print plans and complete tool results
--agent-version              v1, v2, or v2.1; the CLI defaults to v2
```

Every invocation prints its run ID and canonical trace path.

## Python usage

Run the complete natural-language agent:

```python
from sc2_agent import run_agent

result = run_agent(
    "Which Zerg units are Spellcasters?",
    provider="DeepSeek-V4-flash",
    enable_reasoning=False,
    response_language="English",
    agent_version="v2",
)

print(result["answer"])
print(result["run_id"])
print(result["log_path"])
```

Call a deterministic tool directly:

```python
from sc2_query_engine import execute_tool

result = execute_tool(
    "list_subontology_members",
    {"name": "Zerg_Spellcasters"},
)
print(result["results"])
```

Retrieve exact Markdown lines:

```python
result = execute_tool(
    "read_markdown_evidence",
    {
        "document": "markdown/Terran/marine.md",
        "line_start": 21,
        "line_end": 29,
    },
)
```

## Streamlit interface

Start the application from the repository root:

```powershell
streamlit run streamlit_search_app.py --server.port 8501
```

The interface provides:

- dynamic model selection from `API_config/config.json`;
- auto/on/off reasoning selection;
- English or Chinese answer generation;
- answer, run ID, and local trace location;
- expandable routing and planning details;
- provider-visible reasoning by LLM phase;
- complete deterministic tool and evidence results;
- downloadable run results.

The UI does not own the logging mechanism. It calls the same `run_agent` function as the CLI, so closing the browser does not remove the trace.

## Durable logs

Every question creates:

```text
logs/YYYY-MM-DD/<run_id>/
├── events.jsonl
└── trace.json
```

`events.jsonl` is appended and flushed throughout execution. It can survive a process failure before the final answer is produced. `trace.json` is written atomically when the run finishes or fails.

The trace records:

- query, timestamps, run status, and dataset metadata;
- complete router, planner, and answer messages;
- routing decisions and plans;
- tool names, arguments, results, and exceptions;
- answer content and provider-visible reasoning;
- reasoning source and extraction mode;
- model key, model name, latency, usage, and finish reason;
- fallback and failure events.

V1 writes `sc2-agent-trace-v1`. V2 writes `sc2-agent-trace-v2`. V2.1 writes `sc2-agent-trace-v2.1`. V2 and V2.1 additionally record MainAgent decisions, DataSubAgent session boundaries, two-stage tool selection, native tool messages, compressed SubAgent replies, and transient API retries.

Keys whose names resemble credentials, authorization values, tokens, secrets, or passwords are redacted before serialization. API keys and authorization headers are never deliberately included in request metadata.

Set `SC2_LOG_DIR` to move logs to another local directory. Logging is initialized before retrieval begins; an unwritable log location causes the run to fail rather than silently produce an unrecorded answer.

## Security notes

- Never commit `API_config/config.json`.
- Prefer `api_key_env` for shared or long-lived environments.
- Treat traces as sensitive because they contain full user prompts, model output, tool evidence, and provider-visible reasoning.
- Keep `logs/` private and apply an external retention policy appropriate to the deployment.
- Markdown reads are restricted to the active release directory.
- The archived legacy private configuration is also ignored by Git.

## Legacy archive

The pre-2026-07-01 database, builder, schema documentation, provider configuration format, old search-tool documentation, and historical Streamlit output files are stored under:

```text
archive/legacy_v1/
```

These files exist only to explain earlier behavior or support manual migration review. The active code does not fall back to them.

## Troubleshooting

### `Unknown model_key`

Ensure the selected key exists under `llm_agents_pool` in `API_config/config.json`. Model keys are case-sensitive at the Agent boundary.

### Reasoning is empty

Confirm that the endpoint exposes reasoning and that `reasoning_extract_mode` matches its actual response shape. Use `probe_reasoning_extraction.py` to inspect the source and raw message keys.

### A Markdown document cannot be opened

Use release-relative paths beginning with `markdown/`. Absolute paths and paths outside the active Markdown directory are rejected.

### A hard/soft counter query no longer distinguishes severity

This is expected. The current dataset replaced both legacy relations with `counters`; the release does not provide a reliable severity field.

### An entity has no dedicated Markdown page

The structured database contains 204 Units, while the release includes 116 Markdown documents. Use structured fields and relation facts when a dedicated page is unavailable.
