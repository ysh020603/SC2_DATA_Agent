# Main Agent Routing

## Query Families

- Production chain: questions about what a building/unit can produce, train, build, morph, or research.
- Reverse production: questions about where a unit or upgrade comes from.
- Tech dependency: questions about prerequisites, unlock paths, broken chains, add-ons, or dependency impact.
- Tactical profile: questions about abilities, energy, cast range, cooldown, target type, or transformed forms.
- Attribute filtering: questions about numeric fields, tags, booleans, sorting, or cost constraints.

## Tool Routing

- Use `resolve_entity_key` when a mention is natural-language, Chinese, ambiguous, or display-name-like.
- Use `query_production_outputs` for producer -> output joins.
- Use `query_reverse_production_sources` for output -> producer joins.
- Use `query_addon_branches` for one producer split into no-add-on, TechLab-required, Reactor-required, and Reactor-compatible outputs.
- Use `query_addon_producers` for all add-on-capable producers in a race.
- Use `query_research_outputs` for producer -> researched Upgrade joins.
- Use `query_unit_abilities` for Unit -> Ability joins, including energy, range, cooldown, and target type.
- Use `query_dependency_impact` for tech-chain and requirement reverse impact.
- Use `query_upgrade_effects` for Upgrade -> affected Unit inference from descriptions.
- Use `query_gas_units_with_sources` for gas-costing units plus reverse production source and tech chain.
- Use `query_combat_production_options` for production results filtered by combat properties such as anti-air or sorted by time.
- Use `query_tech_tree` for unlock paths and reverse dependency scans.
- Use `query_tactical_profile` for Unit -> Ability tactical fields.
- Use `filter_attributes_and_resources` for direct field filters.

## Query Families (Knowledge Graph)

- **Counter relations**: questions about hard/soft counters between units.
- **Unit synergy**: questions about which units work well together.
- **Garrison / transport**: questions about loading, garrisoning, and transport.
- **Structured upgrade effects**: reverse-direction stat bonus, ability unlock, and morph enabler queries.

## Tool Routing (Knowledge Graph)

- Use `query_counter_relations` for hard/soft counter questions.
- Use `query_combat_synergy` for synergy/composition questions.
- Use `query_garrison_relations` for garrison/transport questions.
- Use `query_stat_bonuses` for upgrade -> unit stat bonus questions.
- Use `query_ability_unlocks` for upgrade -> unlocked ability questions.
- Use `query_morph_enablers` for upgrade -> enabled morph/transform questions.
