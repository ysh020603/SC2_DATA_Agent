#!/usr/bin/env python3
"""Serial GLM reasoning evaluation for the multi-hop SC2 Agent."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import sc2_agent  # noqa: E402


DEFAULT_PROVIDER = "glm-4.7"
RESPONSE_LANGUAGE = "English"


CASES: list[dict[str, Any]] = [
    {
        "id": "T01_barracks_outputs",
        "race": "Terran",
        "question": "What units can a Terran Barracks produce, and what are their mineral, gas, and supply costs?",
        "expected_tools": ["query_production_outputs"],
        "result_keywords": ["Barracks", "Marine", "Marauder", "Reaper", "Ghost"],
        "answer_keywords": ["Marine", "Marauder", "Reaper", "Ghost"],
    },
    {
        "id": "T02_factory_addon_split",
        "race": "Terran",
        "question": "For a Terran Factory, which units are available with a Tech Lab and which are available without a Tech Lab?",
        "expected_tools": ["query_addon_branches"],
        "result_keywords": ["Factory", "Hellion", "SiegeTank", "Thor", "TechLab"],
        "answer_keywords": ["Hellion", "Siege Tank", "Thor", "Tech Lab"],
    },
    {
        "id": "T03_starport_reactor_vs_techlab",
        "race": "Terran",
        "question": "Which Terran Starport units are Reactor-compatible, and which Starport units require a Tech Lab?",
        "expected_tools": ["query_addon_branches"],
        "result_keywords": ["Starport", "Medivac", "VikingFighter", "Banshee", "Raven"],
        "answer_keywords": ["Medivac", "Viking", "Banshee", "Raven"],
    },
    {
        "id": "T04_battlecruiser_source_prereq",
        "race": "Terran",
        "question": "Where is a Battlecruiser produced, what prerequisites does it require, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources", "query_tech_tree"],
        "result_keywords": ["Battlecruiser", "Starport", "FusionCore"],
        "answer_keywords": ["Battlecruiser", "Starport", "Fusion Core"],
    },
    {
        "id": "T05_barracks_dependency_impact",
        "race": "Terran",
        "question": "If the Terran Barracks is missing, which units, buildings, and upgrades become affected downstream?",
        "expected_tools": ["query_dependency_impact", "query_tech_tree"],
        "result_keywords": ["Barracks", "Factory", "Stimpack"],
        "answer_keywords": ["Factory", "Stimpack"],
    },
    {
        "id": "T06_ghost_ability_profile",
        "race": "Terran",
        "question": "What abilities does Ghost have, and for each ability what are the energy, range, cooldown, and target type?",
        "expected_tools": ["query_unit_abilities"],
        "result_keywords": ["Ghost", "EMP_EMP", "EFFECT_GHOSTSNIPE"],
        "answer_keywords": ["Ghost", "EMP", "Snipe"],
    },
    {
        "id": "T07_terran_techlab_research",
        "race": "Terran",
        "question": "Which Terran upgrades require a Tech Lab, and which research building or add-on provides them?",
        "expected_tools": ["query_research_outputs"],
        "result_keywords": ["Stimpack", "BansheeCloak", "TechLab"],
        "answer_keywords": ["Stimpack", "Banshee", "Tech Lab"],
    },
    {
        "id": "T08_marauder_reverse_source",
        "race": "Terran",
        "question": "A Marauder comes from which production building, what add-on is required, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["Marauder", "Barracks", "TechLab"],
        "answer_keywords": ["Marauder", "Barracks", "Tech Lab"],
    },
    {
        "id": "T09_barracks_antiair",
        "race": "Terran",
        "question": "Using only the Barracks production path, which Terran units can attack air, and what are their costs and ranges?",
        "expected_tools": ["query_combat_production_options"],
        "result_keywords": ["Barracks", "Marine"],
        "answer_keywords": ["Marine", "air"],
    },
    {
        "id": "T10_terran_gas_units_sources",
        "race": "Terran",
        "question": "List Terran units that cost gas, and include their production source, add-on requirement, and tech chain evidence.",
        "expected_tools": ["query_gas_units_with_sources"],
        "result_keywords": ["Marauder", "Reaper", "Starport"],
        "answer_keywords": ["Marauder", "Reaper", "Starport"],
    },
    {
        "id": "P01_gateway_outputs",
        "race": "Protoss",
        "question": "What units can a Protoss Gateway produce, and what are their mineral, gas, and supply costs?",
        "expected_tools": ["query_production_outputs"],
        "result_keywords": ["Gateway", "Zealot", "Stalker", "Sentry", "HighTemplar"],
        "answer_keywords": ["Zealot", "Stalker", "Sentry"],
    },
    {
        "id": "P02_robotics_facility_outputs",
        "race": "Protoss",
        "question": "What units can a Protoss Robotics Facility produce, and what are their costs, supply, and prerequisites?",
        "expected_tools": ["query_production_outputs"],
        "result_keywords": ["RoboticsFacility", "Observer", "Immortal", "Colossus", "WarpPrism"],
        "answer_keywords": ["Observer", "Immortal", "Colossus", "Warp Prism"],
    },
    {
        "id": "P03_stargate_outputs",
        "race": "Protoss",
        "question": "What air units can a Protoss Stargate produce, and what are their costs and supply?",
        "expected_tools": ["query_production_outputs"],
        "result_keywords": ["Stargate", "Phoenix", "VoidRay", "Carrier", "Tempest"],
        "answer_keywords": ["Phoenix", "Void Ray", "Carrier", "Tempest"],
    },
    {
        "id": "P04_cybernetics_core_research",
        "race": "Protoss",
        "question": "Which upgrades can the Protoss Cybernetics Core research, and what are their costs?",
        "expected_tools": ["query_research_outputs"],
        "result_keywords": ["CyberneticsCore", "WarpGateResearch", "ProtossAirWeaponsLevel1"],
        "answer_keywords": ["Warp Gate", "Air Weapons"],
    },
    {
        "id": "P05_cybernetics_core_dependency",
        "race": "Protoss",
        "question": "If the Protoss Cybernetics Core is destroyed, which units and upgrades are affected downstream?",
        "expected_tools": ["query_dependency_impact", "query_tech_tree"],
        "result_keywords": ["CyberneticsCore", "Stalker", "Stargate", "WarpGateResearch"],
        "answer_keywords": ["Stalker", "Stargate", "Warp Gate"],
    },
    {
        "id": "P06_stalker_reverse_source",
        "race": "Protoss",
        "question": "Where is a Stalker produced, what prerequisite does it require, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["Stalker", "Gateway", "CyberneticsCore"],
        "answer_keywords": ["Stalker", "Gateway", "Cybernetics Core"],
    },
    {
        "id": "P07_oracle_ability_profile",
        "race": "Protoss",
        "question": "What abilities does Oracle have, and what are their target types, ranges, and energy costs?",
        "expected_tools": ["query_unit_abilities"],
        "result_keywords": ["Oracle", "ORACLEREVELATION_ORACLEREVELATION", "BUILD_STASISTRAP"],
        "answer_keywords": ["Oracle", "Revelation", "Stasis"],
    },
    {
        "id": "P08_protoss_gas_units_sources",
        "race": "Protoss",
        "question": "Find Protoss units that cost gas and explain their production source and tech chain evidence.",
        "expected_tools": ["query_gas_units_with_sources"],
        "result_keywords": ["Colossus", "Mothership", "RoboticsFacility"],
        "answer_keywords": ["Colossus", "Mothership", "Robotics"],
    },
    {
        "id": "P09_forge_upgrade_effects",
        "race": "Protoss",
        "question": "Which Protoss units are affected by Forge ground weapon, armor, or shield upgrades, and where are those units produced?",
        "expected_tools": ["query_upgrade_effects"],
        "result_keywords": ["ProtossGroundWeaponsLevel1", "Zealot", "DarkTemplar", "Archon"],
        "answer_keywords": ["Zealot", "Dark Templar", "Archon"],
    },
    {
        "id": "P10_carrier_reverse_source",
        "race": "Protoss",
        "question": "Where is a Carrier produced, what prerequisite building does it require, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["Carrier", "Stargate", "FleetBeacon"],
        "answer_keywords": ["Carrier", "Stargate", "Fleet Beacon"],
    },
    {
        "id": "Z01_larva_morph_outputs",
        "race": "Zerg",
        "question": "What units can Zerg Larva morph into, and what are their mineral, gas, and supply costs?",
        "expected_tools": ["query_production_outputs"],
        "result_keywords": ["Larva", "Drone", "Zergling", "Roach", "Hydralisk"],
        "answer_keywords": ["Drone", "Zergling", "Roach", "Hydralisk"],
    },
    {
        "id": "Z02_spawning_pool_research",
        "race": "Zerg",
        "question": "Which upgrades can the Zerg Spawning Pool research, and what are their costs?",
        "expected_tools": ["query_research_outputs"],
        "result_keywords": ["SpawningPool", "zerglingmovementspeed", "zerglingattackspeed"],
        "answer_keywords": ["Zergling", "movement", "attack"],
    },
    {
        "id": "Z03_spawning_pool_dependency",
        "race": "Zerg",
        "question": "If the Zerg Spawning Pool is destroyed, which units and upgrades are affected downstream?",
        "expected_tools": ["query_dependency_impact", "query_tech_tree"],
        "result_keywords": ["SpawningPool", "Baneling", "Roach", "zerglingmovementspeed"],
        "answer_keywords": ["Baneling", "Roach", "Zergling"],
    },
    {
        "id": "Z04_roach_reverse_source",
        "race": "Zerg",
        "question": "Where is a Roach produced from, what prerequisite does it require, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["Roach", "Larva", "RoachWarren"],
        "answer_keywords": ["Roach", "Larva", "Roach Warren"],
    },
    {
        "id": "Z05_infestor_ability_profile",
        "race": "Zerg",
        "question": "What abilities does Infestor have, and what are their target types, ranges, and energy costs?",
        "expected_tools": ["query_unit_abilities"],
        "result_keywords": ["Infestor", "FUNGALGROWTH_FUNGALGROWTH", "NEURALPARASITE_NEURALPARASITE"],
        "answer_keywords": ["Infestor", "Fungal", "Neural"],
    },
    {
        "id": "Z06_viper_ability_profile",
        "race": "Zerg",
        "question": "What abilities does Viper have, and what are their target types, ranges, and energy costs?",
        "expected_tools": ["query_unit_abilities"],
        "result_keywords": ["Viper", "BLINDINGCLOUD_BLINDINGCLOUD", "EFFECT_ABDUCT", "PARASITICBOMB_PARASITICBOMB"],
        "answer_keywords": ["Viper", "Blinding", "Abduct", "Parasitic"],
    },
    {
        "id": "Z07_evolution_chamber_research",
        "race": "Zerg",
        "question": "Which upgrades can the Zerg Evolution Chamber research, and what are the Lair or Hive prerequisites for higher levels?",
        "expected_tools": ["query_research_outputs"],
        "result_keywords": ["EvolutionChamber", "ZergMeleeWeaponsLevel1", "ZergGroundArmorsLevel1", "Lair", "Hive"],
        "answer_keywords": ["Evolution Chamber", "Melee", "Ground Armor", "Lair", "Hive"],
    },
    {
        "id": "Z08_lair_dependency_impact",
        "race": "Zerg",
        "question": "If Zerg Lair tech is missing, which units and upgrades are affected downstream?",
        "expected_tools": ["query_dependency_impact", "query_tech_tree"],
        "result_keywords": ["Lair", "Infestor", "EvolutionChamber"],
        "answer_keywords": ["Lair", "Infestor"],
    },
    {
        "id": "Z09_mutalisk_reverse_source",
        "race": "Zerg",
        "question": "Where does a Mutalisk come from, what prerequisite building does it require, and what does it cost?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["Mutalisk", "Larva", "Spire"],
        "answer_keywords": ["Mutalisk", "Larva", "Spire"],
    },
    {
        "id": "Z10_broodlord_reverse_source",
        "race": "Zerg",
        "question": "Where does a Brood Lord come from, what prerequisite building does it require, and what morph ability creates it?",
        "expected_tools": ["query_reverse_production_sources"],
        "result_keywords": ["BroodLord", "Corruptor", "GreaterSpire", "MORPHTOBROODLORD_BROODLORD"],
        "answer_keywords": ["Brood Lord", "Corruptor", "Greater Spire"],
    },
]


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def contains_keyword(text: str, keyword: str) -> bool:
    lower_text = text.lower()
    lower_keyword = keyword.lower()
    if lower_keyword in lower_text:
        return True
    keyword_norm = normalized(keyword)
    return bool(keyword_norm and keyword_norm in normalized(text))


def missing_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if not contains_keyword(text, keyword)]


def collect_plan_errors(result: dict[str, Any]) -> list[str]:
    errors = []
    for step in result.get("plan", {}).get("steps", []):
        if isinstance(step, dict) and step.get("planner_error"):
            errors.append(str(step["planner_error"]))
    for item in result.get("tool_results", []):
        if isinstance(item, dict) and item.get("error"):
            errors.append(str(item["error"]))
    answer = result.get("answer", "")
    if "LLM planning or summarization failed" in answer:
        errors.append("LLM planning or summarization failed")
    return errors


def evaluate_case(case: dict[str, Any], result: dict[str, Any], duration_seconds: float) -> dict[str, Any]:
    called_tools = [item.get("tool") for item in result.get("tool_results", []) if isinstance(item, dict)]
    result_text = json.dumps(result.get("tool_results", []), ensure_ascii=False)
    answer_text = str(result.get("answer", ""))
    expected_tools = case.get("expected_tools") or []

    tool_ok = not expected_tools or any(tool in called_tools for tool in expected_tools)
    result_missing = missing_keywords(result_text, case.get("result_keywords", []))
    answer_missing = missing_keywords(answer_text, case.get("answer_keywords", []))
    errors = collect_plan_errors(result)
    passed = bool(result.get("tool_results")) and tool_ok and not result_missing and not answer_missing and not errors

    return {
        "id": case["id"],
        "race": case["race"],
        "question": case["question"],
        "passed": passed,
        "duration_seconds": round(duration_seconds, 2),
        "called_tools": called_tools,
        "expected_tools": expected_tools,
        "tool_ok": tool_ok,
        "result_missing": result_missing,
        "answer_missing": answer_missing,
        "errors": errors,
        "answer_preview": answer_text[:500],
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "id",
        "race",
        "passed",
        "duration_seconds",
        "called_tools",
        "expected_tools",
        "tool_ok",
        "result_missing",
        "answer_missing",
        "errors",
        "question",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row.get(key), ensure_ascii=False) if isinstance(row.get(key), list) else row.get(key) for key in fieldnames})


def install_pre_request_delay(delay_seconds: float) -> None:
    if delay_seconds <= 0:
        return
    original_call_llm = sc2_agent.call_llm

    def delayed_call_llm(*args: Any, **kwargs: Any) -> str:
        time.sleep(delay_seconds)
        return original_call_llm(*args, **kwargs)

    sc2_agent.call_llm = delayed_call_llm


def load_existing_payload(raw_dir: Path, case_id: str) -> dict[str, Any] | None:
    path = raw_dir / f"{case_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def make_report(
    run_dir: Path,
    started_at: str,
    finished_at: str,
    rows: list[dict[str, Any]],
    provider: str,
    concurrency: int,
    pre_request_delay: float,
) -> str:
    total = len(rows)
    passed = sum(1 for row in rows if row["passed"])
    race_lines = []
    for race in ["Terran", "Protoss", "Zerg"]:
        race_rows = [row for row in rows if row["race"] == race]
        race_passed = sum(1 for row in race_rows if row["passed"])
        race_lines.append(f"| {race} | {race_passed}/{len(race_rows)} |")

    failed_rows = [row for row in rows if not row["passed"]]
    if failed_rows:
        failure_section = "\n".join(
            [
                "| Case | Race | Called tools | Missing in retrieval | Missing in answer | Errors |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            + [
                f"| {row['id']} | {row['race']} | `{', '.join(row['called_tools'])}` | "
                f"{', '.join(row['result_missing']) or '-'} | {', '.join(row['answer_missing']) or '-'} | "
                f"{'; '.join(row['errors']) or '-'} |"
                for row in failed_rows
            ]
        )
    else:
        failure_section = "无失败用例。"

    case_lines = [
        "| Case | Race | Result | Tools | Time(s) |",
        "| --- | --- | --- | --- | ---: |",
    ]
    for row in rows:
        status = "通过" if row["passed"] else "失败"
        case_lines.append(
            f"| {row['id']} | {row['race']} | {status} | `{', '.join(row['called_tools'])}` | {row['duration_seconds']} |"
        )

    return f"""# SC2 多跳 Agent GLM Reasoning English 测试报告

## 测试设置

- 测试时间：{started_at} 至 {finished_at}
- Provider：`{provider}`
- 模式：`reasoning=True`
- Agent 回答语言：`English`
- 执行方式：30 个问题调用主 Agent，并发数 `{concurrency}`，每题保存完整 raw JSON。
- 测试请求前等待：`{pre_request_delay}` 秒，仅在本评测脚本中生效。
- 结果目录：`{run_dir.as_posix()}`

## 总体结论

- 总通过率：{passed}/{total}
- 判定规则：同时检查是否调用了预期多跳工具、工具结果是否包含关键事实、最终英文回答是否覆盖关键事实、是否存在 LLM/工具错误。

| 种族 | 通过数 |
| --- | ---: |
{chr(10).join(race_lines)}

## 失败项

{failure_section}

## 明细

{chr(10).join(case_lines)}

## 说明

本次测试的准确性判定以结构化工具结果为主要证据，最终回答覆盖作为第二层验证。这样可以避免只看自然语言总结时把“检索正确但总结漏写”和“检索链路错误”混在一起。
"""


def run_one_case(
    case: dict[str, Any],
    provider: str,
    raw_dir: Path,
) -> dict[str, Any]:
    begin = time.perf_counter()
    try:
        result = sc2_agent.run_agent(
            case["question"],
            provider=provider,
            dry_run=False,
            enable_reasoning=True,
            response_language=RESPONSE_LANGUAGE,
        )
    except Exception as exc:  # noqa: BLE001
        result = {
            "query": case["question"],
            "plan": {"steps": []},
            "tool_results": [],
            "answer": "",
            "fatal_error": repr(exc),
        }
    duration = time.perf_counter() - begin
    if result.get("fatal_error"):
        evaluation = {
            "id": case["id"],
            "race": case["race"],
            "question": case["question"],
            "passed": False,
            "duration_seconds": round(duration, 2),
            "called_tools": [],
            "expected_tools": case.get("expected_tools", []),
            "tool_ok": False,
            "result_missing": case.get("result_keywords", []),
            "answer_missing": case.get("answer_keywords", []),
            "errors": [result["fatal_error"]],
            "answer_preview": "",
        }
    else:
        evaluation = evaluate_case(case, result, duration)

    raw_payload = {"case": case, "evaluation": evaluation, "result": result}
    (raw_dir / f"{case['id']}.json").write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reasoning evaluation for the SC2 Agent.")
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N cases.")
    parser.add_argument("--case-id", default=None, help="Run one specific case id.")
    parser.add_argument("--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--delay", type=float, default=1.5, help="Seconds to sleep between API calls.")
    parser.add_argument("--pre-request-delay", type=float, default=5.0, help="Seconds to sleep before every LLM request in this test.")
    parser.add_argument("--resume-dir", default=None, help="Reuse a previous result run dir; passed cases are skipped, failed cases rerun.")
    args = parser.parse_args()
    install_pre_request_delay(args.pre_request_delay)

    cases = CASES
    if args.case_id:
        cases = [case for case in cases if case["id"] == args.case_id]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        raise SystemExit("No cases selected.")

    started = datetime.now()
    run_id = started.strftime("%Y%m%d_%H%M%S")
    result_root = ROOT / "result"
    provider_slug = re.sub(r"[^a-zA-Z0-9_.-]+", "_", args.provider)
    run_dir = Path(args.resume_dir).resolve() if args.resume_dir else result_root / f"{provider_slug}_reasoning_english_{run_id}"
    raw_dir = run_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    pending_cases: list[tuple[int, dict[str, Any]]] = []
    for index, case in enumerate(cases, start=1):
        existing_payload = load_existing_payload(raw_dir, case["id"]) if args.resume_dir else None
        if existing_payload and existing_payload.get("result"):
            old_duration = float((existing_payload.get("evaluation") or {}).get("duration_seconds") or 0)
            old_evaluation = evaluate_case(case, existing_payload["result"], old_duration)
            if old_evaluation["passed"]:
                rows.append(old_evaluation)
                print(f"[{index}/{len(cases)}] {case['id']} ({case['race']})", flush=True)
                print(f"  -> SKIP PASS; tools={old_evaluation['called_tools']}", flush=True)
                continue

        pending_cases.append((index, case))

    rows_by_id = {row["id"]: row for row in rows}
    print_lock = Lock()

    def run_and_log(index: int, case: dict[str, Any]) -> dict[str, Any]:
        with print_lock:
            print(f"[{index}/{len(cases)}] {case['id']} ({case['race']})", flush=True)
        evaluation = run_one_case(case, args.provider, raw_dir)
        with print_lock:
            print(
                f"  -> {case['id']} {'PASS' if evaluation['passed'] else 'FAIL'}; tools={evaluation['called_tools']}; "
                f"missing_result={evaluation['result_missing']}; missing_answer={evaluation['answer_missing']}; "
                f"errors={evaluation['errors']}",
                flush=True,
            )
        return evaluation

    if pending_cases:
        max_workers = max(1, args.concurrency)
        if max_workers == 1:
            for index, case in pending_cases:
                evaluation = run_and_log(index, case)
                rows_by_id[evaluation["id"]] = evaluation
                if args.delay > 0:
                    time.sleep(args.delay)
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(run_and_log, index, case) for index, case in pending_cases]
                for future in as_completed(futures):
                    evaluation = future.result()
                    rows_by_id[evaluation["id"]] = evaluation

    rows = [rows_by_id[case["id"]] for case in cases if case["id"] in rows_by_id]

    finished = datetime.now()
    summary = {
        "provider": args.provider,
        "reasoning": True,
        "response_language": RESPONSE_LANGUAGE,
        "concurrency": args.concurrency,
        "pre_request_delay": args.pre_request_delay,
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "total": len(rows),
        "passed": sum(1 for row in rows if row["passed"]),
        "rows": rows,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(run_dir / "summary.csv", rows)

    report = make_report(
        run_dir,
        summary["started_at"],
        summary["finished_at"],
        rows,
        provider=args.provider,
        concurrency=args.concurrency,
        pre_request_delay=args.pre_request_delay,
    )
    (run_dir / "report.md").write_text(report, encoding="utf-8")
    (result_root / "report.md").write_text(report, encoding="utf-8")
    (result_root / "latest_run.txt").write_text(str(run_dir), encoding="utf-8")
    print(f"\nReport: {run_dir / 'report.md'}", flush=True)
    print(f"Passed: {summary['passed']}/{summary['total']}", flush=True)


if __name__ == "__main__":
    main()
