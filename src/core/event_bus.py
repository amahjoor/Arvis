"""
Arvis EventBus

Central pub/sub system for all events in the Arvis system.
Components communicate via events on this bus, enabling
loose coupling and extensibility.

Features:
- Async event handlers
- Wildcard subscriptions (e.g., "presence.*")
- Multiple handlers per event type
"""

import asyncio
import fnmatch
from collections import defaultdict
from typing import Callable, Awaitable, Any
from loguru import logger

from .models import Event


# Type alias for async event handlers
EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    """
    Central event bus for pub/sub communication.
    
    Usage:
        bus = EventBus()
        
        async def handler(event: Event):
            print(f"Received: {event.type}")
        
        bus.subscribe("presence.motion", handler)
        await bus.publish(Event(type="presence.motion"))
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: dict[str, list[EventHandler]] = defaultdict(list)
        logger.debug("EventBus initialized")
    
    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """
        Subscribe a handler to an event type.
        
        Args:
            event_type: Event type to subscribe to. 
                        Supports wildcards (e.g., "presence.*", "*")
            handler: Async function to call when event is published
        """
        if "*" in event_type:
            self._wildcard_handlers[event_type].append(handler)
            logger.debug(f"Subscribed wildcard handler to '{event_type}'")
        else:
            self._handlers[event_type].append(handler)
            logger.debug(f"Subscribed handler to '{event_type}'")
    
    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        """
        Unsubscribe a handler from an event type.
        
        Args:
            event_type: Event type to unsubscribe from
            handler: Handler function to remove
            
        Returns:
            True if handler was found and removed, False otherwise
        """
        if "*" in event_type:
            handlers = self._wildcard_handlers.get(event_type, [])
        else:
            handlers = self._handlers.get(event_type, [])
        
        if handler in handlers:
            handlers.remove(handler)
            logger.debug(f"Unsubscribed handler from '{event_type}'")
            return True
        
        return False
    
    async def publish(self, event: Event) -> None:
        """
        Publish an event to all matching subscribers.
        
        Args:
            event: Event to publish
        """
        logger.debug(f"Publishing event: {event.type}")
        
        handlers_to_call: list[EventHandler] = []
        
        # Get exact match handlers
        handlers_to_call.extend(self._handlers.get(event.type, []))
        
        # Get wildcard match handlers
        for pattern, handlers in self._wildcard_handlers.items():
            if fnmatch.fnmatch(event.type, pattern):
                handlers_to_call.extend(handlers)
        
        # Call all handlers concurrently
        if handlers_to_call:
            await asyncio.gather(
                *[self._call_handler(handler, event) for handler in handlers_to_call],
                return_exceptions=True
            )
    
    async def _call_handler(self, handler: EventHandler, event: Event) -> None:
        """
        Call a handler with error handling.
        
        Args:
            handler: Handler function to call
            event: Event to pass to handler
        """
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Error in event handler for '{event.type}': {e}",
                exc_info=True
            )
    
    def clear(self) -> None:
        """Remove all subscriptions."""
        self._handlers.clear()
        self._wildcard_handlers.clear()
        logger.debug("EventBus cleared all subscriptions")
    
    @property
    def subscription_count(self) -> int:
        """Get total number of subscriptions."""
        exact = sum(len(h) for h in self._handlers.values())
        wildcard = sum(len(h) for h in self._wildcard_handlers.values())
        return exact + wildcard

