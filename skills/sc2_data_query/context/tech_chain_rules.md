# Tech Chain Rules

Tech chains are stored as a list of strings.

## Syntax

```text
[path A] + [path B] -> Target
```

- Square brackets represent one linear prerequisite path.
- `->` inside a path means chronological sequence.
- `+` means parallel AND requirements.
- The final `-> Target` is the unlocked unit, ability, or upgrade.
- Multiple strings in `tech_chain` represent alternative paths, similar to OR logic.

## Forward Unlock

To answer "how do I unlock X?", retrieve the target item's `tech_chain` and parse each path.

## Reverse Broken Chain

To answer "what breaks if X is destroyed?", scan all tech chains and return items whose prerequisite paths contain X.

## Add-ons

If a chain contains `TechLab`, the target depends on a specific Tech Lab path. If it contains `Reactor`, the target depends on a Reactor path.

## Multi-Path

If `len(tech_chain) >= 2`, the item has multiple alternative production, morph, or mode paths in the dataset.
