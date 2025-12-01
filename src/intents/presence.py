"""
Presence intent handlers for entry/exit scenes.

Handles:
- presence.entry → Welcome scene (golden shimmer + "Welcome back, Arman")
- presence.exit → Goodbye scene (fade out + "Goodbye")
"""

from loguru import logger

from src.core.models import Intent
from src.core.intent_router import IntentRouter, HandlerContext


def register_presence_handlers(router: IntentRouter) -> None:
    """
    Register all presence-related intent handlers.
    
    Args:
        router: IntentRouter to register handlers with
    """
    
    @router.handler("presence.entry")
    async def handle_entry(intent: Intent, ctx: HandlerContext) -> None:
        """
        Handle room entry - play welcome scene.
        
        - Golden shimmer LED animation
        - Voice: "Welcome back, Arman."
        """
        logger.info("🚪 Handling presence.entry - Welcome scene")
        
        # Start LED animation (non-blocking)
        ctx.led_controller.animate_golden_shimmer(duration=3.0)
        
        # Voice greeting (blocking call, not async)
        ctx.audio_controller.say("Welcome back, Arman.")
        
        logger.info("✅ Welcome scene complete")
    
    @router.handler("presence.exit")
    async def handle_exit(intent: Intent, ctx: HandlerContext) -> None:
        """
        Handle room exit - play goodbye scene.
        
        - Voice: "Goodbye."
        - Fade out LED animation
        """
        logger.info("🚪 Handling presence.exit - Goodbye scene")
        
        # Voice farewell first (short)
        ctx.audio_controller.say("Goodbye.")
        
        # Then fade out lights
        ctx.led_controller.animate_fade_out(duration=2.0)
        
        logger.info("✅ Goodbye scene complete")
    
    handler_count = 2
    logger.info(f"Registered {handler_count} presence handlers")

