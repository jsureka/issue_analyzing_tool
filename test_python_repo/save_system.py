"""
Save and load game system
"""

import json
import os
from datetime import datetime
from utils import Logger


class SaveData:
    """Represents save game data"""
    
    def __init__(self, save_name):
        """Initialize save data"""
        self.save_name = save_name
        self.timestamp = datetime.now()
        self.data = {}
    
    def set_data(self, key, value):
        """Set data in save"""
        self.data[key] = value
    
    def get_data(self, key, default=None):
        """Get data from save"""
        return self.data.get(key, default)
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            "save_name": self.save_name,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data_dict):
        """Create SaveData from dictionary"""
        save = cls(data_dict["save_name"])
        save.timestamp = datetime.fromisoformat(data_dict["timestamp"])
        save.data = data_dict["data"]
        return save


class SaveManager:
    """Manages game saves"""
    
    def __init__(self, save_directory="saves"):
        """Initialize save manager"""
        self.save_directory = save_directory
        self.logger = Logger("save_system.log")
        self._ensure_save_directory()
    
    def _ensure_save_directory(self):
        """Ensure save directory exists"""
        if not os.path.exists(self.save_directory):
            os.makedirs(self.save_directory)
            self.logger.log(f"Created save directory: {self.save_directory}")
    
    def save_game(self, save_data):
        """Save game data to file"""
        filename = self._get_save_filename(save_data.save_name)
        
        try:
            with open(filename, 'w') as f:
                json.dump(save_data.to_dict(), f, indent=2)
            
            self.logger.log(f"Game saved: {save_data.save_name}")
            return True
        except Exception as e:
            self.logger.log(f"Error saving game: {e}")
            return False
    
    def load_game(self, save_name):
        """Load game data from file"""
        filename = self._get_save_filename(save_name)
        
        try:
            with open(filename, 'r') as f:
                data_dict = json.load(f)
            
            save_data = SaveData.from_dict(data_dict)
            self.logger.log(f"Game loaded: {save_name}")
            return save_data
        except FileNotFoundError:
            self.logger.log(f"Save file not found: {save_name}")
            return None
        except Exception as e:
            self.logger.log(f"Error loading game: {e}")
            return None
    
    def delete_save(self, save_name):
        """Delete a save file"""
        filename = self._get_save_filename(save_name)
        
        try:
            if os.path.exists(filename):
                os.remove(filename)
                self.logger.log(f"Save deleted: {save_name}")
                return True
            return False
        except Exception as e:
            self.logger.log(f"Error deleting save: {e}")
            return False
    
    def list_saves(self):
        """List all available saves"""
        saves = []
        
        try:
            for filename in os.listdir(self.save_directory):
                if filename.endswith('.json'):
                    save_name = filename[:-5]
                    save_data = self.load_game(save_name)
                    if save_data:
                        saves.append({
                            "name": save_name,
                            "timestamp": save_data.timestamp
                        })
        except Exception as e:
            self.logger.log(f"Error listing saves: {e}")
        
        return sorted(saves, key=lambda x: x["timestamp"], reverse=True)
    
    def _get_save_filename(self, save_name):
        """Get full path for save file"""
        return os.path.join(self.save_directory, f"{save_name}.json")
    
    def auto_save(self, character):
        """Create an auto-save"""
        save_data = SaveData("autosave")
        
        # BUG: Trying to access attribute that doesn't exist on base Player class
        save_data.set_data("character", {
            "name": character.name,
            "level": character.level,
            "health": character.health,
            "mana": character.mana,
            "experience": character.experience,
            "score": character.score,
            "inventory_size": character.inventory.max_size  # Will fail if character is Player not Character
        })
        
        return self.save_game(save_data)
