# SC2 多跳 Agent GLM Reasoning English 测试报告

## 测试设置

- 测试时间：2026-06-06T15:03:57 至 2026-06-06T15:09:23
- Provider：`deepseek-v4-flash`
- 模式：`reasoning=True`
- Agent 回答语言：`English`
- 执行方式：30 个问题调用主 Agent，并发数 `5`，每题保存完整 raw JSON。
- 测试请求前等待：`0.0` 秒，仅在本评测脚本中生效。
- 结果目录：`D:/SC2/SC2_DATA_Agen/result/deepseek-v4-flash_reasoning_english_20260606_150357`

## 总体结论

- 总通过率：30/30
- 判定规则：同时检查是否调用了预期多跳工具、工具结果是否包含关键事实、最终英文回答是否覆盖关键事实、是否存在 LLM/工具错误。

| 种族 | 通过数 |
| --- | ---: |
| Terran | 10/10 |
| Protoss | 10/10 |
| Zerg | 10/10 |

## 失败项

无失败用例。

## 明细

| Case | Race | Result | Tools | Time(s) |
| --- | --- | --- | --- | ---: |
| T01_barracks_outputs | Terran | 通过 | `query_production_outputs` | 14.08 |
| T02_factory_addon_split | Terran | 通过 | `query_addon_branches` | 24.49 |
| T03_starport_reactor_vs_techlab | Terran | 通过 | `resolve_entity_key, query_addon_branches` | 28.78 |
| T04_battlecruiser_source_prereq | Terran | 通过 | `resolve_entity_key, query_reverse_production_sources, query_tech_tree, filter_attributes_and_resources` | 37.2 |
| T05_barracks_dependency_impact | Terran | 通过 | `resolve_entity_key, query_dependency_impact, query_tech_tree, query_production_outputs, query_research_outputs, query_tech_tree, query_tech_tree` | 76.52 |
| T06_ghost_ability_profile | Terran | 通过 | `resolve_entity_key, query_unit_abilities, get_entity, query_unit_abilities` | 59.97 |
| T07_terran_techlab_research | Terran | 通过 | `query_research_outputs, query_research_outputs, query_research_outputs, query_research_outputs, query_research_outputs, query_research_outputs, query_research_outputs` | 92.76 |
| T08_marauder_reverse_source | Terran | 通过 | `resolve_entity_key, query_reverse_production_sources, get_entity` | 29.9 |
| T09_barracks_antiair | Terran | 通过 | `resolve_entity_key, query_combat_production_options` | 41.33 |
| T10_terran_gas_units_sources | Terran | 通过 | `query_gas_units_with_sources, query_gas_units_with_sources, filter_attributes_and_resources, filter_attributes_and_resources` | 89.32 |
| P01_gateway_outputs | Protoss | 通过 | `resolve_entity_key, query_production_outputs` | 18.27 |
| P02_robotics_facility_outputs | Protoss | 通过 | `resolve_entity_key, query_production_outputs` | 27.01 |
| P03_stargate_outputs | Protoss | 通过 | `resolve_entity_key, query_production_outputs` | 22.99 |
| P04_cybernetics_core_research | Protoss | 通过 | `query_research_outputs` | 17.76 |
| P05_cybernetics_core_dependency | Protoss | 通过 | `resolve_entity_key, query_dependency_impact, query_tech_tree, query_tech_tree` | 66.46 |
| P06_stalker_reverse_source | Protoss | 通过 | `resolve_entity_key, query_reverse_production_sources, filter_attributes_and_resources, query_tech_tree` | 34.05 |
| P07_oracle_ability_profile | Protoss | 通过 | `resolve_entity_key, query_unit_abilities, get_entity, get_entity, get_entity, get_entity` | 32.39 |
| P08_protoss_gas_units_sources | Protoss | 通过 | `query_gas_units_with_sources` | 26.06 |
| P09_forge_upgrade_effects | Protoss | 通过 | `resolve_entity_key, query_research_outputs, query_upgrade_effects, query_upgrade_effects, query_upgrade_effects, filter_attributes_and_resources, filter_attributes_and_resources` | 89.06 |
| P10_carrier_reverse_source | Protoss | 通过 | `resolve_entity_key, get_entity, query_reverse_production_sources, query_tech_tree` | 25.66 |
| Z01_larva_morph_outputs | Zerg | 通过 | `resolve_entity_key, query_production_outputs, query_production_outputs` | 39.06 |
| Z02_spawning_pool_research | Zerg | 通过 | `resolve_entity_key, query_research_outputs` | 26.01 |
| Z03_spawning_pool_dependency | Zerg | 通过 | `resolve_entity_key, query_dependency_impact, query_tech_tree, query_tech_tree, query_tech_tree` | 76.37 |
| Z04_roach_reverse_source | Zerg | 通过 | `resolve_entity_key, query_reverse_production_sources, get_entity` | 31.84 |
| Z05_infestor_ability_profile | Zerg | 通过 | `resolve_entity_key, query_unit_abilities, query_unit_abilities, get_entity, get_entity, get_entity` | 73.58 |
| Z06_viper_ability_profile | Zerg | 通过 | `resolve_entity_key, query_unit_abilities, get_entity, get_entity, get_entity, get_entity, get_entity` | 50.17 |
| Z07_evolution_chamber_research | Zerg | 通过 | `resolve_entity_key, query_research_outputs, get_entity` | 42.98 |
| Z08_lair_dependency_impact | Zerg | 通过 | `query_tech_tree, query_dependency_impact, query_dependency_impact` | 99.36 |
| Z09_mutalisk_reverse_source | Zerg | 通过 | `resolve_entity_key, query_reverse_production_sources, get_entity` | 43.32 |
| Z10_broodlord_reverse_source | Zerg | 通过 | `resolve_entity_key, query_reverse_production_sources` | 21.83 |

## 说明

本次测试的准确性判定以结构化工具结果为主要证据，最终回答覆盖作为第二层验证。这样可以避免只看自然语言总结时把“检索正确但总结漏写”和“检索链路错误”混在一起。

## 人工复核补充

自动评测的 `30/30` 表示：每个问题都调用了可接受的多跳检索链路，结构化工具结果命中了关键事实，最终英文回答也覆盖了关键关键词。但这不等于最终自然语言回答逐句完全正确，也不等于不存在 LLM 自行补充信息。

人工抽查 raw JSON 后，结论如下：

- **结构化检索结果整体可信**：Barracks/Gateway/Larva 的生产输出、Roach/Mutalisk/BroodLord 的反向来源、TechLab/CyberneticsCore/SpawningPool/Lair 的依赖链路等，均能从工具结果中找到对应证据。
- **最终回答存在少量非 grounded 内容**：部分回答把数据库中的 `time` 原始值自行换算成秒，例如 Battlecruiser、Carrier、Marauder 等。这些换算不是工具结果直接给出的结论，应避免在严格评测中出现。
- **技能能量字段有数据缺口，LLM 有补充外部常识**：Oracle、Infestor、Viper 等问题中，工具结果显示部分技能 `energy_cost = 0`，最终回答又补充了“实际游戏中某技能需要 75/100/125 能量”等内容。这些属于 LLM 基于常识的补充，不是当前数据库检索出的证据。严格模式下应只报告数据库字段，并标注 `energy_cost` 数据可能不完整。
- **长列表总结可能漏项**：例如 Zerg Larva 的工具结果包含 11 个输出，其中包括 `SwarmHostMP`，但最终回答总结为 10 个并漏掉了该项。这说明检索链路正确，但回答阶段仍可能遗漏长列表项目。
- **“complete list / exact” 等措辞需要收敛**：当工具结果被压缩或字段存在数据缺口时，最终回答不应使用过强措辞。更合适的表达是“retrieved results include...”或“according to the database fields returned by tools...”。

因此，本轮结果应解读为：**多跳检索与工具调用能力通过基准测试；最终回答层还需要更严格的 grounded 输出约束，才能保证无编造、无自行换算、无长列表漏项。**

建议后续改进：

1. 回答阶段只允许引用 `tool_results` 中明确存在的字段。
2. 禁止 LLM 自行进行时间单位换算，除非工具层提供统一换算字段。
3. 对 `energy_cost = 0` 但单位有能量池的技能统一标记为“数据库字段可能不完整”，不要补充外部游戏数值。
4. 对生产输出、反向来源、耗气单位等长列表问题，由程序生成表格或做数量一致性校验，再交给 LLM润色。
5. 在自动评测中新增“回答是否包含未由工具结果支持的数值或实体”的 groundedness 检查。
