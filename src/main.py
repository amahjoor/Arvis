"""
Arvis Room Intelligence System - Main Entrypoint

This is the main orchestrator that initializes and runs all components.

Usage:
    python -m src.main [--mock-hardware] [--debug]
"""

import argparse
import asyncio
import signal
import sys
from typing import Optional

from loguru import logger

from src.config import DEBUG, MOCK_HARDWARE
from src.core import EventBus, StateManager, RoomState, IntentRouter, HandlerContext
from src.agents.wake_word import WakeWordDetector
from src.agents.voice_agent import VoiceAgent
from src.agents.presence_agent import PresenceAgent
from src.controllers.led_controller import LEDController
from src.controllers.smart_plug_controller import SmartPlugController
from src.sensors.pir_sensor import PIRSensor
from src.intents.lights import register_light_handlers
from src.intents.presence import register_presence_handlers
from src.intents.devices import register_device_handlers
from src.intents.chat import register_chat_handlers
from src.utils.logging import setup_logging


class Arvis:
    """
    Main Arvis application orchestrator.
    
    Initializes and manages all system components.
    """
    
    def __init__(self, mock_hardware: bool = True, debug: bool = False):
        """
        Initialize Arvis.
        
        Args:
            mock_hardware: If True, use mock implementations for hardware
            debug: If True, enable debug logging
        """
        self.mock_hardware = mock_hardware
        self.debug = debug
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None
        
        # Core components
        self.event_bus = EventBus()
        self.state_manager = StateManager(self.event_bus)
        
        # Controllers
        self.led_controller = LEDController(mock_mode=mock_hardware)
        self.smart_plug_controller = SmartPlugController(mock_mode=mock_hardware)
        
        # Sensors
        self.pir_sensor = PIRSensor(
            event_bus=self.event_bus,
            mock_mode=mock_hardware,
        )
        
        # Agents
        self.wake_word_detector = WakeWordDetector(
            event_bus=self.event_bus,
            mock_mode=mock_hardware,
        )
        self.voice_agent = VoiceAgent(
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            mock_mode=mock_hardware,
        )
        self.presence_agent = PresenceAgent(
            event_bus=self.event_bus,
            state_manager=self.state_manager,
        )
        
        # Intent routing
        self.handler_context = HandlerContext(
            led_controller=self.led_controller,
            audio_controller=self.voice_agent.audio_controller,
            state_manager=self.state_manager,
            event_bus=self.event_bus,
            smart_plug_controller=self.smart_plug_controller,
        )
        self.intent_router = IntentRouter(
            event_bus=self.event_bus,
            context=self.handler_context,
        )
        
        # Register intent handlers
        register_light_handlers(self.intent_router)
        register_presence_handlers(self.intent_router)
        register_device_handlers(self.intent_router)
        register_chat_handlers(self.intent_router)
        
        logger.info(f"Arvis initialized (mock_hardware={mock_hardware}, debug={debug})")
    
    async def start(self) -> None:
        """Start the Arvis system."""
        logger.info("Starting Arvis...")
        
        self._running = True
        self._shutdown_event = asyncio.Event()
        
        # Subscribe to events for logging
        self.event_bus.subscribe("room.state_changed", self._on_state_changed)
        self.event_bus.subscribe("wake_word.detected", self._on_wake_word)
        self.event_bus.subscribe("voice.recording_complete", self._on_recording_complete)
        self.event_bus.subscribe("voice.command", self._on_voice_command)
        self.event_bus.subscribe("presence.motion_detected", self._on_motion_detected)
        self.event_bus.subscribe("presence.entry_detected", self._on_entry_detected)
        self.event_bus.subscribe("presence.exit_detected", self._on_exit_detected)
        
        # Start components
        await self.pir_sensor.start()
        await self.presence_agent.start()
        await self.wake_word_detector.start()
        await self.voice_agent.start()
        await self.intent_router.start()
        
        logger.info("=" * 50)
        logger.info("  Arvis Room Intelligence System")
        logger.info("=" * 50)
        logger.info(f"  Mode: {'Mock' if self.mock_hardware else 'Hardware'}")
        logger.info(f"  Debug: {self.debug}")
        logger.info(f"  State: {self.state_manager.state.value}")
        logger.info(f"  Wake Word: Listening for 'Arvis'")
        logger.info(f"  Intents: {self.intent_router.registered_actions}")
        logger.info("=" * 50)
        logger.info("Arvis is ready. Press Ctrl+C to stop.")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
    
    async def stop(self) -> None:
        """Stop the Arvis system gracefully."""
        logger.info("Stopping Arvis...")
        
        self._running = False
        
        # Stop components
        await self.intent_router.stop()
        await self.wake_word_detector.stop()
        await self.voice_agent.stop()
        await self.presence_agent.stop()
        await self.pir_sensor.stop()
        
        # Clean up core components
        self.event_bus.clear()
        self.state_manager.reset()
        
        if self._shutdown_event:
            self._shutdown_event.set()
        
        logger.info("Arvis stopped.")
    
    async def _on_state_changed(self, event) -> None:
        """Handle room state changes."""
        old_state = event.payload.get("old_state")
        new_state = event.payload.get("new_state")
        logger.info(f"Room state: {old_state} → {new_state}")
    
    async def _on_wake_word(self, event) -> None:
        """Handle wake word detection."""
        logger.info("🎤 Wake word detected! Listening for command...")
        
        # Trigger listening animation
        self.led_controller.animate_listening()
    
    async def _on_recording_complete(self, event) -> None:
        """Handle completed voice recording."""
        duration = event.payload.get("duration", 0)
        size = len(event.payload.get("audio_bytes", b""))
        logger.info(f"📝 Recording complete: {duration:.2f}s, {size} bytes")
    
    async def _on_voice_command(self, event) -> None:
        """Handle processed voice command (after STT/LLM)."""
        text = event.payload.get("text", "")
        intent = event.payload.get("intent", {})
        latency = event.payload.get("latency", {})
        
        action = intent.get("action", "unknown")
        params = intent.get("params", {})
        total_time = latency.get("total", 0)
        
        logger.info(f"🎯 Voice command: '{text}' → {action} (params={params})")
        logger.info(f"⏱️  Latency: STT={latency.get('stt', 0):.2f}s, LLM={latency.get('llm', 0):.2f}s, Total={total_time:.2f}s")
        # IntentRouter handles routing to handlers
    
    async def _on_motion_detected(self, event) -> None:
        """Handle PIR motion detection."""
        timestamp = event.payload.get("timestamp", "")
        logger.info(f"📡 Motion detected at {timestamp}")
        # PresenceAgent handles state transitions
    
    async def _on_entry_detected(self, event) -> None:
        """Handle room entry (EMPTY → OCCUPIED)."""
        logger.info("🚪 Entry detected! Triggering welcome scene...")
        
        # Create and publish a voice.command event to trigger the handler
        from src.core.models import Event, Intent
        
        intent = Intent(
            action="presence.entry",
            params={},
            source="presence_agent",
            raw_text="[auto] entry detected",
        )
        
        await self.event_bus.publish(Event(
            type="voice.command",
            payload={
                "text": "[entry detected]",
                "intent": intent.__dict__,
                "latency": {"total": 0},
            },
            source="presence_agent",
        ))
    
    async def _on_exit_detected(self, event) -> None:
        """Handle room exit (OCCUPIED → EMPTY after timeout)."""
        timeout = event.payload.get("timeout_minutes", 0)
        logger.info(f"🚪 Exit detected! (no motion for {timeout:.0f}min) Triggering goodbye scene...")
        
        from src.core.models import Event, Intent
        
        intent = Intent(
            action="presence.exit",
            params={"timeout_minutes": timeout},
            source="presence_agent",
            raw_text="[auto] exit detected",
        )
        
        await self.event_bus.publish(Event(
            type="voice.command",
            payload={
                "text": "[exit detected]",
                "intent": intent.__dict__,
                "latency": {"total": 0},
            },
            source="presence_agent",
        ))
    
    async def trigger_wake_word(self) -> None:
        """
        Manually trigger wake word detection.
        Useful for testing in mock mode.
        """
        if self.mock_hardware:
            await self.wake_word_detector.trigger_mock_detection()
        else:
            logger.warning("Manual trigger only works in mock mode")
    
    async def trigger_motion(self) -> None:
        """
        Manually trigger PIR motion detection.
        Useful for testing without hardware.
        """
        await self.pir_sensor.trigger_mock_motion()
    
    async def trigger_exit(self) -> None:
        """
        Manually trigger room exit (for testing).
        Bypasses the timeout wait.
        """
        await self.presence_agent.trigger_mock_exit()


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Arvis Room Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src.main                    # Run with defaults (from .env)
    python -m src.main --no-mock-hardware # Use real hardware (disable mock mode)
    python -m src.main --mock-hardware    # Force mock mode
    python -m src.main --debug            # Run with debug logging
        """
    )
    
    parser.add_argument(
        "--mock-hardware",
        action="store_true",
        default=None,
        help="Use mock implementations for hardware (overrides env)"
    )
    
    parser.add_argument(
        "--no-mock-hardware",
        action="store_true",
        help="Disable mock mode, use real hardware (overrides env)"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        default=DEBUG,
        help="Enable debug logging (default: from env)"
    )
    
    return parser.parse_args()


async def main() -> None:
    """Main entry point."""
    args = parse_args()
    
    # Setup logging first
    setup_logging()
    
    # Determine mock mode: CLI flags override env/config
    if args.no_mock_hardware:
        mock_hardware = False
    elif args.mock_hardware:
        mock_hardware = True
    else:
        mock_hardware = MOCK_HARDWARE  # Use env/config default
    
    # Create Arvis instance
    arvis = Arvis(mock_hardware=mock_hardware, debug=args.debug)
    
    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(arvis.stop())
    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await arvis.start()
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        await arvis.stop()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
