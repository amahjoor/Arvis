"""
Chat Intent Handlers for Arvis.

Handles conversational queries and greetings.
"""

import asyncio
from loguru import logger

from src.core.models import Intent
from src.core.intent_router import HandlerContext, IntentRouter


def register_chat_handlers(router: IntentRouter) -> None:
    """
    Register chat-related intent handlers with the router.
    
    Args:
        router: IntentRouter to register handlers with
    """
    
    @router.handler("chat.response")
    async def handle_chat_response(intent: Intent, ctx: HandlerContext) -> None:
        """Handle conversational queries."""
        message = intent.params.get("message", "Yes.")
        
        logger.info(f"Handling chat.response: {message}")
        
        await _say(ctx, message)
    
    logger.info("Registered chat handlers")


async def _say(ctx: HandlerContext, text: str) -> None:
    """Helper to speak via audio controller."""
    if ctx.audio_controller:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            ctx.audio_controller.say,
            text
        )

