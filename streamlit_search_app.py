#!/usr/bin/env python3
"""Streamlit interface for the evidence-aware SC2 data agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sc2_agent import DEFAULT_PROVIDER, get_provider_catalog, run_agent  # noqa: E402
from sc2_search_tools import DEFAULT_DATA_PATH  # noqa: E402


st.set_page_config(page_title="SC2 Data Agent", layout="wide")
st.title("StarCraft II Data Agent")
st.caption(
    "Query the 2026-07-01 structured graph, SubOntology classes, and line-addressable Markdown evidence. "
    "Every run is persisted under the repository logs directory."
)

catalog = get_provider_catalog()
model_keys = sorted(catalog)
if not model_keys:
    st.error("No models are configured in API_config/config.json.")
    st.stop()

with st.sidebar:
    st.header("Agent settings")
    agent_version = st.selectbox("Agent version", ["v2", "v1"], index=0)
    default_index = model_keys.index(DEFAULT_PROVIDER) if DEFAULT_PROVIDER in model_keys else 0
    model_key = st.selectbox("Model key", model_keys, index=default_index)
    configured_reasoning = bool(catalog[model_key].get("is_reasoning"))
    reasoning_mode = st.selectbox(
        "Reasoning mode",
        ["auto", "on", "off"],
        index=0,
        help="Auto follows the selected model entry. On/off selects a paired _think/non-think entry when available.",
    )
    response_language = st.selectbox("Answer language", ["English", "Chinese"])
    st.caption(f"Configured reasoning: {configured_reasoning}")
    st.caption(f"Dataset: {DEFAULT_DATA_PATH}")

query = st.text_area(
    "Question",
    height=130,
    placeholder="Example: Which Terran spellcasters counter Zerg ground units, and what evidence supports the relations?",
)

if st.button("Run agent", type="primary"):
    if not query.strip():
        st.warning("Enter a question first.")
        st.stop()
    enable_reasoning = configured_reasoning if reasoning_mode == "auto" else reasoning_mode == "on"
    with st.spinner("Routing, retrieving evidence, and composing the answer..."):
        try:
            st.session_state.agent_result = run_agent(
                query.strip(),
                provider=model_key,
                data_path=DEFAULT_DATA_PATH,
                enable_reasoning=enable_reasoning,
                response_language=response_language,
                agent_version=agent_version,
            )
        except Exception as exc:
            st.exception(exc)

result = st.session_state.get("agent_result")
if result:
    st.subheader("Answer")
    st.markdown(result.get("answer", ""))
    col1, col2, col3 = st.columns(3)
    col1.metric("Run ID", result.get("run_id", ""))
    col2.code(result.get("log_path", ""), language=None)
    col3.metric("Agent version", result.get("agent_version", ""))

    with st.expander("Reasoning trace", expanded=False):
        traces = result.get("reasoning_trace") or []
        if not traces:
            st.caption("No LLM reasoning trace was produced for this run.")
        for trace in traces:
            st.markdown(f"#### {trace.get('phase', 'LLM call')}")
            st.caption(
                f"model={trace.get('model_key')} | source={trace.get('reasoning_source')} | "
                f"latency={trace.get('latency_seconds')}s"
            )
            if trace.get("reasoning"):
                st.text(trace["reasoning"])
            else:
                st.caption("The provider did not expose a reasoning payload for this call.")

    with st.expander("Plans and routing", expanded=False):
        st.json({"routing": result.get("routing"), "plan": result.get("plan")}, expanded=True)

    with st.expander("Tool calls and evidence", expanded=False):
        for index, tool_result in enumerate(result.get("tool_results", []), 1):
            st.markdown(f"#### {index}. `{tool_result.get('tool')}`")
            st.json(tool_result, expanded=False)

    st.download_button(
        "Download complete run result",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name=f"sc2_agent_{result.get('run_id', 'trace')}.json",
        mime="application/json",
    )
