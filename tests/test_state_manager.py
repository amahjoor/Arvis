"""
Tests for StateManager.

Tests cover:
- Initial state
- Valid state transitions
- Invalid state transitions
- Event publishing on state change
- Reset functionality
"""

import pytest
import asyncio

from src.core.state_manager import StateManager, VALID_TRANSITIONS
from src.core.event_bus import EventBus
from src.core.models import RoomState, Event


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def state_manager(event_bus):
    """Create a StateManager with an EventBus."""
    return StateManager(event_bus)


@pytest.fixture
def state_manager_no_bus():
    """Create a StateManager without an EventBus."""
    return StateManager(None)


class TestInitialState:
    """Test initial state configuration."""
    
    def test_initial_state_is_empty(self, state_manager):
        """Test that initial state is EMPTY."""
        assert state_manager.state == RoomState.EMPTY
        assert state_manager.get_state() == RoomState.EMPTY
    
    def test_state_manager_without_bus(self, state_manager_no_bus):
        """Test that StateManager works without an EventBus."""
        assert state_manager_no_bus.state == RoomState.EMPTY


class TestValidTransitions:
    """Test valid state transitions."""
    
    def test_can_transition_same_state(self, state_manager):
        """Test that same-state transition is valid (no-op)."""
        assert state_manager.can_transition(RoomState.EMPTY, RoomState.EMPTY) is True
    
    def test_empty_to_occupied_valid(self, state_manager):
        """Test EMPTY → OCCUPIED is valid."""
        assert state_manager.can_transition(RoomState.EMPTY, RoomState.OCCUPIED) is True
    
    def test_occupied_to_empty_valid(self, state_manager):
        """Test OCCUPIED → EMPTY is valid."""
        assert state_manager.can_transition(RoomState.OCCUPIED, RoomState.EMPTY) is True
    
    def test_occupied_to_sleep_valid(self, state_manager):
        """Test OCCUPIED → SLEEP is valid."""
        assert state_manager.can_transition(RoomState.OCCUPIED, RoomState.SLEEP) is True
    
    def test_sleep_to_wake_valid(self, state_manager):
        """Test SLEEP → WAKE is valid."""
        assert state_manager.can_transition(RoomState.SLEEP, RoomState.WAKE) is True
    
    def test_wake_to_occupied_valid(self, state_manager):
        """Test WAKE → OCCUPIED is valid."""
        assert state_manager.can_transition(RoomState.WAKE, RoomState.OCCUPIED) is True
    
    @pytest.mark.asyncio
    async def test_set_state_valid_transition(self, state_manager):
        """Test that valid transitions succeed."""
        # EMPTY → OCCUPIED
        result = await state_manager.set_state(RoomState.OCCUPIED)
        assert result is True
        assert state_manager.state == RoomState.OCCUPIED
        
        # OCCUPIED → SLEEP
        result = await state_manager.set_state(RoomState.SLEEP)
        assert result is True
        assert state_manager.state == RoomState.SLEEP


class TestInvalidTransitions:
    """Test invalid state transitions."""
    
    def test_empty_to_sleep_invalid(self, state_manager):
        """Test EMPTY → SLEEP is invalid."""
        assert state_manager.can_transition(RoomState.EMPTY, RoomState.SLEEP) is False
    
    def test_empty_to_wake_invalid(self, state_manager):
        """Test EMPTY → WAKE is invalid."""
        assert state_manager.can_transition(RoomState.EMPTY, RoomState.WAKE) is False
    
    def test_sleep_to_empty_invalid(self, state_manager):
        """Test SLEEP → EMPTY is invalid (must go through WAKE/OCCUPIED)."""
        assert state_manager.can_transition(RoomState.SLEEP, RoomState.EMPTY) is False
    
    @pytest.mark.asyncio
    async def test_set_state_invalid_transition_fails(self, state_manager):
        """Test that invalid transitions return False."""
        # Try EMPTY → SLEEP (invalid)
        result = await state_manager.set_state(RoomState.SLEEP)
        assert result is False
        assert state_manager.state == RoomState.EMPTY  # Unchanged
    
    @pytest.mark.asyncio
    async def test_force_bypasses_validation(self, state_manager):
        """Test that force=True bypasses validation."""
        # EMPTY → SLEEP normally invalid, but force=True allows it
        result = await state_manager.set_state(RoomState.SLEEP, force=True)
        assert result is True
        assert state_manager.state == RoomState.SLEEP


class TestEventPublishing:
    """Test state change event publishing."""
    
    @pytest.mark.asyncio
    async def test_state_change_publishes_event(self, state_manager, event_bus):
        """Test that state changes publish room.state_changed events."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe("room.state_changed", handler)
        
        await state_manager.set_state(RoomState.OCCUPIED)
        
        assert len(received_events) == 1
        assert received_events[0].type == "room.state_changed"
        assert received_events[0].payload["old_state"] == "empty"
        assert received_events[0].payload["new_state"] == "occupied"
    
    @pytest.mark.asyncio
    async def test_same_state_no_event(self, state_manager, event_bus):
        """Test that setting same state doesn't publish event."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe("room.state_changed", handler)
        
        # Set to same state (EMPTY → EMPTY)
        await state_manager.set_state(RoomState.EMPTY)
        
        assert len(received_events) == 0
    
    @pytest.mark.asyncio
    async def test_no_event_bus_no_error(self, state_manager_no_bus):
        """Test that state changes work without an EventBus."""
        # Should not raise
        result = await state_manager_no_bus.set_state(RoomState.OCCUPIED)
        assert result is True


class TestSyncOperations:
    """Test synchronous state operations."""
    
    def test_set_state_sync_valid(self, state_manager):
        """Test synchronous state change."""
        result = state_manager.set_state_sync(RoomState.OCCUPIED)
        assert result is True
        assert state_manager.state == RoomState.OCCUPIED
    
    def test_set_state_sync_invalid(self, state_manager):
        """Test synchronous invalid state change."""
        result = state_manager.set_state_sync(RoomState.SLEEP)
        assert result is False
        assert state_manager.state == RoomState.EMPTY


class TestReset:
    """Test reset functionality."""
    
    @pytest.mark.asyncio
    async def test_reset_returns_to_empty(self, state_manager):
        """Test that reset() returns state to EMPTY."""
        await state_manager.set_state(RoomState.OCCUPIED)
        await state_manager.set_state(RoomState.SLEEP, force=True)
        
        assert state_manager.state == RoomState.SLEEP
        
        state_manager.reset()
        
        assert state_manager.state == RoomState.EMPTY


class TestTransitionMatrix:
    """Verify the complete transition matrix."""
    
    def test_all_valid_transitions_documented(self):
        """Ensure all states have defined valid transitions."""
        for state in RoomState:
            assert state in VALID_TRANSITIONS, f"Missing transitions for {state}"
    
    def test_transition_matrix_complete(self, state_manager):
        """Test all defined transitions are working."""
        test_cases = [
            (RoomState.EMPTY, RoomState.OCCUPIED, True),
            (RoomState.EMPTY, RoomState.SLEEP, False),
            (RoomState.EMPTY, RoomState.WAKE, False),
            (RoomState.OCCUPIED, RoomState.EMPTY, True),
            (RoomState.OCCUPIED, RoomState.SLEEP, True),
            (RoomState.OCCUPIED, RoomState.WAKE, False),
            (RoomState.SLEEP, RoomState.WAKE, True),
            (RoomState.SLEEP, RoomState.OCCUPIED, True),
            (RoomState.SLEEP, RoomState.EMPTY, False),
            (RoomState.WAKE, RoomState.OCCUPIED, True),
            (RoomState.WAKE, RoomState.SLEEP, True),
            (RoomState.WAKE, RoomState.EMPTY, False),
        ]
        
        for from_state, to_state, expected in test_cases:
            result = state_manager.can_transition(from_state, to_state)
            assert result == expected, \
                f"Transition {from_state} → {to_state} should be {expected}, got {result}"

