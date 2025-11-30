"""
Arvis Voice Agent

Handles the voice interaction pipeline:
1. Listens for wake word detection events
2. Records user speech until silence
3. (Future: sends to STT, gets intent from LLM, responds via TTS)

Usage:
    agent = VoiceAgent(event_bus)
    await agent.start()
"""

import asyncio
from typing import Optional
from loguru import logger

from src.config import MOCK_HARDWARE
from src.core.event_bus import EventBus
from src.core.models import Event
from src.utils.audio_utils import record_until_silence


class VoiceAgent:
    """
    Voice interaction agent.
    
    Subscribes to wake word events and handles the voice command flow:
    - Records speech after wake word
    - Publishes recording_complete events for downstream processing
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        mock_mode: bool = MOCK_HARDWARE,
    ):
        """
        Initialize the voice agent.
        
        Args:
            event_bus: EventBus for events
            mock_mode: If True, use mock audio recording
        """
        self.event_bus = event_bus
        self.mock_mode = mock_mode
        self._running = False
        self._is_recording = False
        self._last_audio: Optional[bytes] = None
        self._last_duration: float = 0.0
        
        logger.info(f"VoiceAgent initialized (mock_mode={mock_mode})")
    
    async def start(self) -> None:
        """Start the voice agent."""
        if self._running:
            logger.warning("VoiceAgent already running")
            return
        
        self._running = True
        
        # Subscribe to wake word events
        self.event_bus.subscribe("wake_word.detected", self._on_wake_word)
        
        logger.info("VoiceAgent started, listening for wake word events")
    
    async def stop(self) -> None:
        """Stop the voice agent."""
        logger.info("Stopping VoiceAgent...")
        
        self._running = False
        self.event_bus.unsubscribe("wake_word.detected", self._on_wake_word)
        
        logger.info("VoiceAgent stopped")
    
    async def _on_wake_word(self, event: Event) -> None:
        """
        Handle wake word detection.
        
        Starts recording user speech.
        """
        if self._is_recording:
            logger.warning("Already recording, ignoring wake word")
            return
        
        logger.info("Wake word received, starting voice capture...")
        
        self._is_recording = True
        
        try:
            # Record audio until silence
            audio_bytes, duration = await record_until_silence(
                mock_mode=self.mock_mode
            )
            
            self._last_audio = audio_bytes
            self._last_duration = duration
            
            if audio_bytes:
                # Publish recording complete event
                await self.event_bus.publish(Event(
                    type="voice.recording_complete",
                    payload={
                        "audio_bytes": audio_bytes,
                        "duration": duration,
                        "format": "wav",
                        "sample_rate": 16000,
                    },
                    source="voice_agent",
                ))
                
                logger.info(
                    f"Voice recording complete: {duration:.2f}s, "
                    f"{len(audio_bytes)} bytes"
                )
            else:
                logger.warning("No audio captured")
                
        except Exception as e:
            logger.error(f"Error during voice capture: {e}")
            
        finally:
            self._is_recording = False
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    @property
    def last_audio(self) -> Optional[bytes]:
        """Get the last recorded audio bytes."""
        return self._last_audio
    
    @property
    def last_duration(self) -> float:
        """Get the duration of the last recording."""
        return self._last_duration
    
    async def process_command_manual(self, audio_bytes: bytes) -> None:
        """
        Manually process audio bytes as a command.
        
        Useful for testing or when wake word is bypassed.
        
        Args:
            audio_bytes: WAV audio data
        """
        self._last_audio = audio_bytes
        
        await self.event_bus.publish(Event(
            type="voice.recording_complete",
            payload={
                "audio_bytes": audio_bytes,
                "duration": 0.0,  # Unknown
                "format": "wav",
                "sample_rate": 16000,
            },
            source="voice_agent",
        ))

