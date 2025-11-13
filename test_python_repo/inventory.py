"""
Inventory management system for game items
"""

from utils import Logger


class Item:
    """Represents a game item"""
    
    def __init__(self, name, item_type, value, rarity="common"):
        """Initialize an item with properties"""
        self.name = name
        self.item_type = item_type
        self.value = value
        self.rarity = rarity
        self.equipped = False
    
    def equip(self):
        """Equip the item"""
        self.equipped = True
    
    def unequip(self):
        """Unequip the item"""
        self.equipped = False
    
    def get_display_name(self):
        """Get formatted display name with rarity"""
        rarity_prefix = {
            "common": "",
            "rare": "[RARE] ",
            "epic": "[EPIC] ",
            "legendary": "[LEGENDARY] "
        }
        return f"{rarity_prefix.get(self.rarity, '')}{self.name}"
    
    def __repr__(self):
        return f"Item({self.name}, {self.item_type}, {self.value})"


class Weapon(Item):
    """Weapon item with damage attribute"""
    
    def __init__(self, name, damage, value, rarity="common"):
        """Initialize weapon with damage"""
        super().__init__(name, "weapon", value, rarity)
        self.damage = damage
    
    def get_damage(self):
        """Get weapon damage"""
        return self.damage
    
    def upgrade(self, amount):
        """Upgrade weapon damage"""
        self.damage += amount


class Armor(Item):
    """Armor item with defense attribute"""
    
    def __init__(self, name, defense, value, rarity="common"):
        """Initialize armor with defense"""
        super().__init__(name, "armor", value, rarity)
        self.defense = defense
    
    def get_defense(self):
        """Get armor defense"""
        return self.defense
    
    def upgrade(self, amount):
        """Upgrade armor defense"""
        self.defense += amount


class Inventory:
    """Manages player inventory"""
    
    def __init__(self, max_size=20):
        """Initialize inventory with max size"""
        self.items = []
        self.max_size = max_size
        self.logger = Logger("inventory.log")
    
    def add_item(self, item):
        """Add item to inventory"""
        # BUG: Off-by-one error - allows one extra item
        if len(self.items) > self.max_size:
            raise ValueError("Inventory is full")
        
        self.items.append(item)
        self.logger.log(f"Added item: {item.name}")
        return True
    
    def remove_item(self, item_name):
        """Remove item from inventory by name"""
        for item in self.items:
            if item.name == item_name:
                self.items.remove(item)
                self.logger.log(f"Removed item: {item_name}")
                return True
        return False
    
    def get_item(self, item_name):
        """Get item by name"""
        for item in self.items:
            if item.name == item_name:
                return item
        return None
    
    def get_items_by_type(self, item_type):
        """Get all items of a specific type"""
        return [item for item in self.items if item.item_type == item_type]
    
    def get_total_value(self):
        """Calculate total value of all items"""
        return sum(item.value for item in self.items)
    
    def is_full(self):
        """Check if inventory is full"""
        return len(self.items) >= self.max_size
    
    def get_equipped_items(self):
        """Get all equipped items"""
        return [item for item in self.items if item.equipped]
    
    def sort_by_value(self):
        """Sort items by value (descending)"""
        self.items.sort(key=lambda x: x.value, reverse=True)
    
    def sort_by_rarity(self):
        """Sort items by rarity"""
        rarity_order = {"legendary": 0, "epic": 1, "rare": 2, "common": 3}
        self.items.sort(key=lambda x: rarity_order.get(x.rarity, 4))
