#!/usr/bin/env python3
"""Streamlit UI for SC2 DATA_BASE search tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from sc2_search_tools import (
    DEFAULT_DATA_PATH,
    combined_search,
    flatten_items,
    get_value,
    load_data,
)


COMMON_NUMERIC_FIELDS = [
    "id",
    "cast_range",
    "energy_cost",
    "cooldown",
    "max_health",
    "max_shield",
    "armor",
    "sight",
    "speed",
    "supply",
    "minerals",
    "gas",
    "time",
    "cost.minerals",
    "cost.gas",
    "cost.time",
    "weapons.range",
    "weapons.damage_per_hit",
    "weapons.dps",
    "weapons.bonuses.damage",
]

BOOLEAN_FIELDS = [
    "allow_minimap",
    "allow_autocast",
    "accepts_addon",
    "needs_power",
    "needs_creep",
    "needs_geyser",
    "is_structure",
    "is_addon",
    "is_worker",
    "is_townhall",
    "is_flying",
]

DEFAULT_OUTPUT_KEYS = ["_section", "id", "name", "race", "attributes", "tech_chain", "description"]


st.set_page_config(page_title="SC2 DATA_BASE Search", layout="wide")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1rem; }
      div[data-testid="stMetricValue"] { font-size: 1.4rem; }
      code { white-space: pre-wrap; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_data(path: str) -> dict[str, list[dict[str, Any]]]:
    return load_data(path)


@st.cache_data(show_spinner=False)
def cached_items(path: str) -> list[dict[str, Any]]:
    return flatten_items(data=cached_data(path))


def unique_values(items: list[dict[str, Any]], key: str) -> list[str]:
    values = set()
    for item in items:
        value = get_value(item, key)
        if isinstance(value, list):
            values.update(str(part) for part in value)
        elif value is not None:
            values.add(str(value))
    return sorted(values)


def all_output_keys(items: list[dict[str, Any]]) -> list[str]:
    keys = {"_section", "id", "name", "race", "attributes", "tech_chain", "description"}
    for item in items:
        keys.update(item.keys())
    keys.update(["cost.minerals", "cost.gas", "cost.time", "weapons.range", "weapons.dps"])
    return sorted(keys)


def build_ranges(selected_fields: list[str]) -> dict[str, dict[str, float | None]]:
    ranges: dict[str, dict[str, float | None]] = {}
    for field in selected_fields:
        cols = st.columns([2, 1, 1])
        cols[0].markdown(f"`{field}`")
        min_value = cols[1].number_input(f"{field} min", value=None, key=f"{field}_min")
        max_value = cols[2].number_input(f"{field} max", value=None, key=f"{field}_max")
        bounds: dict[str, float | None] = {}
        if min_value is not None:
            bounds["min"] = float(min_value)
        if max_value is not None:
            bounds["max"] = float(max_value)
        if bounds:
            ranges[field] = bounds
    return ranges


def build_boolean_filters(selected_fields: list[str]) -> dict[str, bool]:
    booleans: dict[str, bool] = {}
    for field in selected_fields:
        expected = st.selectbox(field, ["true", "false"], key=f"bool_{field}")
        booleans[field] = expected == "true"
    return booleans


def compact_table(items: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in items:
        weapons = item.get("weapons") or []
        descriptions = item.get("description") or []
        chains = item.get("tech_chain") or []
        rows.append(
            {
                "section": item.get("_section"),
                "id": item.get("id"),
                "name": item.get("name"),
                "race": item.get("race", ""),
                "attributes": ", ".join(item.get("attributes") or []),
                "weapons": len(weapons),
                "chains": len(chains),
                "descriptions": len(descriptions),
            }
        )
    return pd.DataFrame(rows)


def parse_json_text(text: str, fallback: Any) -> Any:
    if not text.strip():
        return fallback
    return json.loads(text)


data_path = str(DEFAULT_DATA_PATH)
items = cached_items(data_path)

st.title("SC2 DATA_BASE 检索")
st.caption("名称检索、字段范围筛选、标签/布尔筛选、战斗属性筛选可以单独使用，也可以组合使用。")

with st.sidebar:
    st.subheader("检索范围")
    sections = st.multiselect("Section", ["Ability", "Unit", "Upgrade"], default=["Ability", "Unit", "Upgrade"])
    limit = st.number_input("最多返回数量", min_value=1, max_value=5000, value=200, step=50)

    st.subheader("名称检索")
    name_query = st.text_input("name 查询")
    name_mode = st.radio("匹配方式", ["contains", "exact", "fuzzy"], horizontal=True)

    st.subheader("字段范围筛选")
    selected_numeric_fields = st.multiselect("选择数值字段", COMMON_NUMERIC_FIELDS)
    numeric_ranges = build_ranges(selected_numeric_fields)
    custom_ranges_text = st.text_area(
        "自定义 ranges JSON",
        placeholder='{"max_health":{"min":100},"weapons.range":{"min":6}}',
        height=80,
    )

    st.subheader("标签 / 布尔筛选")
    race_options = [""] + unique_values(items, "race")
    race = st.selectbox("race", race_options)
    attributes = unique_values(items, "attributes")
    attributes_any = st.multiselect("attributes 任意包含", attributes)
    attributes_all = st.multiselect("attributes 必须全部包含", attributes)
    selected_boolean_fields = st.multiselect("布尔字段", BOOLEAN_FIELDS)
    boolean_filters = build_boolean_filters(selected_boolean_fields)

    st.subheader("战斗属性筛选")
    has_weapons_choice = st.selectbox("是否有武器", ["不限", "有武器", "无武器"])
    attack_air_choice = st.selectbox("能否攻击空中", ["不限", "是", "否"])
    attack_ground_choice = st.selectbox("能否攻击地面", ["不限", "是", "否"])
    target_type = st.selectbox("武器 target_type", ["", "Air", "Ground", "Any"])
    min_range = st.number_input("最小射程", value=None)
    max_range = st.number_input("最大射程", value=None)
    min_damage = st.number_input("最小单次伤害", value=None)
    min_dps = st.number_input("最小 DPS", value=None)
    bonus_against = st.selectbox("bonus against", ["", "Light", "Armored", "Biological", "Mechanical", "Massive", "Structure", "Psionic"])

    st.subheader("返回字段")
    output_mode = st.radio("返回内容", ["完整返回", "只返回选中 key"], horizontal=True)
    output_keys = None
    if output_mode == "只返回选中 key":
        output_keys = st.multiselect("输出 keys", all_output_keys(items), default=DEFAULT_OUTPUT_KEYS)

    run = st.button("运行检索", type="primary", use_container_width=True)


if custom_ranges_text.strip():
    try:
        numeric_ranges.update(parse_json_text(custom_ranges_text, {}))
    except json.JSONDecodeError as exc:
        st.error(f"自定义 ranges JSON 解析失败: {exc}")

tag_filters: dict[str, Any] = {}
if race:
    tag_filters["race"] = race
if attributes_any:
    tag_filters["attributes_any"] = attributes_any
if attributes_all:
    tag_filters["attributes_all"] = attributes_all
if boolean_filters:
    tag_filters["booleans"] = boolean_filters

combat_filters: dict[str, Any] = {}
if has_weapons_choice != "不限":
    combat_filters["has_weapons"] = has_weapons_choice == "有武器"
if attack_air_choice != "不限":
    combat_filters["can_attack_air"] = attack_air_choice == "是"
if attack_ground_choice != "不限":
    combat_filters["can_attack_ground"] = attack_ground_choice == "是"
if target_type:
    combat_filters["target_type"] = target_type
if min_range is not None:
    combat_filters["min_range"] = float(min_range)
if max_range is not None:
    combat_filters["max_range"] = float(max_range)
if min_damage is not None:
    combat_filters["min_damage_per_hit"] = float(min_damage)
if min_dps is not None:
    combat_filters["min_dps"] = float(min_dps)
if bonus_against:
    combat_filters["bonus_against"] = bonus_against

active_filters = {
    "name": bool(name_query),
    "numeric_ranges": bool(numeric_ranges),
    "tags": bool(tag_filters),
    "combat": bool(combat_filters),
}

if run or True:
    try:
        results = combined_search(
            name_query=name_query or None,
            name_mode=name_mode,
            numeric_ranges=numeric_ranges or None,
            tag_filters=tag_filters or None,
            combat_filters=combat_filters or None,
            sections=sections,
            keys=output_keys,
            limit=int(limit),
            data_path=data_path,
        )
    except Exception as exc:  # noqa: BLE001 - Streamlit should show the error in UI.
        st.error(f"检索失败: {exc}")
        st.stop()

    metric_cols = st.columns(5)
    metric_cols[0].metric("结果数量", len(results))
    metric_cols[1].metric("名称检索", "ON" if active_filters["name"] else "OFF")
    metric_cols[2].metric("范围筛选", "ON" if active_filters["numeric_ranges"] else "OFF")
    metric_cols[3].metric("标签筛选", "ON" if active_filters["tags"] else "OFF")
    metric_cols[4].metric("战斗筛选", "ON" if active_filters["combat"] else "OFF")

    st.subheader("结果概览")
    if output_keys:
        st.dataframe(pd.DataFrame(results), use_container_width=True, height=360)
    else:
        st.dataframe(compact_table(results), use_container_width=True, height=360)

    st.subheader("结果 JSON")
    st.download_button(
        "下载结果 JSON",
        data=json.dumps(results, ensure_ascii=False, indent=2),
        file_name="sc2_search_results.json",
        mime="application/json",
    )
    st.json(results, expanded=False)
