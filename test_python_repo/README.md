# Test Python Game Repository

A medium-complexity Python game repository for testing knowledge base systems.

## Project Structure

```
test_python_repo/
├── game.py              # Core game classes (Player, GameBoard)
├── character.py         # RPG character system (extends Player)
├── inventory.py         # Item and inventory management
├── combat.py            # Combat system and arena
├── quest.py             # Quest and objective system
├── shop.py              # Shopping and marketplace
├── world.py             # World, regions, and locations
├── events.py            # Event system and listeners
├── achievements.py      # Achievement tracking
├── ai.py                # NPC AI behaviors
├── stats.py             # Statistics and leaderboards
├── save_system.py       # Save/load functionality
├── config.py            # Configuration management
├── utils.py             # Utility functions and Logger
└── main.py              # Main application entry point
```

## Module Dependencies

### Core Modules

- **game.py**: Base classes for Player and GameBoard
- **utils.py**: Shared utilities (Logger, random, file operations)

### Character System

- **character.py**: Extends Player from game.py, uses Inventory
- **inventory.py**: Item, Weapon, Armor classes
- **combat.py**: Uses Character for battles

### Game Systems

- **quest.py**: Quest management, uses inventory items as rewards
- **shop.py**: Uses inventory items, interacts with Character
- **world.py**: Location and travel management
- **events.py**: Event-driven system
- **achievements.py**: Progress tracking for characters

### AI & NPCs

- **ai.py**: NPC behaviors, extends Character class

### Meta Systems

- **stats.py**: Statistics tracking
- **save_system.py**: Persistence layer
- **config.py**: Game configuration

## Class Relationships

```
Player (game.py)
  └── Character (character.py)
       ├── NPC (ai.py)
       └── uses Inventory (inventory.py)
            ├── Item
            ├── Weapon (extends Item)
            └── Armor (extends Item)

Combat (combat.py)
  ├── uses Character
  └── managed by Arena

Quest (quest.py)
  ├── has Objectives
  └── managed by QuestManager
       └── uses Character

Shop (shop.py)
  ├── uses Items/Weapons/Armor
  └── managed by Marketplace

World (world.py)
  ├── has Regions
  │    └── has Locations
  │         └── contains Characters
  └── managed by TravelManager
```

## Key Features

1. **Inheritance**: Character extends Player, Weapon/Armor extend Item
2. **Composition**: Character has Inventory, Quest has Objectives
3. **Manager Pattern**: QuestManager, SaveManager, AIController
4. **Event System**: EventManager with listeners
5. **Persistence**: SaveManager for game state
6. **Configuration**: GameConfig with difficulty settings

## Usage Example

```python
from character import Character
from inventory import Weapon, Armor
from combat import Combat, Arena
from quest import Quest, Objective

# Create characters
hero = Character("Hero", "warrior", level=5)
enemy = Character("Goblin", "warrior", level=3)

# Equip items
sword = Weapon("Iron Sword", damage=15, value=100)
hero.inventory.add_item(sword)
hero.equip_weapon("Iron Sword")

# Start combat
arena = Arena("Battle Arena")
winner = arena.host_combat(hero, enemy)

# Create quest
quest = Quest("quest_1", "Defeat the Goblin", "Defeat the goblin in combat")
objective = Objective("Defeat goblin", "combat", 1)
quest.add_objective(objective)
```
