"""
Tests for TTSBackend.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.backends.tts_backend import TTSBackend


class TestTTSBackend:
    """Test suite for TTSBackend."""
    
    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        backend = TTSBackend(mock_mode=True)
        assert backend._mock_mode is True
        assert backend._client is None
    
    def test_mock_synthesize(self):
        """Test mock synthesis returns bytes."""
        backend = TTSBackend(mock_mode=True)
        result = backend.synthesize("Hello world")
        
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_mock_synthesize_empty_text(self):
        """Test mock synthesis with empty text."""
        backend = TTSBackend(mock_mode=True)
        result = backend.synthesize("")
        
        assert isinstance(result, bytes)
    
    @patch('src.backends.tts_backend.OpenAI')
    @patch('src.backends.tts_backend.OPENAI_API_KEY', 'test-key')
    def test_real_synthesize_success(self, mock_openai_class):
        """Test successful synthesis with mocked OpenAI."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        
        # Mock response
        mock_response = MagicMock()
        mock_response.content = b'fake mp3 audio data'
        mock_client.audio.speech.create.return_value = mock_response
        
        backend = TTSBackend(mock_mode=False)
        result = backend.synthesize("Hello world")
        
        assert result == b'fake mp3 audio data'
        mock_client.audio.speech.create.assert_called_once()
        
        # Verify correct parameters
        call_kwargs = mock_client.audio.speech.create.call_args.kwargs
        assert call_kwargs['voice'] == 'onyx'
        assert call_kwargs['input'] == 'Hello world'
    
    @patch('src.backends.tts_backend.OpenAI')
    @patch('src.backends.tts_backend.OPENAI_API_KEY', 'test-key')
    def test_real_synthesize_timeout(self, mock_openai_class):
        """Test synthesis timeout handling."""
        from openai import APITimeoutError
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.speech.create.side_effect = APITimeoutError(request=Mock())
        
        backend = TTSBackend(mock_mode=False)
        
        with pytest.raises(RuntimeError, match="timed out"):
            backend.synthesize("test")
    
    @patch('src.backends.tts_backend.OpenAI')
    @patch('src.backends.tts_backend.OPENAI_API_KEY', 'test-key')
    def test_real_synthesize_connection_error(self, mock_openai_class):
        """Test synthesis connection error handling."""
        from openai import APIConnectionError
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.speech.create.side_effect = APIConnectionError(request=Mock())
        
        backend = TTSBackend(mock_mode=False)
        
        with pytest.raises(RuntimeError, match="Cannot connect"):
            backend.synthesize("test")

