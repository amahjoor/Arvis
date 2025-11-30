"""
Arvis StateManager

Maintains the room state and enforces valid state transitions.
Publishes state change events to the EventBus.

States:
- EMPTY: No one in room
- OCCUPIED: Someone present, awake
- SLEEP: User sleeping
- WAKE: Alarm active, waking up
"""

from typing import Optional
from loguru import logger

from .models import RoomState, Event
from .event_bus import EventBus


# Valid state transitions
# Key: from_state, Value: set of allowed to_states
VALID_TRANSITIONS: dict[RoomState, set[RoomState]] = {
    RoomState.EMPTY: {RoomState.OCCUPIED},
    RoomState.OCCUPIED: {RoomState.EMPTY, RoomState.SLEEP},
    RoomState.SLEEP: {RoomState.WAKE, RoomState.OCCUPIED},
    RoomState.WAKE: {RoomState.OCCUPIED, RoomState.SLEEP},
}


class StateManager:
    """
    Manages room state with validated transitions.
    
    Usage:
        bus = EventBus()
        state_mgr = StateManager(bus)
        
        state_mgr.set_state(RoomState.OCCUPIED)  # Valid from EMPTY
        state_mgr.set_state(RoomState.SLEEP)     # Valid from OCCUPIED
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize the state manager.
        
        Args:
            event_bus: Optional EventBus for publishing state changes.
                      If None, state changes won't be published.
        """
        self._state = RoomState.EMPTY
        self._event_bus = event_bus
        logger.info(f"StateManager initialized with state: {self._state.value}")
    
    @property
    def state(self) -> RoomState:
        """Get current room state."""
        return self._state
    
    def get_state(self) -> RoomState:
        """Get current room state."""
        return self._state
    
    def can_transition(self, from_state: RoomState, to_state: RoomState) -> bool:
        """
        Check if a state transition is valid.
        
        Args:
            from_state: Current state
            to_state: Desired state
            
        Returns:
            True if transition is valid, False otherwise
        """
        if from_state == to_state:
            return True  # No-op is always valid
        
        valid_targets = VALID_TRANSITIONS.get(from_state, set())
        return to_state in valid_targets
    
    async def set_state(self, new_state: RoomState, force: bool = False) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: Desired state
            force: If True, skip validation (use with caution)
            
        Returns:
            True if transition succeeded, False if invalid
        """
        old_state = self._state
        
        # No-op if same state
        if old_state == new_state:
            logger.debug(f"State unchanged: {old_state.value}")
            return True
        
        # Validate transition
        if not force and not self.can_transition(old_state, new_state):
            logger.warning(
                f"Invalid state transition: {old_state.value} → {new_state.value}"
            )
            return False
        
        # Perform transition
        self._state = new_state
        logger.info(f"State changed: {old_state.value} → {new_state.value}")
        
        # Publish state change event
        if self._event_bus:
            event = Event(
                type="room.state_changed",
                payload={
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                },
                source="state_manager"
            )
            await self._event_bus.publish(event)
        
        return True
    
    def set_state_sync(self, new_state: RoomState, force: bool = False) -> bool:
        """
        Synchronous version of set_state (does not publish events).
        
        Use this only when you cannot use async, e.g., during initialization.
        
        Args:
            new_state: Desired state
            force: If True, skip validation
            
        Returns:
            True if transition succeeded, False if invalid
        """
        old_state = self._state
        
        if old_state == new_state:
            return True
        
        if not force and not self.can_transition(old_state, new_state):
            logger.warning(
                f"Invalid state transition: {old_state.value} → {new_state.value}"
            )
            return False
        
        self._state = new_state
        logger.info(f"State changed (sync): {old_state.value} → {new_state.value}")
        return True
    
    def reset(self) -> None:
        """Reset state to EMPTY."""
        self._state = RoomState.EMPTY
        logger.info("StateManager reset to EMPTY")

