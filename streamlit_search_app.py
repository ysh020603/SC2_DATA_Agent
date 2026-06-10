#!/usr/bin/env python3
"""Streamlit UI for the SC2 natural-language query Agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sc2_agent import DEFAULT_PROVIDER, get_provider_catalog, run_agent, call_llm  # noqa: E402
from sc2_search_tools import DEFAULT_DATA_PATH  # noqa: E402


# ---------------------------------------------------------------------------
# Load example queries from test_set_60.jsonl
# ---------------------------------------------------------------------------
def _load_examples() -> list[tuple[str, str]]:
    test_path = BASE_DIR / "tests" / "test_set_60.jsonl"
    if not test_path.exists():
        return []
    examples: list[tuple[str, str]] = []
    with open(test_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            qid = obj.get("id", "")
            question = obj.get("question", "")
            category = obj.get("category", "")
            race = obj.get("race", "")
            label = f"[{race}] {qid}  ({category})"
            examples.append((label, question))
    return examples


EXAMPLES = _load_examples()


# ---------------------------------------------------------------------------
# UI text
# ---------------------------------------------------------------------------
TEXT = {
    "title": "SC2 自然语言 Agent 搜索",
    "caption": "输入自然语言指令，Agent 会自动规划工具调用、检索数据，并总结结果。",
    "settings": "Agent 设置",
    "provider": "模型提供商",
    "reasoning": "启用 reasoning",
    "reasoning_caption": "reasoning 仅对本次请求生效，不写入配置文件。",
    "translate": "翻译回答为中文",
    "translate_caption": "开启后自动将 Agent 的英文回答翻译为中文并显示在下方。",
    "examples": "示例查询 (来自 test_set_60.jsonl)",
    "insert_example": "选择一条示例",
    "instruction": "自然语言指令",
    "default_query": "列出所有建造时间小于 30 秒且矿物消耗不超过 50 的虫族单位。",
    "run": "运行 Agent",
    "empty": "请输入搜索指令。",
    "spinner": "Agent 正在规划、检索并总结 …",
    "spinner_translate": "正在翻译 …",
    "answer": "回答",
    "translation": "中文翻译",
    "llm_summary": "LLM 规划摘要（每步 planner 输出）",
    "step": "步骤",
    "plan_trace": "Agent 规划轨迹",
    "tool_trace": "工具调用与原始返回结果",
    "arguments": "参数",
    "result_count": "结果数量",
    "tool_call": "工具调用",
    "download": "下载完整 Agent trace",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(page_title="SC2 Agent 搜索", layout="wide")

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.subheader(TEXT["settings"])
    catalog = get_provider_catalog()
    provider_names = sorted(catalog)
    default_index = provider_names.index(DEFAULT_PROVIDER) if DEFAULT_PROVIDER in provider_names else 0
    provider = st.selectbox(TEXT["provider"], provider_names, index=default_index)
    enable_reasoning = st.toggle(TEXT["reasoning"], value=False)
    st.caption(TEXT["reasoning_caption"])

    st.divider()
    translate_enabled = st.toggle(TEXT["translate"], value=False)
    st.caption(TEXT["translate_caption"])

    st.divider()
    st.subheader(TEXT["examples"])
    example_labels = [""] + [label for label, _ in EXAMPLES]
    selected_label = st.selectbox(TEXT["insert_example"], example_labels, key="example_selector")
    if selected_label:
        selected_example = next((q for lbl, q in EXAMPLES if lbl == selected_label), "")
        if st.session_state.get("_last_example_label") != selected_label:
            st.session_state.query_text = selected_example
            st.session_state._last_example_label = selected_label
    else:
        selected_example = ""

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title(TEXT["title"])
st.caption(TEXT["caption"])

if "query_text" not in st.session_state:
    st.session_state.query_text = ""
if "_last_example_label" not in st.session_state:
    st.session_state._last_example_label = ""

query = st.text_area(TEXT["instruction"], key="query_text", height=120)
run = st.button(TEXT["run"], type="primary")

if run:
    if not query.strip():
        st.warning(TEXT["empty"])
        st.stop()

    st.session_state.translated_answer = None
    st.session_state.translated_query = None

    with st.spinner(TEXT["spinner"]):
        result = run_agent(
            query.strip(),
            provider=provider,
            data_path=DEFAULT_DATA_PATH,
            enable_reasoning=enable_reasoning,
        )

    st.session_state.agent_result = result
    st.session_state.agent_provider = provider
else:
    result = st.session_state.get("agent_result")
    provider = st.session_state.get("agent_provider", provider)

# ---------------------------------------------------------------------------
# Display results
# ---------------------------------------------------------------------------
if "agent_result" in st.session_state:
    result = st.session_state.agent_result
    provider = st.session_state.get("agent_provider", provider)

    st.subheader(TEXT["answer"])
    st.markdown(result["answer"])

    if translate_enabled:
        if (
            st.session_state.get("translated_answer") is None
            or st.session_state.get("translated_query") != result["answer"]
        ):
            with st.spinner(TEXT["spinner_translate"]):
                translate_prompt = [
                    {
                        "role": "system",
                        "content": (
                            "You are a translator. Translate the following English text "
                            "into Chinese. Output only the Chinese translation, no additional commentary."
                        ),
                    },
                    {"role": "user", "content": result["answer"]},
                ]
                try:
                    translated = call_llm(
                        translate_prompt,
                        provider=provider,
                        enable_reasoning=False,
                    )
                    st.session_state.translated_answer = translated
                    st.session_state.translated_query = result["answer"]
                except Exception as exc:
                    st.session_state.translated_answer = f"翻译失败: {exc}"
                    st.session_state.translated_query = result["answer"]

        if st.session_state.get("translated_answer"):
            st.divider()
            st.subheader(TEXT["translation"])
            st.markdown(st.session_state.translated_answer)

    with st.expander(TEXT["llm_summary"], expanded=False):
        steps = result.get("plan", {}).get("steps", [])
        if not steps:
            st.caption("无规划步骤记录。")
        else:
            for idx, step in enumerate(steps):
                status = step.get("status", "?")
                notes = step.get("notes", [])
                tool_calls = step.get("tool_calls", [])
                planner_err = step.get("planner_error", "")
                st.markdown(f"**{TEXT['step']} {idx + 1}**  (状态: `{status}`)")
                if notes:
                    for n in notes:
                        st.markdown(f"- {n}")
                if tool_calls:
                    tools_list = ", ".join(c.get("tool", "?") for c in tool_calls)
                    st.caption(f"工具调用: {tools_list}")
                if planner_err:
                    st.caption(f"规划错误: {planner_err}")
                st.divider()

    with st.expander(TEXT["plan_trace"], expanded=False):
        st.json(result["plan"], expanded=True)

    with st.expander(TEXT["tool_trace"], expanded=False):
        for index, tool_result in enumerate(result.get("tool_results", []), 1):
            st.markdown(f"### {TEXT['tool_call']} {index}: `{tool_result.get('tool')}`")
            st.markdown(TEXT["arguments"])
            st.json(tool_result.get("arguments", {}), expanded=True)
            if "error" in tool_result:
                st.error(tool_result["error"])
            else:
                tool_payload = tool_result.get("result", {})
                st.markdown(f"{TEXT['result_count']}: `{tool_payload.get('count', 'unknown')}`")
                st.json(tool_payload, expanded=False)

    st.download_button(
        TEXT["download"],
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name="sc2_agent_trace.json",
        mime="application/json",
    )
