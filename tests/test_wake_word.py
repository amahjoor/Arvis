"""
Tests for WakeWordDetector.

Tests cover:
- Initialization
- Mock detection triggering
- Event publishing on detection
- Start/stop lifecycle
"""

import pytest
import asyncio

from src.core.event_bus import EventBus
from src.core.models import Event
from src.agents.wake_word import WakeWordDetector


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def detector(event_bus):
    """Create a WakeWordDetector in mock mode."""
    return WakeWordDetector(event_bus, mock_mode=True)


class TestWakeWordDetectorInit:
    """Test WakeWordDetector initialization."""
    
    def test_init_mock_mode(self, detector):
        """Test initialization in mock mode."""
        assert detector.mock_mode is True
        assert detector.is_running is False
    
    def test_init_with_sensitivity(self, event_bus):
        """Test initialization with custom sensitivity."""
        detector = WakeWordDetector(event_bus, sensitivity=0.7, mock_mode=True)
        assert detector.sensitivity == 0.7


class TestWakeWordDetectorLifecycle:
    """Test WakeWordDetector start/stop lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_stop(self, detector):
        """Test start and stop methods."""
        assert detector.is_running is False
        
        await detector.start()
        assert detector.is_running is True
        
        await detector.stop()
        assert detector.is_running is False
    
    @pytest.mark.asyncio
    async def test_double_start(self, detector):
        """Test that starting twice doesn't cause issues."""
        await detector.start()
        await detector.start()  # Should log warning but not error
        assert detector.is_running is True
        await detector.stop()


class TestWakeWordDetection:
    """Test wake word detection functionality."""
    
    @pytest.mark.asyncio
    async def test_mock_detection_publishes_event(self, detector, event_bus):
        """Test that mock detection publishes wake_word.detected event."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe("wake_word.detected", handler)
        
        await detector.start()
        await detector.trigger_mock_detection()
        
        assert len(received_events) == 1
        assert received_events[0].type == "wake_word.detected"
        assert received_events[0].source == "wake_word_detector"
        
        await detector.stop()
    
    @pytest.mark.asyncio
    async def test_callback_is_called(self, detector):
        """Test that registered callbacks are called on detection."""
        callback_called = []
        
        async def callback():
            callback_called.append(True)
        
        detector.on_wake_word(callback)
        
        await detector.start()
        await detector.trigger_mock_detection()
        
        assert len(callback_called) == 1
        
        await detector.stop()
    
    @pytest.mark.asyncio
    async def test_multiple_callbacks(self, detector):
        """Test that multiple callbacks are all called."""
        results = []
        
        async def callback1():
            results.append("callback1")
        
        async def callback2():
            results.append("callback2")
        
        detector.on_wake_word(callback1)
        detector.on_wake_word(callback2)
        
        await detector.start()
        await detector.trigger_mock_detection()
        
        assert "callback1" in results
        assert "callback2" in results
        
        await detector.stop()
    
    @pytest.mark.asyncio
    async def test_trigger_without_start(self, detector, event_bus):
        """Test that triggering before start logs warning."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe("wake_word.detected", handler)
        
        # Don't start the detector
        await detector.trigger_mock_detection()
        
        # Event should not be published (detector not running)
        assert len(received_events) == 0

