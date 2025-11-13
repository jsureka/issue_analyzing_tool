"""
Event system for game events and triggers
"""

from utils import Logger, generate_random_number
from datetime import datetime


class Event:
    """Represents a game event"""
    
    def __init__(self, event_id, event_type, description):
        """Initialize event"""
        self.event_id = event_id
        self.event_type = event_type
        self.description = description
        self.timestamp = datetime.now()
        self.triggered = False
    
    def trigger(self):
        """Trigger the event"""
        self.triggered = True
        self.timestamp = datetime.now()
    
    def is_triggered(self):
        """Check if event has been triggered"""
        return self.triggered


class EventListener:
    """Listens for and handles events"""
    
    def __init__(self, event_type, callback):
        """Initialize event listener"""
        self.event_type = event_type
        self.callback = callback
        self.active = True
    
    def handle_event(self, event):
        """Handle an event if type matches"""
        if self.active and event.event_type == self.event_type:
            self.callback(event)
            return True
        return False
    
    def deactivate(self):
        """Deactivate listener"""
        self.active = False
    
    def activate(self):
        """Activate listener"""
        self.active = True


class EventManager:
    """Manages game events and listeners"""
    
    def __init__(self):
        """Initialize event manager"""
        self.events = []
        self.listeners = []
        self.logger = Logger("events.log")
    
    def register_listener(self, listener):
        """Register an event listener"""
        self.listeners.append(listener)
        self.logger.log(f"Registered listener for {listener.event_type}")
    
    def unregister_listener(self, listener):
        """Unregister an event listener"""
        if listener in self.listeners:
            self.listeners.remove(listener)
            self.logger.log(f"Unregistered listener for {listener.event_type}")
    
    def trigger_event(self, event):
        """Trigger an event and notify listeners"""
        event.trigger()
        self.events.append(event)
        
        self.logger.log(f"Event triggered: {event.event_type} - {event.description}")
        
        # Notify all matching listeners
        for listener in self.listeners:
            listener.handle_event(event)
    
    def get_events_by_type(self, event_type):
        """Get all events of a specific type"""
        return [e for e in self.events if e.event_type == event_type]
    
    def clear_events(self):
        """Clear all events"""
        self.events.clear()
        self.logger.log("Cleared all events")


class RandomEventGenerator:
    """Generates random events during gameplay"""
    
    def __init__(self, event_manager):
        """Initialize random event generator"""
        self.event_manager = event_manager
        self.event_pool = []
        self.logger = Logger("random_events.log")
    
    def add_event_to_pool(self, event_template):
        """Add event template to pool"""
        self.event_pool.append(event_template)
    
    def generate_random_event(self):
        """Generate a random event from pool"""
        if not self.event_pool:
            return None
        
        # Random chance to generate event
        if generate_random_number(1, 100) <= 30:  # 30% chance
            template = self.event_pool[generate_random_number(0, len(self.event_pool) - 1)]
            
            event = Event(
                event_id=f"random_{datetime.now().timestamp()}",
                event_type=template["type"],
                description=template["description"]
            )
            
            self.event_manager.trigger_event(event)
            self.logger.log(f"Generated random event: {event.description}")
            return event
        
        return None
