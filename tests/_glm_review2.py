#!/usr/bin/env python3
import json, re, sys, time, random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from pathlib import Path
from openai import OpenAI

ROOT = Path(r"D:\SC2\SC2_DATA_Agen")
RAW_DIR = ROOT / "result" / "deepseek-v4-flash_reasoning_english_20260609_233431" / "raw"
TEST_FILE = ROOT / "tests" / "test_set_60.jsonl"

with open(ROOT/"config"/"provider_config.json", encoding="utf-8") as f:
    cfg = json.load(f)
ds = cfg["providers"]["deepseek-v4-flash"]
client = OpenAI(api_key=ds["api_key"], base_url=ds["base_url"], timeout=180)

with open(TEST_FILE, encoding="utf-8") as f:
    cases = {json.loads(l)["id"]: json.loads(l) for l in f}

# files loaded in main()


def format_tool_results(tool_results):
    parts = []
    for tr in tool_results:
        r = tr.get("result", {})
        if isinstance(r, dict) and "results" in r:
            results = r["results"]
            parts.append("Tool " + tr["tool"] + " (" + str(len(results)) + " results):")
            for row in results:
                if isinstance(row, dict):
                    p = row.get("produced", {})
                    a = row.get("ability", {})
                    name = row.get("name") or p.get("name") or a.get("name", "")
                    rel = row.get("relation", "")
                    subj = row.get("subject_name", "")
                    obj = row.get("object_name", "")
                    desc = row.get("description", "")
                    minerals = p.get("minerals") or row.get("minerals", "")
                    gas = p.get("gas") or row.get("gas", "")
                    supply = p.get("supply") or row.get("supply", "")
                    t = p.get("time") or row.get("time", "")
                    energy = a.get("energy_cost", "")
                    crange = a.get("cast_range", "")
                    if name and (minerals != "" or gas != ""):
                        parts.append("  " + str(name) + ": " + str(minerals) + "m/" + str(gas) + "g/" + str(supply) + "s")
                    elif rel and subj and obj:
                        parts.append("  " + str(subj) + " --" + str(rel) + "--> " + str(obj) + (": " + str(desc)[:80] if desc else ""))
                    elif name and (energy != "" or crange != ""):
                        parts.append("  " + str(name) + ": energy=" + str(energy) + " range=" + str(crange))
                    elif name:
                        parts.append("  " + str(name))
                    else:
                        parts.append("  " + str({k:v for k,v in row.items() if v})[:120])
                else:
                    parts.append("  " + str(row)[:100])
        else:
            parts.append("Tool " + tr["tool"] + ": " + str(r)[:300])
    return chr(10).join(parts)


def main():
    files = sorted(RAW_DIR.glob("*.json"))
    # Skip already-reviewed cases (those with list-format eval_criteria in test_set_60)
    reviewed_ids = {c["id"] for c in cases.values() if isinstance(c.get("eval_criteria"), list) and len(c.get("eval_criteria", [])) > 0}
    target_ids = {"P02_robotics_facility_outputs","P04_cybernetics_core_research","P05_cybernetics_core_dependency","P08_protoss_gas_units_sources","P09_forge_upgrade_effects","P10_carrier_reverse_source","P15_protoss_unlocks","P16_warpgate_morph_unlock","P20_protoss_air_upgrades","T02_factory_addon_split","T03_starport_reactor_vs_techlab","T04_battlecruiser_source_prereq","T05_barracks_dependency_impact","T09_barracks_antiair","T15_missileturret_stat_bonus","T17_hellion_morph_unlock","Z04_roach_reverse_source","Z05_infestor_ability_profile","Z06_viper_ability_profile","Z08_lair_dependency_impact","Z11_zergling_counter","Z13_nydus_garrison","Z14_burrow_unlocks","Z19_zerg_air_upgrades"}
    pending_files = [fp for fp in files if fp.stem in target_ids]
    #pending_files
    print("Starting review: " + str(len(files)) + " total, " + str(len(reviewed_ids)) + " already done, " + str(len(pending_files)) + " remaining")
    results_summary = []
    
    # Parallel execution with 5 workers
    def process_one(args):
        i, fp = args
        qid = fp.stem
        try:
            case = cases.get(qid, {})
            with open(fp, encoding="utf-8") as f:
                data = json.load(f)
            question = data["case"]["question"]
            answer = data["result"].get("answer", "")
            race = data["case"].get("race", "?")
            tr_text = format_tool_results(data["result"].get("tool_results", []))
    
            prompt = """You are reviewing a StarCraft II knowledge-base agent answer. Below are:
    
    (1) USER QUESTION
    (2) COMPLETE TOOL RESULTS - all data retrieved from the SC2 database (NOT truncated, use ALL of it)
    (3) AGENT ANSWER - what the agent replied
    
    Your task:
    (A) Check if the agent answer covers what the question asks. If the answer mentions entities or values not in tool results, use your SC2 knowledge to verify: are they correct SC2 facts? If tool results show agent is wrong, flag as incorrect. If agent mentions things beyond tool results but they are factually correct SC2 knowledge, do NOT penalize.
    (B) Verify ALL numeric values (costs, times, ranges, supply, energy, cooldown) are correct against tool results. Flag any mismatches.
    (C) Write a REFERENCE ANSWER that correctly answers the question based on ALL tool results.
    (D) Write EVALUATION CRITERIA: 4-6 specific checkpoints, each listing what entities/values MUST appear in a correct answer.
    
    Respond ONLY with this JSON (no other text):
    {"correct": true or false, "issues": "brief description (empty if correct)", "reference_answer": "concise answer with correct values", "eval_criteria": [{"point": "checkpoint description", "required": ["specific", "values"]}]}
    """
    
            full_prompt = prompt + chr(10) + "QUESTION: " + question + chr(10) + chr(10)
            full_prompt += "TOOL RESULTS:" + chr(10) + tr_text + chr(10) + chr(10)
            full_prompt += "AGENT ANSWER:" + chr(10) + answer
    
            completion = client.chat.completions.create(
                model=ds["model"],
                messages=[{"role": "user", "content": full_prompt}],
                temperature=0.1, max_tokens=8192,
                extra_body={"thinking": {"type": "enabled"}},
            )
            resp = completion.choices[0].message.content or ""
            m = re.search(r"\{.*\}", resp, re.DOTALL)
            if m:
                review = json.loads(m.group())
            else:
                review = {"correct": None, "issues": "Parse error: " + resp[:200], "reference_answer": "", "eval_criteria": []}
        except Exception as e:
            review = {"correct": None, "issues": str(e)[:200], "reference_answer": "", "eval_criteria": []}
    
    # case assembly moved to parallel result handler
        corr = review.get("correct")
        return {"id": qid, "correct": corr, "issues": str(review.get("issues",""))[:200]}, case, review

    # Run all pending
    write_lock = Lock()
    work = [(i+1, fp) for i, fp in enumerate(pending_files)]
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(process_one, w): w for w in work}
        for fut in as_completed(futures):
            w = futures[fut]
            idx = w[0]
            try:
                summary, case, review = fut.result()
                corr = review.get("correct")
            except Exception as e:
                w = futures[fut]
                idx = w[0]
                fp = w[1]
                summary = {"id": fp.stem, "correct": None, "issues": "Worker crash: " + str(e)[:200]}
                case = cases.get(fp.stem, {})
                corr = None
            with write_lock:
                results_summary.append(summary)
            status = "OK" if corr is True else ("FAIL" if corr is False else "ERR")
            print("[{}/{}] {}: {} | {}".format(idx, len(pending_files), summary["id"], status, summary["issues"][:100]), flush=True)
        
    
    
    ok = sum(1 for r in results_summary if r["correct"] is True)
    bad = sum(1 for r in results_summary if r["correct"] is False)
    err = sum(1 for r in results_summary if r["correct"] is None)
    print("")
    print("=== GLM Review Complete ===")
    print("{} OK, {} FAIL, {} PARSE_ERR / {} total".format(ok, bad, err, len(files)))
    print("Updated: " + str(TEST_FILE))
    
    # Write report
    from datetime import datetime
    now = datetime.now()
    report = []
    report.append("# GLM Review Report")
    report.append("**Date**: " + now.strftime("%Y-%m-%d %H:%M"))
    report.append("**Total**: {} | **Correct**: {} | **Incorrect**: {} | **Errors**: {} | **Rate**: {:.1f}%".format(len(files), ok, bad, err, ok*100/len(files)))
    report.append("")
    # By race
    race_map = {}
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            d = json.load(f)
        race = d["case"].get("race", "?")
        qid = fp.stem
        for r in results_summary:
            if r["id"] == qid:
                if race not in race_map: race_map[race] = {"t":0,"c":0}
                race_map[race]["t"] += 1
                if r["correct"]: race_map[race]["c"] += 1
    report.append("## By Race")
    for race in ["Terran","Protoss","Zerg"]:
        rm = race_map.get(race, {"t":0,"c":0})
        report.append("- **{}**: {}/{} ({:.0f}%)".format(race, rm["c"], rm["t"], rm["c"]*100/max(rm["t"],1)))
    report.append("")
    report.append("## Failed / Error Cases")
    for r in results_summary:
        if r["correct"] is not True:
            report.append("- **{}**: {} - {}".format(r["id"], "FAIL" if r["correct"] is False else "ERR", r["issues"][:150]))
    report.append("")
    report.append("## All Results")
    for i, r in enumerate(results_summary):
        status = "OK" if r["correct"] is True else ("FAIL" if r["correct"] is False else "ERR")
        report.append("| {} | {} | {} |".format(i+1, r["id"], status))
    
    report_txt = chr(10).join(report)
    report_path = ROOT / "result" / "glm_review_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_txt)
    print("Report: " + str(report_path))

if __name__ == "__main__":
    main()
