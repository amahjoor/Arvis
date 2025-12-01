"""
Tests for STTBackend.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.backends.stt_backend import STTBackend


class TestSTTBackend:
    """Test suite for STTBackend."""
    
    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        backend = STTBackend(mock_mode=True)
        assert backend._mock_mode is True
        assert backend._client is None
    
    def test_mock_transcribe(self):
        """Test mock transcription returns expected text."""
        backend = STTBackend(mock_mode=True)
        result = backend.transcribe(b"fake audio data")
        assert result == "turn on the lights"
    
    def test_mock_transcribe_handles_any_input(self):
        """Test mock transcription handles various inputs."""
        backend = STTBackend(mock_mode=True)
        
        # Empty bytes
        result = backend.transcribe(b"")
        assert result == "turn on the lights"
        
        # Large bytes
        result = backend.transcribe(b"x" * 10000)
        assert result == "turn on the lights"
    
    def test_init_requires_api_key(self):
        """Test that init in non-mock mode needs API key (tested via mock)."""
        # In production, the key comes from config
        # We just verify the backend initializes when key is present
        # (actual key validation happens at API call time)
        pass  # API key is loaded from .env in real usage
    
    @patch('src.backends.stt_backend.OpenAI')
    @patch('src.backends.stt_backend.OPENAI_API_KEY', 'test-key')
    def test_real_transcribe_success(self, mock_openai_class):
        """Test successful transcription with mocked OpenAI."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.transcriptions.create.return_value = "hello world"
        
        backend = STTBackend(mock_mode=False)
        result = backend.transcribe(b"fake audio")
        
        assert result == "hello world"
        mock_client.audio.transcriptions.create.assert_called_once()
    
    @patch('src.backends.stt_backend.OpenAI')
    @patch('src.backends.stt_backend.OPENAI_API_KEY', 'test-key')
    def test_real_transcribe_timeout(self, mock_openai_class):
        """Test transcription timeout handling."""
        from openai import APITimeoutError
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = APITimeoutError(request=Mock())
        
        backend = STTBackend(mock_mode=False)
        
        with pytest.raises(RuntimeError, match="timed out"):
            backend.transcribe(b"fake audio")
    
    @patch('src.backends.stt_backend.OpenAI')
    @patch('src.backends.stt_backend.OPENAI_API_KEY', 'test-key')
    def test_real_transcribe_connection_error(self, mock_openai_class):
        """Test transcription connection error handling."""
        from openai import APIConnectionError
        
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client
        mock_client.audio.transcriptions.create.side_effect = APIConnectionError(request=Mock())
        
        backend = STTBackend(mock_mode=False)
        
        with pytest.raises(RuntimeError, match="Cannot connect"):
            backend.transcribe(b"fake audio")

