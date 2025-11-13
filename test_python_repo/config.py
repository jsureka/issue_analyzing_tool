"""
Configuration and settings management
"""

import json
from utils import Logger


class GameConfig:
    """Manages game configuration settings"""
    
    DEFAULT_CONFIG = {
        "difficulty": "normal",
        "max_players": 4,
        "starting_health": 100,
        "starting_mana": 50,
        "starting_gold": 100,
        "inventory_size": 20,
        "auto_save": True,
        "sound_enabled": True,
        "music_volume": 0.7,
        "sfx_volume": 0.8
    }
    
    def __init__(self, config_file="game_config.json"):
        """Initialize game config"""
        self.config_file = config_file
        self.settings = self.DEFAULT_CONFIG.copy()
        self.logger = Logger("config.log")
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            with open(self.config_file, 'r') as f:
                loaded_config = json.load(f)
                self.settings.update(loaded_config)
                self.logger.log("Configuration loaded successfully")
        except FileNotFoundError:
            self.logger.log("Config file not found, using defaults")
            self.save_config()
        except json.JSONDecodeError:
            self.logger.log("Invalid config file, using defaults")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
                self.logger.log("Configuration saved successfully")
            return True
        except Exception as e:
            self.logger.log(f"Error saving config: {e}")
            return False
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.settings[key] = value
        self.logger.log(f"Config updated: {key} = {value}")
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.DEFAULT_CONFIG.copy()
        self.save_config()
        self.logger.log("Configuration reset to defaults")


class DifficultySettings:
    """Manages difficulty-specific settings"""
    
    DIFFICULTY_MODIFIERS = {
        "easy": {
            "enemy_health_multiplier": 0.7,
            "enemy_damage_multiplier": 0.7,
            "player_damage_multiplier": 1.3,
            "experience_multiplier": 1.5,
            "gold_multiplier": 1.5
        },
        "normal": {
            "enemy_health_multiplier": 1.0,
            "enemy_damage_multiplier": 1.0,
            "player_damage_multiplier": 1.0,
            "experience_multiplier": 1.0,
            "gold_multiplier": 1.0
        },
        "hard": {
            "enemy_health_multiplier": 1.5,
            "enemy_damage_multiplier": 1.5,
            "player_damage_multiplier": 0.8,
            "experience_multiplier": 1.2,
            "gold_multiplier": 1.2
        },
        "expert": {
            "enemy_health_multiplier": 2.0,
            "enemy_damage_multiplier": 2.0,
            "player_damage_multiplier": 0.7,
            "experience_multiplier": 1.5,
            "gold_multiplier": 1.5
        }
    }
    
    def __init__(self, difficulty="normal"):
        """Initialize difficulty settings"""
        self.difficulty = difficulty
        self.modifiers = self.DIFFICULTY_MODIFIERS.get(difficulty, self.DIFFICULTY_MODIFIERS["normal"])
    
    def get_modifier(self, modifier_name):
        """Get specific difficulty modifier"""
        return self.modifiers.get(modifier_name, 1.0)
    
    def set_difficulty(self, difficulty):
        """Change difficulty level"""
        if difficulty in self.DIFFICULTY_MODIFIERS:
            self.difficulty = difficulty
            self.modifiers = self.DIFFICULTY_MODIFIERS[difficulty]
            return True
        return False
