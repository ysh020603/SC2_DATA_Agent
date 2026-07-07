# SC2 Agent V2.1

V2.1 is an isolated copy of V2. It keeps the same MainAgent plus DataSubAgent architecture and does not modify V1 or V2.

## Main differences from V2

- MainAgent maximum rounds: 20.
- All prompts and static context are English.
- MainAgent has stronger generic guidance for weakly constrained questions, multi-candidate evidence, endpoint-role separation, and best-effort final answers.
- DataSubAgent may return `candidate_entities` with role, supporting relation, fields, and limitations.
- Upgrade field extraction maps research time to `cost.time` when keyed lookups are empty.
- Large production-output results are compacted to preserve full candidate coverage.
- Forward morph candidate discovery is supplemented by production-output candidates when direct relation results are incomplete.

V2.1 does not contain test-case-specific answer rules. Ambiguous questions should receive detailed candidate-aware answers instead of unsupported single-endpoint guesses.

## Usage

```python
from sc2_agent import run_agent

result = run_agent(
    "Which upgrade unlocks an additional ability for a Stalker?",
    provider="Kimi-k2.5",
    enable_reasoning=False,
    response_language="English",
    agent_version="v2.1",
)
```

Direct import:

```python
from sc2_agents.v2_1 import run_agent
```

## Smoke test

```powershell
python -m SC2_QA.evaluation.cli `
  --config SC2_QA\configs\v2_1_kimi_smoke.example.json
```

The smoke set covers upgrade nested time fields, multi-candidate upgrade answers, and production-output candidate coverage.
