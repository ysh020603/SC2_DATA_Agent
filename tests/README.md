# SC2 Agent Test Suite
*Last updated: 2026-06-10*

## Directory Structure

`
tests/
  README.md                   # This file
  run_glm_reasoning_eval.py   # Original GLM eval runner (keyword-based, 30Q)
  run_multihop_cases.py       # Multi-hop stress test cases
  test_set_60.jsonl           # 60-question test set
  _glm_review2.py             # DeepSeek AI review script (60Q, concurrency=5)
  _glm_review.py              # GLM review script (original, rate-limited)
  _check_answers.py           # Answer verification utility

../result/                    # Evaluation results and reports
  glm_review_report.md        # Latest AI review report
  report.md                   # Latest report (symlink)
`

## Test Set: test_set_60.jsonl

60 questions: 20 Terran, 20 Protoss, 20 Zerg.

### Original Categories (30Q, keyword-eval)

| Category | Qty |
|----------|-----|
| production | 5 |
| reverse_source | 7 |
| dependency_impact | 4 |
| ability_profile | 4 |
| research_outputs | 4 |
| addon_branches | 2 |
| gas_units | 2 |
| combat_filter | 1 |
| upgrade_effects | 1 |

### KG-Enhanced Categories (30Q, NEW)

| Category | Qty | KG Relations |
|----------|-----|-------------|
| counter_relations | 9 | hard_counters, soft_counters |
| stat_bonus | 7 | grants_stat_bonus |
| synergy | 6 | synergizes_with |
| garrison | 3 | garrisons_in |
| unlocks_ability | 3 | unlocks_unit_ability |
| enables_morph | 2 | enables_morph |

## Evaluation Tools

### run_glm_reasoning_eval.py (Legacy)

Original 30Q runner using GLM-4.7 with reasoning mode. Keyword-based evaluation. Hardcoded CASES list.

### run_multihop_cases.py

Multi-hop stress test cases for complex SC2 queries involving chained tool calls.

### _glm_review2.py (Latest - Recommended)

60-question AI-powered review using DeepSeek-v4-Flash with reasoning mode. The LLM evaluates answer correctness by comparing agent answers against complete tool results and SC2 knowledge.

- Method: LLM semantic evaluation (not keyword matching)
- Concurrency: 5 (ThreadPoolExecutor)
- Checks: Coverage, numeric accuracy, entity correctness, hallucination
- Output: result/glm_review_report.md
- No writes to test_set_60.jsonl (report only)

`ash
python tests/_glm_review2.py
`

### _glm_review.py (Deprecated)

Original GLM-4.7 review script. Rate-limited and replaced by _glm_review2.py.

### _check_answers.py

Utility to verify answers against evaluation criteria in test_set_60.jsonl.
