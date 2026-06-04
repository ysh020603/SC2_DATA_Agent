# Data Schema

The dataset has three top-level sections.

## Ability

Ability records represent actions, skills, commands, research actions, build commands, train commands, and morph commands.

Important fields:

- `id`: numeric ability id.
- `name`: internal ability name.
- `cast_range`: cast range.
- `energy_cost`: energy required.
- `allow_minimap`: whether minimap targeting is allowed.
- `allow_autocast`: whether autocast is supported.
- `cooldown`: cooldown value.
- `target`: target type or structured payload such as `Build`, `Train`, `Morph`, or `Research`.
- `tech_chain`: list of chain strings.
- `description`: list of plain-language descriptions.

## Unit

Unit records include units, buildings, add-ons, forms, summons, and some hidden or technical variants.

Important fields:

- `id`: numeric unit id.
- `name`: internal unit name.
- `race`: `Terran`, `Protoss`, or `Zerg`.
- `supply`: supply used, or supply provided when negative.
- `max_health`, `max_shield`, `armor`, `sight`, `speed`.
- `minerals`, `gas`, `time`: resource and production fields.
- `attributes`: tags such as `Armored`, `Light`, `Biological`, `Mechanical`, `Structure`, `Massive`, `Psionic`.
- `weapons`: list of weapon records.
- `abilities`: list of ability id references.
- `is_structure`, `is_flying`, `is_worker`, `is_townhall`, `is_addon`.
- `accepts_addon`, `needs_power`, `needs_creep`, `needs_geyser`.
- `normal_mode`: base form id for transformed variants.
- `tech_chain`: list of chain strings.
- `description`: list of plain-language descriptions.

## Upgrade

Upgrade records represent researched technologies.

Important fields:

- `id`: numeric upgrade id.
- `name`: internal upgrade name.
- `cost.minerals`, `cost.gas`, `cost.time`.
- `tech_chain`: list of chain strings.
- `description`: list of plain-language descriptions.

## Join Rules

- `Unit.abilities[*].ability` joins to `Ability.id`.
- `Ability.target.Research.upgrade` joins to `Upgrade.id`.
- `Ability.target.*.produces` joins to `Unit.id`.
