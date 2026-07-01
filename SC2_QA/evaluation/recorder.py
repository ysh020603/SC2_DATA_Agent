"""Crash-resilient experiment logging inside SC2_QA/logs."""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


QA_DIR = Path(__file__).resolve().parents[1]
DEFAULT_LOG_ROOT = QA_DIR / "logs"
SECRET_RE = re.compile(
    r"(^|[_-])(api[_-]?key|authorization|access[_-]?token|auth[_-]?token|secret|password)($|[_-])",
    re.IGNORECASE,
)


def json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, BaseException):
        return {"type": type(value).__name__, "message": str(value)}
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if SECRET_RE.search(str(key)) else json_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    for method_name in ("model_dump", "dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            try:
                return json_safe(method())
            except Exception:
                pass
    return repr(value)


def slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_.-")
    return cleaned or "experiment"


class EvaluationRecorder:
    def __init__(self, experiment_id: str, run_dir: str | Path | None = None) -> None:
        self.run_dir = Path(run_dir).resolve() if run_dir else (DEFAULT_LOG_ROOT / experiment_id).resolve()
        self.cases_dir = self.run_dir / "cases"
        self.agent_traces_dir = self.run_dir / "agent_traces"
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cases_dir.mkdir(exist_ok=True)
        self.agent_traces_dir.mkdir(exist_ok=True)
        self.events_path = self.run_dir / "events.jsonl"
        self.lock = threading.Lock()

    def event(self, event_type: str, payload: Any = None) -> None:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": event_type,
            "payload": json_safe(payload or {}),
        }
        line = json.dumps(event, ensure_ascii=False)
        with self.lock:
            with self.events_path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
                handle.flush()
                os.fsync(handle.fileno())

    def write_json(self, path: str | Path, payload: Any) -> Path:
        destination = Path(path)
        if not destination.is_absolute():
            destination = self.run_dir / destination
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(json.dumps(json_safe(payload), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)
        return destination

    def case_path(self, case_id: str) -> Path:
        return self.cases_dir / f"{slug(case_id)}.json"

    def write_case(self, case_id: str, payload: Any) -> Path:
        with self.lock:
            return self.write_json(self.case_path(case_id), payload)

    def read_case(self, case_id: str) -> dict[str, Any] | None:
        path = self.case_path(case_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def all_cases(self) -> list[dict[str, Any]]:
        return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(self.cases_dir.glob("*.json"))]
