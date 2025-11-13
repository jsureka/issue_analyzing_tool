"""
Statistics tracking and analytics
"""

from utils import Logger, calculate_percentage
from datetime import datetime


class PlayerStatistics:
    """Tracks detailed player statistics"""
    
    def __init__(self, player_name):
        """Initialize player statistics"""
        self.player_name = player_name
        self.stats = {
            "total_playtime": 0,
            "enemies_defeated": 0,
            "quests_completed": 0,
            "quests_failed": 0,
            "items_collected": 0,
            "gold_earned": 0,
            "gold_spent": 0,
            "damage_dealt": 0,
            "damage_taken": 0,
            "deaths": 0,
            "levels_gained": 0,
            "distance_traveled": 0
        }
        self.session_start = datetime.now()
        self.logger = Logger("stats.log")
    
    def increment(self, stat_name, amount=1):
        """Increment a statistic"""
        if stat_name in self.stats:
            self.stats[stat_name] += amount
            self.logger.log(f"{self.player_name}: {stat_name} +{amount}")
    
    def get_stat(self, stat_name):
        """Get a specific statistic"""
        return self.stats.get(stat_name, 0)
    
    def get_all_stats(self):
        """Get all statistics"""
        return self.stats.copy()
    
    def calculate_kdr(self):
        """Calculate kill/death ratio"""
        deaths = self.stats["deaths"]
        if deaths == 0:
            return self.stats["enemies_defeated"]
        return self.stats["enemies_defeated"] / deaths
    
    def calculate_quest_success_rate(self):
        """Calculate quest success rate"""
        total_quests = self.stats["quests_completed"] + self.stats["quests_failed"]
        if total_quests == 0:
            return 0.0
        return calculate_percentage(self.stats["quests_completed"], total_quests)
    
    def get_net_gold(self):
        """Get net gold (earned - spent)"""
        return self.stats["gold_earned"] - self.stats["gold_spent"]
    
    def update_playtime(self):
        """Update total playtime"""
        current_time = datetime.now()
        session_duration = (current_time - self.session_start).total_seconds()
        self.stats["total_playtime"] += session_duration
        self.session_start = current_time


class Leaderboard:
    """Manages game leaderboards"""
    
    def __init__(self, leaderboard_name):
        """Initialize leaderboard"""
        self.name = leaderboard_name
        self.entries = []
        self.logger = Logger("leaderboard.log")
    
    def add_entry(self, player_name, score, metadata=None):
        """Add entry to leaderboard"""
        entry = {
            "player_name": player_name,
            "score": score,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        self.entries.append(entry)
        self._sort_entries()
        self.logger.log(f"Added {player_name} to {self.name}: {score}")
    
    def _sort_entries(self):
        """Sort entries by score (descending)"""
        self.entries.sort(key=lambda x: x["score"], reverse=True)
    
    def get_top_entries(self, count=10):
        """Get top N entries"""
        return self.entries[:count]
    
    def get_player_rank(self, player_name):
        """Get player's rank on leaderboard"""
        for i, entry in enumerate(self.entries):
            if entry["player_name"] == player_name:
                return i + 1
        return None
    
    def get_player_best_score(self, player_name):
        """Get player's best score"""
        player_entries = [e for e in self.entries if e["player_name"] == player_name]
        if player_entries:
            return max(e["score"] for e in player_entries)
        return None


class SessionTracker:
    """Tracks game session information"""
    
    def __init__(self):
        """Initialize session tracker"""
        self.session_id = datetime.now().timestamp()
        self.start_time = datetime.now()
        self.end_time = None
        self.events = []
        self.logger = Logger("session.log")
    
    def log_event(self, event_type, description):
        """Log a session event"""
        event = {
            "type": event_type,
            "description": description,
            "timestamp": datetime.now()
        }
        self.events.append(event)
        self.logger.log(f"Session event: {event_type} - {description}")
    
    def end_session(self):
        """End the session"""
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        self.logger.log(f"Session ended. Duration: {duration}s")
        return duration
    
    def get_session_duration(self):
        """Get session duration in seconds"""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    def get_events_by_type(self, event_type):
        """Get all events of a specific type"""
        return [e for e in self.events if e["type"] == event_type]
