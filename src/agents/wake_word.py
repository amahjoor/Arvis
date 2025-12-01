"""
Arvis Wake Word Detector

Always-listening wake word detection using OpenWakeWord.
Detects custom wake words and publishes events to EventBus.

Usage:
    detector = WakeWordDetector(event_bus)
    await detector.start()  # Runs until stopped
    await detector.stop()
"""

import asyncio
from typing import Optional, Callable, Awaitable
from pathlib import Path
import numpy as np
from loguru import logger

from src.config import (
    WAKE_WORD_SENSITIVITY,
    WAKE_WORD_MODEL_PATH,
    SAMPLE_RATE,
    MOCK_HARDWARE,
)
from src.core.event_bus import EventBus
from src.core.models import Event


class WakeWordDetector:
    """
    Wake word detector using OpenWakeWord.
    
    Listens continuously for the wake word "Arvis"
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
            sensitivity: Detection sensitivity/threshold (0.0 to 1.0)
            mock_mode: If True, use mock detection instead of real OpenWakeWord
        """
        self.event_bus = event_bus
        self.sensitivity = sensitivity
        self.mock_mode = mock_mode
        self._running = False
        self._oww_model = None
        self._audio_stream = None
        self._task: Optional[asyncio.Task] = None
        
        # Callbacks for wake word detection
        self._on_wake_callbacks: list[Callable[[], Awaitable[None]]] = []
        
        logger.info(f"WakeWordDetector initialized (mock_mode={mock_mode}, engine=OpenWakeWord)")
    
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
            logger.info("Starting wake word detector with OpenWakeWord")
            await self._init_openwakeword()
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
    
    async def _init_openwakeword(self) -> None:
        """Initialize OpenWakeWord engine."""
        try:
            import openwakeword
            from openwakeword.model import Model
            
            # Check for custom model or use default
            if WAKE_WORD_MODEL_PATH and Path(WAKE_WORD_MODEL_PATH).exists():
                logger.info(f"Loading custom wake word model: {WAKE_WORD_MODEL_PATH}")
                self._oww_model = Model(
                    wakeword_models=[str(WAKE_WORD_MODEL_PATH)],
                    inference_framework="onnx"
                )
            else:
                # Use pre-trained model - "hey_jarvis" is closest to "Arvis"
                logger.info("Loading pre-trained 'hey_jarvis' model (say 'Hey Jarvis')")
                
                # Download pre-trained models on first run
                openwakeword.utils.download_models()
                
                self._oww_model = Model(
                    wakeword_models=["hey_jarvis_v0.1"],
                    inference_framework="onnx"
                )
            
            logger.info("OpenWakeWord initialized successfully")
            
        except ImportError:
            logger.error("openwakeword not installed. Run: pip install openwakeword")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize OpenWakeWord: {e}")
            raise
    
    async def _detection_loop(self) -> None:
        """Main detection loop using OpenWakeWord."""
        import sounddevice as sd
        
        try:
            # OpenWakeWord expects 16kHz mono audio in chunks of 1280 samples
            chunk_size = 1280
            
            # Open audio stream
            self._audio_stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype=np.int16,
                blocksize=chunk_size,
            )
            self._audio_stream.start()
            
            logger.info("🎤 Listening for wake word...")
            
            while self._running:
                # Read audio frame
                audio_frame, overflowed = self._audio_stream.read(chunk_size)
                
                if overflowed:
                    logger.warning("Audio buffer overflow")
                
                # Convert to format expected by OpenWakeWord
                audio_frame = audio_frame.flatten().astype(np.int16)
                
                # Process through OpenWakeWord
                predictions = self._oww_model.predict(audio_frame)
                
                # Check each wake word model for detection
                for model_name, score in predictions.items():
                    if score > self.sensitivity:
                        logger.info(f"🎤 Wake word detected! (model={model_name}, score={score:.3f})")
                        await self._on_detection()
                        
                        # Reset the model to avoid repeated triggers
                        self._oww_model.reset()
                        break
                
                # Small yield to prevent blocking
                await asyncio.sleep(0.01)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            raise
    
    async def _mock_detection_loop(self) -> None:
        """Mock detection loop for testing without hardware."""
        logger.info("Mock wake word detector running")
        
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
        
        self._oww_model = None
    
    @property
    def is_running(self) -> bool:
        """Check if detector is running."""
        return self._running
