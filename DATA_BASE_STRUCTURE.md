# DATA_BASE JSON Structure

`DATA_BASE/data_base.json` is derived from `data.json`. It keeps the original top-level sections and original object fields, then adds two fields to every Ability, Unit, and Upgrade object: `tech_chain` and `description`.

## Top-Level Object

| Key | Type | Meaning |
| --- | --- | --- |
| `Ability` | list<object> | Ability/action records copied from `data.json`, enriched with chain and description lists. |
| `Unit` | list<object> | Unit/building records copied from `data.json`, enriched with chain and description lists. |
| `Upgrade` | list<object> | Upgrade/technology records copied from `data.json`, enriched with chain and description lists. |

Current counts:

| Section | Count |
| --- | ---: |
| `Ability` | 683 |
| `Unit` | 204 |
| `Upgrade` | 124 |

## Common Added Keys

These two keys are present on every object in `Ability`, `Unit`, and `Upgrade`.

| Key | Type | Meaning |
| --- | --- | --- |
| `tech_chain` | list<string> | Action-chain text matched from `DATA_0/action_chain_text.json`. If the item has one chain, the list has one string. If it has multiple alternative chains, each option is stored as a separate list element. A string may contain `[path A] + [path B] -> target`, where `+` means parallel AND requirements. |
| `description` | list<string> | Plain-text descriptions mapped from the description sources. Source metadata is intentionally not stored in this field. |

## Description Sources

| Target section | Source file | Mapping rule |
| --- | --- | --- |
| `Unit` | `DATA_summary_classified/category_1_unit_attributes.json` | Match by normalized name, ignoring spaces, underscores, punctuation, and case. Example: `Cybernetics Core` maps to `CyberneticsCore`. |
| `Ability` | `DATA_0/ability_csv_data_action_mapping.json` | Use non-empty `csv_description` for matches whose `data_ability.name` equals the ability name. |
| `Upgrade` | `DATA_0/ability_csv_data_action_mapping.json` | Use non-empty `csv_description` for matches whose `data_upgrade.name` equals the upgrade name. |

Some Liquipedia display names differ from `data.json` internal names. The builder uses explicit aliases for these cases: `Stasis Ward -> OracleStasisTrap`, `Templar Archives -> TemplarArchive`, `Hellbat -> HellionTank`, `Liberator Fighter Mode -> Liberator`, `Siege Tank Tank Mode -> SiegeTank`, `Thor Explosive Payload -> Thor`, `Viking Fighter Mode -> VikingFighter`, `Lurker Den -> LurkerDenMP`, `Nydus Worm -> NydusCanal`, `Infested Terran -> InfestorTerran`, `Landed Locust -> LocustMP`, `Lurker -> LurkerMP`, `Swarm Host -> SwarmHostMP`, and `Cocoon (Ground) -> BanelingCocoon / RavagerCocoon / LurkerMPEgg`.

Description coverage in this build:

| Section | Entries with non-empty `description` |
| --- | ---: |
| `Ability` | 281 |
| `Unit` | 118 |
| `Upgrade` | 84 |

## Ability Object Keys

Ability objects keep their original `data.json` keys when present:

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | number | Numeric ability id. |
| `name` | string | Ability/action name. |
| `cast_range` | number | Cast range. |
| `energy_cost` | number | Energy required. |
| `allow_minimap` | bool | Whether the ability can be issued through minimap targeting. |
| `allow_autocast` | bool | Whether autocast is supported. |
| `effect` | list | Effect ids or effect metadata from the source data. |
| `buff` | list | Buff ids or buff metadata from the source data. |
| `cooldown` | number | Cooldown value. |
| `target` | string or object | Target type, or structured target payload such as `Build`, `Train`, `Morph`, or `Research`. |
| `remaps_to_ability_id` | number | Optional remap target ability id. |
| `tech_chain` | list<string> | Added chain list. |
| `description` | list<string> | Added ability/action descriptions. |

## Unit Object Keys

Unit objects keep their original `data.json` keys when present:

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | number | Numeric unit id. |
| `name` | string | Unit or building name. |
| `race` | string | Race, usually `Terran`, `Protoss`, or `Zerg`. |
| `supply` | number | Supply usage or supply provided when negative. |
| `cargo_capacity` | number | Optional transport cargo capacity. |
| `max_health` | number | Maximum health. |
| `max_shield` | number | Maximum Protoss shield value, when present. |
| `armor` | number | Base armor. |
| `sight` | number | Sight range. |
| `speed` | number | Movement speed, when relevant. |
| `speed_creep_mul` | number | Creep speed multiplier. |
| `max_energy` | number | Maximum energy, when present. |
| `start_energy` | number | Starting energy, when present. |
| `weapons` | list<object> | Weapon definitions. |
| `attributes` | list<string> | Unit attributes such as `Light`, `Armored`, `Biological`, `Mechanical`, or `Structure`. |
| `abilities` | list<object> | Ability references and optional requirements available to this unit/building. |
| `size` | number | Source size field. |
| `radius` | number | Collision/selection radius. |
| `power_radius` | number | Protoss power radius, when present. |
| `accepts_addon` | bool | Whether the structure can accept add-ons. |
| `needs_power` | bool | Whether the structure needs Protoss power. |
| `needs_creep` | bool | Whether the unit/building needs creep. |
| `needs_geyser` | bool | Whether it must be built on a geyser. |
| `is_structure` | bool | Whether this record is a structure/building. |
| `is_addon` | bool | Whether this record is a Terran add-on. |
| `is_worker` | bool | Whether this record is a worker. |
| `is_townhall` | bool | Whether this record is a town hall. |
| `is_flying` | bool | Whether this record is flying. |
| `minerals` | number | Mineral cost. |
| `gas` | number | Vespene gas cost. |
| `time` | number | Build/train/research time from the source data. |
| `tech_alias` | list<number> | Unit ids treated as tech aliases. |
| `unit_alias` | number | Unit alias id, when present. |
| `normal_mode` | number | Normal/base form id for transformed variants, when present. |
| `tech_chain` | list<string> | Added chain list. |
| `description` | list<string> | Added unit/building descriptions. |

## Upgrade Object Keys

Upgrade objects keep their original `data.json` keys when present:

| Key | Type | Meaning |
| --- | --- | --- |
| `id` | number | Numeric upgrade id. |
| `name` | string | Upgrade/technology name. |
| `cost` | object | Cost payload, usually with `minerals`, `gas`, and `time`. |
| `tech_chain` | list<string> | Added chain list. |
| `description` | list<string> | Added upgrade/technology descriptions. |

## Build Notes

- `tech_chain` values are copied from `DATA_0/action_chain_text.json`.
- `description` values are plain strings only; source file paths and URLs are deliberately removed.
- The JSON itself does not store source metadata. Source files are documented here instead.
- Objects without a matched chain or description still include the corresponding key with an empty list.
- The builder script is `build_data_base.py`.
