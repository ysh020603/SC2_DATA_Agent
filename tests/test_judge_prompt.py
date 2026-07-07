from __future__ import annotations

import json
import unittest

from SC2_QA.evaluation.judge import JUDGE_SYSTEM_PROMPT, build_judge_messages, validate_and_score
from SC2_QA.evaluation.schemas import JudgeInput


class JudgeLeniencyPromptTests(unittest.TestCase):
    def test_prompt_uses_containment_based_grading(self):
        self.assertIn("containment-based grading", JUDGE_SYSTEM_PROMPT)
        self.assertIn("alternative", JUDGE_SYSTEM_PROMPT)
        self.assertIn("Do not require it to be the first, primary, or unique endpoint", JUDGE_SYSTEM_PROMPT)

    def test_messages_include_lenient_system_prompt(self):
        judge_input = JudgeInput(
            case_id="CASE_001",
            question="Which unit gains an ability?",
            candidate_answer="Alternative candidate: Stalker - minerals 125.",
            standard_answer="The endpoint is Stalker. It costs 125 minerals.",
            scoring={
                "max_points": 2,
                "criteria": [
                    {
                        "point_id": "endpoint_name",
                        "points": 1,
                        "criterion": "Identifies the endpoint as Stalker.",
                        "expected_answer": "Stalker",
                    },
                    {
                        "point_id": "mineral_cost",
                        "points": 1,
                        "criterion": "States that Stalker costs 125 minerals.",
                        "expected_answer": "125",
                    },
                ],
            },
        )
        messages = build_judge_messages(judge_input)
        self.assertIn("containment-based grading", messages[0]["content"])
        payload = json.loads(messages[1]["content"])
        self.assertIn("Alternative candidate: Stalker", payload["candidate_answer"])

    def test_validator_accepts_full_credit_for_contained_alternative(self):
        judge_input = JudgeInput(
            case_id="CASE_001",
            question="Which unit gains an ability?",
            candidate_answer="Zealot is one candidate. Alternative candidate: Stalker, minerals 125.",
            standard_answer="The endpoint is Stalker. It costs 125 minerals.",
            scoring={
                "max_points": 2,
                "criteria": [
                    {
                        "point_id": "endpoint_name",
                        "points": 1,
                        "criterion": "Identifies the endpoint as Stalker.",
                        "expected_answer": "Stalker",
                    },
                    {
                        "point_id": "mineral_cost",
                        "points": 1,
                        "criterion": "States that Stalker costs 125 minerals.",
                        "expected_answer": "125",
                    },
                ],
            },
        )
        parsed = {
            "point_results": [
                {
                    "point_id": "endpoint_name",
                    "awarded_points": 1,
                    "max_points": 1,
                    "candidate_evidence": "Alternative candidate: Stalker",
                    "reason": "The expected endpoint appears as a candidate.",
                },
                {
                    "point_id": "mineral_cost",
                    "awarded_points": 1,
                    "max_points": 1,
                    "candidate_evidence": "Stalker, minerals 125",
                    "reason": "The expected endpoint block contains the expected mineral value.",
                },
            ],
            "overall_comment": "Full credit under containment-based grading.",
        }
        judgment = validate_and_score(parsed, judge_input)
        self.assertEqual(2, judgment["earned_points"])
        self.assertTrue(judgment["full_credit"])


if __name__ == "__main__":
    unittest.main()
