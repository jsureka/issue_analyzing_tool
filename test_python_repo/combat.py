"""
Combat system for character battles
"""

from utils import generate_random_number, Logger
from character import Character


class CombatAction:
    """Represents a combat action"""
    
    def __init__(self, action_type, source, target, value=0):
        """Initialize combat action"""
        self.action_type = action_type
        self.source = source
        self.target = target
        self.value = value
    
    def execute(self):
        """Execute the combat action"""
        if self.action_type == "attack":
            return self._execute_attack()
        elif self.action_type == "defend":
            return self._execute_defend()
        elif self.action_type == "heal":
            return self._execute_heal()
        else:
            return False
    
    def _execute_attack(self):
        """Execute attack action"""
        damage = self.source.get_attack_power()
        actual_damage = self.target.take_damage(damage)
        return actual_damage
    
    def _execute_defend(self):
        """Execute defend action (reduces next damage)"""
        # Placeholder for defend logic
        return True
    
    def _execute_heal(self):
        """Execute heal action"""
        heal_amount = 20
        if self.source.use_mana(10):
            return self.source.heal(heal_amount)
        return 0


class CombatRound:
    """Represents a single round of combat"""
    
    def __init__(self, round_number):
        """Initialize combat round"""
        self.round_number = round_number
        self.actions = []
    
    def add_action(self, action):
        """Add action to this round"""
        self.actions.append(action)
    
    def execute(self):
        """Execute all actions in this round"""
        results = []
        for action in self.actions:
            result = action.execute()
            results.append(result)
        return results


class Combat:
    """Manages combat between characters"""
    
    def __init__(self, character1, character2):
        """Initialize combat between two characters"""
        if not isinstance(character1, Character) or not isinstance(character2, Character):
            raise ValueError("Both participants must be Character instances")
        
        self.character1 = character1
        self.character2 = character2
        self.current_round = 0
        self.combat_log = []
        self.logger = Logger("combat.log")
        self.is_active = False
    
    def start_combat(self):
        """Start the combat"""
        self.is_active = True
        self.logger.log(f"Combat started: {self.character1.name} vs {self.character2.name}")
    
    def execute_round(self):
        """Execute a single combat round"""
        if not self.is_active:
            return None
        
        self.current_round += 1
        combat_round = CombatRound(self.current_round)
        
        # Determine turn order based on random initiative
        first, second = self._determine_turn_order()
        
        # First character attacks
        action1 = CombatAction("attack", first, second)
        combat_round.add_action(action1)
        
        # Second character attacks if still alive
        if second.is_alive():
            action2 = CombatAction("attack", second, first)
            combat_round.add_action(action2)
        
        results = combat_round.execute()
        self.combat_log.append({
            "round": self.current_round,
            "actions": combat_round.actions,
            "results": results
        })
        
        # Check for combat end
        if not self.character1.is_alive() or not self.character2.is_alive():
            self.end_combat()
        
        return results
    
    def _determine_turn_order(self):
        """Determine which character goes first"""
        # BUG: Always returns same order - random not working
        if generate_random_number(0, 1) == 0:
            return self.character1, self.character2
        return self.character1, self.character2
    
    def end_combat(self):
        """End the combat"""
        self.is_active = False
        winner = self.get_winner()
        
        if winner:
            self.logger.log(f"Combat ended. Winner: {winner.name}")
            # Award experience to winner
            winner.gain_experience(50)
        else:
            self.logger.log("Combat ended in a draw")
    
    def get_winner(self):
        """Get the winner of the combat"""
        if self.character1.is_alive() and not self.character2.is_alive():
            return self.character1
        elif self.character2.is_alive() and not self.character1.is_alive():
            return self.character2
        return None
    
    def get_combat_summary(self):
        """Get summary of the combat"""
        return {
            "rounds": self.current_round,
            "winner": self.get_winner().name if self.get_winner() else "Draw",
            "character1_final_health": self.character1.health,
            "character2_final_health": self.character2.health
        }


class Arena:
    """Manages multiple combat sessions"""
    
    def __init__(self, name="Battle Arena"):
        """Initialize arena"""
        self.name = name
        self.combat_history = []
        self.logger = Logger("arena.log")
    
    def host_combat(self, character1, character2):
        """Host a combat between two characters"""
        self.logger.log(f"Arena hosting: {character1.name} vs {character2.name}")
        
        combat = Combat(character1, character2)
        combat.start_combat()
        
        # Execute combat rounds until completion
        while combat.is_active:
            combat.execute_round()
        
        self.combat_history.append(combat)
        return combat.get_winner()
    
    def get_leaderboard(self):
        """Get leaderboard of characters by wins"""
        wins = {}
        
        for combat in self.combat_history:
            winner = combat.get_winner()
            if winner:
                wins[winner.name] = wins.get(winner.name, 0) + 1
        
        return sorted(wins.items(), key=lambda x: x[1], reverse=True)
