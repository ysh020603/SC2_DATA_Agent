# Tech Dependency Subskill

Use this subskill for questions about prerequisites, unlock paths, broken dependencies, add-ons, and multi-path production.

## Forward Unlock

Use `query_tech_tree` with `target`.

## Reverse Impact

Use `query_tech_tree` with `broken_node`.

## Add-On Dependencies

Use `query_tech_tree` with `requires_addon` or `strategic_join_analysis` with `analysis_type="addon_dependencies"`.

## Evidence Rule

If the user asks for costs or production sources after a tech-chain result, follow up with `query_reverse_production_sources` or `filter_attributes_and_resources` to retrieve those fields.
