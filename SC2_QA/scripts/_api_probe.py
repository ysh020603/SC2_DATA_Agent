"""Exit 0 if a Kimi-k2.5 call succeeds, else exit 1. Used for stability gating."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from API_Tools.llm_caller import call_openai_detailed

result = call_openai_detailed(
    [{"role": "user", "content": "ok"}],
    model_key="Kimi-k2.5",
    is_reasoning=False,
)
sys.exit(0 if (not result.get("error") and result.get("content")) else 1)
