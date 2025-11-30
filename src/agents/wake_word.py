"""
Arvis Wake Word Detector

Always-listening wake word detection using Porcupine.
Detects "Arvis" (using "Jarvis" keyword) and publishes events to EventBus.

Usage:
    detector = WakeWordDetector(event_bus)
    await detector.start()  # Runs until stopped
    await detector.stop()
"""

import asyncio
from typing import Optional, Callable, Awaitable
from loguru import logger

from src.config import (
    PORCUPINE_ACCESS_KEY,
    WAKE_WORD_SENSITIVITY,
    WAKE_WORD_MODEL_PATH,
    SAMPLE_RATE,
    MOCK_HARDWARE,
)
from src.core.event_bus import EventBus
from src.core.models import Event


class WakeWordDetector:
    """
    Wake word detector using Picovoice Porcupine.
    
    Listens continuously for the wake word "Arvis" (using "Jarvis" keyword)
    and publishes `wake_word.detected` events when triggered.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        sensitivity: float = WAKE_WORD_SENSITIVITY,
        mock_mode: bool = MOCK_HARDWARE,
    ):
        """
        Initialize the wake word detector.
        
        Args:
            event_bus: EventBus for publishing detection events
            sensitivity: Detection sensitivity (0.0 to 1.0)
            mock_mode: If True, use mock detection instead of real Porcupine
        """
        self.event_bus = event_bus
        self.sensitivity = sensitivity
        self.mock_mode = mock_mode
        self._running = False
        self._porcupine = None
        self._audio_stream = None
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks for wake word detection
        self._on_wake_callbacks: list[Callable[[], Awaitable[None]]] = []
        
        logger.info(f"WakeWordDetector initialized (mock_mode={mock_mode})")
    
    def on_wake_word(self, callback: Callable[[], Awaitable[None]]) -> None:
        """
        Register a callback to be called when wake word is detected.
        
        Args:
            callback: Async function to call on detection
        """
        self._on_wake_callbacks.append(callback)
    
    async def start(self) -> None:
        """Start the wake word detection loop."""
        if self._running:
            logger.warning("WakeWordDetector already running")
            return
        
        self._running = True
        
        if self.mock_mode:
            logger.info("Starting wake word detector in MOCK mode")
            self._task = asyncio.create_task(self._mock_detection_loop())
        else:
            logger.info("Starting wake word detector with Porcupine")
            await self._init_porcupine()
            self._task = asyncio.create_task(self._detection_loop())
    
    async def stop(self) -> None:
        """Stop the wake word detection loop."""
        logger.info("Stopping wake word detector...")
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        await self._cleanup()
        logger.info("Wake word detector stopped")
    
    async def _init_porcupine(self) -> None:
        """Initialize Porcupine engine."""
        try:
            import pvporcupine
            
            if not PORCUPINE_ACCESS_KEY:
                raise ValueError(
                    "PORCUPINE_ACCESS_KEY not set. "
                    "Get a free key from https://picovoice.ai/"
                )
            
            # Check for custom wake word model
            if WAKE_WORD_MODEL_PATH and WAKE_WORD_MODEL_PATH.exists():
                # Use custom "Arvis" model
                logger.info(f"Using custom wake word model: {WAKE_WORD_MODEL_PATH}")
                self._porcupine = pvporcupine.create(
                    access_key=PORCUPINE_ACCESS_KEY,
                    keyword_paths=[str(WAKE_WORD_MODEL_PATH)],
                    sensitivities=[self.sensitivity],
                )
            else:
                # Fall back to built-in "Jarvis" keyword
                logger.info("Using built-in 'Jarvis' keyword (custom model not found)")
                self._porcupine = pvporcupine.create(
                    access_key=PORCUPINE_ACCESS_KEY,
                    keywords=["jarvis"],
                    sensitivities=[self.sensitivity],
                )
            
            logger.info(
                f"Porcupine initialized: "
                f"sample_rate={self._porcupine.sample_rate}, "
                f"frame_length={self._porcupine.frame_length}"
            )
            
        except ImportError:
            logger.error("pvporcupine not installed. Run: pip install pvporcupine")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}")
            raise
    
    async def _detection_loop(self) -> None:
        """Main detection loop using Porcupine."""
        import sounddevice as sd
        import numpy as np
        
        try:
            # Open audio stream
            self._audio_stream = sd.InputStream(
                samplerate=self._porcupine.sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=self._porcupine.frame_length,
            )
            self._audio_stream.start()
            
            logger.info("Listening for wake word 'Arvis'...")
            
            while self._running:
                # Read audio frame
                audio_frame, overflowed = self._audio_stream.read(
                    self._porcupine.frame_length
                )
                
                if overflowed:
                    logger.warning("Audio buffer overflow")
                
                # Process through Porcupine
                audio_frame = audio_frame.flatten()
                keyword_index = self._porcupine.process(audio_frame)
                
                if keyword_index >= 0:
                    logger.info("🎤 Wake word detected!")
                    await self._on_detection()
                
                # Small yield to prevent blocking
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            raise
    
    async def _mock_detection_loop(self) -> None:
        """Mock detection loop for testing without hardware."""
        logger.info("Mock wake word detector running (type 'wake' in console to simulate)")
        
        while self._running:
            # In mock mode, we just wait
            # Detection can be triggered via trigger_mock_detection()
            await asyncio.sleep(0.1)
    
    async def trigger_mock_detection(self) -> None:
        """
        Manually trigger a mock wake word detection.
        Useful for testing without a real microphone.
        """
        if not self.mock_mode:
            logger.warning("trigger_mock_detection called but not in mock mode")
            return
        
        if not self._running:
            logger.warning("WakeWordDetector not running, ignoring trigger")
            return
        
        logger.info("🎤 Mock wake word triggered!")
        await self._on_detection()
    
    async def _on_detection(self) -> None:
        """Handle wake word detection."""
        # Publish event
        event = Event(
            type="wake_word.detected",
            payload={},
            source="wake_word_detector",
        )
        await self.event_bus.publish(event)
        
        # Call registered callbacks
        for callback in self._on_wake_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")
    
    async def _cleanup(self) -> None:
        """Clean up resources."""
        if self._audio_stream:
            self._audio_stream.stop()
            self._audio_stream.close()
            self._audio_stream = None
        
        if self._porcupine:
            self._porcupine.delete()
            self._porcupine = None
    
    @property
    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running

