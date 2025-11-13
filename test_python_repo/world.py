"""
World and location management system
"""

from utils import Logger, generate_random_number
from character import Character


class Location:
    """Represents a location in the game world"""
    
    def __init__(self, name, location_type, description=""):
        """Initialize location"""
        self.name = name
        self.location_type = location_type
        self.description = description
        self.connected_locations = []
        self.characters_present = []
        self.items = []
    
    def add_connection(self, location, direction):
        """Add connection to another location"""
        self.connected_locations.append({
            "location": location,
            "direction": direction
        })
    
    def get_connections(self):
        """Get all connected locations"""
        return self.connected_locations
    
    def add_character(self, character):
        """Add character to this location"""
        if character not in self.characters_present:
            self.characters_present.append(character)
    
    def remove_character(self, character):
        """Remove character from this location"""
        if character in self.characters_present:
            self.characters_present.remove(character)
    
    def add_item(self, item):
        """Add item to location"""
        self.items.append(item)
    
    def remove_item(self, item_name):
        """Remove item from location"""
        for item in self.items:
            if item.name == item_name:
                self.items.remove(item)
                return item
        return None


class Region:
    """Represents a region containing multiple locations"""
    
    def __init__(self, name, difficulty_level=1):
        """Initialize region"""
        self.name = name
        self.difficulty_level = difficulty_level
        self.locations = []
        self.logger = Logger("world.log")
    
    def add_location(self, location):
        """Add location to region"""
        self.locations.append(location)
        self.logger.log(f"Added location {location.name} to region {self.name}")
    
    def get_location(self, location_name):
        """Get location by name"""
        for location in self.locations:
            if location.name == location_name:
                return location
        return None
    
    def get_all_characters(self):
        """Get all characters in the region"""
        characters = []
        for location in self.locations:
            characters.extend(location.characters_present)
        return characters


class World:
    """Manages the entire game world"""
    
    def __init__(self, name="Game World"):
        """Initialize world"""
        self.name = name
        self.regions = []
        self.logger = Logger("world.log")
    
    def add_region(self, region):
        """Add region to world"""
        self.regions.append(region)
        self.logger.log(f"Added region: {region.name}")
    
    def get_region(self, region_name):
        """Get region by name"""
        for region in self.regions:
            if region.name == region_name:
                return region
        return None
    
    def find_character(self, character_name):
        """Find character location in world"""
        for region in self.regions:
            for location in region.locations:
                for character in location.characters_present:
                    if character.name == character_name:
                        return {
                            "region": region.name,
                            "location": location.name
                        }
        return None
    
    def get_world_statistics(self):
        """Get world statistics"""
        total_locations = sum(len(region.locations) for region in self.regions)
        total_characters = sum(len(region.get_all_characters()) for region in self.regions)
        
        return {
            "regions": len(self.regions),
            "locations": total_locations,
            "characters": total_characters
        }


class TravelManager:
    """Manages character travel between locations"""
    
    def __init__(self):
        """Initialize travel manager"""
        self.logger = Logger("travel.log")
    
    def travel(self, character, from_location, to_location):
        """Move character from one location to another"""
        # BUG: Removed connection check - allows teleportation anywhere
        
        # Move character
        from_location.remove_character(character)
        to_location.add_character(character)
        
        self.logger.log(f"{character.name} traveled from {from_location.name} to {to_location.name}")
        return True
    
    def _are_connected(self, location1, location2):
        """Check if two locations are connected"""
        for connection in location1.get_connections():
            if connection["location"] == location2:
                return True
        return False
    
    def get_travel_options(self, location):
        """Get available travel destinations from location"""
        return [conn["location"].name for conn in location.get_connections()]
