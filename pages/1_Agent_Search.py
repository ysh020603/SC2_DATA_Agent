#!/usr/bin/env python3
"""Streamlit page for the natural-language SC2 query Agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import streamlit as st

PAGE_DIR = Path(__file__).resolve().parent
BASE_DIR = PAGE_DIR.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from sc2_agent import DEFAULT_PROVIDER, get_provider_catalog, run_agent  # noqa: E402
from sc2_query_engine import execute_tool  # noqa: E402
from sc2_search_tools import DEFAULT_DATA_PATH  # noqa: E402


EXAMPLES_EN = [
    "List all Zerg units that take under 30 seconds to build and cost no more than 50 minerals.",
    "Filter Terran Armored units taking >= 4 supply, sorted by max_health descending.",
    "Query all Protoss units marked as structures that have weapons.",
    "Find all flying units that cost gas but do not need Protoss power.",
    "Retrieve the complete tech_chain to build a Mothership.",
    "Reverse inference: If my Cybernetics Core is destroyed, which units and upgrades will have their tech_chain broken?",
    "What are the prerequisites to unlock Terran Stimpack? Does it require a specific add-on?",
    "Query units with two or more distinct production or morphing paths.",
    "Find units with start_energy > 50 and spell energy_cost >= 75 to evaluate if they can cast immediately upon spawning.",
    "Find units or abilities mentioning detector or reveal to counter cloaked units.",
    "Calculate the top 3 most cost-efficient Armored units with base armor > 2.",
]

EXAMPLES_ZH = [
    "列出所有建造时间小于 30 秒，并且矿物消耗不超过 50 的虫族单位。",
    "筛选所有补给占用大于等于 4 的人族重甲单位，并按最大生命值降序排序。",
    "查询所有被标记为建筑，并且拥有武器的星灵单位。",
    "查找所有消耗气体、会飞、并且不需要星灵能量场的单位。",
    "检索建造母舰所需的完整科技链。",
    "反向推理：如果我的控制核心被摧毁，哪些单位和升级的科技链会断掉？",
    "解锁人族兴奋剂需要哪些前置条件？它是否需要特定挂件？",
    "查询拥有两条或更多生产/变形路径的单位。",
    "查找初始能量大于 50，并且技能能量消耗大于等于 75 的单位或技能。",
    "查找描述中提到 detector 或 reveal、可用于反隐的单位或技能。",
    "计算生命值/矿物效率最高的 3 个基础护甲大于 2 的重甲单位。",
]

TEXT = {
    "Chinese": {
        "title": "SC2 Natural-Language Agent 自然语言检索",
        "caption": "输入自然语言指令，Agent 会规划工具调用、执行检索，并用自然语言总结结果。",
        "settings": "Agent 设置",
        "language": "界面与回答语言",
        "provider": "模型提供方",
        "reasoning": "开启 reasoning",
        "reasoning_caption": "reasoning 只在本次请求中生效，不写入 config。",
        "examples": "示例",
        "insert_example": "插入示例",
        "instruction": "自然语言指令",
        "default_query": "哪些虫族地面单位是重甲，并且射程大于 5？",
        "run": "运行 Agent",
        "empty": "请输入一个检索指令。",
        "spinner": "Agent 正在规划、检索并总结...",
        "answer": "回答",
        "plan_trace": "Agent 规划过程",
        "tool_trace": "工具调用与原始返回",
        "arguments": "参数",
        "result_count": "结果数量",
        "tool_call": "工具调用",
        "download": "下载完整 Agent trace",
        "manual_tests": "手动工具冒烟测试",
        "manual_caption": "这些按钮会直接调用确定性工具，不经过 LLM 规划。",
        "manual_tech_chain": "科技链：母舰",
        "manual_broken_chain": "断链：控制核心",
        "manual_semantic": "语义：反隐 reveal",
    },
    "English": {
        "title": "SC2 Natural-Language Agent Natural Language Search",
        "caption": "Enter a natural-language instruction. The Agent plans tool calls, retrieves evidence, and summarizes the result.",
        "settings": "Agent Settings",
        "language": "Interface and answer language",
        "provider": "Provider",
        "reasoning": "Enable reasoning",
        "reasoning_caption": "Reasoning is controlled per request and is not stored in config.",
        "examples": "Examples",
        "insert_example": "Insert an example",
        "instruction": "Natural-language instruction",
        "default_query": "Find Zerg ground units that are Armored and have weapon range greater than 5.",
        "run": "Run Agent",
        "empty": "Please enter a search instruction.",
        "spinner": "Agent is planning, searching, and summarizing...",
        "answer": "Answer",
        "plan_trace": "Agent planning trace",
        "tool_trace": "Tool calls and raw tool results",
        "arguments": "Arguments",
        "result_count": "Result count",
        "tool_call": "Tool call",
        "download": "Download full Agent trace",
        "manual_tests": "Manual tool smoke tests",
        "manual_caption": "These buttons call deterministic tools without LLM planning.",
        "manual_tech_chain": "Tech chain: Mothership",
        "manual_broken_chain": "Broken chain: CyberneticsCore",
        "manual_semantic": "Semantic: detector reveal",
    },
}


st.set_page_config(page_title="SC2 Agent Search", layout="wide")

with st.sidebar:
    language = st.radio("Language / 语言", ["Chinese", "English"], horizontal=True)

t = TEXT[language]
response_language = "Chinese" if language == "Chinese" else "English"

st.title(t["title"])
st.caption(t["caption"])

catalog = get_provider_catalog()
provider_names = sorted(catalog)
default_index = provider_names.index(DEFAULT_PROVIDER) if DEFAULT_PROVIDER in provider_names else 0

with st.sidebar:
    st.subheader(t["settings"])
    provider = st.selectbox(t["provider"], provider_names, index=default_index)
    enable_reasoning = st.toggle(t["reasoning"], value=False)
    st.caption(t["reasoning_caption"])

    st.subheader(t["examples"])
    examples = EXAMPLES_ZH if language == "Chinese" else EXAMPLES_EN
    selected_example = st.selectbox(t["insert_example"], [""] + examples)

default_query = selected_example or t["default_query"]
query = st.text_area(t["instruction"], value=default_query, height=120)

run = st.button(t["run"], type="primary")

if run:
    if not query.strip():
        st.warning(t["empty"])
        st.stop()

    with st.spinner(t["spinner"]):
        result = run_agent(
            query.strip(),
            provider=provider,
            data_path=DEFAULT_DATA_PATH,
            enable_reasoning=enable_reasoning,
            response_language=response_language,
        )

    st.subheader(t["answer"])
    st.markdown(result["answer"])

    with st.expander(t["plan_trace"], expanded=False):
        st.json(result["plan"], expanded=True)

    with st.expander(t["tool_trace"], expanded=False):
        for index, tool_result in enumerate(result["tool_results"], 1):
            st.markdown(f"### {t['tool_call']} {index}: `{tool_result.get('tool')}`")
            st.markdown(t["arguments"])
            st.json(tool_result.get("arguments", {}), expanded=True)
            if "error" in tool_result:
                st.error(tool_result["error"])
            else:
                tool_payload = tool_result.get("result", {})
                st.markdown(f"{t['result_count']}: `{tool_payload.get('count', 'unknown')}`")
                st.json(tool_payload, expanded=False)

    st.download_button(
        t["download"],
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name="sc2_agent_trace.json",
        mime="application/json",
    )

with st.expander(t["manual_tests"], expanded=False):
    st.caption(t["manual_caption"])
    cols = st.columns(3)
    if cols[0].button(t["manual_tech_chain"]):
        st.json(execute_tool("query_tech_tree", {"target": "Mothership", "sections": ["Unit"], "limit": 5}, data_path=DEFAULT_DATA_PATH))
    if cols[1].button(t["manual_broken_chain"]):
        st.json(execute_tool("query_tech_tree", {"broken_node": "CyberneticsCore", "sections": ["Unit", "Upgrade"], "limit": 20}, data_path=DEFAULT_DATA_PATH))
    if cols[2].button(t["manual_semantic"]):
        st.json(execute_tool("search_descriptions", {"keywords": ["detector", "reveal"], "mode": "any", "sections": ["Unit", "Ability"], "limit": 20}, data_path=DEFAULT_DATA_PATH))
