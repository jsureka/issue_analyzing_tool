# Knowledge Base Testing with Buggy Repository

## Summary

Successfully expanded the `test_python_repo` into a medium-sized Python repository with **17 files**, **257 functions**, and **44 classes** to test the Knowledge Base system's ability to identify and localize bugs.

## Repository Structure

### Files Created

1. **game.py** - Base Player and GameBoard classes
2. **character.py** - Character class extending Player with RPG attributes
3. **inventory.py** - Item, Weapon, Armor classes and Inventory management
4. **combat.py** - Combat system with CombatAction, CombatRound, Combat, and Arena
5. **quest.py** - Quest, Objective, and QuestManager classes
6. **shop.py** - Shop, ShopItem, and Marketplace classes
7. **world.py** - Location, Region, World, and TravelManager classes
8. **events.py** - Event, EventListener, EventManager, and RandomEventGenerator
9. **ai.py** - NPC class with AI behaviors (Aggressive, Passive, Friendly)
10. **achievements.py** - Achievement and AchievementManager classes
11. **stats.py** - PlayerStatistics, Leaderboard, SessionTracker
12. **save_system.py** - SaveData and SaveManager for persistence
13. **config.py** - GameConfig and DifficultySettings
14. **database.py** - GameDatabase with repository pattern
15. **utils.py** - Shared utilities (Logger, random, file operations)
16. **main.py** - Entry point with system demonstrations
17. **README.md** - Documentation

### Complexity Features

- **Inheritance hierarchies**: Character → Player, Weapon/Armor → Item, NPC → Character
- **Composition patterns**: Character has Inventory, Quest has Objectives, World has Regions
- **Cross-file dependencies**: 15+ classes interact across different modules
- **Manager patterns**: QuestManager, SaveManager, AIController, EventManager, AchievementManager

## Bugs Introduced

Nine intentional bugs were introduced to test the Knowledge Base system's bug localization capabilities:

### 1. Division by Zero (character.py)

**Location**: `take_damage()` method
**Bug**: `actual_damage = damage / (damage - defense)` causes division by zero when defense equals damage
**Original**: `actual_damage = max(0, damage - defense)`

### 2. Infinite Loop (character.py)

**Location**: `gain_experience()` method
**Bug**: `while self.experience >= exp_needed: self.level_up()` creates infinite loop
**Original**: `if self.experience >= exp_needed: self.level_up()`
**Issue**: level_up() doesn't consume experience, so condition remains true

### 3. Logic Error (utils.py)

**Location**: `calculate_percentage()` function
**Bug**: Returns `100.0` instead of `0.0` when total is 0
**Impact**: Incorrect percentage calculations

### 4. Missing Validation (world.py)

**Location**: `travel()` method in TravelManager
**Bug**: Removed connection check, allows teleportation anywhere
**Original**: Had `if not self._are_connected(from_location, to_location): return False`

### 5. Missing Validation (shop.py)

**Location**: `buy_item()` method
**Bug**: Missing inventory space check before adding item
**Impact**: Can overflow inventory beyond max_size

### 6. Type Error (save_system.py)

**Location**: `auto_save()` method
**Bug**: Accesses `character.inventory.max_size` which doesn't exist on base Player class
**Impact**: AttributeError when saving a Player instead of Character

### 7. Off-by-One Error (inventory.py)

**Location**: `add_item()` method
**Bug**: `if len(self.items) > self.max_size:` should be `>=`
**Impact**: Allows one extra item beyond max_size

### 8. Logic Error (combat.py)

**Location**: `_determine_turn_order()` method
**Bug**: Both branches return `self.character1, self.character2`
**Impact**: Turn order is never randomized

### 9. Missing Bounds Check (quest.py)

**Location**: `update_objective()` method
**Bug**: Removed bounds checking `if 0 <= objective_index < len(self.objectives):`
**Impact**: IndexError when invalid index is provided

## Test Queries

Five test issues were created to evaluate bug localization:

1. **Division by Zero in Character Damage Calculation**

   - Tests if KB can locate the take_damage method bug

2. **Game Freezes When Character Levels Up**

   - Tests if KB can identify the infinite loop in gain_experience

3. **Shop Allows Buying Items with Full Inventory**

   - Tests if KB can find the missing validation in buy_item

4. **Inventory Can Hold One Extra Item**

   - Tests if KB can detect the off-by-one error in add_item

5. **Quest System Crashes on Invalid Objective Index**
   - Tests if KB can locate the missing bounds check in update_objective

## Test Execution

### Test Script: `test_buggy_repo_simple.py`

The test script:

1. Checks if repository is indexed
2. Indexes the repository if needed (257 functions, 44 classes)
3. Runs 5 bug localization queries
4. Reports top files and functions for each query
5. Shows confidence scores

### Expected Outcomes

The Knowledge Base system should:

- Successfully index all 16 Python files
- Extract and embed 257 functions
- Retrieve relevant code chunks for each bug query
- Rank files containing bugs higher in results
- Provide confidence scores for localization accuracy

## Current Status

✅ Repository created with 17 files and complex relationships
✅ 9 bugs introduced across different files and bug types
✅ Test script created and running
⏳ Indexing in progress (generating embeddings for 257 functions)
⏳ Awaiting bug localization query results

## Files for Testing

- **Test Repository**: `test_python_repo/`
- **Test Script**: `SPRINT Tool/test_buggy_repo_simple.py`
- **Bug Documentation**: This file (TEST_SUMMARY.md)
