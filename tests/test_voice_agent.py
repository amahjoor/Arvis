"""
Tests for VoiceAgent.

Tests cover:
- Initialization
- Wake word event handling
- Recording flow
- Event publishing
"""

import pytest
import asyncio

from src.core.event_bus import EventBus
from src.core.models import Event
from src.agents.voice_agent import VoiceAgent


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def agent(event_bus):
    """Create a VoiceAgent in mock mode."""
    return VoiceAgent(event_bus, mock_mode=True)


class TestVoiceAgentInit:
    """Test VoiceAgent initialization."""
    
    def test_init_mock_mode(self, agent):
        """Test initialization in mock mode."""
        assert agent.mock_mode is True
        assert agent.is_recording is False
        assert agent.last_audio is None
    
    def test_init_not_running(self, agent):
        """Test agent starts in non-running state."""
        assert agent._running is False


class TestVoiceAgentLifecycle:
    """Test VoiceAgent start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, agent):
        """Test start and stop methods."""
        assert agent._running is False
        
        await agent.start()
        assert agent._running is True
        
        await agent.stop()
        assert agent._running is False
    
    @pytest.mark.asyncio
    async def test_subscribes_on_start(self, agent, event_bus):
        """Test that agent subscribes to wake word events on start."""
        await agent.start()
        
        # Check that handler is subscribed
        assert event_bus.subscription_count > 0
        
        await agent.stop()


class TestVoiceAgentRecording:
    """Test VoiceAgent recording functionality."""
    
    @pytest.mark.asyncio
    async def test_records_on_wake_word(self, agent, event_bus):
        """Test that agent records audio when wake word event is received."""
        recording_events = []
        
        async def handler(event: Event):
            recording_events.append(event)
        
        event_bus.subscribe("voice.recording_complete", handler)
        
        await agent.start()
        
        # Simulate wake word detection
        await event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="test",
        ))
        
        # Wait for recording to complete
        await asyncio.sleep(0.6)  # Mock recording takes ~0.5s
        
        assert len(recording_events) == 1
        assert recording_events[0].type == "voice.recording_complete"
        assert "audio_bytes" in recording_events[0].payload
        assert "duration" in recording_events[0].payload
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_recording_complete_event_format(self, agent, event_bus):
        """Test the format of recording complete events."""
        recording_event = None
        
        async def handler(event: Event):
            nonlocal recording_event
            recording_event = event
        
        event_bus.subscribe("voice.recording_complete", handler)
        
        await agent.start()
        
        await event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="test",
        ))
        
        await asyncio.sleep(0.6)
        
        assert recording_event is not None
        payload = recording_event.payload
        
        assert "audio_bytes" in payload
        assert "duration" in payload
        assert "format" in payload
        assert "sample_rate" in payload
        
        assert payload["format"] == "wav"
        assert payload["sample_rate"] == 16000
        assert isinstance(payload["audio_bytes"], bytes)
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_stores_last_audio(self, agent, event_bus):
        """Test that agent stores the last recorded audio."""
        assert agent.last_audio is None
        
        await agent.start()
        
        await event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="test",
        ))
        
        await asyncio.sleep(0.6)
        
        assert agent.last_audio is not None
        assert isinstance(agent.last_audio, bytes)
        assert agent.last_duration > 0
        
        await agent.stop()
    
    @pytest.mark.asyncio
    async def test_ignores_wake_word_while_recording(self, agent, event_bus):
        """Test that additional wake words are ignored during recording."""
        recording_count = 0
        
        async def handler(event: Event):
            nonlocal recording_count
            recording_count += 1
        
        event_bus.subscribe("voice.recording_complete", handler)
        
        await agent.start()
        
        # Send wake word
        await event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="test",
        ))
        
        # Wait briefly for recording to start
        await asyncio.sleep(0.1)
        
        # Verify we're in recording state
        assert agent.is_recording is True
        
        # Send another wake word while still recording - should be ignored
        await event_bus.publish(Event(
            type="wake_word.detected",
            payload={},
            source="test",
        ))
        
        # Wait for recordings to complete
        await asyncio.sleep(0.6)
        
        # Should only have one recording (second was ignored)
        assert recording_count == 1
        
        await agent.stop()


class TestVoiceAgentManualProcessing:
    """Test manual audio processing."""
    
    @pytest.mark.asyncio
    async def test_process_command_manual(self, agent, event_bus):
        """Test manually processing audio bytes."""
        recording_events = []
        
        async def handler(event: Event):
            recording_events.append(event)
        
        event_bus.subscribe("voice.recording_complete", handler)
        
        await agent.start()
        
        # Manually process some audio
        test_audio = b"RIFF" + b"\x00" * 100  # Fake WAV header
        await agent.process_command_manual(test_audio)
        
        assert len(recording_events) == 1
        assert recording_events[0].payload["audio_bytes"] == test_audio
        
        await agent.stop()

