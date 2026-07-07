"""Stable V1 package entry point backed by the packaged runtime snapshot."""

from typing import Any

from .legacy_runtime import run_agent as _run_agent


def run_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    kwargs["agent_version"] = "v1"
    return _run_agent(*args, **kwargs)


__all__ = ["run_agent"]
