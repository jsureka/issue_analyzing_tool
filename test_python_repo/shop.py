"""
Shop system for buying and selling items
"""

from inventory import Item, Weapon, Armor
from utils import Logger


class ShopItem:
    """Represents an item in the shop"""
    
    def __init__(self, item, stock, discount=0.0):
        """Initialize shop item with stock and discount"""
        self.item = item
        self.stock = stock
        self.discount = discount
    
    def get_price(self):
        """Get item price with discount applied"""
        base_price = self.item.value
        return int(base_price * (1 - self.discount))
    
    def is_in_stock(self):
        """Check if item is in stock"""
        return self.stock > 0
    
    def reduce_stock(self, amount=1):
        """Reduce stock by amount"""
        if self.stock >= amount:
            self.stock -= amount
            return True
        return False
    
    def increase_stock(self, amount=1):
        """Increase stock by amount"""
        self.stock += amount


class Shop:
    """Shop for buying and selling items"""
    
    def __init__(self, name, shop_type="general"):
        """Initialize shop"""
        self.name = name
        self.shop_type = shop_type
        self.inventory = []
        self.logger = Logger("shop.log")
        self.buy_back_rate = 0.5  # Sell items for 50% of value
    
    def add_item_to_shop(self, item, stock, discount=0.0):
        """Add item to shop inventory"""
        shop_item = ShopItem(item, stock, discount)
        self.inventory.append(shop_item)
        self.logger.log(f"Added {item.name} to {self.name} (stock: {stock})")
    
    def get_shop_item(self, item_name):
        """Get shop item by name"""
        for shop_item in self.inventory:
            if shop_item.item.name == item_name:
                return shop_item
        return None
    
    def buy_item(self, character, item_name):
        """Character buys item from shop"""
        shop_item = self.get_shop_item(item_name)
        
        if not shop_item:
            self.logger.log(f"Item not found: {item_name}")
            return False
        
        if not shop_item.is_in_stock():
            self.logger.log(f"Item out of stock: {item_name}")
            return False
        
        price = shop_item.get_price()
        
        # Check if character has enough gold (using score as gold)
        if character.score < price:
            self.logger.log(f"{character.name} cannot afford {item_name}")
            return False
        
        # BUG: Missing inventory space check - can overflow inventory
        
        # Complete transaction
        character.add_points(-price)  # Deduct gold
        shop_item.reduce_stock()
        
        # Create new item instance for character
        new_item = self._create_item_copy(shop_item.item)
        character.inventory.add_item(new_item)
        
        self.logger.log(f"{character.name} bought {item_name} for {price} gold")
        return True
    
    def sell_item(self, character, item_name):
        """Character sells item to shop"""
        item = character.inventory.get_item(item_name)
        
        if not item:
            self.logger.log(f"{character.name} doesn't have {item_name}")
            return False
        
        # Calculate sell price
        sell_price = int(item.value * self.buy_back_rate)
        
        # Complete transaction
        character.inventory.remove_item(item_name)
        character.add_points(sell_price)
        
        self.logger.log(f"{character.name} sold {item_name} for {sell_price} gold")
        return True
    
    def _create_item_copy(self, item):
        """Create a copy of an item"""
        if isinstance(item, Weapon):
            return Weapon(item.name, item.damage, item.value, item.rarity)
        elif isinstance(item, Armor):
            return Armor(item.name, item.defense, item.value, item.rarity)
        else:
            return Item(item.name, item.item_type, item.value, item.rarity)
    
    def get_items_by_type(self, item_type):
        """Get all shop items of a specific type"""
        return [si for si in self.inventory if si.item.item_type == item_type]
    
    def apply_sale(self, discount):
        """Apply sale discount to all items"""
        for shop_item in self.inventory:
            shop_item.discount = discount
        
        self.logger.log(f"{self.name} applied {discount*100}% sale")
    
    def restock(self, item_name, amount):
        """Restock an item"""
        shop_item = self.get_shop_item(item_name)
        
        if shop_item:
            shop_item.increase_stock(amount)
            self.logger.log(f"Restocked {item_name} (+{amount})")
            return True
        return False


class Marketplace:
    """Manages multiple shops"""
    
    def __init__(self):
        """Initialize marketplace"""
        self.shops = []
        self.logger = Logger("marketplace.log")
    
    def add_shop(self, shop):
        """Add shop to marketplace"""
        self.shops.append(shop)
        self.logger.log(f"Added shop: {shop.name}")
    
    def get_shop(self, shop_name):
        """Get shop by name"""
        for shop in self.shops:
            if shop.name == shop_name:
                return shop
        return None
    
    def find_item(self, item_name):
        """Find which shops have an item"""
        shops_with_item = []
        
        for shop in self.shops:
            shop_item = shop.get_shop_item(item_name)
            if shop_item and shop_item.is_in_stock():
                shops_with_item.append({
                    "shop": shop.name,
                    "price": shop_item.get_price(),
                    "stock": shop_item.stock
                })
        
        return shops_with_item
    
    def get_best_price(self, item_name):
        """Find shop with best price for an item"""
        shops_with_item = self.find_item(item_name)
        
        if not shops_with_item:
            return None
        
        return min(shops_with_item, key=lambda x: x["price"])
