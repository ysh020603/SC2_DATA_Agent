# SC2 DATA 检索与自然语言 Agent

这个项目整理了《星际争霸 II：Legacy of the Void》的单位、建筑、技能/指令、升级/科技数据，并在 `DATA_BASE` 中构建了一个可检索的结构化数据库。项目同时提供确定性检索工具、Streamlit 可视化检索界面，以及一个可以用自然语言调用检索工具的 Agent。

## 数据库内容

核心数据库文件：

```text
DATA_BASE/data_base.json
```

它由原始 `data.json` 和前面生成的科技链、描述信息整合而来，包含三个顶层部分：

| Section | 内容 | 当前数量 |
| --- | --- | ---: |
| `Ability` | 技能、动作、指令，例如训练、建造、研究、施法、移动、攻击等 action | 683 |
| `Unit` | 单位与建筑，包括神族、虫族、人族的作战单位、生产建筑、科技建筑、变形形态等 | 204 |
| `Upgrade` | 升级与科技，例如攻防升级、技能解锁、特殊科技等 | 124 |

每个对象保留了 `data.json` 中适合检索的原始字段，内部数字 id 已替换为对应名称，并额外加入：

| Key | 类型 | 说明 |
| --- | --- | --- |
| `tech_chain` | `list<string>` | 科技链。支持单路径、多路径，以及 `[路径 A] + [路径 B] -> 目标` 这种并行 AND 依赖格式。 |
| `description` | `list<string>` | 与该单位、技能或升级相关的自然语言描述。 |

常见字段包括：

- 基础信息：`name`、`race`
- 资源与时间：`minerals`、`gas`、`supply`、`time`、`cost.minerals`、`cost.gas`、`cost.time`
- 战斗属性：`max_health`、`max_shield`、`armor`、`sight`、`speed`、`weapons`
- 关系字段：`ability_name`、`produces_name`、`upgrade_name`、`building_name`、`normal_mode_name`
- 标签属性：`attributes`、`is_structure`、`is_flying`、`is_worker`、`is_townhall`
- 建筑约束：`needs_power`、`needs_creep`、`needs_geyser`、`accepts_addon`、`is_addon`
- 技能属性：`cast_range`、`energy_cost`、`cooldown`、`target`、`allow_autocast`

更完整的数据结构说明见：

```text
DATA_BASE/DATA_BASE_STRUCTURE.md
```

## 检索器能力

检索器代码主要在：

```text
DATA_BASE/sc2_search_tools.py
DATA_BASE/sc2_query_engine.py
```

它们可以作为普通 Python 函数单独调用，也可以被 Agent 当作 Tools 使用。

### 1. 名称检索

支持按 `name` 查询：

- `exact`：完全匹配
- `contains`：包含匹配
- `fuzzy`：模糊匹配

适合查询 `Battlecruiser`、`Barracks`、`Stimpack` 这类明确名称。

### 2. 字段范围筛选

支持数值字段范围过滤，例如：

- `minerals <= 50`
- `time < 30`
- `max_health >= 300`
- `weapons.range > 5`
- `cost.gas > 0`

可以用于资源预算、生产时间、射程、伤害、生命值等筛选。

### 3. 标签 / 布尔属性筛选

支持按种族、属性标签和布尔字段筛选：

- 种族：`Terran`、`Protoss`、`Zerg`
- 属性：`Armored`、`Light`、`Biological`、`Mechanical`、`Structure`
- 布尔字段：`is_structure`、`is_flying`、`needs_power`、`accepts_addon`

例如：筛选所有虫族重甲地面单位，或者所有不需要星灵能量场的飞行单位。

### 4. 战斗属性检索

支持按武器与战斗配置过滤：

- 是否能对空
- 是否能对地
- 最小/最大射程
- 最小伤害
- 最小 DPS
- 对特定属性的 bonus damage

例如：查找射程大于 5 的虫族重甲单位，或查找能对空且有范围伤害描述的单位。

### 5. 科技链与依赖推理

`sc2_query_engine.py` 提供更高层的科技链查询：

- 查询某个单位、建筑、技能或升级的完整科技链
- 查询某个建筑被摧毁后会影响哪些单位或升级
- 查询需要 `TechLab` 或 `Reactor` 的内容
- 查询拥有多条生产/变形路径的单位
- 解析 `[路径 A] + [路径 B] -> 目标` 中的并行依赖

例如：

```text
Mothership:
[Pylon -> Gateway -> CyberneticsCore -> Stargate -> FleetBeacon] + [Nexus] -> Mothership
```

### 6. 语义描述检索

可以在 `description` 中按关键词搜索战术效果，例如：

- `detector`
- `reveal`
- `cloak`
- `splash`
- `burrow`
- `armor reduction`
- `harass`

这适合用户不知道准确名称，只描述效果的情况。

### 7. 组合检索与返回字段控制

检索条件可以组合使用。默认返回完整记录，也可以指定只返回某些 key，例如：

```python
keys=["_section", "name", "race", "tech_chain"]
```

支持嵌套字段：

```python
keys=["name", "cost.minerals", "cost.gas", "weapons.range"]
```

更详细的检索工具说明见：

```text
DATA_BASE/SC2_SEARCH_TOOLS.md
```

## 自然语言 Agent

Agent 代码在：

```text
DATA_BASE/sc2_agent.py
DATA_BASE/pages/1_Agent_Search.py
```

Agent 的流程是：

1. 用户输入自然语言问题
2. LLM 将问题规划成一个或多个工具调用
3. 检索器执行确定性查询
4. LLM 根据检索结果生成自然语言回答
5. UI 中可以展开查看 Agent 调用了哪些工具、传入了哪些参数、原始返回是什么

Agent 支持中文和英文两种模式：

- 中文模式：界面和回答都使用中文
- 英文模式：界面和回答都使用英文

Agent 支持在界面中控制是否开启 `reasoning`。这个开关只对当前请求生效，不写入配置文件。

API 配置文件：

```text
DATA_BASE/config/provider_config.json
```

这个文件包含 API key，已经被 `DATA_BASE/.gitignore` 忽略。提交或分享项目时使用样例文件：

```text
DATA_BASE/config/provider_config.example.json
```

也可以使用环境变量覆盖：

```text
GLM_API_KEY
GLM_BASE_URL
KIMI_API_KEY
KIMI_BASE_URL
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
```

命令行调用示例：

```powershell
python DATA_BASE\sc2_agent.py "Retrieve the complete tech_chain to build a Mothership."
python DATA_BASE\sc2_agent.py "检索建造母舰所需的完整科技链。" --language Chinese
python DATA_BASE\sc2_agent.py "Retrieve the complete tech_chain to build a Mothership." --reasoning
```

## 启动 UI

在项目根目录运行：

```powershell
python -m streamlit run DATA_BASE\streamlit_search_app.py --server.port 8501
```

然后打开：

```text
http://localhost:8501
```

页面包括：

- 主检索页：手动组合名称、字段范围、标签、战斗属性等检索条件
- `Agent Search` 子页面：输入自然语言指令，由 Agent 自动规划检索并总结结果

如果端口已经被占用，可以换一个端口：

```powershell
python -m streamlit run DATA_BASE\streamlit_search_app.py --server.port 8502
```

## 常用文件

| 文件 | 说明 |
| --- | --- |
| `data.json` | 原始 SC2 数据来源 |
| `DATA_BASE/data_base.json` | 整合后的核心数据库 |
| `DATA_BASE/build_data_base.py` | 构建 `data_base.json` 的脚本 |
| `DATA_BASE/sc2_search_tools.py` | 基础检索工具 |
| `DATA_BASE/sc2_query_engine.py` | 高层查询引擎 |
| `DATA_BASE/sc2_agent.py` | 自然语言 Agent |
| `DATA_BASE/streamlit_search_app.py` | Streamlit 主检索 UI |
| `DATA_BASE/pages/1_Agent_Search.py` | Streamlit Agent 子页面 |
| `DATA_BASE/config/provider_config.example.json` | API 配置样例 |

