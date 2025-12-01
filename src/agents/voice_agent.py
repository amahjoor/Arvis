"""
Arvis Voice Agent

Handles the complete voice interaction pipeline:
1. Listens for wake word detection events
2. Records user speech until silence
3. Transcribes audio via STT (Whisper)
4. Extracts intent via LLM (GPT-4o-mini)
5. Publishes voice.command event for action execution

Usage:
    agent = VoiceAgent(event_bus, state_manager)
    await agent.start()
"""

import asyncio
import time
from typing import Optional

from loguru import logger

from src.config import MOCK_HARDWARE, ERROR_MESSAGES
from src.core.event_bus import EventBus
from src.core.models import Event, Intent, RoomState
from src.core.state_manager import StateManager
from src.utils.audio_utils import record_until_silence
from src.backends.stt_backend import STTBackend
from src.backends.llm_backend import LLMBackend
from src.backends.tts_backend import TTSBackend
from src.controllers.audio_controller import AudioController


class VoiceAgent:
    """
    Voice interaction agent.
    
    Orchestrates the full voice pipeline:
    Wake word → Record → STT → LLM → Publish intent
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: Optional[StateManager] = None,
        mock_mode: bool = MOCK_HARDWARE,
    ):
        """
        Initialize the voice agent.
        
        Args:
            event_bus: EventBus for events
            state_manager: StateManager for room state context
            mock_mode: If True, use mock backends
        """
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.mock_mode = mock_mode
        self._running = False
        self._is_recording = False
        self._is_processing = False
        self._last_audio: Optional[bytes] = None
        self._last_duration: float = 0.0
        
        # Initialize backends
        self._stt = STTBackend(mock_mode=mock_mode)
        self._llm = LLMBackend(mock_mode=mock_mode)
        self._tts = TTSBackend(mock_mode=mock_mode)
        self._audio = AudioController(self._tts, mock_mode=mock_mode)
        
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
        self._audio.stop()
        
        logger.info("VoiceAgent stopped")
    
    async def _on_wake_word(self, event: Event) -> None:
        """
        Handle wake word detection.
        
        Starts the full voice processing pipeline.
        """
        if self._is_recording or self._is_processing:
            logger.warning("Already recording/processing, ignoring wake word")
            return
        
        logger.info("Wake word received, starting voice capture...")
        pipeline_start = time.time()
        
        self._is_recording = True
        
        try:
            # ============================================
            # Step 1: Record audio until silence
            # ============================================
            record_start = time.time()
            audio_bytes, duration = await record_until_silence(
                mock_mode=self.mock_mode
            )
            record_time = time.time() - record_start
            
            self._last_audio = audio_bytes
            self._last_duration = duration
            
            if not audio_bytes or len(audio_bytes) < 1000:
                logger.warning("No significant audio captured")
                return
            
            logger.info(f"Recording complete: {duration:.2f}s ({record_time:.2f}s)")
            
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
            
            self._is_recording = False
            self._is_processing = True
            
            # ============================================
            # Step 2: Transcribe via STT
            # ============================================
            stt_start = time.time()
            try:
                text = self._stt.transcribe(audio_bytes)
                stt_time = time.time() - stt_start
                logger.info(f"STT result: '{text}' ({stt_time:.2f}s)")
            except RuntimeError as e:
                logger.error(f"STT failed: {e}")
                await self._say_error("offline")
                return
            
            if not text or text.strip() == "":
                logger.warning("STT returned empty text")
                await self._say_error("not_understood")
                return
            
            # ============================================
            # Step 3: Extract intent via LLM
            # ============================================
            llm_start = time.time()
            room_state = self.state_manager.get_state() if self.state_manager else RoomState.OCCUPIED
            
            try:
                intent = self._llm.extract_intent(text, room_state)
                llm_time = time.time() - llm_start
                logger.info(f"Intent: {intent.action} ({llm_time:.2f}s)")
            except RuntimeError as e:
                logger.error(f"LLM failed: {e}")
                await self._say_error("offline")
                return
            
            # ============================================
            # Step 4: Publish voice.command event
            # ============================================
            pipeline_time = time.time() - pipeline_start
            
            await self.event_bus.publish(Event(
                type="voice.command",
                payload={
                    "text": text,
                    "intent": {
                        "action": intent.action,
                        "params": intent.params,
                    },
                    "latency": {
                        "record": record_time,
                        "stt": stt_time,
                        "llm": llm_time,
                        "total": pipeline_time,
                    }
                },
                source="voice_agent",
            ))
            
            logger.info(
                f"✅ Voice pipeline complete: '{text}' → {intent.action} "
                f"({pipeline_time:.2f}s total)"
            )
            
            # ============================================
            # Step 5: Handle clarify intent directly
            # ============================================
            if intent.action == "clarify":
                message = intent.params.get("message", ERROR_MESSAGES["not_understood"])
                await self._say(message)
                
        except Exception as e:
            import traceback
            logger.error(f"Error in voice pipeline: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await self._say_error("error")
            
        finally:
            self._is_recording = False
            self._is_processing = False
    
    async def _say(self, text: str) -> bool:
        """Speak text via TTS."""
        if not text:
            return True
        
        # Run TTS in thread pool to not block event loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._audio.say, text)
    
    async def _say_error(self, error_key: str) -> None:
        """Speak an error message."""
        message = ERROR_MESSAGES.get(error_key, ERROR_MESSAGES["error"])
        await self._say(message)
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    @property
    def is_processing(self) -> bool:
        """Check if currently processing (STT/LLM)."""
        return self._is_processing
    
    @property
    def last_audio(self) -> Optional[bytes]:
        """Get the last recorded audio bytes."""
        return self._last_audio
    
    @property
    def last_duration(self) -> float:
        """Get the duration of the last recording."""
        return self._last_duration
    
    @property
    def audio_controller(self) -> AudioController:
        """Get the audio controller for direct TTS access."""
        return self._audio
    
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
