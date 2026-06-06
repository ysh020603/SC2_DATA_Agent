# Entity Key Resolver Subagent

This subagent maps user mentions to canonical `Unit`, `Ability`, or `Upgrade` keys.

## Inputs

- `mention`: user-facing name or alias.
- `expected_section`: optional `Unit`, `Ability`, or `Upgrade`.
- `race`: optional race hint.

## Outputs

Return a structured resolution with canonical section, name, confidence, and candidates.

## Context Loading

Load only the relevant race and section dictionaries when possible.

Available generated dictionaries:

- `context/all/units.md`
- `context/all/abilities.md`
- `context/all/upgrades.md`
- `context/terran/units.md`
- `context/terran/abilities.md`
- `context/terran/upgrades.md`
- `context/protoss/units.md`
- `context/protoss/abilities.md`
- `context/protoss/upgrades.md`
- `context/zerg/units.md`
- `context/zerg/abilities.md`
- `context/zerg/upgrades.md`

Prefer race-specific files when a race is mentioned. Use `all/*` only when the query is explicitly cross-race or no race hint exists and deterministic matching is ambiguous.
