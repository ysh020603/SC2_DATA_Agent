# Combat + Production Filter Subskill

Use this subskill when the user asks a question that combines a production source (building or tech line) with combat filtering, sorting, or add-on constraints. Typical patterns:

- "Which units from [Barracks] can [attack air] and what are their costs and ranges?"
- "Using only [the Factory tech line], which units can [attack ground]?"
- "What are the fastest [anti-air] units from [the Starport]?"
- "From [Gateway], which units have [range > 5]?"
- "Without [TechLab], which [Terran] units can [attack air]?"
- "With [Reactor], what are the [cheapest] units from [Barracks]?"

## Key Insight

When the query asks for units **from a specific producer** AND filters by **combat attributes** (can attack air, attack ground, range, speed) OR **add-on constraints** (TechLab required, no add-on), prefer `query_combat_production_options` over composing `query_production_outputs` + manual filtering.

`query_combat_production_options` is designed for this exact compound pattern — it joins production data with combat attributes in a single tool call.

## When to use query_combat_production_options

Use this tool when **at least two** of these conditions overlap in one query:

1. A **production source** is specified (producer_name or race)
2. A **combat capability** filter is needed (can_attack_air, sort_by time/range)
3. An **add-on constraint** is relevant (require_no_addon, required_addon)

## Tool Reference

```json
{
  "tool": "query_combat_production_options",
  "arguments": {
    "producer_name": "optional string (e.g. Barracks, Factory, Starport)",
    "race": "optional string (Terran, Protoss, Zerg)",
    "can_attack_air": "optional boolean",
    "require_no_addon": "optional boolean",
    "required_addon": "optional string (TechLab, Reactor)",
    "sort_by": "optional string (time, minerals, gas, supply, range)",
    "limit": "integer"
  }
}
```

## When NOT to use

- Pure production listing without combat filters → use `query_production_outputs`
- Pure combat/tactical queries without production source → use `query_tactical_profile` or `query_unit_abilities`
- Tech-tree or prerequisite questions → use `query_tech_tree`

## Examples

Query: "Using only the Barracks production path, which Terran units can attack air, and what are their costs and ranges?"
Tool:
```json
{
  "tool": "query_combat_production_options",
  "arguments": {
    "producer_name": "Barracks",
    "can_attack_air": true,
    "limit": 50
  }
}
```

Query: "Without a Tech Lab, what are the fastest Terran combat units to produce?"
Tool:
```json
{
  "tool": "query_combat_production_options",
  "arguments": {
    "race": "Terran",
    "require_no_addon": true,
    "sort_by": "time",
    "limit": 50
  }
}
```

Query: "Which Factory units can attack air with a Tech Lab?"
Tool:
```json
{
  "tool": "query_combat_production_options",
  "arguments": {
    "producer_name": "Factory",
    "can_attack_air": true,
    "required_addon": "TechLab",
    "limit": 50
  }
}
```
