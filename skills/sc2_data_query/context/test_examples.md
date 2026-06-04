# Test Examples

Use these examples as regression cases.

1. List all Zerg units that take under 30 seconds to build and cost no more than 50 minerals.
2. Filter Terran Armored units taking >= 4 supply, sorted by max_health descending.
3. Query all Protoss units marked as structures (`is_structure == true`) that have weapons.
4. Find all flying units that cost gas but do not need Protoss power (`needs_power == false).
5. Retrieve the complete tech_chain to build a Mothership.
6. Reverse inference: If my Cybernetics Core is destroyed, which units and upgrades will have their tech_chain broken?
7. What are the prerequisites to unlock Terran Stimpack? Does it require a specific add-on?
8. Query units with two or more distinct production/morphing paths.
9. Find units with start_energy > 50 and spell energy_cost >= 75.
10. Filter Zerg Light units with base speed > 3.0 and speed_creep_mul > 1.
11. Retrieve spells targeting structures with cast_range > 8.
12. List transforming units using `normal_mode` and compare armor and range across forms.
13. Find units or abilities mentioning detector or reveal.
14. Search descriptions for anti-air and splash / area of effect.
15. Search for abilities describing armor reduction or shred.
16. Retrieve units described for harass or bonus to light that possess high mobility.
17. Calculate top 3 most cost-efficient Armored units with base armor > 2.
18. Verify if a detected enemy spell ID includes my current unit in its valid target types.
19. Find all Terran structures that accept add-ons and cross-reference which tech upgrades depend on those add-ons.
