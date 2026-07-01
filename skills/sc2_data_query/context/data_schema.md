# Dataset Schema

The active release is `data_sc2_260701/data_base_sc2_260701.json`.

## Collections

- `Ability`: 683 commands, casts, builds, trains, researches, and morph actions.
- `Unit`: 204 units, structures, alternate forms, and temporary entities.
- `Upgrade`: 124 technologies and improvements.
- `SubOntology`: 109 canonical Unit classes.

## New Unit fields

- `attack_type`: `None`, `Ground`, `Air`, or `Both`.
- `dimension_a_classes`: membership in the 28 primary Unit classes.

## SubOntology fields

- `name`, `entity_type`, `level`, `parents`, `members`, `description`, `relations`.
- `level` is `dimension_a`, `race`, or `secondary`.
- Secondary classes are non-empty Race × Dimension intersections.

## Unified relation object

Every relation contains `relation_id`, typed subject and object names, `relation`, list-valued `description`, list-valued `source`, and list-valued `fact`.

Source kinds are `structured_data_direct`, `structured_data_inference`, `markdown_semantic_extraction`, `subontology_expansion`, and `pending_postprocess`.

Markdown facts contain document path, document entity, race, heading path, one-based line range, block ID, fact ID, and exact evidence text.

The semantic relations are `counters`, `synergizes_with`, `garrisons_in`, `grants_stat_bonus`, and `enables_morph`. Structured relations include production, research, abilities, requirements, spawns, morphs, action results, and ability unlocks.
