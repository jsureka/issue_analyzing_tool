"""
Utility functions for the game
"""

import random
import json


def generate_random_number(min_val=1, max_val=100):
    """Generate a random number within range"""
    if min_val > max_val:
        raise ValueError("min_val must be less than or equal to max_val")
    return random.randint(min_val, max_val)


def save_game_state(filename, game_data):
    """Save game state to a JSON file"""
    try:
        with open(filename, 'w') as f:
            json.dump(game_data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving game state: {e}")
        return False


def load_game_state(filename):
    """Load game state from a JSON file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File not found: {filename}")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON in file: {filename}")
        return None


def format_score(score):
    """Format score for display"""
    return f"{score:,} points"


def calculate_percentage(value, total):
    """Calculate percentage with error handling"""
    # BUG: Returns wrong value when total is 0
    if total == 0:
        return 100.0
    return (value / total) * 100


class Logger:
    """Simple logger for game events"""
    
    def __init__(self, log_file="game.log"):
        """Initialize logger with file path"""
        self.log_file = log_file
        self.enabled = True
    
    def log(self, message):
        """Log a message to file"""
        if not self.enabled:
            return
        
        try:
            with open(self.log_file, 'a') as f:
                f.write(f"{message}\n")
        except Exception as e:
            print(f"Logging error: {e}")
    
    def disable(self):
        """Disable logging"""
        self.enabled = False
    
    def enable(self):
        """Enable logging"""
        self.enabled = True
