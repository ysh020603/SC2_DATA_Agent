# SC2 Multi-Hop Test Prompt Set (English)

## Tested Baseline Prompts (problematic-field prompts removed)

### Terran

1. What units can a Terran Barracks produce, and what are their mineral, gas, and supply costs?
2. For a Terran Factory, which units are available with a Tech Lab and which are available without a Tech Lab?
3. Which Terran Starport units are Reactor-compatible, and which Starport units require a Tech Lab?
4. Where is a Battlecruiser produced, what prerequisites does it require, and what does it cost?
5. If the Terran Barracks is missing, which units, buildings, and upgrades become affected downstream?
6. Which Terran upgrades require a Tech Lab, and which research building or add-on provides them?
7. A Marauder comes from which production building, what add-on is required, and what does it cost?
8. Using only the Barracks production path, which Terran units can attack air, and what are their costs and ranges?
9. List Terran units that cost gas, and include their production source, add-on requirement, and tech-chain evidence.

### Protoss

1. What units can a Protoss Gateway produce, and what are their mineral, gas, and supply costs?
2. What units can a Protoss Robotics Facility produce, and what are their costs, supply, and prerequisites?
3. What air units can a Protoss Stargate produce, and what are their costs and supply?
4. Which upgrades can the Protoss Cybernetics Core research, and what are their costs?
5. If the Protoss Cybernetics Core is destroyed, which units and upgrades are affected downstream?
6. Where is a Stalker produced, what prerequisite does it require, and what does it cost?
7. Find Protoss units that cost gas and explain their production source and tech-chain evidence.
8. Which Protoss units are affected by Forge ground weapon, armor, or shield upgrades, and where are those units produced?
9. Where is a Carrier produced, what prerequisite building does it require, and what does it cost?

### Zerg

1. What units can Zerg Larva morph into, and what are their mineral, gas, and supply costs?
2. Which upgrades can the Zerg Spawning Pool research, and what are their costs?
3. If the Zerg Spawning Pool is destroyed, which units and upgrades are affected downstream?
4. Where is a Roach produced from, what prerequisite does it require, and what does it cost?
5. Which upgrades can the Zerg Evolution Chamber research, and what are the Lair or Hive prerequisites for higher levels?
6. If Zerg Lair tech is missing, which units and upgrades are affected downstream?
7. Where does a Mutalisk come from, what prerequisite building does it require, and what does it cost?
8. Where does a Brood Lord come from, what prerequisite building does it require, and what morph ability creates it?

## Additional Multi-Hop Stress Prompts

### Terran

1. Which Terran units require Factory somewhere in their tech chain but are not directly produced by Factory? List the unit, actual production building, and key prerequisites.
2. Starting from Barracks, which units can eventually gain cloak, stealth, invisibility, or related hidden-state capabilities through upgrades or abilities?
3. Which Terran units have production chains that depend on both Starport and TechLab? List cost, supply, and training ability.
4. If Armory is unavailable, which Factory units, Starport units, and upgrades are affected?
5. Which Terran units can attack air and do not require TechLab in their production chain? List production building, cost, and range.
6. What Terran units, abilities, and upgrades require Ghost Academy? Explain which data fields link them to Ghost Academy.
7. Among upgrades researched at EngineeringBay, which affect Barracks units and which affect buildings? List affected targets separately.
8. Find all Terran units unlocked by TechLab, group them by production building, and list minerals, gas, and supply.
9. If Terran can tech only up to Factory and cannot build Starport, which anti-air units remain available and which detection options are lost?
10. Compare Marine, Marauder, Reaper, and Ghost by production requirements, cost, weapon target type, and affected upgrades.
11. Find all Terran building-to-building production chains, such as SCV construction and upgrades into OrbitalCommand or PlanetaryFortress.
12. Which Terran upgrades are researched by a producer building that itself requires another prerequisite building? List upgrade, research source, and tech chain.
13. Looking backward from FusionCore, which units, upgrades, or abilities does it affect, and what are their production sources?
14. Possibly unsupported: Within 400 minerals and 200 gas, what are the fastest Terran anti-air combat units to unlock? This requires resource budget, tech chain, and production-time reasoning.

### Protoss

1. Which Protoss units require CyberneticsCore but are not directly produced by Gateway? List actual production building and tech chain.
2. If RoboticsBay is unavailable, which units and upgrades are affected? Distinguish RoboticsFacility outputs from other sources.
3. What Protoss units or upgrades require FleetBeacon? List production or research source, cost, and supply.
4. From Gateway to WarpGate, which unit production methods change? Compare Gateway and WarpGate training abilities.
5. Which Protoss units are obtained through Morph? List source unit, target unit, ability, and prerequisites.
6. Which units are affected by Forge upgrades, and do those units come from Gateway, WarpGate, Robotics, or Morph?
7. Find all Protoss gas-costing units and group them by production source: Gateway/WarpGate, RoboticsFacility, Stargate, or Morph.
8. If TemplarArchive is unavailable, which units, abilities, and upgrades are affected, and what are their production sources?
9. If DarkShrine is unavailable, which units or morph routes become unavailable? Does it affect Archon?
10. Compare Stalker, Sentry, and Adept by prerequisites, cost, abilities, and CyberneticsCore dependency.
11. Which Protoss air units can attack ground? List cost, supply, production building, and prerequisites.
12. Starting from Nexus, what units or buildings can it produce, morph, or unlock? Separate direct production from indirect tech-chain impact.
13. Find all Protoss objects that require the Pylon tech chain, grouped by Unit and Upgrade.
14. Possibly unsupported: If the goal is fastest detection, what Protoss routes exist? Compare Observer, Oracle Revelation, and PhotonCannon by tech chain and cost.

### Zerg

1. Which Zerg units are not directly morphed from Larva but are instead morphed from another unit? List source, target, ability, and prerequisite.
2. If Lair is unavailable, which units, buildings, and upgrades are blocked? Group direct and indirect dependencies.
3. If Spire is unavailable, which air units, morph units, and flyer upgrades are affected?
4. Starting from HydraliskDen, which units and upgrades depend on it, including Lurker-related chains?
5. What Zerg units or upgrades require Hive? List source building, research or production ability, and cost.
6. Find all Zerg gas-costing units and group them by source: Larva, Morph, building production, or summoned by ability.
7. What is the morph chain from Roach to Ravager? List Roach prerequisites, Ravager morph ability, and cost.
8. What can Corruptor morph into? What prerequisites are needed, and what are the target unit costs?
9. If InfestationPit is unavailable, which units, upgrades, and Hive tech are affected?
10. Compare Mutalisk, Corruptor, BroodLord, and Viper by tech chain, cost, supply, and source.
11. What prerequisites are required for EvolutionChamber level 1, 2, and 3 upgrades, and which units may be affected by these upgrades?
12. Which Zerg defensive buildings are built by Drone? Do they depend on SpawningPool, EvolutionChamber, or other buildings?
13. Starting from Overlord, what units or abilities can it morph into or unlock? Include Overseer, Transport, Changeling, and related chains.
14. Possibly unsupported: Using only Hatchery tech and no Lair upgrade, which combat units, anti-air units, and scouting options can Zerg obtain?

### Cross-Race Stress Prompts

1. For each race, which units require advanced tech buildings before they can be produced? Group by race and list building, unit, and cost.
2. Where do all gas-costing air units across all three races come from? List production source, tech chain, and supply.
3. Which units across all three races can attack air without requiring advanced tech buildings?
4. Possibly unsupported: Under a 300 minerals / 150 gas budget, what is each race's fastest route to an anti-air unit?
