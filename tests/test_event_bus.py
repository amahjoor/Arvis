"""
Tests for EventBus.

Tests cover:
- Basic publish/subscribe
- Multiple handlers
- Wildcard subscriptions
- Unsubscribe functionality
- Error handling in handlers
"""

import pytest
import asyncio
from datetime import datetime

from src.core.event_bus import EventBus
from src.core.models import Event


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    return Event(
        type="test.event",
        payload={"key": "value"},
        source="test"
    )


class TestEventBusBasics:
    """Test basic EventBus functionality."""
    
    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, event_bus, sample_event):
        """Test that a subscribed handler receives published events."""
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        event_bus.subscribe("test.event", handler)
        await event_bus.publish(sample_event)
        
        assert len(received_events) == 1
        assert received_events[0].type == "test.event"
        assert received_events[0].payload == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_no_handler_no_error(self, event_bus, sample_event):
        """Test that publishing without handlers doesn't raise errors."""
        # Should not raise
        await event_bus.publish(sample_event)
    
    @pytest.mark.asyncio
    async def test_multiple_handlers(self, event_bus, sample_event):
        """Test that multiple handlers all receive the event."""
        results = []
        
        async def handler1(event: Event):
            results.append("handler1")
        
        async def handler2(event: Event):
            results.append("handler2")
        
        event_bus.subscribe("test.event", handler1)
        event_bus.subscribe("test.event", handler2)
        await event_bus.publish(sample_event)
        
        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results
    
    @pytest.mark.asyncio
    async def test_handler_only_receives_matching_events(self, event_bus):
        """Test that handlers only receive events they subscribed to."""
        received = []
        
        async def handler(event: Event):
            received.append(event.type)
        
        event_bus.subscribe("type.a", handler)
        
        await event_bus.publish(Event(type="type.a", source="test"))
        await event_bus.publish(Event(type="type.b", source="test"))
        await event_bus.publish(Event(type="type.a", source="test"))
        
        assert received == ["type.a", "type.a"]


class TestWildcardSubscriptions:
    """Test wildcard subscription patterns."""
    
    @pytest.mark.asyncio
    async def test_wildcard_star(self, event_bus):
        """Test that * wildcard matches all events."""
        received = []
        
        async def handler(event: Event):
            received.append(event.type)
        
        event_bus.subscribe("*", handler)
        
        await event_bus.publish(Event(type="presence.motion", source="test"))
        await event_bus.publish(Event(type="voice.command", source="test"))
        await event_bus.publish(Event(type="anything", source="test"))
        
        assert len(received) == 3
    
    @pytest.mark.asyncio
    async def test_wildcard_prefix(self, event_bus):
        """Test that prefix.* matches events starting with prefix."""
        received = []
        
        async def handler(event: Event):
            received.append(event.type)
        
        event_bus.subscribe("presence.*", handler)
        
        await event_bus.publish(Event(type="presence.motion", source="test"))
        await event_bus.publish(Event(type="presence.timeout", source="test"))
        await event_bus.publish(Event(type="voice.command", source="test"))
        
        assert received == ["presence.motion", "presence.timeout"]
    
    @pytest.mark.asyncio
    async def test_wildcard_and_exact_both_fire(self, event_bus):
        """Test that both wildcard and exact subscriptions receive events."""
        received = []
        
        async def wildcard_handler(event: Event):
            received.append(f"wildcard:{event.type}")
        
        async def exact_handler(event: Event):
            received.append(f"exact:{event.type}")
        
        event_bus.subscribe("presence.*", wildcard_handler)
        event_bus.subscribe("presence.motion", exact_handler)
        
        await event_bus.publish(Event(type="presence.motion", source="test"))
        
        assert len(received) == 2
        assert "wildcard:presence.motion" in received
        assert "exact:presence.motion" in received


class TestUnsubscribe:
    """Test unsubscribe functionality."""
    
    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, event_bus):
        """Test that unsubscribed handlers no longer receive events."""
        received = []
        
        async def handler(event: Event):
            received.append(event.type)
        
        event_bus.subscribe("test.event", handler)
        await event_bus.publish(Event(type="test.event", source="test"))
        
        assert len(received) == 1
        
        result = event_bus.unsubscribe("test.event", handler)
        assert result is True
        
        await event_bus.publish(Event(type="test.event", source="test"))
        assert len(received) == 1  # Still 1, not 2
    
    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_returns_false(self, event_bus):
        """Test that unsubscribing a non-existent handler returns False."""
        async def handler(event: Event):
            pass
        
        result = event_bus.unsubscribe("nonexistent", handler)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear_removes_all(self, event_bus):
        """Test that clear() removes all subscriptions."""
        async def handler(event: Event):
            pass
        
        event_bus.subscribe("a", handler)
        event_bus.subscribe("b", handler)
        event_bus.subscribe("c.*", handler)
        
        assert event_bus.subscription_count == 3
        
        event_bus.clear()
        
        assert event_bus.subscription_count == 0


class TestErrorHandling:
    """Test error handling in event handlers."""
    
    @pytest.mark.asyncio
    async def test_handler_error_doesnt_stop_others(self, event_bus):
        """Test that an error in one handler doesn't prevent others from running."""
        results = []
        
        async def failing_handler(event: Event):
            raise ValueError("Test error")
        
        async def working_handler(event: Event):
            results.append("success")
        
        event_bus.subscribe("test.event", failing_handler)
        event_bus.subscribe("test.event", working_handler)
        
        # Should not raise, and working_handler should still run
        await event_bus.publish(Event(type="test.event", source="test"))
        
        assert "success" in results

