#!/usr/bin/env python3
import json, time, random, re, sys
from pathlib import Path
from openai import OpenAI

ROOT = Path(r"D:\SC2\SC2_DATA_Agen")
RAW_DIR = ROOT / "result" / "deepseek-v4-flash_reasoning_english_20260609_233431" / "raw"
TEST_FILE = ROOT / "test_set_60.jsonl"

with open(ROOT/"config"/"provider_config.json", encoding="utf-8") as f:
    cfg = json.load(f)
glm = cfg["providers"]["glm-4.7"]
client = OpenAI(api_key=glm["api_key"], base_url=glm["base_url"], timeout=120)

with open(TEST_FILE, encoding="utf-8") as f:
    cases = {json.loads(l)["id"]: json.loads(l) for l in f}

files = sorted(RAW_DIR.glob("*.json"))
print(f"Starting GLM review of {len(files)} cases")

out = []
results_summary = []
for i, fp in enumerate(files):
    qid = fp.stem
    try:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        question = data["case"]["question"]
        answer = data["result"].get("answer", "")

        tr_text = ""
        for tr in data["result"].get("tool_results", []):
            r = tr.get("result", {})
            if isinstance(r, dict) and "results" in r:
                tr_text += "Tool " + tr["tool"] + ": " + json.dumps(r["results"][:8], ensure_ascii=False) + chr(10)
            else:
                tr_text += "Tool " + tr["tool"] + ": " + str(r)[:300] + chr(10)

        prompt = ("You are reviewing an SC2 knowledge-base agent answer. Below are: (1) User question, (2) Data retrieved from SC2 database, (3) Agent answer.\n"
            "Your job: (A) Check if agent answer covers what question asks, and if ALL numeric values are CORRECT per tool results.\n"
            "(B) Write a REFERENCE ANSWER based on tool results that correctly answers the question.\n"
            "(C) Write EVALUATION CRITERIA: list 4-6 specific checkpoints with entities/values that MUST appear.\n"
            "Respond ONLY in JSON: " + json.dumps({"correct":True,"issues":"","reference_answer":"...","eval_criteria":[{"point":"desc","required":["val1","val2"]}]}) + "\n\n"
            "Question: " + question + "\n"
            "Tool Results: " + tr_text[:2500] + "\n"
            "Agent Answer: " + answer[:1500])

        completion = client.chat.completions.create(
            model=glm["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1, max_tokens=4096,
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

    case = cases.get(qid, {})
    case["reference_answer"] = review.get("reference_answer", "")
    case["eval_criteria"] = review.get("eval_criteria", [])
    if review.get("correct") is None:
        case["reference_answer"] = ""
        case["eval_criteria"] = []
    out.append(case)
    status = "OK" if review.get("correct") else ("FAIL" if review.get("correct") is False else "ERR")
    print("[{}/{}] {}: {} | {}".format(i+1, len(files), qid, status, str(review.get("issues",""))[:100]), flush=True)
    results_summary.append({"id": qid, "correct": review.get("correct"), "issues": str(review.get("issues",""))[:200]})
    time.sleep(random.uniform(5, 10))

with open(TEST_FILE, "w", encoding="utf-8") as f:
    for c in out:
        f.write(json.dumps(c, ensure_ascii=False) + chr(10))

correct = sum(1 for r in results_summary if r["correct"] is True)
failed = sum(1 for r in results_summary if r["correct"] is False)
errors = sum(1 for r in results_summary if r["correct"] is None)
print("")
print("GLM Review Complete: {} correct, {} incorrect, {} errors / {} total".format(correct, failed, errors, len(files)))