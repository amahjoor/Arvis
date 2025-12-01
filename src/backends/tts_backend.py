"""
Text-to-Speech Backend using OpenAI TTS API.

Synthesizes speech from text.
"""

import time
from typing import Optional

from loguru import logger
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError

from src.config import OPENAI_API_KEY, TTS_MODEL, TTS_VOICE


class TTSBackend:
    """Handles text-to-speech synthesis using OpenAI TTS."""
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize TTS backend.
        
        Args:
            mock_mode: If True, return mock audio
        """
        self._mock_mode = mock_mode
        self._client: Optional[OpenAI] = None
        
        if not mock_mode:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        
        logger.info(f"TTSBackend initialized (mock_mode={mock_mode}, voice={TTS_VOICE})")
    
    def synthesize(self, text: str) -> bytes:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to speak
            
        Returns:
            Audio bytes (MP3 format)
            
        Raises:
            RuntimeError: If synthesis fails
        """
        if self._mock_mode:
            return self._mock_synthesize(text)
        
        return self._real_synthesize(text)
    
    def _mock_synthesize(self, text: str) -> bytes:
        """Return mock audio for testing."""
        logger.debug(f"Mock synthesize: '{text}'")
        time.sleep(0.1)
        # Return minimal valid MP3 header (silence)
        # This is just for testing - won't play real audio
        return b'\xff\xfb\x90\x00' + b'\x00' * 100
    
    def _real_synthesize(self, text: str) -> bytes:
        """Synthesize using OpenAI TTS API."""
        start_time = time.time()
        
        try:
            logger.debug(f"Sending to TTS: '{text}'")
            
            response = self._client.audio.speech.create(
                model=TTS_MODEL,
                voice=TTS_VOICE,
                input=text,
                response_format="mp3"
            )
            
            audio_bytes = response.content
            elapsed = time.time() - start_time
            
            logger.info(f"TTS synthesis complete: {len(audio_bytes)} bytes ({elapsed:.2f}s)")
            return audio_bytes
            
        except APITimeoutError as e:
            logger.error(f"TTS timeout: {e}")
            raise RuntimeError("Speech synthesis timed out") from e
            
        except APIConnectionError as e:
            logger.error(f"TTS connection error: {e}")
            raise RuntimeError("Cannot connect to speech service") from e
            
        except APIError as e:
            logger.error(f"TTS API error: {e}")
            raise RuntimeError(f"Speech synthesis failed: {e}") from e
            
        except Exception as e:
            logger.error(f"TTS unexpected error: {e}")
            raise RuntimeError(f"Speech synthesis failed: {e}") from e

