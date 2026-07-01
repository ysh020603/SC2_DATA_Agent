# Query Recipes

## Attribute and Resource Filtering

User asks:

> List all Zerg units under 30 seconds and no more than 50 minerals.

Tool:

```json
{
  "tool": "filter_attributes_and_resources",
  "arguments": {
    "sections": ["Unit"],
    "numeric_ranges": {
      "time": {"max": 672},
      "minerals": {"max": 50}
    },
    "tag_filters": {"race": "Zerg"},
    "limit": 50
  }
}
```

The 30-second limit is converted to 672 game loops before querying (`30 * 22.4`).

## Sorting

User asks:

> Filter Terran Armored units taking >= 4 supply, sorted by max_health descending.

Use `filter_attributes_and_resources` with:

```json
{
  "sections": ["Unit"],
  "numeric_ranges": {"supply": {"min": 4}},
  "tag_filters": {"race": "Terran", "attributes_any": ["Armored"]},
  "sort": [{"field": "max_health", "order": "desc"}]
}
```

## Tech Chain Forward

User asks:

> Retrieve the complete tech_chain to build a Mothership.

Use `query_tech_tree`:

```json
{"target": "Mothership", "sections": ["Unit"], "limit": 5}
```

## Tech Chain Reverse

User asks:

> If Cybernetics Core is destroyed, which units and upgrades are broken?

Use `query_tech_tree`:

```json
{"broken_node": "CyberneticsCore", "sections": ["Unit", "Upgrade", "Ability"], "limit": 100}
```

## Tactical Profile

User asks:

> Find units with start_energy > 50 and spell energy_cost >= 75.

Use `query_tactical_profile`:

```json
{
  "unit_filters": {"start_energy": {"op": "gt", "value": 50}},
  "ability_filters": {"energy_cost": {"op": "gte", "value": 75}},
  "immediate_cast": true
}
```

## Semantic Search

User asks:

> Find units or abilities mentioning detector or reveal.

Use `search_descriptions`:

```json
{"keywords": ["detector", "reveal"], "mode": "any", "sections": ["Unit", "Ability"], "limit": 50}
```

## Strategic Analysis

User asks:

> Calculate top 3 most cost-efficient Armored units with armor > 2.

Use `strategic_join_analysis`:

```json
{
  "analysis_type": "cost_efficiency",
  "filters": {
    "tag_filters": {"attributes_any": ["Armored"]},
    "numeric_ranges": {"armor": {"min": 2.0001}}
  },
  "top_n": 3
}
```

## Unified Counter Relation

User asks:

> What counters Marine, and where is the evidence?

Use `query_counter_relations` with `direction: both`. Keep each result's `relation_id`, `description`, `source`, and `fact`. Cite fact documents and line ranges in the answer.

## SubOntology Expansion

User asks:

> Which Terran units are Spellcasters?

Use:

```json
{"tool": "list_subontology_members", "arguments": {"name": "Terran_Spellcasters"}}
```

Use `query_unit_classes` for the reverse question: which ontology classes contain a specific Unit.

## Markdown Evidence

When a relation already supplies a fact, call `read_markdown_evidence` with the returned `document`, `line_start`, and `line_end`. When starting from an entity, call `resolve_markdown_documents`. Use `search_markdown` only when no structured field or relation represents the requested information.
