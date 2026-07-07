# SC2 Agent V1 and V2

## Version overview

V1 and V2 share the active SC2 dataset, deterministic query engine, provider configuration, and QA evaluator. They differ only in LLM orchestration.

### V1

V1 preserves the original pipeline:

```text
question -> context router -> planner -> deterministic tools -> planner -> final answer
```

The planner receives tool descriptions and compacted observations. Optional execution-oriented skills and race dictionaries may be loaded by the context router.

Explicit Python entry point:

```python
from sc2_agents.v1 import run_agent
```

The V1 manifest is stored at `sc2_agents/v1/MANIFEST.json`.

### V2

V2 separates orchestration and retrieval:

```text
question -> MainAgent -> focused subquestion -> fresh DataSubAgent session
                                      DataSubAgent -> tool selection
                                                   -> native tool calls
                                                   -> compressed reply
         -> MainAgent -> next subquestion or final answer
```

V2 enforces these boundaries:

- MainAgent receives no tool definitions.
- MainAgent receives no raw tool result.
- Every focused subquestion starts a new DataSubAgent message history.
- DataSubAgent initially sees only the English tool catalog.
- Full JSON schemas are exposed only for the selected tools.
- Native assistant `tool_calls` and `tool` messages are used during execution.
- Only the validated DataSubAgent reply returns to MainAgent.
- Execution-oriented V1 skills and race dictionaries are not loaded.
- All static prompts, contexts, and tool descriptions are English.

V2 limits MainAgent to 12 decisions and each DataSubAgent session to 5 tool rounds. Transient 429, timeout, overloaded, and 5xx model errors receive up to three attempts with a short backoff.

## Command-line usage

Run V2:

```powershell
python sc2_agent.py "Which structure researches Stimpack?" `
  --agent-version v2 `
  --model-key Kimi-k2.5 `
  --reasoning-mode off
```

Run the same question through V1:

```powershell
python sc2_agent.py "Which structure researches Stimpack?" `
  --agent-version v1 `
  --model-key Kimi-k2.5 `
  --reasoning-mode off
```

The CLI defaults to V2. The root Python compatibility function accepts `agent_version="v1"` or `agent_version="v2"`; its default remains V1 to avoid silently changing existing integrations.

## Python usage

Use the compatibility entry point when the version is runtime configuration:

```python
from sc2_agent import run_agent

result = run_agent(
    "Which structure researches Stimpack?",
    provider="Kimi-k2.5",
    enable_reasoning=False,
    response_language="English",
    agent_version="v2",
)
```

Use a versioned import when the version must be fixed in code:

```python
from sc2_agents.v1 import run_agent as run_v1
from sc2_agents.v2 import run_agent as run_v2
```

## Local tests

Run syntax compilation and the V2 protocol tests without API calls:

```powershell
python -m compileall -q sc2_agent.py sc2_agents SC2_QA
python -m unittest discover -s tests -v
```

The tests verify catalog/dispatcher parity, native tool schemas, English-only V2 prompt files, JSON contracts, MainAgent tool isolation, and the standard SubAgent tool message sequence.

## QA evaluation

The QA evaluator has an `agent_version` field and a matching `--agent-version` override. Run V1 and V2 as separate experiments so each version retains independent traces and reports.

### Kimi request limit and concurrency

All Kimi model keys, including thinking and non-thinking variants used for answers or judging, share one cross-process rolling-window limiter. The provider ceiling is 60 requests per minute; the repository defaults to 58 requests per minute to retain clock and transport headroom. Retries also consume a slot. DeepSeek, Qwen, Gemini, and other providers bypass this limiter.

The limiter state is stored under the ignored `logs/.rate_limits/` directory and is shared by concurrent evaluator threads and sequential Python processes. Override the conservative default only when necessary:

```powershell
$env:SC2_KIMI_RPM = "58"  # valid range: 1 through 60
```

Recommended evaluator concurrency is four workers for Agent experiments and eight workers for Plain experiments. Agent requests are multi-step and naturally occupy workers longer; Plain requests are single-call and benefit from wider concurrency. The shared limiter queues only Kimi calls, so other provider requests continue without an artificial rate delay.

Validate a V2 configuration without API calls:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\agent.example.json `
  --agent-version v2 `
  --validate-only
```

Run three non-thinking Kimi smoke cases covering 3, 4, and 5 hops:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\v2_kimi_smoke.example.json
```

Run the same selected cases with V1:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\v2_kimi_smoke.example.json `
  --agent-version v1
```

For a full 60-case comparison, create separate V1 and V2 configurations with empty `ids` and `limit: null`, then run each configuration independently. Compare their generated `summary.json` files. Do not reuse one experiment directory across versions.

## Verified Kimi smoke run

On 2026-07-06, V2 was exercised with `Kimi-k2.5`, answer reasoning off, and Judge reasoning off:

| Case | Race | Hops | Verified score |
|---|---|---:|---:|
| `TERRAN_001` | Terran | 3 | 5/5 after the canonical-name follow-up verification |
| `PROTOSS_009` | Protoss | 4 | 5/5 |
| `ZERG_019` | Zerg | 5 | 5/5 |

All three stable smoke cases were individually verified at 5/5 with zero answer and Judge errors. `ZERG_017` and `ZERG_018` are intentionally excluded from the stable smoke gate because their question text does not uniquely select the hidden generated path. They remain useful for exploratory robustness testing, but not as deterministic release gates. Generated experiment logs remain local under `SC2_QA/logs/` and are not committed.
