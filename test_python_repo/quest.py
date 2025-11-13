"""
Quest and mission system
"""

from utils import Logger
from inventory import Item, Weapon, Armor


class Objective:
    """Represents a quest objective"""
    
    def __init__(self, description, objective_type, target_value):
        """Initialize objective"""
        self.description = description
        self.objective_type = objective_type
        self.target_value = target_value
        self.current_value = 0
        self.completed = False
    
    def update_progress(self, amount):
        """Update objective progress"""
        self.current_value += amount
        
        if self.current_value >= self.target_value:
            self.completed = True
            self.current_value = self.target_value
    
    def get_progress_percentage(self):
        """Get progress as percentage"""
        if self.target_value == 0:
            return 100.0
        return (self.current_value / self.target_value) * 100
    
    def is_completed(self):
        """Check if objective is completed"""
        return self.completed


class Quest:
    """Represents a quest with objectives and rewards"""
    
    def __init__(self, quest_id, title, description, difficulty="normal"):
        """Initialize quest"""
        self.quest_id = quest_id
        self.title = title
        self.description = description
        self.difficulty = difficulty
        self.objectives = []
        self.rewards = []
        self.status = "not_started"
        self.logger = Logger("quest.log")
    
    def add_objective(self, objective):
        """Add objective to quest"""
        self.objectives.append(objective)
    
    def add_reward(self, reward):
        """Add reward to quest"""
        self.rewards.append(reward)
    
    def start(self):
        """Start the quest"""
        if self.status == "not_started":
            self.status = "in_progress"
            self.logger.log(f"Quest started: {self.title}")
            return True
        return False
    
    def update_objective(self, objective_index, amount):
        """Update specific objective progress"""
        # BUG: No bounds checking - can cause IndexError
        self.objectives[objective_index].update_progress(amount)
        
        # Check if all objectives completed
        if self.are_all_objectives_completed():
            self.complete()
    
    def are_all_objectives_completed(self):
        """Check if all objectives are completed"""
        return all(obj.is_completed() for obj in self.objectives)
    
    def complete(self):
        """Complete the quest"""
        if self.status == "in_progress" and self.are_all_objectives_completed():
            self.status = "completed"
            self.logger.log(f"Quest completed: {self.title}")
            return True
        return False
    
    def fail(self):
        """Fail the quest"""
        if self.status == "in_progress":
            self.status = "failed"
            self.logger.log(f"Quest failed: {self.title}")
            return True
        return False
    
    def get_progress(self):
        """Get overall quest progress"""
        if not self.objectives:
            return 0.0
        
        total_progress = sum(obj.get_progress_percentage() for obj in self.objectives)
        return total_progress / len(self.objectives)
    
    def get_rewards(self):
        """Get quest rewards"""
        return self.rewards if self.status == "completed" else []


class QuestManager:
    """Manages all quests for a character"""
    
    def __init__(self, character):
        """Initialize quest manager for character"""
        self.character = character
        self.active_quests = []
        self.completed_quests = []
        self.failed_quests = []
        self.logger = Logger("quest_manager.log")
    
    def add_quest(self, quest):
        """Add quest to active quests"""
        if quest.status == "not_started":
            quest.start()
            self.active_quests.append(quest)
            self.logger.log(f"{self.character.name} accepted quest: {quest.title}")
            return True
        return False
    
    def complete_quest(self, quest_id):
        """Complete a quest and grant rewards"""
        quest = self._find_quest_by_id(quest_id, self.active_quests)
        
        if quest and quest.complete():
            self.active_quests.remove(quest)
            self.completed_quests.append(quest)
            
            # Grant rewards
            self._grant_rewards(quest)
            
            self.logger.log(f"{self.character.name} completed quest: {quest.title}")
            return True
        return False
    
    def fail_quest(self, quest_id):
        """Fail a quest"""
        quest = self._find_quest_by_id(quest_id, self.active_quests)
        
        if quest and quest.fail():
            self.active_quests.remove(quest)
            self.failed_quests.append(quest)
            
            self.logger.log(f"{self.character.name} failed quest: {quest.title}")
            return True
        return False
    
    def _find_quest_by_id(self, quest_id, quest_list):
        """Find quest by ID in a list"""
        for quest in quest_list:
            if quest.quest_id == quest_id:
                return quest
        return None
    
    def _grant_rewards(self, quest):
        """Grant quest rewards to character"""
        for reward in quest.get_rewards():
            if isinstance(reward, dict):
                if reward.get("type") == "experience":
                    self.character.gain_experience(reward.get("amount", 0))
                elif reward.get("type") == "gold":
                    self.character.add_points(reward.get("amount", 0))
            elif isinstance(reward, (Item, Weapon, Armor)):
                self.character.inventory.add_item(reward)
    
    def get_active_quests(self):
        """Get all active quests"""
        return self.active_quests
    
    def get_completed_quests(self):
        """Get all completed quests"""
        return self.completed_quests
    
    def get_quest_statistics(self):
        """Get quest statistics"""
        return {
            "active": len(self.active_quests),
            "completed": len(self.completed_quests),
            "failed": len(self.failed_quests),
            "total": len(self.active_quests) + len(self.completed_quests) + len(self.failed_quests)
        }
