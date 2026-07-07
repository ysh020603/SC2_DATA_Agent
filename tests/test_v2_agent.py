from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from sc2_agents.v2.contracts import parse_json_object, validate_main_decision
from sc2_agents.v2.main_agent import MainAgent
from sc2_agents.v2.runtime import V2TraceRecorder
from sc2_agents.v2.sub_agent import DataSubAgent
from sc2_agents.v2.tool_registry import CATALOG, ToolRegistry, dispatcher_tool_names


class FakeInvoker:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.main_calls = 0
        self.sub_tool_calls = 0

    def __call__(self, phase, messages, *, tools=None, reasoning=None):
        self.calls.append({"phase": phase, "messages": list(messages), "tools": tools or []})
        if phase.startswith("main_round"):
            self.main_calls += 1
            if self.main_calls == 1:
                content = json.dumps({
                    "action": "ask_subagent",
                    "sub_question": "What are Probe's mineral cost and maximum health?",
                    "decision_summary": "The requested fields require one entity lookup.",
                    "final_answer": None,
                })
            else:
                content = json.dumps({
                    "action": "final_answer",
                    "sub_question": None,
                    "decision_summary": "The requested fields are supported.",
                    "final_answer": "Probe costs 50 minerals and has 20 maximum health.",
                })
            return {"content": content, "raw_message": {"role": "assistant", "content": content}}
        if phase.endswith("select_tools"):
            content = json.dumps({
                "selected_tools": ["get_entity"],
                "selection_summary": "Fetch exact fields from Probe.",
            })
            return {"content": content, "raw_message": {"role": "assistant", "content": content}}
        self.sub_tool_calls += 1
        if self.sub_tool_calls == 1:
            arguments = json.dumps({"section": "Unit", "name": "Probe", "keys": ["minerals", "health"]})
            return {
                "content": "",
                "raw_message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_entity", "arguments": arguments},
                    }],
                },
            }
        content = json.dumps({
            "answer": "Probe costs 50 minerals and has 20 maximum health.",
            "confidence": "high",
            "entities_mentioned": ["Probe"],
            "evidence_summary": "The Unit record supplies both fields.",
            "limitations": [],
        })
        return {"content": content, "raw_message": {"role": "assistant", "content": content}}


class V2ContractTests(unittest.TestCase):
    def test_json_contract_parser_accepts_fenced_object(self):
        value = parse_json_object('```json\n{"action":"final_answer","final_answer":"ok"}\n```')
        self.assertEqual("ok", value["final_answer"])

    def test_main_contract_rejects_empty_subquestion(self):
        with self.assertRaises(ValueError):
            validate_main_decision({"action": "ask_subagent", "sub_question": ""})


class ToolRegistryTests(unittest.TestCase):
    def test_catalog_matches_dispatcher(self):
        self.assertEqual(dispatcher_tool_names(), set(CATALOG))

    def test_selected_schema_is_native_function_tool(self):
        tool = ToolRegistry().openai_tools(["get_entity"])[0]
        self.assertEqual("function", tool["type"])
        self.assertEqual(["section", "name"], tool["function"]["parameters"]["required"])

    def test_v2_prompt_and_context_files_are_ascii_english(self):
        root = Path(__file__).resolve().parents[1] / "sc2_agents" / "v2"
        for folder in (root / "prompts", root / "context"):
            for path in folder.glob("*.md"):
                path.read_text(encoding="utf-8").encode("ascii")
        for summary in CATALOG.values():
            summary.encode("ascii")


class V2FlowTests(unittest.TestCase):
    def test_main_is_isolated_from_tools_and_raw_results(self):
        with tempfile.TemporaryDirectory() as directory:
            recorder = V2TraceRecorder("test", log_dir=directory)
            invoker = FakeInvoker()
            subagent = DataSubAgent(invoker, recorder)
            mainagent = MainAgent(invoker, recorder)
            answer, decisions, sessions = mainagent.run("Tell me about Probe.", subagent.run)
            self.assertIn("50 minerals", answer)
            self.assertEqual(2, len(decisions))
            self.assertEqual(1, len(sessions))
            main_requests = [call for call in invoker.calls if call["phase"].startswith("main_round")]
            self.assertTrue(all(not call["tools"] for call in main_requests))
            serialized = json.dumps(main_requests)
            self.assertNotIn('"tool_calls"', serialized)
            self.assertNotIn('"minerals": 50', serialized)
            tool_requests = [call for call in invoker.calls if "tool_round" in call["phase"]]
            self.assertTrue(tool_requests[0]["tools"])


if __name__ == "__main__":
    unittest.main()
