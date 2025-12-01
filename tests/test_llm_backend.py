"""
Tests for LLMBackend.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.backends.llm_backend import LLMBackend
from src.core.models import Intent, RoomState


class TestLLMBackend:
    """Test suite for LLMBackend."""
    
    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        backend = LLMBackend(mock_mode=True)
        assert backend._mock_mode is True
        assert backend._client is None
    
    def test_mock_extract_lights_on(self):
        """Test mock intent extraction for lights on."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("turn on the lights")
        
        assert intent.action == "lights.on"
        assert intent.params == {}
        assert intent.raw_text == "turn on the lights"
    
    def test_mock_extract_lights_off(self):
        """Test mock intent extraction for lights off."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("turn off the lights")
        
        assert intent.action == "lights.off"
        assert intent.params == {}
    
    def test_mock_extract_focus_scene(self):
        """Test mock intent extraction for focus scene."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("focus mode please")
        
        assert intent.action == "lights.scene"
        assert intent.params == {"scene": "focus"}
    
    def test_mock_extract_night_scene(self):
        """Test mock intent extraction for night scene."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("night mode")
        
        assert intent.action == "lights.scene"
        assert intent.params == {"scene": "night"}
    
    def test_mock_extract_timer(self):
        """Test mock intent extraction for timer."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("set a timer for 5 minutes")
        
        assert intent.action == "timer.set"
        assert intent.params == {"minutes": 5}
    
    def test_mock_extract_status(self):
        """Test mock intent extraction for status."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("what's the status")
        
        assert intent.action == "status.get"
        assert intent.params == {}
    
    def test_mock_extract_unclear(self):
        """Test mock intent extraction for unclear command."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("blah blah blah")
        
        assert intent.action == "clarify"
        assert "message" in intent.params
    
    def test_real_extract_uses_openai(self):
        """Test that real mode uses OpenAI client."""
        # Just verify non-mock mode initializes with a client
        # Actual API calls are integration tests
        backend = LLMBackend(mock_mode=False)
        assert backend._client is not None
    
    def test_intent_has_raw_text(self):
        """Test that intent includes raw text."""
        backend = LLMBackend(mock_mode=True)
        intent = backend.extract_intent("turn on lights")
        
        assert intent.raw_text == "turn on lights"
    
    def test_intent_default_room_state(self):
        """Test that extract_intent works with default room state."""
        backend = LLMBackend(mock_mode=True)
        # Should not raise when room_state is not provided
        intent = backend.extract_intent("test command")
        assert intent is not None
    
    def test_mock_case_insensitive(self):
        """Test mock extraction is case insensitive."""
        backend = LLMBackend(mock_mode=True)
        
        intent1 = backend.extract_intent("TURN ON THE LIGHTS")
        intent2 = backend.extract_intent("Turn On The Lights")
        
        assert intent1.action == "lights.on"
        assert intent2.action == "lights.on"
