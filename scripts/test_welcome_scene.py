#!/usr/bin/env python3
"""
Test the welcome scene (entry detection → voice + LED animation).

This starts a minimal Arvis instance to test the full flow.
"""

import asyncio
from src.core.event_bus import EventBus
from src.core.state_manager import StateManager
from src.core.intent_router import IntentRouter, HandlerContext
from src.core.models import Event, RoomState
from src.agents.presence_agent import PresenceAgent
from src.sensors.pir_sensor import PIRSensor
from src.controllers.led_controller import LEDController
from src.controllers.audio_controller import AudioController
from src.backends.tts_backend import TTSBackend
from src.intents.presence import register_presence_handlers


async def main():
    print("=" * 50)
    print("  Welcome Scene Test")
    print("=" * 50)
    
    # Setup components
    bus = EventBus()
    state = StateManager(bus)
    led = LEDController(mock_mode=True)
    tts = TTSBackend(mock_mode=False)  # Real TTS!
    audio = AudioController(tts_backend=tts, mock_mode=False)  # Real audio!
    
    # Setup intent router
    ctx = HandlerContext(
        led_controller=led,
        audio_controller=audio,
        state_manager=state,
        event_bus=bus,
    )
    router = IntentRouter(bus, ctx)
    register_presence_handlers(router)
    
    # Setup presence detection
    pir = PIRSensor(bus, mock_mode=True, debounce_seconds=1.0)
    agent = PresenceAgent(bus, state, timeout_minutes=0.1)
    
    # Wire entry event to trigger welcome intent
    async def on_entry(event):
        from src.core.models import Intent
        print("\n🚪 Entry detected! Triggering welcome scene...")
        
        intent = Intent(
            action="presence.entry",
            params={},
            source="presence_agent",
            raw_text="[auto] entry detected",
        )
        
        await bus.publish(Event(
            type="voice.command",
            payload={
                "text": "[entry detected]",
                "intent": intent.__dict__,
                "latency": {"total": 0},
            },
            source="presence_agent",
        ))
    
    bus.subscribe("presence.entry_detected", on_entry)
    
    # Start everything
    await pir.start()
    await agent.start()
    await router.start()
    
    print(f"\n🏠 Initial state: {state.state.value}")
    print("🎬 Triggering motion in 2 seconds...\n")
    
    await asyncio.sleep(2)
    
    # Trigger motion!
    print("📡 [PIR] Motion detected!")
    await pir.trigger_mock_motion()
    
    # Wait for welcome scene to play
    print("⏳ Waiting for welcome scene...\n")
    await asyncio.sleep(5)
    
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

