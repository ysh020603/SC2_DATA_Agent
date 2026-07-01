# Main Agent Routing

## Core entity and production routing

- Use `resolve_entity_key` for natural-language, Chinese, ambiguous, display, or SubOntology names.
- Use `get_entity` for one complete Unit, Ability, Upgrade, or SubOntology record.
- Use `query_production_outputs` and `query_reverse_production_sources` for production joins.
- Use `query_addon_branches` and `query_addon_producers` for Terran add-on logic.
- Use `query_research_outputs` for structure-to-upgrade joins.
- Use `query_unit_abilities` and `query_tactical_profile` for ability and tactical fields.
- Use `query_dependency_impact` and `query_tech_tree` for prerequisites and reverse impact.
- Use `filter_attributes_and_resources` for numeric, race, attribute, boolean, `attack_type`, or class filters.

## Unified graph routing

- Use `query_counter_relations` for the unified `counters` relation.
- Use `query_combat_synergy` for `synergizes_with`.
- Use `query_garrison_relations` for `garrisons_in`.
- Use `query_stat_bonuses` for `grants_stat_bonus`.
- Use `query_ability_unlocks` for `unlocks_unit_ability`.
- Use `query_morph_enablers` for `enables_morph`.
- Use `query_relations` when relation type, endpoint type, or direction must be selected dynamically.

## SubOntology routing

- Use `get_subontology` for definition, level, parents, members, and ontology-scope relations.
- Use `list_subontology_members` or `filter_units_by_subontology` for class-to-unit expansion.
- Use `query_unit_classes` for unit-to-class reverse lookup.
- Secondary classes are race intersections, for example `Protoss_Spellcasters`.

## Evidence routing

- Use `query_relation_evidence` when a `relation_id` or `fact_id` is already known.
- Use `resolve_markdown_documents` to map an entity/display name to copied Markdown documents.
- Use `read_markdown_evidence` for exact line-addressed excerpts.
- Use `search_markdown` for semantic information not represented by a structured field.
- Do not infer that every one of the 204 Units has a dedicated Markdown page; this release contains 116 copied documents.
