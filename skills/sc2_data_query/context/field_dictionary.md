# Field Dictionary

Map natural-language phrases to fields.

## Resources

- minerals, mineral cost, mineral budget -> `minerals` or `cost.minerals`
- gas, vespene, vespene gas -> `gas` or `cost.gas`
- supply, population -> `supply`
- build time, train time, research time -> `time` or `cost.time`

## Unit Stats

- health, HP -> `max_health`
- shield -> `max_shield`
- armor -> `armor`
- sight, vision -> `sight`
- speed, mobility -> `speed`
- creep speed multiplier -> `speed_creep_mul`

## Tags

- Terran -> `race == Terran`
- Protoss -> `race == Protoss`
- Zerg -> `race == Zerg`
- armored, heavy armor -> `attributes contains Armored`
- light -> `attributes contains Light`
- biological -> `attributes contains Biological`
- mechanical -> `attributes contains Mechanical`
- structure, building -> `attributes contains Structure` or `is_structure == true`
- massive -> `attributes contains Massive`
- psionic -> `attributes contains Psionic`

## Boolean Fields

- flying, air unit -> `is_flying == true`
- ground unit -> `is_flying == false`
- building, structure -> `is_structure == true`
- worker -> `is_worker == true`
- town hall -> `is_townhall == true`
- needs Protoss power -> `needs_power == true`
- does not need Protoss power -> `needs_power == false`
- needs creep -> `needs_creep == true`
- accepts add-on -> `accepts_addon == true`

## Combat Fields

- can attack air -> weapon `target_type` is `Air` or `Any`
- can attack ground -> weapon `target_type` is `Ground` or `Any`
- weapon range -> `weapons.range`
- damage -> `weapons.damage_per_hit`
- DPS -> `weapons.dps`
- bonus to armored -> `weapons.bonuses.against == Armored`
- bonus to light -> `weapons.bonuses.against == Light`

## Ability Fields

- spell energy -> `Ability.energy_cost`
- cast range -> `Ability.cast_range`
- cooldown -> `Ability.cooldown`
- target type -> `Ability.target`
- autocast -> `Ability.allow_autocast`
