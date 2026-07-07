# SC2 Agent V1

V1 is the preserved router/planner implementation that existed before the MainAgent plus DataSubAgent architecture.

Use the explicit import when running historical comparisons:

```python
from sc2_agents.v1 import run_agent
```

The complete orchestration runtime snapshot is stored in `legacy_runtime.py`. The package pins the original implementation revision and active dataset in `MANIFEST.json`. It continues to use the shared deterministic query engine, data release, and API client so existing repository scripts remain compatible.
