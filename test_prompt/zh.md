# SC2 多跳测试 Prompt 集合（中文）

## 已测试基准题（已剔除问题字段相关题）

### 人族 Terran

1. 人族兵营能生产哪些单位？这些单位分别需要多少矿、气和人口？
2. 人族重工厂挂 Tech Lab 和不挂 Tech Lab 时分别能生产哪些单位？
3. 人族星港哪些单位可以配合 Reactor 双产？哪些单位必须 Tech Lab？
4. 战列巡航舰从哪里生产？需要哪些前置？成本是多少？
5. 如果人族兵营缺失，会影响哪些下游单位、建筑和升级？
6. 哪些人族升级需要 Tech Lab？分别由哪个研究建筑或插件提供？
7. Marauder 从哪个建筑生产？需要什么插件？成本是多少？
8. 只走兵营生产路线时，哪些人族单位可以攻击空中目标？成本和射程是多少？
9. 列出所有耗气的人族单位，并说明生产来源、插件需求和科技链证据。

### 神族 Protoss

1. 神族传送门能生产哪些单位？这些单位分别需要多少矿、气和人口？
2. 神族 Robotics Facility 能生产哪些单位？成本、人口和前置是什么？
3. 神族 Stargate 能生产哪些空军单位？成本和人口是多少？
4. 神族 Cybernetics Core 能研究哪些升级？成本是多少？
5. 如果神族 Cybernetics Core 被摧毁，会影响哪些下游单位和升级？
6. Stalker 从哪里生产？需要什么前置？成本是多少？
7. 找出所有耗气的神族单位，并说明生产来源和科技链证据。
8. Forge 的地面武器、护甲或护盾升级影响哪些单位？这些单位从哪里生产？
9. Carrier 从哪里生产？需要什么前置建筑？成本是多少？

### 虫族 Zerg

1. 虫族 Larva 能变成哪些单位？这些单位分别需要多少矿、气和人口？
2. 虫族 Spawning Pool 能研究哪些升级？成本是多少？
3. 如果虫族 Spawning Pool 被摧毁，会影响哪些下游单位和升级？
4. Roach 从哪里生产？需要什么前置？成本是多少？
5. Evolution Chamber 能研究哪些升级？高级别升级是否需要 Lair 或 Hive？
6. 如果没有 Lair 科技，会影响哪些下游单位和升级？
7. Mutalisk 从哪里来？需要什么前置建筑？成本是多少？
8. Brood Lord 从哪里来？需要什么前置建筑？由哪个 morph 技能产生？

## 新增多跳压力测试 Prompt

### 人族 Terran

1. 人族有哪些单位需要 Factory 作为科技链前置，但不是由 Factory 直接生产的？列出单位、实际生产建筑和关键前置。
2. 从 Barracks 出发，哪些单位最终可以通过升级或技能获得隐形、潜行或不可见相关能力？
3. 哪些人族单位的生产链路中同时依赖 Starport 和 TechLab？列出成本、人口和训练技能。
4. 如果没有 Armory，会影响哪些 Factory 单位、Starport 单位和升级？
5. 哪些人族单位可以攻击空中目标，并且生产链路不需要 TechLab？列出生产建筑、成本和射程。
6. 人族所有需要 Ghost Academy 的单位、技能、升级分别是什么？说明它们通过哪个字段关联到 Ghost Academy。
7. 从 EngineeringBay 研究的升级里，哪些影响 Barracks 单位，哪些影响建筑？分别列出影响对象。
8. 找出所有由 TechLab 解锁的人族单位，按生产建筑分组，并列出矿、气、人口。
9. 如果只允许建到 Factory，不允许 Starport，人族还能生产哪些对空单位？哪些反隐能力会丢失？
10. 比较 Marine、Marauder、Reaper、Ghost 的生产要求、成本、攻击目标类型和受影响升级。
11. 找出所有人族“建筑生产建筑”的链路，例如 SCV 建造、升级成 OrbitalCommand 或 PlanetaryFortress。
12. 哪些人族升级的研究建筑本身需要某个前置建筑？列出升级、研究来源和科技链。
13. 从 FusionCore 反向看，它影响哪些单位、升级或技能？这些对象的生产来源是什么？
14. 可能暂不支持：在 400 矿 200 气以内，人族能最快解锁哪些可对空战斗单位？需要推理资源预算、科技链和生产时间。

### 神族 Protoss

1. 神族哪些单位需要 CyberneticsCore，但不是 Gateway 直接生产的？列出实际生产建筑和科技链。
2. 如果没有 RoboticsBay，哪些单位和升级会受到影响？说明它们来自 RoboticsFacility 还是其他来源。
3. 神族所有需要 FleetBeacon 的单位或升级是什么？列出生产或研究来源、成本、人口。
4. 从 Gateway 到 WarpGate，哪些单位生产方式发生变化？比较 Gateway 和 WarpGate 的训练技能。
5. 哪些神族单位是通过 Morph 得到的？列出来源单位、目标单位、技能和前置。
6. Forge 研究的升级分别影响哪些单位？这些单位来自 Gateway、WarpGate、Robotics 还是 Morph？
7. 找出所有神族耗气单位，并按生产来源分组：Gateway/WarpGate、RoboticsFacility、Stargate、Morph。
8. 如果没有 TemplarArchive，会影响哪些单位、技能、升级？它们的生产来源是什么？
9. 如果没有 DarkShrine，哪些单位或 morph 路线不可用？是否会影响 Archon？
10. 比较 Stalker、Sentry、Adept 的前置、成本、技能和是否受 CyberneticsCore 影响。
11. 哪些神族空军单位可以攻击地面？列出成本、人口、生产建筑和前置。
12. 从 Nexus 出发，能生产、变形或解锁哪些单位或建筑？区分直接生产和间接科技链影响。
13. 找出所有需要 Pylon 科技链的神族对象，并按 Unit/Upgrade 分类。
14. 可能暂不支持：如果目标是最快获得反隐能力，神族有哪些路线？比较 Observer、Oracle Revelation、PhotonCannon 的科技链和成本。

### 虫族 Zerg

1. 虫族哪些单位不是 Larva 直接 morph 出来的，而是由其他单位继续 morph 得到的？列出来源、目标、技能和前置。
2. 如果没有 Lair，哪些单位、建筑、升级会被阻断？按直接依赖和间接依赖分组。
3. 如果没有 Spire，哪些空军单位、morph 单位、飞行升级会受到影响？
4. 从 HydraliskDen 出发，哪些单位和升级依赖它？包括 Lurker 相关链路。
5. 虫族所有需要 Hive 的单位或升级是什么？列出来源建筑、研究或生产技能、成本。
6. 找出所有虫族耗气单位，按来源分组：Larva、Morph、建筑生产、技能召唤。
7. Roach 到 Ravager 的 morph 链路是什么？列出 Roach 的生产前置、Ravager 的 morph 技能和成本。
8. Corruptor 可以 morph 成哪些单位？需要什么前置？目标单位成本是多少？
9. 如果没有 InfestationPit，哪些单位、升级、Hive 科技会被影响？
10. 比较 Mutalisk、Corruptor、BroodLord、Viper 的科技链、成本、人口和来源。
11. EvolutionChamber 的 1/2/3 级升级分别需要哪些前置？哪些单位可能受到这些升级影响？
12. 哪些虫族防御建筑来自 Drone 建造？它们是否依赖 SpawningPool、EvolutionChamber 或其他建筑？
13. 从 Overlord 出发，可以 morph 或解锁哪些单位或能力？列出 Overseer、Transport、Changeling 等链路。
14. 可能暂不支持：只用 Hatchery tech，不升级 Lair，虫族能获得哪些战斗单位、反空单位和侦察能力？

### 跨种族压力测试

1. 三族分别有哪些单位需要高级科技建筑才能生产？按种族列出建筑、单位、成本。
2. 三族所有耗气空军单位分别来自哪里？列出生产源、科技链、人口。
3. 三族哪些单位可以攻击空中目标但不需要高级科技建筑？
4. 可能暂不支持：在不超过 300 矿 150 气的条件下，三族各自最快可获得哪些对空单位？
