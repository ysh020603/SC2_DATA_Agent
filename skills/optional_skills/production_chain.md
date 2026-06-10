# Production Chain Subskill

Use this subskill for questions like:

- What units can Barracks produce?
- What can Factory train with or without Tech Lab?
- Which Starport outputs cost gas?

## Chain

1. Resolve producer mention to a canonical `Unit.name`.
2. Call `query_production_outputs`.
3. Default `target_types` to `["Train"]` when the user asks for units a producer can train/produce.
4. Include `return_keys` for every requested output field, such as `name`, `minerals`, `gas`, `supply`, `time`, `weapons.range`, or `tech_chain`.
5. Keep `include_requirements=true` when add-ons, upgrades, or building prerequisites might matter.

## Example

User asks: "Tell me what units Barracks can produce, with minerals, gas, and supply."

Tool:

```json
{
  "tool": "query_production_outputs",
  "arguments": {
    "producer_name": "Barracks",
    "producer_section": "Unit",
    "output_sections": ["Unit"],
    "target_types": ["Train"],
    "return_keys": ["name", "race", "minerals", "gas", "supply"],
    "include_requirements": true,
    "include_ability": true,
    "limit": 50
  }
}
```
