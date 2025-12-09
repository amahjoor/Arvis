"""
Tests for PIR Sensor.
"""

import asyncio
import pytest

from src.core.event_bus import EventBus
from src.sensors.pir_sensor import PIRSensor


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def mock_pir(event_bus):
    """Create a PIRSensor in mock mode."""
    return PIRSensor(
        event_bus=event_bus,
        mock_mode=True,
        debounce_seconds=0.1,
    )


@pytest.mark.asyncio
async def test_pir_starts_and_stops(mock_pir):
    """Test sensor lifecycle."""
    assert not mock_pir.is_running
    
    await mock_pir.start()
    assert mock_pir.is_running
    
    await mock_pir.stop()
    assert not mock_pir.is_running


@pytest.mark.asyncio
async def test_pir_publishes_motion_event(mock_pir, event_bus):
    """Test that motion detection publishes event."""
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    event_bus.subscribe("presence.motion_detected", handler)
    
    await mock_pir.start()
    await mock_pir.trigger_mock_motion()
    
    await asyncio.sleep(0.05)
    
    assert len(received_events) == 1
    assert received_events[0].type == "presence.motion_detected"
    assert received_events[0].source == "pir_sensor"
    
    await mock_pir.stop()


@pytest.mark.asyncio
async def test_pir_debounce(mock_pir, event_bus):
    """Test that rapid motion events are debounced."""
    received_events = []
    
    async def handler(event):
        received_events.append(event)
    
    event_bus.subscribe("presence.motion_detected", handler)
    
    await mock_pir.start()
    
    await mock_pir.trigger_mock_motion()
    await mock_pir.trigger_mock_motion()
    await mock_pir.trigger_mock_motion()
    
    await asyncio.sleep(0.05)
    
    assert len(received_events) == 1
    
    await mock_pir.stop()


@pytest.mark.asyncio
async def test_pir_last_motion_time(mock_pir):
    """Test last motion time tracking."""
    await mock_pir.start()
    
    assert mock_pir.last_motion_time is None
    
    await mock_pir.trigger_mock_motion()
    
    assert mock_pir.last_motion_time is not None
    assert mock_pir.seconds_since_motion < 1.0
    
    await mock_pir.stop()


