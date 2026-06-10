# SC2 Data Query Skill

Use this skill when a user asks natural-language questions about StarCraft II units, buildings, abilities, upgrades, tactical properties, tech chains, or strategic constraints.

## Operating Rules

- Do not read the full `data_base.json` into the LLM context.
- First classify the user request into one of the supported query patterns.
- Use the query tools to retrieve evidence.
- Summarize the retrieved evidence in natural language.
- Do not return raw JSON to the user unless explicitly requested.
- If a result depends on approximate field interpretation, state that clearly.
- **Time conversion:** All `time` / `cost.time` values are stored in *game loops*. Always convert to seconds by dividing by **22.4 game loops/sec** and annotate the conversion explicitly in the answer (see `context/field_dictionary.md`).

## Supported Query Families

1. Attribute and resource filtering.
2. Tech tree and dependency inference.
3. Tactical and micro-management assessment.
4. Semantic and feature-based search.
5. Complex strategic decision support.

## Tool Preference

- Use `filter_attributes_and_resources` for numeric budgets, tags, boolean fields, and sorting.
- Use `query_tech_tree` for unlock paths, broken-chain reverse inference, add-ons, or multiple tech paths.
- Use `query_tactical_profile` for unit ability joins, energy, cast range, cooldown, target type, and transforming units.
- Use `search_descriptions` for natural-language tactical effects.
- Use `strategic_join_analysis` for derived metrics and cross-table analysis.

6. Counter and matchup analysis.
7. Unit synergy and composition advice.
8. Garrison and transport logistics.
9. Structured upgrade effect queries (reverse-direction bonuses, unlocks, morph enablers).

## Tool Preference (Knowledge Graph)

- Use `query_counter_relations` for hard/soft counter analysis.
- Use `query_combat_synergy` for unit synergy and composition advice.
- Use `query_garrison_relations` for garrison, loading, and transport queries.
- Use `query_stat_bonuses`, `query_ability_unlocks`, `query_morph_enablers` for reverse upgrade effect queries.