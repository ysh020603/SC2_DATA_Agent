# Main Multi-Hop SC2 Agent

Use this skill for natural-language SC2 questions that require planning across Unit, Ability, Upgrade, requirements, production outputs, reverse production sources, or tech-chain dependencies.

## Operating Rules

- Treat the main agent as the orchestrator, not as the source of database facts.
- Resolve user-facing entity mentions before issuing relationship-heavy queries.
- Prefer deterministic retrieval tools for joins and graph-like traversal.
- Keep an evidence state after each tool call.
- Replan from observations when the first result exposes new entities or missing fields.
- Return the final answer only after all user-requested fields are present or an evidence gap is explicit.
- **Time in answers:** All `time`/`cost.time` values are in game loops; ensure the answer converts to seconds using **22.4 game loops/sec** and annotates the conversion.

## Minimal Context Policy

Load only the routing and subskill files relevant to the current question. Do not load full entity key dictionaries unless the entity resolver needs them.

## Standard Multi-Hop Loop

1. Classify the query family.
2. Resolve canonical keys for named entities.
3. Select a deterministic query tool.
4. Execute the tool and store the observation.
5. Inspect missing fields or newly discovered entities.
6. Continue until the answer is ready.