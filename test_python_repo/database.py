"""
Simple database-like storage for game entities
"""

import json
from utils import Logger


class GameDatabase:
    """In-memory database for game entities"""
    
    def __init__(self):
        """Initialize database"""
        self.tables = {
            "characters": {},
            "items": {},
            "quests": {},
            "locations": {}
        }
        self.logger = Logger("database.log")
    
    def insert(self, table_name, entity_id, data):
        """Insert data into table"""
        if table_name not in self.tables:
            self.tables[table_name] = {}
        
        self.tables[table_name][entity_id] = data
        self.logger.log(f"Inserted into {table_name}: {entity_id}")
        return True
    
    def get(self, table_name, entity_id):
        """Get data from table"""
        if table_name in self.tables:
            return self.tables[table_name].get(entity_id)
        return None
    
    def update(self, table_name, entity_id, data):
        """Update data in table"""
        if table_name in self.tables and entity_id in self.tables[table_name]:
            self.tables[table_name][entity_id].update(data)
            self.logger.log(f"Updated {table_name}: {entity_id}")
            return True
        return False
    
    def delete(self, table_name, entity_id):
        """Delete data from table"""
        if table_name in self.tables and entity_id in self.tables[table_name]:
            del self.tables[table_name][entity_id]
            self.logger.log(f"Deleted from {table_name}: {entity_id}")
            return True
        return False
    
    def query(self, table_name, filter_func=None):
        """Query table with optional filter"""
        if table_name not in self.tables:
            return []
        
        results = list(self.tables[table_name].values())
        
        if filter_func:
            results = [r for r in results if filter_func(r)]
        
        return results
    
    def count(self, table_name):
        """Count entries in table"""
        if table_name in self.tables:
            return len(self.tables[table_name])
        return 0
    
    def clear_table(self, table_name):
        """Clear all data from table"""
        if table_name in self.tables:
            self.tables[table_name].clear()
            self.logger.log(f"Cleared table: {table_name}")
            return True
        return False
    
    def export_to_json(self, filename):
        """Export database to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.tables, f, indent=2)
            self.logger.log(f"Exported database to {filename}")
            return True
        except Exception as e:
            self.logger.log(f"Error exporting database: {e}")
            return False
    
    def import_from_json(self, filename):
        """Import database from JSON file"""
        try:
            with open(filename, 'r') as f:
                self.tables = json.load(f)
            self.logger.log(f"Imported database from {filename}")
            return True
        except Exception as e:
            self.logger.log(f"Error importing database: {e}")
            return False


class CharacterRepository:
    """Repository pattern for character data"""
    
    def __init__(self, database):
        """Initialize repository with database"""
        self.db = database
        self.table_name = "characters"
    
    def save_character(self, character):
        """Save character to database"""
        data = {
            "name": character.name,
            "class": character.character_class,
            "level": character.level,
            "health": character.health,
            "max_health": character.max_health,
            "mana": character.mana,
            "max_mana": character.max_mana,
            "experience": character.experience,
            "score": character.score
        }
        return self.db.insert(self.table_name, character.name, data)
    
    def load_character(self, character_name):
        """Load character from database"""
        return self.db.get(self.table_name, character_name)
    
    def get_all_characters(self):
        """Get all characters"""
        return self.db.query(self.table_name)
    
    def get_characters_by_level(self, min_level):
        """Get characters above certain level"""
        return self.db.query(
            self.table_name,
            lambda c: c.get("level", 0) >= min_level
        )
    
    def delete_character(self, character_name):
        """Delete character from database"""
        return self.db.delete(self.table_name, character_name)


class QuestRepository:
    """Repository pattern for quest data"""
    
    def __init__(self, database):
        """Initialize repository with database"""
        self.db = database
        self.table_name = "quests"
    
    def save_quest(self, quest):
        """Save quest to database"""
        data = {
            "quest_id": quest.quest_id,
            "title": quest.title,
            "description": quest.description,
            "difficulty": quest.difficulty,
            "status": quest.status
        }
        return self.db.insert(self.table_name, quest.quest_id, data)
    
    def load_quest(self, quest_id):
        """Load quest from database"""
        return self.db.get(self.table_name, quest_id)
    
    def get_active_quests(self):
        """Get all active quests"""
        return self.db.query(
            self.table_name,
            lambda q: q.get("status") == "in_progress"
        )
    
    def get_completed_quests(self):
        """Get all completed quests"""
        return self.db.query(
            self.table_name,
            lambda q: q.get("status") == "completed"
        )
