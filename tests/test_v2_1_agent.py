from __future__ import annotations

import unittest
from pathlib import Path

from sc2_agents.v2_1.contracts import validate_sub_reply
from sc2_agents.v2_1.main_agent import MAX_MAIN_ROUNDS
from sc2_agents.v2_1.tool_registry import ToolRegistry


class V21LocalBehaviorTests(unittest.TestCase):
    def test_main_round_limit_is_twenty(self):
        self.assertEqual(20, MAX_MAIN_ROUNDS)

    def test_prompt_and_context_files_are_ascii_english(self):
        root = Path(__file__).resolve().parents[1] / "sc2_agents" / "v2_1"
        for folder in (root / "prompts", root / "context"):
            for path in folder.glob("*.md"):
                path.read_text(encoding="utf-8").encode("ascii")

    def test_sub_reply_preserves_candidate_entities(self):
        reply = validate_sub_reply({
            "answer": "Two candidates are supported.",
            "confidence": "medium",
            "entities_mentioned": ["A", "B"],
            "candidate_entities": [{
                "name": "A",
                "section": "Unit",
                "role": "ability_result",
                "supporting_relation": "action_result",
                "fields": {"minerals": 0},
                "limitations": [],
            }],
            "evidence_summary": "Synthetic contract test.",
            "limitations": [],
        })
        self.assertEqual("A", reply["candidate_entities"][0]["name"])
        self.assertEqual(0, reply["candidate_entities"][0]["fields"]["minerals"])

    def test_upgrade_keyed_lookup_falls_back_to_nested_cost_time(self):
        result = ToolRegistry().execute(
            "get_entity",
            {"name": "BlinkTech", "section": "Upgrade", "keys": ["minerals", "gas", "research_time"]},
        )
        self.assertEqual({"minerals": 150, "gas": 150, "research_time": 2720.0}, result["results"][0])
        self.assertIn("field_fallback", result)

    def test_larva_candidate_discovery_includes_production_outputs(self):
        result = ToolRegistry().execute(
            "query_relations",
            {"entity_name": "Larva", "relation": ["morphs_into"], "direction": "forward", "endpoint_type": "Unit"},
        )
        names = {item["object_name"] for item in result["results"]}
        self.assertIn("SwarmHostMP", names)
        self.assertIn("supplemented", result)


if __name__ == "__main__":
    unittest.main()
