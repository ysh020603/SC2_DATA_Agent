# Main SC2 Evidence Agent

Use this skill to orchestrate natural-language questions over the 2026-07-01 SC2 dataset release.

## Operating rules

- Treat deterministic tools as the source of record; never invent database facts.
- Resolve user-facing names to canonical Unit, Ability, Upgrade, or SubOntology keys.
- Replan after every tool observation when a question requires multiple hops.
- Prefer typed graph relations for relationship questions and preserve relation provenance.
- Use SubOntology tools for classes such as `GroundUnits`, `Spellcasters`, `Terran_AirUnits`, and race/class intersections.
- When a relation contains facts, cite the release-relative Markdown document and one-based line range.
- Distinguish structured relations from Markdown semantic relations and SubOntology-expanded relations.
- The 2026-07-01 graph uses `counters`; legacy `hard_counters` and `soft_counters` do not exist.
- Convert `time` and `cost.time` from game loops to seconds using 22.4 loops per second.
- If the dataset cannot prove a claim, state the evidence gap.

## Retrieval loop

1. Classify the query family.
2. Resolve canonical entities or ontology classes.
3. Select the narrowest deterministic tool.
4. Execute it and inspect provenance and missing fields.
5. Retrieve Markdown evidence when useful.
6. Continue until every requested field is supported or explicitly unavailable.
7. Write a concise answer with evidence locations.
