"""
PIR Sensor for motion detection.

Reads GPIO input from HC-SR501 PIR sensor on Raspberry Pi.
Mock mode available for development on macOS.
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

from loguru import logger

from src.config import PIR_GPIO_PIN, PIR_DEBOUNCE_SECONDS, MOCK_HARDWARE
from src.core.event_bus import EventBus
from src.core.models import Event


class PIRSensor:
    """
    PIR motion sensor interface.
    
    In mock mode, provides trigger_mock_motion() for testing.
    In real mode, reads GPIO pin state via interrupt or polling.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        gpio_pin: int = PIR_GPIO_PIN,
        mock_mode: bool = MOCK_HARDWARE,
        debounce_seconds: float = PIR_DEBOUNCE_SECONDS,
    ):
        """
        Initialize PIR sensor.
        
        Args:
            event_bus: EventBus for publishing motion events
            gpio_pin: GPIO pin number (BCM numbering)
            mock_mode: If True, skip GPIO and allow manual triggers
            debounce_seconds: Minimum time between motion events
        """
        self.event_bus = event_bus
        self._gpio_pin = gpio_pin
        self._mock_mode = mock_mode
        self._debounce_seconds = debounce_seconds
        
        self._running = False
        self._last_motion_time: float = 0
        self._gpio_setup = False
        self._detection_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"PIRSensor initialized (mock_mode={mock_mode}, "
            f"pin={gpio_pin}, debounce={debounce_seconds}s)"
        )
    
    async def start(self) -> None:
        """Start the PIR sensor."""
        if self._running:
            logger.warning("PIRSensor already running")
            return
        
        self._running = True
        
        if not self._mock_mode:
            self._setup_gpio()
        
        # Start detection loop
        self._detection_task = asyncio.create_task(self._detection_loop())
        
        mode = "mock" if self._mock_mode else f"GPIO {self._gpio_pin}"
        logger.info(f"PIRSensor started ({mode})")
    
    async def stop(self) -> None:
        """Stop the PIR sensor and cleanup."""
        logger.info("Stopping PIRSensor...")
        
        self._running = False
        
        if self._detection_task:
            self._detection_task.cancel()
            try:
                await self._detection_task
            except asyncio.CancelledError:
                pass
        
        if self._gpio_setup and not self._mock_mode:
            self._cleanup_gpio()
        
        logger.info("PIRSensor stopped")
    
    def _setup_gpio(self) -> None:
        """Setup GPIO pin for reading PIR sensor."""
        try:
            import RPi.GPIO as GPIO
            
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self._gpio_pin, GPIO.IN)
            
            # Add interrupt callback for rising edge (motion detected)
            GPIO.add_event_detect(
                self._gpio_pin,
                GPIO.RISING,
                callback=self._gpio_callback,
                bouncetime=int(self._debounce_seconds * 1000)
            )
            
            self._gpio_setup = True
            logger.info(f"GPIO {self._gpio_pin} configured for PIR input")
            
        except ImportError:
            logger.warning("RPi.GPIO not available, falling back to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to setup GPIO: {e}")
            self._mock_mode = True
    
    def _cleanup_gpio(self) -> None:
        """Cleanup GPIO resources."""
        try:
            import RPi.GPIO as GPIO
            GPIO.cleanup(self._gpio_pin)
            logger.debug(f"GPIO {self._gpio_pin} cleaned up")
        except Exception as e:
            logger.error(f"Failed to cleanup GPIO: {e}")
    
    def _gpio_callback(self, channel: int) -> None:
        """
        Callback when GPIO detects rising edge (motion).
        
        Note: This runs in a separate thread from RPi.GPIO.
        """
        # Schedule the async handler on the event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._handle_motion_detected(),
                    loop
                )
        except Exception as e:
            logger.error(f"Error in GPIO callback: {e}")
    
    async def _detection_loop(self) -> None:
        """
        Background task for mock mode polling.
        
        In real mode, GPIO interrupts handle detection.
        This loop just keeps the task alive and handles mock triggers.
        """
        logger.debug("PIR detection loop started")
        
        while self._running:
            await asyncio.sleep(0.1)  # Small sleep to prevent busy loop
        
        logger.debug("PIR detection loop stopped")
    
    async def _handle_motion_detected(self) -> None:
        """Handle a motion detection event with debounce."""
        current_time = time.time()
        
        # Check debounce
        if current_time - self._last_motion_time < self._debounce_seconds:
            logger.debug("Motion detected but debounced")
            return
        
        self._last_motion_time = current_time
        
        logger.info("📡 Motion detected!")
        
        # Publish event
        await self.event_bus.publish(Event(
            type="presence.motion_detected",
            payload={
                "timestamp": datetime.now().isoformat(),
                "gpio_pin": self._gpio_pin,
            },
            source="pir_sensor",
        ))
    
    async def trigger_mock_motion(self) -> None:
        """
        Manually trigger a motion event (for testing).
        
        Works in both mock and real mode.
        """
        if not self._running:
            logger.warning("Cannot trigger motion - sensor not running")
            return
        
        logger.info("📡 [MOCK] Triggering motion event")
        await self._handle_motion_detected()
    
    @property
    def is_running(self) -> bool:
        """Check if sensor is running."""
        return self._running
    
    @property
    def last_motion_time(self) -> Optional[datetime]:
        """Get timestamp of last motion detection."""
        if self._last_motion_time == 0:
            return None
        return datetime.fromtimestamp(self._last_motion_time)
    
    @property
    def seconds_since_motion(self) -> Optional[float]:
        """Get seconds since last motion, or None if no motion yet."""
        if self._last_motion_time == 0:
            return None
        return time.time() - self._last_motion_time

