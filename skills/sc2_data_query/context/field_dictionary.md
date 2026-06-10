# Field Dictionary

Map natural-language phrases to fields.

## Resources &amp; Time

- minerals, mineral cost, mineral budget -> `minerals` or `cost.minerals`
- gas, vespene, vespene gas -> `gas` or `cost.gas`
- supply, population -> `supply`
- build time, train time, research time -> `time` or `cost.time`

### Time Conversion (Game Loops to Seconds)

All `time` / `cost.time` values in the data are stored as **game loops** (logical frames).

**Conversion rule:**  
1 real second = 1 game UI second = **22.4 game loops**

To convert a time value to seconds: **divide by 22.4**.

When presenting any time value in the final answer:
- Always show both the raw game-loop value from the data and the converted seconds (rounded to 1 decimal).
- Explicitly annotate that the conversion uses **22.4 game loops per second**.
- If the raw data provides a time value in game loops, never present it as seconds without this annotated conversion.

Example: `"1440 game loops / 22.4 ~ 64.3 seconds (converted at 22.4 game loops/sec)"`

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
