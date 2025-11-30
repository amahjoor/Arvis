"""
Mock Audio Components

Mock implementations of audio components for testing without real hardware.
"""

import asyncio
import numpy as np
from typing import Optional, Callable, Awaitable
from loguru import logger

from src.core.event_bus import EventBus
from src.core.models import Event
from src.utils.audio_utils import audio_to_wav
from src.config import SAMPLE_RATE


class MockWakeWordDetector:
    """
    Mock wake word detector for testing.
    
    Allows manual triggering of wake word detection.
    """
    
    def __init__(self, event_bus: EventBus):
        """
        Initialize mock detector.
        
        Args:
            event_bus: EventBus for publishing events
        """
        self.event_bus = event_bus
        self._running = False
        self._detection_count = 0
        self._callbacks: list[Callable[[], Awaitable[None]]] = []
        
        logger.info("MockWakeWordDetector initialized")
    
    def on_wake_word(self, callback: Callable[[], Awaitable[None]]) -> None:
        """Register wake word callback."""
        self._callbacks.append(callback)
    
    async def start(self) -> None:
        """Start the mock detector."""
        self._running = True
        logger.info("MockWakeWordDetector started")
    
    async def stop(self) -> None:
        """Stop the mock detector."""
        self._running = False
        logger.info("MockWakeWordDetector stopped")
    
    async def trigger_detection(self) -> None:
        """
        Manually trigger a wake word detection.
        
        Use this in tests to simulate wake word being spoken.
        """
        if not self._running:
            logger.warning("MockWakeWordDetector not running")
            return
        
        self._detection_count += 1
        logger.info(f"Mock wake word triggered (count: {self._detection_count})")
        
        # Publish event
        await self.event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="mock_wake_word_detector",
        ))
        
        # Call callbacks
        for callback in self._callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Callback error: {e}")
    
    @property
    def is_running(self) -> bool:
        """Check if running."""
        return self._running
    
    @property
    def detection_count(self) -> int:
        """Get total detection count."""
        return self._detection_count


class MockMicrophone:
    """
    Mock microphone for testing audio capture.
    
    Returns pre-defined test audio instead of real recording.
    """
    
    def __init__(
        self,
        test_audio: Optional[np.ndarray] = None,
        duration: float = 1.0,
    ):
        """
        Initialize mock microphone.
        
        Args:
            test_audio: Pre-defined audio data (or generates silence)
            duration: Duration of generated audio if test_audio not provided
        """
        if test_audio is not None:
            self._audio = test_audio
        else:
            # Generate silent audio
            samples = int(SAMPLE_RATE * duration)
            self._audio = np.zeros(samples, dtype=np.int16)
        
        self._duration = len(self._audio) / SAMPLE_RATE
        self._is_recording = False
        
        logger.info(f"MockMicrophone initialized ({self._duration:.2f}s audio)")
    
    async def record(self) -> tuple[bytes, float]:
        """
        Record audio (returns mock data).
        
        Returns:
            Tuple of (wav_bytes, duration)
        """
        self._is_recording = True
        
        # Simulate brief recording time
        await asyncio.sleep(0.1)
        
        wav_bytes = audio_to_wav(self._audio, SAMPLE_RATE)
        
        self._is_recording = False
        
        return wav_bytes, self._duration
    
    def set_audio(self, audio: np.ndarray) -> None:
        """
        Set the audio to return from record().
        
        Args:
            audio: Audio data as numpy array
        """
        self._audio = audio
        self._duration = len(audio) / SAMPLE_RATE
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording


def generate_test_audio(
    duration: float = 1.0,
    frequency: float = 440.0,
    amplitude: float = 0.5,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """
    Generate test audio (sine wave).
    
    Args:
        duration: Duration in seconds
        frequency: Frequency in Hz (440 = A4)
        amplitude: Amplitude (0.0 to 1.0)
        sample_rate: Sample rate in Hz
        
    Returns:
        Audio data as int16 numpy array
    """
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = amplitude * np.sin(2 * np.pi * frequency * t)
    
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    
    return audio_int16


def generate_speech_like_audio(
    duration: float = 2.0,
    sample_rate: int = SAMPLE_RATE,
) -> np.ndarray:
    """
    Generate audio that simulates speech patterns.
    
    Creates audio with varying amplitude (simulating words/pauses).
    
    Args:
        duration: Duration in seconds
        sample_rate: Sample rate in Hz
        
    Returns:
        Audio data as int16 numpy array
    """
    samples = int(sample_rate * duration)
    audio = np.zeros(samples, dtype=np.float32)
    
    # Create "words" with gaps
    word_duration = int(0.3 * sample_rate)  # 300ms words
    gap_duration = int(0.1 * sample_rate)   # 100ms gaps
    
    pos = 0
    while pos < samples:
        # Add a "word" (noise burst)
        word_end = min(pos + word_duration, samples)
        audio[pos:word_end] = np.random.uniform(-0.3, 0.3, word_end - pos)
        pos = word_end
        
        # Add gap
        gap_end = min(pos + gap_duration, samples)
        audio[pos:gap_end] = np.random.uniform(-0.01, 0.01, gap_end - pos)
        pos = gap_end
    
    # Convert to int16
    audio_int16 = (audio * 32767).astype(np.int16)
    
    return audio_int16

