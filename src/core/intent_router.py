"""
Intent Router for Arvis.

Routes voice.command events to registered intent handlers.
"""

import asyncio
from typing import Callable, Dict, Any, Optional
from dataclasses import dataclass

from loguru import logger

from src.core.event_bus import EventBus
from src.core.models import Event, Intent


@dataclass
class HandlerContext:
    """Context passed to intent handlers."""
    led_controller: Any  # LEDController
    audio_controller: Any  # AudioController
    state_manager: Any  # StateManager
    event_bus: EventBus


# Type alias for intent handlers
IntentHandler = Callable[[Intent, HandlerContext], Any]


class IntentRouter:
    """
    Routes intents to registered handlers.
    
    Subscribes to voice.command events and dispatches to appropriate handlers
    based on the intent action.
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        context: HandlerContext,
    ):
        """
        Initialize the intent router.
        
        Args:
            event_bus: EventBus for subscribing to events
            context: HandlerContext with controller references
        """
        self.event_bus = event_bus
        self.context = context
        self._handlers: Dict[str, IntentHandler] = {}
        self._running = False
        
        logger.info("IntentRouter initialized")
    
    def register(self, action: str, handler: IntentHandler) -> None:
        """
        Register a handler for an intent action.
        
        Args:
            action: Intent action to handle (e.g., "lights.on")
            handler: Async function to handle the intent
        """
        if action in self._handlers:
            logger.warning(f"Overwriting handler for action: {action}")
        
        self._handlers[action] = handler
        logger.debug(f"Registered handler for '{action}'")
    
    def handler(self, action: str):
        """
        Decorator for registering intent handlers.
        
        Usage:
            @router.handler("lights.on")
            async def handle_lights_on(intent, ctx):
                ...
        """
        def decorator(func: IntentHandler) -> IntentHandler:
            self.register(action, func)
            return func
        return decorator
    
    async def start(self) -> None:
        """Start listening for voice.command events."""
        if self._running:
            logger.warning("IntentRouter already running")
            return
        
        self._running = True
        self.event_bus.subscribe("voice.command", self._on_voice_command)
        
        logger.info(f"IntentRouter started with {len(self._handlers)} handlers")
    
    async def stop(self) -> None:
        """Stop the intent router."""
        self._running = False
        self.event_bus.unsubscribe("voice.command", self._on_voice_command)
        logger.info("IntentRouter stopped")
    
    async def _on_voice_command(self, event: Event) -> None:
        """Handle incoming voice.command events."""
        try:
            # Extract intent from event payload
            intent_data = event.payload.get("intent", {})
            text = event.payload.get("text", "")
            
            action = intent_data.get("action", "unknown")
            params = intent_data.get("params", {})
            
            intent = Intent(
                action=action,
                params=params,
                raw_text=text,
                source="voice"
            )
            
            logger.info(f"Routing intent: {action}")
            
            # Route to handler
            await self.route(intent)
            
        except Exception as e:
            logger.error(f"Error handling voice command: {e}")
    
    async def route(self, intent: Intent) -> bool:
        """
        Route an intent to its handler.
        
        Args:
            intent: Intent to route
            
        Returns:
            True if handler was found and executed, False otherwise
        """
        handler = self._handlers.get(intent.action)
        
        if handler is None:
            logger.warning(f"No handler for action: {intent.action}")
            # Say we don't understand
            if self.context.audio_controller:
                await self._say("I can't do that yet.")
            return False
        
        try:
            # Call the handler
            result = handler(intent, self.context)
            
            # Await if coroutine
            if asyncio.iscoroutine(result):
                await result
            
            logger.debug(f"Handler executed for: {intent.action}")
            return True
            
        except Exception as e:
            logger.error(f"Handler error for {intent.action}: {e}")
            if self.context.audio_controller:
                await self._say("Something went wrong.")
            return False
    
    async def _say(self, text: str) -> None:
        """Speak via audio controller."""
        if self.context.audio_controller:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, 
                self.context.audio_controller.say, 
                text
            )
    
    @property
    def registered_actions(self) -> list:
        """Get list of registered action names."""
        return list(self._handlers.keys())

