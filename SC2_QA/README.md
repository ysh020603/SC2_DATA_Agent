# SC2 Multi-Hop QA Evaluation

This directory contains a 60-question StarCraft II multi-hop QA dataset and a resumable LLM evaluation pipeline. The pipeline evaluates one answer mode at a time:

- **Agent mode** sends each dataset question to the repository's SC2 Data Agent, including its own router, skills, planner, deterministic tools, and answer stage.
- **Plain mode** sends the exact dataset question directly to one configured OpenAI-compatible model without a system message, tools, skills, reference data, or additional answer guidance.

Both modes use a separately selected Judge LLM to score the resulting answer against the reference answer and atomic scoring criteria. There is intentionally no combined or comparison mode. Agent and Plain experiments are independent runs with independent logs and reports.

## Dataset

The active dataset is:

```text
SC2_QA/qa_multihop_sc2_60.json
```

It contains:

- 60 English questions;
- 20 Terran, 20 Protoss, and 20 Zerg questions;
- 24 three-hop, 24 four-hop, and 12 five-hop questions;
- 57 questions worth five points and 3 questions worth four points.

Every question record contains:

| Field | Purpose |
|---|---|
| `id` | Stable race-prefixed case identifier |
| `race` | Terran, Protoss, or Zerg |
| `question` | Exact text supplied to the answer model |
| `standard_answer` | Reference answer visible only to the Judge stage |
| `scoring` | Four or five atomic scoring criteria |
| `reasoning_path` | Auditable graph path; never supplied to an answer model |
| `metadata` | Hop count, endpoints, and relation pattern |

The scoring criteria cover endpoint names, mineral cost, gas cost, maximum health, armor, and—in three Upgrade cases—research time.

## Strict answer-input contract

The answer model receives only the value of `case["question"]`.

The following data is never supplied to an answer model:

- `standard_answer`;
- `scoring`;
- expected answers or evidence values;
- `reasoning_path`;
- hop count, terminal entity, or relation pattern;
- extra instructions such as "think step by step," "answer concisely," or output-format guidance.

Each result stores the exact answer input and its SHA-256 digest:

```json
{
  "answer_input_source": "question",
  "answer_input_text": "<exact dataset question>",
  "answer_input_sha256": "...",
  "extra_answer_guidance": false
}
```

This contract is enforced by the `AnswerInput` data type, which contains only `case_id` and `question`.

## Agent mode

Agent mode calls the repository Agent with the original question:

```python
run_agent(
    case["question"],
    provider=answer_model_key,
    enable_reasoning=reasoning_enabled,
    response_language="English",
    log_dir=case_agent_log_directory,
)
```

The evaluator adds no textual guidance. The Agent may use only its normal internal behavior:

1. context routing;
2. main and optional skills;
3. race dictionaries;
4. planning, with the repository's current maximum of 10 planning steps;
5. deterministic SC2 tools;
6. observations from earlier tool calls;
7. its normal final-answer prompt.

The Agent's nested trace is redirected into the evaluation experiment directory instead of the repository's general `logs/` directory.

## Plain mode

Plain mode makes one answer request with exactly this message array:

```json
[
  {
    "role": "user",
    "content": "<exact dataset question>"
  }
]
```

Plain mode does not add a system message. It does not use the SC2 database, tools, skills, Markdown evidence, standard answer, scoring criteria, or reasoning path.

Reasoning mode may change provider request parameters, such as a `thinking` request body, but it never changes the question text. A failed request may be retried only with the same message array.

## Judge stage

The Judge runs only after answer generation. Its input contains:

- the question;
- the candidate answer;
- the standard answer;
- `max_points`;
- every atomic scoring criterion, expected answer, and evidence value.

The hidden `reasoning_path` is not sent to the Judge. Intermediate graph traversal is explicitly outside the scoring scope.

The Judge must return one result for every `point_id` exactly once:

```json
{
  "case_id": "TERRAN_001",
  "point_results": [
    {
      "point_id": "endpoint_name",
      "awarded_points": 1,
      "max_points": 1,
      "candidate_evidence": "FusionCore",
      "reason": "The candidate explicitly identifies FusionCore."
    }
  ],
  "overall_comment": "Brief assessment"
}
```

### Scoring rules

- Every criterion receives either zero or its full point value.
- Partial point values are rejected.
- Equivalent numeric forms such as `150` and `150.0` are accepted.
- Missing facts are not inferred from correct intermediate reasoning.
- Facts outside the scoring criteria do not earn points.
- Style, verbosity, and harmless extra information do not reduce the score.
- Empty or failed answers receive a recorded zero result without spending a Judge request.
- Malformed Judge JSON, missing points, duplicates, or illegal scores trigger a repair retry.
- The evaluator recomputes `earned_points`, `max_points`, accuracy, and full-credit status locally.
- A Judge failure is recorded as `judge_error`; it is not silently converted into a zero score.

## Directory layout

```text
SC2_QA/
├── qa_multihop_sc2_60.json
├── README.md
├── configs/
│   ├── agent.example.json
│   └── plain.example.json
├── evaluation/
│   ├── answer_runners.py
│   ├── cli.py
│   ├── dataset.py
│   ├── experiment.py
│   ├── judge.py
│   ├── recorder.py
│   ├── reporting.py
│   └── schemas.py
├── scripts/
│   ├── run_agent.ps1
│   ├── run_plain.ps1
│   ├── resume_run.ps1
│   └── summarize_run.ps1
└── logs/                         # generated locally and ignored by Git
```

## Prerequisites

Install the repository dependencies from the repository root:

```powershell
cd C:\code\SC2_DATA_Agent
python -m pip install -r requirements.txt
```

Configure answer and Judge models in:

```text
API_config/config.json
```

Model names used by an experiment are keys under `llm_agents_pool`. API credentials remain in the existing ignored configuration and are not copied into `SC2_QA`.

## Experiment configuration

Agent and Plain use separate configuration templates. The `mode` field is a single string and cannot be an array.

```json
{
  "experiment_name": "agent",
  "mode": "agent",
  "answer_model_key": "DeepSeek-V4-flash",
  "judge_model_key": "Kimi-k2.5_think",
  "dataset": "qa_multihop_sc2_60.json",
  "answer_reasoning": "auto",
  "judge_reasoning": "auto",
  "workers": 1,
  "answer_retries": 2,
  "judge_retries": 2,
  "retry_backoff_seconds": 3.0,
  "request_delay_seconds": 0.0,
  "races": [],
  "hop_counts": [],
  "ids": [],
  "limit": null
}
```

Reasoning modes are:

- `auto`: follow the selected model entry's `is_reasoning` value;
- `on`: select the paired `_think` entry when available;
- `off`: select the paired non-thinking entry when available.

Only reasoning exposed by the provider is stored. If no reasoning field or tag is returned, the record contains `reasoning_available: false`.

## Validate without API calls

Validate the dataset, configuration, model keys, and selected cases:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\agent.example.json `
  --validate-only
```

Validation does not create an experiment directory and does not call an API.

## Run Agent evaluation

Using the example configuration:

```powershell
.\SC2_QA\scripts\run_agent.ps1
```

Override model keys and run only two cases:

```powershell
.\SC2_QA\scripts\run_agent.ps1 `
  -AnswerModelKey DeepSeek-V4-flash_think `
  -JudgeModelKey Kimi-k2.5_think `
  -AnswerReasoning on `
  -Limit 2
```

Direct CLI equivalent:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\agent.example.json `
  --mode agent
```

## Run Plain evaluation

Using the example configuration:

```powershell
.\SC2_QA\scripts\run_plain.ps1
```

Override model keys:

```powershell
.\SC2_QA\scripts\run_plain.ps1 `
  -AnswerModelKey Qwen3-8b `
  -JudgeModelKey Kimi-k2.5_think `
  -AnswerReasoning off
```

There is no command that runs Agent and Plain in one experiment. Start separate experiments when both behaviors need evaluation.

## Case filtering

The CLI supports small or targeted runs:

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\agent.example.json `
  --ids TERRAN_001,PROTOSS_003
```

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\plain.example.json `
  --races Zerg `
  --hop-counts 5 `
  --limit 5
```

Filters can also be stored in the configuration file.

## Logs and result files

Every experiment writes only under:

```text
SC2_QA/logs/<experiment_id>/
```

The experiment ID is generated automatically with this format:

```text
{UTC时间}_{mode}_{answer_model_key}_{judge_model_key}_{config指纹}
```

For example:

```text
20260701_103352_agent_Kimi-k2.5_Kimi-k2.5_bbe1c68e
```

`config指纹` is the first 8 characters of the SHA-256 hash of the full experiment configuration JSON.

```text
logs/<experiment_id>/
├── run_config.json
├── manifest.json
├── events.jsonl
├── cases/
│   ├── TERRAN_001.json
│   └── ...
├── agent_traces/                  # populated only in Agent mode
│   └── TERRAN_001/
│       └── YYYY-MM-DD/<agent_run_id>/
│           ├── events.jsonl
│           └── trace.json
├── summary.json
├── summary.csv
└── report.md
```

`events.jsonl` is appended and flushed as the experiment runs. Each case is written atomically to a separate JSON file. A case record contains:

- the complete dataset record for audit;
- exact answer input and hash;
- answer output and provider-visible reasoning;
- API timing and usage metadata where available;
- Agent trace location, planning count, and tool-call count in Agent mode;
- all Judge attempts, Judge reasoning, and validation errors;
- validated point-by-point scores.

Credential-like fields are redacted before serialization. `SC2_QA/logs/` is ignored by Git.

## Resume an interrupted run

Resume skips every case that already has a case JSON file:

```powershell
.\SC2_QA\scripts\resume_run.ps1 `
  -RunDirectory .\SC2_QA\logs\<experiment_id>
```

To rerun cases whose status is `answer_error` or `judge_error`:

```powershell
.\SC2_QA\scripts\resume_run.ps1 `
  -RunDirectory .\SC2_QA\logs\<experiment_id> `
  -RetryFailed
```

Retries never alter the original answer question. Plain retries reuse the same single user message. Agent retries call the normal Agent again with the same question.

## Rebuild reports without API calls

```powershell
.\SC2_QA\scripts\summarize_run.ps1 `
  -RunDirectory .\SC2_QA\logs\<experiment_id>
```

This reads existing case files and rewrites `summary.json`, `summary.csv`, and `report.md`.

## Reported metrics

Each experiment reports only its own mode. No Agent-versus-Plain winner or score-difference metrics are produced.

Metrics include:

- earned and maximum points;
- micro accuracy (`total earned / total possible`);
- macro accuracy (mean per-question accuracy);
- full-credit count and rate;
- results by race;
- results by three-, four-, and five-hop groups;
- results by scoring criterion;
- answer and Judge error counts;
- average answer and Judge latency.
- aggregate answer-model and Judge token usage when the APIs report usage fields.

`summary.csv` contains one row per evaluated case for downstream analysis.

## Concurrency and retries

`workers` defaults to 1. Agent mode may make many API calls per question, so low concurrency is recommended until endpoint rate limits are understood.

`answer_retries` and `judge_retries` count retries after the first attempt. For example, a value of 2 permits at most three total attempts. `retry_backoff_seconds` controls the delay between attempts, while `request_delay_seconds` can pace answer requests.

## Security and evaluation integrity

- Do not commit `API_config/config.json` or `SC2_QA/logs/`.
- Evaluation logs contain full prompts, answers, reference answers, scores, and provider-visible reasoning; treat them as sensitive.
- Use a Judge model different from the answer model when practical.
- The manifest records the dataset SHA-256, Git commit, dirty-worktree status, selected case count, and Agent step limit.
- The evaluator never modifies the QA dataset.
- The answer and Judge stages use separate data contracts so scoring information cannot accidentally enter answer requests.

## Common failures

### Unknown model key

Confirm that both model keys exist under `llm_agents_pool` in `API_config/config.json`. Model keys are case-sensitive.

### Judge error

Inspect the case file's `judgment.attempts`. It contains the raw Judge content, provider-visible reasoning, and the validation error used for a repair attempt.

### Empty reasoning

The provider may not expose reasoning, or the model's `reasoning_extract_mode` may not match its response shape. This does not invalidate the final answer.

### Missing Agent trace

Check the answer record's `error` and `attempts`. Agent trace initialization happens before routing; filesystem or configuration failures are recorded at the case level.
