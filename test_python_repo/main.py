"""
Main game application - demonstrates module integration
"""

from game import Player, GameBoard, calculate_winner, validate_player_name
from character import Character
from inventory import Weapon, Armor, Inventory
from combat import Combat, Arena
from quest import Quest, Objective, QuestManager
from shop import Shop, Marketplace
from world import World, Region, Location, TravelManager
from ai import NPC, AggressiveBehavior, AIController
from achievements import Achievement, AchievementManager
from stats import PlayerStatistics, Leaderboard
from save_system import SaveManager, SaveData
from config import GameConfig
from utils import generate_random_number, save_game_state, load_game_state, Logger


def create_sample_world():
    """Create a sample game world"""
    world = World("Fantasy World")
    
    # Create regions
    forest_region = Region("Dark Forest", difficulty_level=1)
    town_region = Region("Peaceful Town", difficulty_level=0)
    
    # Create locations
    town_square = Location("Town Square", "town", "A bustling town square")
    forest_entrance = Location("Forest Entrance", "forest", "Edge of the dark forest")
    
    # Connect locations
    town_square.add_connection(forest_entrance, "north")
    forest_entrance.add_connection(town_square, "south")
    
    # Add locations to regions
    town_region.add_location(town_square)
    forest_region.add_location(forest_entrance)
    
    # Add regions to world
    world.add_region(town_region)
    world.add_region(forest_region)
    
    return world, town_square


def create_sample_character():
    """Create a sample character with equipment"""
    hero = Character("Hero", "warrior", level=5)
    
    # Add items to inventory
    sword = Weapon("Iron Sword", damage=15, value=100, rarity="common")
    armor = Armor("Leather Armor", defense=10, value=80, rarity="common")
    
    hero.inventory.add_item(sword)
    hero.inventory.add_item(armor)
    
    # Equip items
    hero.equip_weapon("Iron Sword")
    hero.equip_armor("Leather Armor")
    
    return hero


def create_sample_shop():
    """Create a sample shop with items"""
    shop = Shop("Blacksmith", "weapons")
    
    # Add items to shop
    shop.add_item_to_shop(Weapon("Steel Sword", damage=25, value=200), stock=5)
    shop.add_item_to_shop(Armor("Chain Mail", defense=20, value=150), stock=3)
    shop.add_item_to_shop(Weapon("Magic Staff", damage=30, value=300, rarity="rare"), stock=1)
    
    return shop


def create_sample_quest():
    """Create a sample quest"""
    quest = Quest("quest_001", "Defeat the Goblin", "Defeat the goblin terrorizing the town", "normal")
    
    # Add objectives
    objective1 = Objective("Defeat goblin", "combat", 1)
    quest.add_objective(objective1)
    
    # Add rewards
    quest.add_reward({"type": "experience", "amount": 100})
    quest.add_reward({"type": "gold", "amount": 50})
    
    return quest


def demo_combat_system():
    """Demonstrate the combat system"""
    print("\n=== Combat System Demo ===")
    
    hero = create_sample_character()
    goblin = Character("Goblin", "warrior", level=3)
    
    arena = Arena("Training Arena")
    winner = arena.host_combat(hero, goblin)
    
    if winner:
        print(f"Winner: {winner.name}")
        print(f"Final stats: {winner.get_stats()}")


def demo_quest_system():
    """Demonstrate the quest system"""
    print("\n=== Quest System Demo ===")
    
    hero = create_sample_character()
    quest_manager = QuestManager(hero)
    
    quest = create_sample_quest()
    quest_manager.add_quest(quest)
    
    # Simulate quest progress
    quest.update_objective(0, 1)
    
    if quest.are_all_objectives_completed():
        quest_manager.complete_quest(quest.quest_id)
        print(f"Quest '{quest.title}' completed!")


def demo_shop_system():
    """Demonstrate the shop system"""
    print("\n=== Shop System Demo ===")
    
    hero = create_sample_character()
    hero.add_points(500)  # Give hero some gold
    
    shop = create_sample_shop()
    
    print(f"Hero gold: {hero.score}")
    success = shop.buy_item(hero, "Steel Sword")
    
    if success:
        print("Purchase successful!")
        print(f"Remaining gold: {hero.score}")


def start_game(num_players=2):
    """Start a new game with specified number of players"""
    players = []
    
    for i in range(num_players):
        name = input(f"Enter name for Player {i+1}: ")
        try:
            validated_name = validate_player_name(name)
            player = Player(validated_name)
            players.append(player)
        except ValueError as e:
            print(f"Error: {e}")
            return None
    
    board = GameBoard()
    logger = Logger()
    logger.log(f"Game started with {num_players} players")
    
    return {
        'players': players,
        'board': board,
        'logger': logger
    }


def play_turn(player, board):
    """Execute a single turn for a player"""
    points = generate_random_number(1, 10)
    player.add_points(points)
    
    print(f"{player.name} earned {points} points!")
    print(f"Total score: {player.get_score()}")


def end_game(players, logger):
    """End the game and determine winner"""
    winner = calculate_winner(players)
    
    if isinstance(winner, list):
        print("It's a tie!")
        for w in winner:
            print(f"  - {w.name}: {w.get_score()} points")
    else:
        print(f"Winner: {winner.name} with {winner.get_score()} points!")
    
    logger.log(f"Game ended. Winner: {winner.name if not isinstance(winner, list) else 'Tie'}")


if __name__ == "__main__":
    print("=== Game System Demonstrations ===")
    
    # Run demonstrations
    demo_combat_system()
    demo_quest_system()
    demo_shop_system()
    
    print("\n=== Starting Interactive Game ===")
    game = start_game()
    if game:
        print("Game initialized successfully!")
