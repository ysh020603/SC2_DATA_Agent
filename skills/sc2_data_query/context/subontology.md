# SubOntology Guidance

SubOntologies are classes over canonical Units, not additional Units.

- 28 Dimension A classes describe combat role, movement domain, attributes, and functions.
- 3 race classes are `Protoss`, `Terran`, and `Zerg`.
- 78 secondary classes are non-empty race/class intersections.
- `GroundUnits` and `AirUnits` are disjoint and cover all 204 Units.
- A source assertion may use a class endpoint. Concrete member relations record `source.kind = subontology_expansion` and retain the original facts.

Use ontology tools for group questions. Do not reconstruct class membership from names or descriptions.
