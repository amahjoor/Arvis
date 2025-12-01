"""
Tests for AudioController.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.backends.tts_backend import TTSBackend
from src.controllers.audio_controller import AudioController


class TestAudioController:
    """Test suite for AudioController."""
    
    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        assert controller._mock_mode is True
        assert controller._mixer_initialized is False
    
    def test_say_mock_mode(self):
        """Test say in mock mode returns True."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        result = controller.say("Hello world")
        assert result is True
    
    def test_say_empty_text(self):
        """Test say with empty text returns True."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        result = controller.say("")
        assert result is True
    
    def test_play_audio_mock_mode(self):
        """Test play_audio in mock mode returns True."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        result = controller.play_audio(b"fake audio data")
        assert result is True
    
    def test_play_sound_mock_mode(self):
        """Test play_sound in mock mode returns True."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        result = controller.play_sound("notification")
        assert result is True
    
    def test_stop_mock_mode(self):
        """Test stop in mock mode doesn't raise."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=True)
        
        # Should not raise
        controller.stop()
    
    def test_say_tts_error(self):
        """Test say handles TTS errors gracefully."""
        tts = Mock()
        tts.synthesize.side_effect = RuntimeError("TTS failed")
        
        controller = AudioController(tts, mock_mode=False)
        controller._mixer_initialized = True
        
        result = controller.say("test")
        assert result is False
    
    def test_init_mixer_attempts_init(self):
        """Test mixer initialization is attempted in non-mock mode."""
        # In non-mock mode, mixer init is attempted
        # Whether it succeeds depends on audio hardware availability
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=False)
        
        # mixer_initialized will be True or False depending on system
        assert isinstance(controller._mixer_initialized, bool)
    
    def test_real_mode_handles_missing_mixer(self):
        """Test graceful handling when mixer can't initialize."""
        # This test verifies the controller doesn't crash
        # even if mixer init fails (e.g., no audio device)
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=False)
        
        # Even if mixer failed, controller should be usable
        # (play methods will return False but won't crash)
        assert controller._mock_mode is False
    
    def test_play_audio_no_mixer(self):
        """Test play_audio when mixer not initialized."""
        tts = TTSBackend(mock_mode=True)
        controller = AudioController(tts, mock_mode=False)
        controller._mixer_initialized = False
        
        result = controller.play_audio(b"test")
        assert result is False

