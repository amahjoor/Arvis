#!/usr/bin/env python3
"""
Test the goodbye scene (exit detection → voice + LED fade out).

Simulates: Enter room → Wait → Exit (timeout) → Goodbye
"""

import asyncio
from src.core.event_bus import EventBus
from src.core.state_manager import StateManager
from src.core.intent_router import IntentRouter, HandlerContext
from src.core.models import Event, RoomState, Intent
from src.agents.presence_agent import PresenceAgent
from src.sensors.pir_sensor import PIRSensor
from src.controllers.led_controller import LEDController
from src.controllers.audio_controller import AudioController
from src.backends.tts_backend import TTSBackend
from src.intents.presence import register_presence_handlers


async def main():
    print("=" * 50)
    print("  Goodbye Scene Test")
    print("=" * 50)
    
    # Setup components
    bus = EventBus()
    state = StateManager(bus)
    led = LEDController(mock_mode=True)
    tts = TTSBackend(mock_mode=False)  # Real TTS!
    audio = AudioController(tts_backend=tts, mock_mode=False)
    
    # Setup intent router
    ctx = HandlerContext(
        led_controller=led,
        audio_controller=audio,
        state_manager=state,
        event_bus=bus,
    )
    router = IntentRouter(bus, ctx)
    register_presence_handlers(router)
    
    # Setup presence detection (short timeout for testing)
    pir = PIRSensor(bus, mock_mode=True, debounce_seconds=0.5)
    agent = PresenceAgent(bus, state, timeout_minutes=0.05)  # 3 second timeout
    
    # Wire exit event to trigger goodbye intent
    async def on_exit(event):
        print("\n🚪 Exit detected! Triggering goodbye scene...")
        
        intent = Intent(
            action="presence.exit",
            params={"timeout_minutes": 0.05},
            source="presence_agent",
            raw_text="[auto] exit detected",
        )
        
        await bus.publish(Event(
            type="voice.command",
            payload={
                "text": "[exit detected]",
                "intent": intent.__dict__,
                "latency": {"total": 0},
            },
            source="presence_agent",
        ))
    
    bus.subscribe("presence.exit_detected", on_exit)
    
    # Start everything
    await pir.start()
    await agent.start()
    await router.start()
    
    print(f"\n🏠 Initial state: {state.state.value}")
    
    # Step 1: Enter room
    print("\n📡 Step 1: Entering room...")
    await pir.trigger_mock_motion()
    await asyncio.sleep(0.5)
    print(f"   State: {state.state.value}")
    
    # Step 2: Wait for exit timeout
    print("\n⏳ Step 2: Waiting for exit timeout (3s)...")
    print("   ", end="", flush=True)
    for i in range(4):
        await asyncio.sleep(1)
        print(".", end="", flush=True)
    print()
    
    # Step 3: Trigger exit manually (since timeout loop runs every 30s)
    print("\n📡 Step 3: Triggering exit...")
    await agent.trigger_mock_exit()
    
    # Wait for goodbye scene
    await asyncio.sleep(3)
    
    print(f"\n🏠 Final state: {state.state.value}")
    
    # Cleanup
    await router.stop()
    await agent.stop()
    await pir.stop()
    
    print("\n" + "=" * 50)
    print("  Test Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())

