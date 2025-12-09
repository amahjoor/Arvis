"""
Tests for Presence Agent.
"""

import asyncio
import pytest

from src.core.event_bus import EventBus
from src.core.state_manager import StateManager
from src.core.models import Event, RoomState
from src.agents.presence_agent import PresenceAgent


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def state_manager(event_bus):
    """Create StateManager."""
    return StateManager(event_bus)


@pytest.fixture
def presence_agent(event_bus, state_manager):
    """Create PresenceAgent with short timeout for testing."""
    return PresenceAgent(
        event_bus=event_bus,
        state_manager=state_manager,
        timeout_minutes=0.01,  # 0.6 seconds for fast testing
    )


@pytest.mark.asyncio
async def test_presence_agent_starts_and_stops(presence_agent):
    """Test agent lifecycle."""
    assert not presence_agent.is_running
    
    await presence_agent.start()
    assert presence_agent.is_running
    
    await presence_agent.stop()
    assert not presence_agent.is_running


@pytest.mark.asyncio
async def test_motion_triggers_entry(presence_agent, event_bus, state_manager):
    """Test that motion in EMPTY room triggers entry."""
    entry_events = []
    
    async def handler(event):
        entry_events.append(event)
    
    event_bus.subscribe("presence.entry_detected", handler)
    
    await presence_agent.start()
    
    # Verify initial state is EMPTY
    assert state_manager.state == RoomState.EMPTY
    
    # Simulate motion event
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={"timestamp": "2024-01-01T00:00:00"},
        source="test",
    ))
    
    await asyncio.sleep(0.05)
    
    # State should now be OCCUPIED
    assert state_manager.state == RoomState.OCCUPIED
    
    # Entry event should have fired
    assert len(entry_events) == 1
    assert entry_events[0].type == "presence.entry_detected"
    
    await presence_agent.stop()


@pytest.mark.asyncio
async def test_motion_while_occupied_no_entry_event(presence_agent, event_bus, state_manager):
    """Test that motion while OCCUPIED doesn't trigger entry again."""
    entry_events = []
    
    async def handler(event):
        entry_events.append(event)
    
    event_bus.subscribe("presence.entry_detected", handler)
    
    await presence_agent.start()
    
    # First motion - should trigger entry
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={},
        source="test",
    ))
    await asyncio.sleep(0.05)
    assert len(entry_events) == 1
    
    # Second motion - should NOT trigger entry
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={},
        source="test",
    ))
    await asyncio.sleep(0.05)
    assert len(entry_events) == 1  # Still 1
    
    await presence_agent.stop()


@pytest.mark.asyncio
async def test_mock_exit_triggers_correctly(presence_agent, event_bus, state_manager):
    """Test manual exit trigger."""
    exit_events = []
    
    async def handler(event):
        exit_events.append(event)
    
    event_bus.subscribe("presence.exit_detected", handler)
    
    await presence_agent.start()
    
    # First, enter the room
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={},
        source="test",
    ))
    await asyncio.sleep(0.05)
    assert state_manager.state == RoomState.OCCUPIED
    
    # Trigger mock exit
    await presence_agent.trigger_mock_exit()
    await asyncio.sleep(0.05)
    
    # State should be EMPTY
    assert state_manager.state == RoomState.EMPTY
    
    # Exit event should have fired
    assert len(exit_events) == 1
    assert exit_events[0].type == "presence.exit_detected"
    
    await presence_agent.stop()


@pytest.mark.asyncio
async def test_exit_only_fires_when_occupied(presence_agent, event_bus, state_manager):
    """Test that exit doesn't fire when already EMPTY."""
    exit_events = []
    
    async def handler(event):
        exit_events.append(event)
    
    event_bus.subscribe("presence.exit_detected", handler)
    
    await presence_agent.start()
    
    # Room is EMPTY, try to exit
    assert state_manager.state == RoomState.EMPTY
    await presence_agent.trigger_mock_exit()
    await asyncio.sleep(0.05)
    
    # No exit event should fire
    assert len(exit_events) == 0
    
    await presence_agent.stop()


@pytest.mark.asyncio
async def test_full_entry_exit_cycle(presence_agent, event_bus, state_manager):
    """Test complete entry → exit cycle."""
    entry_events = []
    exit_events = []
    
    async def entry_handler(event):
        entry_events.append(event)
    
    async def exit_handler(event):
        exit_events.append(event)
    
    event_bus.subscribe("presence.entry_detected", entry_handler)
    event_bus.subscribe("presence.exit_detected", exit_handler)
    
    await presence_agent.start()
    
    # Enter
    assert state_manager.state == RoomState.EMPTY
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={},
        source="test",
    ))
    await asyncio.sleep(0.05)
    assert state_manager.state == RoomState.OCCUPIED
    assert len(entry_events) == 1
    
    # Exit
    await presence_agent.trigger_mock_exit()
    await asyncio.sleep(0.05)
    assert state_manager.state == RoomState.EMPTY
    assert len(exit_events) == 1
    
    # Enter again
    await event_bus.publish(Event(
        type="presence.motion_detected",
        payload={},
        source="test",
    ))
    await asyncio.sleep(0.05)
    assert state_manager.state == RoomState.OCCUPIED
    assert len(entry_events) == 2  # Second entry
    
    await presence_agent.stop()


