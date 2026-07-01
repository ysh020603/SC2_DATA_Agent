# SC2 2026-07-01 Data Query Skill

Use this skill for structured, graph, ontology, and evidence-backed queries over the current SC2 dataset release.

## Rules

- Never inject the complete multi-megabyte database into the model prompt.
- Retrieve only the entities, relations, classes, and Markdown lines required by the question.
- Preserve canonical names, typed endpoints, `relation_id`, `source`, and `fact` metadata.
- Treat `description`, `source`, and `fact` as lists.
- Use the unified `counters` relation; do not request legacy hard/soft counter edges.
- Use SubOntology membership rather than manually approximating groups such as ground, air, detector, caster, or worker.
- Cite Markdown evidence as `document:line_start-line_end` when present.
- Convert game-loop time values to seconds by dividing by 22.4.
- State clearly when an answer is approximate or not represented in the release.

## Supported families

1. Entity resolution and field projection.
2. Attribute, resource, weapon, and class filtering.
3. Production, research, morph, and tech dependency traversal.
4. Unified semantic and structured relation traversal.
5. SubOntology definition, expansion, and reverse membership.
6. Markdown document routing and line-addressed evidence retrieval.
7. Derived tactical and strategic analysis over deterministic results.
