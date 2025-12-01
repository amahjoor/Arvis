"""
Speech-to-Text Backend using OpenAI Whisper API.

Transcribes audio bytes into text.
"""

import io
import time
from typing import Optional

from loguru import logger
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError

from src.config import OPENAI_API_KEY, STT_MODEL


class STTBackend:
    """Handles speech-to-text transcription using OpenAI Whisper."""
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize STT backend.
        
        Args:
            mock_mode: If True, return mock transcriptions
        """
        self._mock_mode = mock_mode
        self._client: Optional[OpenAI] = None
        
        if not mock_mode:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        
        logger.info(f"STTBackend initialized (mock_mode={mock_mode})")
    
    def transcribe(self, audio_bytes: bytes) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio data (16-bit PCM, 16kHz, mono)
            
        Returns:
            Transcribed text string
            
        Raises:
            RuntimeError: If transcription fails
        """
        if self._mock_mode:
            return self._mock_transcribe(audio_bytes)
        
        return self._real_transcribe(audio_bytes)
    
    def _mock_transcribe(self, audio_bytes: bytes) -> str:
        """Return mock transcription for testing."""
        logger.debug(f"Mock transcribe: {len(audio_bytes)} bytes")
        # Simulate processing time
        time.sleep(0.1)
        return "turn on the lights"
    
    def _real_transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe using OpenAI Whisper API."""
        start_time = time.time()
        
        try:
            # Create a file-like object with the audio data
            # Whisper expects a file with proper audio format
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "audio.wav"  # Whisper needs a filename hint
            
            logger.debug(f"Sending {len(audio_bytes)} bytes to Whisper API")
            
            response = self._client.audio.transcriptions.create(
                model=STT_MODEL,
                file=audio_file,
                response_format="text"
            )
            
            elapsed = time.time() - start_time
            text = response.strip() if isinstance(response, str) else response.text.strip()
            
            logger.info(f"STT transcription complete: '{text}' ({elapsed:.2f}s)")
            return text
            
        except APITimeoutError as e:
            logger.error(f"STT timeout: {e}")
            raise RuntimeError("Transcription timed out") from e
            
        except APIConnectionError as e:
            logger.error(f"STT connection error: {e}")
            raise RuntimeError("Cannot connect to transcription service") from e
            
        except APIError as e:
            logger.error(f"STT API error: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e
            
        except Exception as e:
            logger.error(f"STT unexpected error: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e

