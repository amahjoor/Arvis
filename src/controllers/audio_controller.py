"""
Audio Controller for playing TTS and sound effects.

Handles audio playback through speakers.
"""

import io
import time
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

from src.config import SOUNDS_DIR
from src.backends.tts_backend import TTSBackend


class AudioController:
    """Controls audio playback for TTS and sound effects."""
    
    def __init__(self, tts_backend: TTSBackend, mock_mode: bool = False):
        """
        Initialize audio controller.
        
        Args:
            tts_backend: TTS backend for speech synthesis
            mock_mode: If True, skip actual audio playback
        """
        self._tts = tts_backend
        self._mock_mode = mock_mode
        self._mixer_initialized = False
        
        if not mock_mode:
            self._init_mixer()
        
        logger.info(f"AudioController initialized (mock_mode={mock_mode})")
    
    def _init_mixer(self):
        """Initialize pygame mixer for audio playback."""
        try:
            import pygame
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
            self._mixer_initialized = True
            logger.debug("Pygame mixer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize mixer: {e}")
            self._mixer_initialized = False
    
    def say(self, text: str) -> bool:
        """
        Synthesize and play speech.
        
        Args:
            text: Text to speak
            
        Returns:
            True if successful, False otherwise
        """
        if not text:
            return True
            
        logger.info(f"Speaking: '{text}'")
        
        try:
            # Synthesize speech
            audio_bytes = self._tts.synthesize(text)
            
            # Play the audio
            return self.play_audio(audio_bytes)
            
        except Exception as e:
            logger.error(f"Failed to speak: {e}")
            return False
    
    def play_audio(self, audio_bytes: bytes, wait: bool = True) -> bool:
        """
        Play audio bytes through speakers.
        
        Args:
            audio_bytes: Audio data (MP3 format)
            wait: If True, block until playback completes
            
        Returns:
            True if successful, False otherwise
        """
        if self._mock_mode:
            logger.debug(f"Mock play audio: {len(audio_bytes)} bytes")
            return True
        
        if not self._mixer_initialized:
            logger.warning("Mixer not initialized, cannot play audio")
            return False
        
        try:
            import pygame
            
            # Write to temporary file (pygame needs file path for MP3)
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                f.write(audio_bytes)
                temp_path = f.name
            
            try:
                # Load and play
                pygame.mixer.music.load(temp_path)
                pygame.mixer.music.play()
                
                if wait:
                    # Wait for playback to complete
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                
                logger.debug(f"Audio playback complete: {len(audio_bytes)} bytes")
                return True
                
            finally:
                # Clean up temp file
                try:
                    Path(temp_path).unlink()
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
            return False
    
    def play_sound(self, sound_name: str) -> bool:
        """
        Play a sound effect by name.
        
        Args:
            sound_name: Name of sound file (without extension)
            
        Returns:
            True if successful, False otherwise
        """
        if self._mock_mode:
            logger.debug(f"Mock play sound: {sound_name}")
            return True
        
        # Try common audio extensions
        for ext in ['.mp3', '.wav', '.ogg']:
            sound_path = SOUNDS_DIR / f"{sound_name}{ext}"
            if sound_path.exists():
                try:
                    with open(sound_path, 'rb') as f:
                        audio_bytes = f.read()
                    return self.play_audio(audio_bytes, wait=False)
                except Exception as e:
                    logger.error(f"Failed to play sound {sound_name}: {e}")
                    return False
        
        logger.warning(f"Sound not found: {sound_name}")
        return False
    
    def stop(self):
        """Stop any currently playing audio."""
        if self._mock_mode or not self._mixer_initialized:
            return
            
        try:
            import pygame
            pygame.mixer.music.stop()
            logger.debug("Audio stopped")
        except Exception as e:
            logger.error(f"Failed to stop audio: {e}")

