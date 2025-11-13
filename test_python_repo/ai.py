"""
AI and NPC behavior system
"""

from utils import generate_random_number, Logger
from character import Character


class AIBehavior:
    """Base class for AI behaviors"""
    
    def __init__(self, behavior_type):
        """Initialize AI behavior"""
        self.behavior_type = behavior_type
        self.active = True
    
    def execute(self, npc, context):
        """Execute the behavior (to be overridden)"""
        pass
    
    def activate(self):
        """Activate behavior"""
        self.active = True
    
    def deactivate(self):
        """Deactivate behavior"""
        self.active = False


class AggressiveBehavior(AIBehavior):
    """Aggressive AI that attacks on sight"""
    
    def __init__(self):
        """Initialize aggressive behavior"""
        super().__init__("aggressive")
    
    def execute(self, npc, context):
        """Execute aggressive behavior"""
        if not self.active:
            return None
        
        # Look for nearby enemies
        nearby_characters = context.get("nearby_characters", [])
        
        if nearby_characters:
            target = nearby_characters[0]
            return {"action": "attack", "target": target}
        
        return {"action": "patrol"}


class PassiveBehavior(AIBehavior):
    """Passive AI that avoids combat"""
    
    def __init__(self):
        """Initialize passive behavior"""
        super().__init__("passive")
    
    def execute(self, npc, context):
        """Execute passive behavior"""
        if not self.active:
            return None
        
        nearby_characters = context.get("nearby_characters", [])
        
        if nearby_characters:
            return {"action": "flee"}
        
        return {"action": "wander"}


class FriendlyBehavior(AIBehavior):
    """Friendly AI that helps players"""
    
    def __init__(self):
        """Initialize friendly behavior"""
        super().__init__("friendly")
    
    def execute(self, npc, context):
        """Execute friendly behavior"""
        if not self.active:
            return None
        
        nearby_characters = context.get("nearby_characters", [])
        
        for character in nearby_characters:
            if hasattr(character, 'health') and character.health < character.max_health * 0.5:
                return {"action": "heal", "target": character}
        
        return {"action": "idle"}


class NPC(Character):
    """Non-player character with AI behavior"""
    
    def __init__(self, name, character_class="warrior", level=1, behavior=None):
        """Initialize NPC"""
        super().__init__(name, character_class, level)
        self.behavior = behavior or PassiveBehavior()
        self.is_npc = True
        self.dialogue = []
        self.quest_giver = False
    
    def set_behavior(self, behavior):
        """Set NPC behavior"""
        self.behavior = behavior
    
    def add_dialogue(self, dialogue_text):
        """Add dialogue option"""
        self.dialogue.append(dialogue_text)
    
    def get_random_dialogue(self):
        """Get random dialogue"""
        if not self.dialogue:
            return "..."
        
        index = generate_random_number(0, len(self.dialogue) - 1)
        return self.dialogue[index]
    
    def decide_action(self, context):
        """Decide next action based on behavior"""
        return self.behavior.execute(self, context)


class AIController:
    """Controls all NPCs in the game"""
    
    def __init__(self):
        """Initialize AI controller"""
        self.npcs = []
        self.logger = Logger("ai.log")
    
    def register_npc(self, npc):
        """Register NPC for AI control"""
        if isinstance(npc, NPC):
            self.npcs.append(npc)
            self.logger.log(f"Registered NPC: {npc.name}")
    
    def unregister_npc(self, npc):
        """Unregister NPC"""
        if npc in self.npcs:
            self.npcs.remove(npc)
            self.logger.log(f"Unregistered NPC: {npc.name}")
    
    def update_all(self, context):
        """Update all NPCs"""
        actions = []
        
        for npc in self.npcs:
            if npc.is_alive():
                action = npc.decide_action(context)
                if action:
                    actions.append({"npc": npc, "action": action})
        
        return actions
    
    def get_npcs_in_location(self, location):
        """Get all NPCs in a specific location"""
        return [npc for npc in self.npcs if npc in location.characters_present]
