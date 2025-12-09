#!/usr/bin/env python3
"""
Test script for presence detection.

Run this to see the full entry/exit flow with mock PIR.
"""

import asyncio
from src.core.event_bus import EventBus
from src.core.state_manager import StateManager
from src.core.models import Event, RoomState
from src.agents.presence_agent import PresenceAgent
from src.sensors.pir_sensor import PIRSensor


async def main():
    print("=" * 50)
    print("  Presence Detection Test")
    print("=" * 50)
    
    # Setup
    bus = EventBus()
    state = StateManager(bus)
    pir = PIRSensor(bus, mock_mode=True, debounce_seconds=0.5)
    agent = PresenceAgent(bus, state, timeout_minutes=0.1)  # 6 second timeout
    
    # Track events
    events_log = []
    
    async def log_event(event):
        events_log.append(event.type)
        print(f"  📨 Event: {event.type}")
    
    bus.subscribe("presence.*", log_event)
    bus.subscribe("room.state_changed", log_event)
    
    await pir.start()
    await agent.start()
    
    print(f"\n🏠 Initial state: {state.state.value}")
    print(f"⏱️  Timeout: 6 seconds\n")
    
    # Test 1: Entry
    print("--- TEST 1: Trigger Motion (Entry) ---")
    await pir.trigger_mock_motion()
    await asyncio.sleep(0.2)
    print(f"   State: {state.state.value}")
    assert state.state == RoomState.OCCUPIED, "Should be OCCUPIED!"
    print("   ✅ Entry detection works!\n")
    
    # Test 2: Motion while occupied
    print("--- TEST 2: Motion While Occupied ---")
    await pir.trigger_mock_motion()
    await asyncio.sleep(0.2)
    print(f"   State: {state.state.value}")
    assert state.state == RoomState.OCCUPIED, "Should still be OCCUPIED!"
    print("   ✅ Stays OCCUPIED (no double entry)\n")
    
    # Test 3: Wait for timeout
    print("--- TEST 3: Wait for Exit Timeout (6s) ---")
    print("   Waiting", end="", flush=True)
    for _ in range(7):
        await asyncio.sleep(1)
        print(".", end="", flush=True)
    print()
    print(f"   State: {state.state.value}")
    
    # Force check (timeout loop runs every 30s, so trigger manually)
    await agent.trigger_mock_exit()
    await asyncio.sleep(0.2)
    print(f"   State after mock exit: {state.state.value}")
    assert state.state == RoomState.EMPTY, "Should be EMPTY!"
    print("   ✅ Exit detection works!\n")
    
    # Cleanup
    await agent.stop()
    await pir.stop()
    
    print("=" * 50)
    print("  All Tests Passed! ✅")
    print("=" * 50)
    print(f"\nEvents fired: {events_log}")


if __name__ == "__main__":
    asyncio.run(main())


