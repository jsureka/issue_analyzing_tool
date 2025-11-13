"""
Achievement and progression tracking system
"""

from utils import Logger
from datetime import datetime


class Achievement:
    """Represents an achievement"""
    
    def __init__(self, achievement_id, title, description, points, requirement):
        """Initialize achievement"""
        self.achievement_id = achievement_id
        self.title = title
        self.description = description
        self.points = points
        self.requirement = requirement
        self.unlocked = False
        self.unlock_date = None
        self.progress = 0
    
    def check_unlock(self, player_stats):
        """Check if achievement should be unlocked"""
        if self.unlocked:
            return False
        
        # Check requirement
        if self._meets_requirement(player_stats):
            self.unlock()
            return True
        
        # Update progress
        self._update_progress(player_stats)
        return False
    
    def _meets_requirement(self, player_stats):
        """Check if player meets achievement requirement"""
        req_type = self.requirement.get("type")
        req_value = self.requirement.get("value")
        
        if req_type == "level":
            return player_stats.get("level", 0) >= req_value
        elif req_type == "score":
            return player_stats.get("score", 0) >= req_value
        elif req_type == "quests_completed":
            return player_stats.get("quests_completed", 0) >= req_value
        elif req_type == "enemies_defeated":
            return player_stats.get("enemies_defeated", 0) >= req_value
        
        return False
    
    def _update_progress(self, player_stats):
        """Update achievement progress"""
        req_type = self.requirement.get("type")
        req_value = self.requirement.get("value")
        
        if req_type == "level":
            current = player_stats.get("level", 0)
        elif req_type == "score":
            current = player_stats.get("score", 0)
        elif req_type == "quests_completed":
            current = player_stats.get("quests_completed", 0)
        elif req_type == "enemies_defeated":
            current = player_stats.get("enemies_defeated", 0)
        else:
            current = 0
        
        self.progress = min(100, int((current / req_value) * 100))
    
    def unlock(self):
        """Unlock the achievement"""
        self.unlocked = True
        self.unlock_date = datetime.now()
        self.progress = 100
    
    def get_progress_percentage(self):
        """Get progress as percentage"""
        return self.progress


class AchievementManager:
    """Manages player achievements"""
    
    def __init__(self, character):
        """Initialize achievement manager"""
        self.character = character
        self.achievements = []
        self.logger = Logger("achievements.log")
    
    def add_achievement(self, achievement):
        """Add achievement to track"""
        self.achievements.append(achievement)
    
    def check_achievements(self):
        """Check all achievements for unlocks"""
        player_stats = self._get_player_stats()
        newly_unlocked = []
        
        for achievement in self.achievements:
            if achievement.check_unlock(player_stats):
                newly_unlocked.append(achievement)
                self.logger.log(f"{self.character.name} unlocked: {achievement.title}")
        
        return newly_unlocked
    
    def _get_player_stats(self):
        """Get player statistics for achievement checking"""
        return {
            "level": getattr(self.character, "level", 0),
            "score": self.character.score,
            "quests_completed": 0,  # Would be tracked separately
            "enemies_defeated": 0   # Would be tracked separately
        }
    
    def get_unlocked_achievements(self):
        """Get all unlocked achievements"""
        return [a for a in self.achievements if a.unlocked]
    
    def get_locked_achievements(self):
        """Get all locked achievements"""
        return [a for a in self.achievements if not a.unlocked]
    
    def get_total_points(self):
        """Get total achievement points earned"""
        return sum(a.points for a in self.achievements if a.unlocked)
    
    def get_completion_percentage(self):
        """Get overall achievement completion percentage"""
        if not self.achievements:
            return 0.0
        
        unlocked = len(self.get_unlocked_achievements())
        return (unlocked / len(self.achievements)) * 100
