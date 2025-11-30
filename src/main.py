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
from src.core import EventBus, StateManager, RoomState
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
        
        logger.info(f"Arvis initialized (mock_hardware={mock_hardware}, debug={debug})")
    
    async def start(self) -> None:
        """Start the Arvis system."""
        logger.info("Starting Arvis...")
        
        self._running = True
        self._shutdown_event = asyncio.Event()
        
        # Subscribe to state changes for logging
        self.event_bus.subscribe("room.state_changed", self._on_state_changed)
        
        logger.info("=" * 50)
        logger.info("  Arvis Room Intelligence System")
        logger.info("=" * 50)
        logger.info(f"  Mode: {'Mock' if self.mock_hardware else 'Hardware'}")
        logger.info(f"  Debug: {self.debug}")
        logger.info(f"  State: {self.state_manager.state.value}")
        logger.info("=" * 50)
        logger.info("Arvis is ready. Press Ctrl+C to stop.")
        
        # Wait for shutdown signal
        await self._shutdown_event.wait()
    
    async def stop(self) -> None:
        """Stop the Arvis system gracefully."""
        logger.info("Stopping Arvis...")
        
        self._running = False
        
        # Clean up components
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


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Arvis Room Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m src.main                    # Run with defaults
    python -m src.main --mock-hardware    # Run with mocked hardware
    python -m src.main --debug            # Run with debug logging
        """
    )
    
    parser.add_argument(
        "--mock-hardware",
        action="store_true",
        default=MOCK_HARDWARE,
        help="Use mock implementations for hardware (default: from env)"
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
    
    # Create Arvis instance
    arvis = Arvis(mock_hardware=args.mock_hardware, debug=args.debug)
    
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

