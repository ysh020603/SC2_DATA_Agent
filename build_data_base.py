#!/usr/bin/env python3
"""Build DATA_BASE/data_base.json from data.json plus tech-chain and description sources."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name == "DATA_BASE" else SCRIPT_DIR
SOURCE_DATA = ROOT / "data.json"
ACTION_CHAINS = ROOT / "DATA_0" / "action_chain_text.json"
UNIT_DESCRIPTIONS = ROOT / "DATA_summary_classified" / "category_1_unit_attributes.json"
ABILITY_MAPPING = ROOT / "DATA_0" / "ability_csv_data_action_mapping.json"
OUT_DIR = ROOT / "DATA_BASE"
OUT_JSON = OUT_DIR / "data_base.json"
OUT_DOC = OUT_DIR / "DATA_BASE_STRUCTURE.md"

UNIT_DESCRIPTION_ALIASES = {
    "Stasis Ward": ["OracleStasisTrap"],
    "Templar Archives": "TemplarArchive",
    "Hellbat": "HellionTank",
    "Liberator Fighter Mode": "Liberator",
    "Siege Tank Tank Mode": "SiegeTank",
    "Thor Explosive Payload": "Thor",
    "Viking Fighter Mode": "VikingFighter",
    "Lurker Den": "LurkerDenMP",
    "Nydus Worm": "NydusCanal",
    "Infested Terran": "InfestorTerran",
    "Landed Locust": "LocustMP",
    "Lurker": "LurkerMP",
    "Swarm Host": "SwarmHostMP",
    "Cocoon (Ground)": ["BanelingCocoon", "RavagerCocoon", "LurkerMPEgg"],
}


def normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def append_unique(target: list[str], values: list[str]) -> None:
    seen = set(target)
    for value in values:
        value = value.strip()
        if not value or value in seen:
            continue
        target.append(value)
        seen.add(value)


def build_chain_index(action_chains: list[dict[str, Any]]) -> dict[tuple[str, str], list[str]]:
    index: dict[tuple[str, str], list[str]] = {}
    for entry in action_chains:
        name = entry.get("name")
        kind = entry.get("kind")
        if not name or not kind:
            continue
        options = entry.get("parallel_action_chain_options")
        if not options:
            text = entry.get("action_chain_text")
            options = [text] if text else []
        index[(kind, name)] = [str(option) for option in options if option]
    return index


def build_unit_description_index(raw: dict[str, list[dict[str, Any]]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for source_name, entries in raw.items():
        target_names = UNIT_DESCRIPTION_ALIASES.get(source_name, source_name)
        if isinstance(target_names, str):
            target_names = [target_names]
        for entry in entries:
            text = entry.get("text")
            if isinstance(text, str) and text.strip():
                for target_name in target_names:
                    index[normalize_name(target_name)].append(text.strip())
    return dict(index)


def build_action_description_indexes(mapping: dict[str, Any]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    ability_descriptions: dict[str, list[str]] = defaultdict(list)
    upgrade_descriptions: dict[str, list[str]] = defaultdict(list)
    for match in mapping.get("matches", []):
        description = str(match.get("csv_description") or "").strip()
        if not description:
            continue

        ability = match.get("data_ability")
        if isinstance(ability, dict) and ability.get("name"):
            ability_descriptions[ability["name"]].append(description)

        upgrade = match.get("data_upgrade")
        if isinstance(upgrade, dict) and upgrade.get("name"):
            upgrade_descriptions[upgrade["name"]].append(description)

    return dict(ability_descriptions), dict(upgrade_descriptions)


def enrich_section(
    section_name: str,
    items: list[dict[str, Any]],
    chain_index: dict[tuple[str, str], list[str]],
    unit_descriptions: dict[str, list[str]],
    ability_descriptions: dict[str, list[str]],
    upgrade_descriptions: dict[str, list[str]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        new_item = deepcopy(item)
        name = str(new_item.get("name", ""))
        new_item["tech_chain"] = list(chain_index.get((section_name, name), []))

        descriptions: list[str] = []
        if section_name == "Unit":
            append_unique(descriptions, unit_descriptions.get(normalize_name(name), []))
        elif section_name == "Ability":
            append_unique(descriptions, ability_descriptions.get(name, []))
        elif section_name == "Upgrade":
            append_unique(descriptions, upgrade_descriptions.get(name, []))

        new_item["description"] = descriptions
        enriched.append(new_item)
    return enriched


def build_schema_doc(output: dict[str, Any], stats: dict[str, Any]) -> str:
    counts = {
        "Ability": len(output["Ability"]),
        "Unit": len(output["Unit"]),
        "Upgrade": len(output["Upgrade"]),
    }
    return f"""# DATA_BASE JSON Structure

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
| `Ability` | {counts["Ability"]} |
| `Unit` | {counts["Unit"]} |
| `Upgrade` | {counts["Upgrade"]} |

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
| `Ability` | {stats["described"]["Ability"]} |
| `Unit` | {stats["described"]["Unit"]} |
| `Upgrade` | {stats["described"]["Upgrade"]} |

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
"""


def main() -> None:
    data = load_json(SOURCE_DATA)
    chain_index = build_chain_index(load_json(ACTION_CHAINS))
    unit_descriptions = build_unit_description_index(load_json(UNIT_DESCRIPTIONS))
    ability_descriptions, upgrade_descriptions = build_action_description_indexes(load_json(ABILITY_MAPPING))

    output = {
        "Ability": enrich_section(
            "Ability",
            data.get("Ability", []),
            chain_index,
            unit_descriptions,
            ability_descriptions,
            upgrade_descriptions,
        ),
        "Unit": enrich_section(
            "Unit",
            data.get("Unit", []),
            chain_index,
            unit_descriptions,
            ability_descriptions,
            upgrade_descriptions,
        ),
        "Upgrade": enrich_section(
            "Upgrade",
            data.get("Upgrade", []),
            chain_index,
            unit_descriptions,
            ability_descriptions,
            upgrade_descriptions,
        ),
    }

    stats = {
        "described": {
            section: sum(1 for item in output[section] if item["description"])
            for section in ("Ability", "Unit", "Upgrade")
        }
    }

    write_json(OUT_JSON, output)
    OUT_DOC.write_text(build_schema_doc(output, stats), encoding="utf-8")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_DOC}")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
