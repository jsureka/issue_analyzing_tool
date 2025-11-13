"""
Character management system
"""

from game import Player
from inventory import Inventory, Weapon, Armor
from utils import Logger


class Character(Player):
    """Extended player with RPG character attributes"""
    
    def __init__(self, name, character_class="warrior", level=1):
        """Initialize character with class and level"""
        super().__init__(name, score=0)
        self.character_class = character_class
        self.level = level
        self.health = 100
        self.max_health = 100
        self.mana = 50
        self.max_mana = 50
        self.inventory = Inventory()
        self.experience = 0
        self.logger = Logger("character.log")
    
    def take_damage(self, damage):
        """Reduce health by damage amount"""
        equipped_armor = self._get_equipped_armor()
        defense = sum(armor.get_defense() for armor in equipped_armor)
        
        # BUG: Division by zero when defense equals damage
        actual_damage = damage / (damage - defense)
        self.health = max(0, self.health - actual_damage)
        
        self.logger.log(f"{self.name} took {actual_damage} damage (defense: {defense})")
        
        if self.health == 0:
            self.logger.log(f"{self.name} has been defeated!")
        
        return actual_damage
    
    def heal(self, amount):
        """Restore health"""
        old_health = self.health
        self.health = min(self.max_health, self.health + amount)
        healed = self.health - old_health
        
        self.logger.log(f"{self.name} healed {healed} HP")
        return healed
    
    def use_mana(self, amount):
        """Use mana for abilities"""
        if self.mana < amount:
            return False
        
        self.mana -= amount
        self.logger.log(f"{self.name} used {amount} mana")
        return True
    
    def restore_mana(self, amount):
        """Restore mana"""
        old_mana = self.mana
        self.mana = min(self.max_mana, self.mana + amount)
        restored = self.mana - old_mana
        
        return restored
    
    def gain_experience(self, exp):
        """Gain experience points"""
        self.experience += exp
        self.logger.log(f"{self.name} gained {exp} experience")
        
        # BUG: Infinite loop - level_up doesn't consume experience
        exp_needed = self._calculate_exp_for_level(self.level + 1)
        while self.experience >= exp_needed:
            self.level_up()
    
    def level_up(self):
        """Level up the character"""
        self.level += 1
        self.max_health += 10
        self.max_mana += 5
        self.health = self.max_health
        self.mana = self.max_mana
        
        self.logger.log(f"{self.name} leveled up to level {self.level}!")
    
    def _calculate_exp_for_level(self, level):
        """Calculate experience needed for a level"""
        return level * 100
    
    def equip_weapon(self, weapon_name):
        """Equip a weapon from inventory"""
        weapon = self.inventory.get_item(weapon_name)
        
        if not weapon or not isinstance(weapon, Weapon):
            return False
        
        # Unequip other weapons
        for item in self.inventory.get_items_by_type("weapon"):
            item.unequip()
        
        weapon.equip()
        self.logger.log(f"{self.name} equipped {weapon_name}")
        return True
    
    def equip_armor(self, armor_name):
        """Equip armor from inventory"""
        armor = self.inventory.get_item(armor_name)
        
        if not armor or not isinstance(armor, Armor):
            return False
        
        armor.equip()
        self.logger.log(f"{self.name} equipped {armor_name}")
        return True
    
    def _get_equipped_armor(self):
        """Get all equipped armor pieces"""
        return [item for item in self.inventory.get_equipped_items() 
                if isinstance(item, Armor)]
    
    def get_attack_power(self):
        """Calculate total attack power"""
        equipped_weapons = [item for item in self.inventory.get_equipped_items() 
                           if isinstance(item, Weapon)]
        
        base_damage = 10
        weapon_damage = sum(weapon.get_damage() for weapon in equipped_weapons)
        
        return base_damage + weapon_damage
    
    def is_alive(self):
        """Check if character is alive"""
        return self.health > 0
    
    def get_stats(self):
        """Get character statistics"""
        return {
            "name": self.name,
            "class": self.character_class,
            "level": self.level,
            "health": f"{self.health}/{self.max_health}",
            "mana": f"{self.mana}/{self.max_mana}",
            "experience": self.experience,
            "attack_power": self.get_attack_power()
        }
