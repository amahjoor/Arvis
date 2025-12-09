"""
Light Intent Handlers for Arvis.

Handles voice commands related to lighting control.
"""

import asyncio
from loguru import logger

from src.core.models import Intent
from src.core.intent_router import HandlerContext, IntentRouter
from src.config import SCENES


def register_light_handlers(router: IntentRouter) -> None:
    """
    Register all light-related intent handlers with the router.
    
    Args:
        router: IntentRouter to register handlers with
    """
    
    @router.handler("lights.on")
    async def handle_lights_on(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'lights on' command."""
        logger.info("Handling lights.on intent")
        
        # Turn on LED strip
        ctx.led_controller.set_on()
        
        # Also turn on smart plug "light" if it exists
        if hasattr(ctx, 'smart_plug_controller') and ctx.smart_plug_controller:
            try:
                success = await ctx.smart_plug_controller.turn_on("light")
                if success:
                    logger.info("Also turned on smart plug 'light'")
                else:
                    logger.debug("Smart plug 'light' not found or failed to turn on")
            except Exception as e:
                logger.debug(f"Error controlling smart plug 'light': {e}")
        
        # Voice confirmation
        await _say(ctx, "Lights on.")
    
    @router.handler("lights.off")
    async def handle_lights_off(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'lights off' command."""
        logger.info("Handling lights.off intent")
        
        # Turn off LED strip
        ctx.led_controller.set_off()
        
        # Also turn off smart plug "light" if it exists
        if hasattr(ctx, 'smart_plug_controller') and ctx.smart_plug_controller:
            try:
                success = await ctx.smart_plug_controller.turn_off("light")
                if success:
                    logger.info("Also turned off smart plug 'light'")
                else:
                    logger.debug("Smart plug 'light' not found or failed to turn off")
            except Exception as e:
                logger.debug(f"Error controlling smart plug 'light': {e}")
        
        # Voice confirmation
        await _say(ctx, "Lights off.")
    
    @router.handler("lights.scene")
    async def handle_lights_scene(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'set scene' command."""
        scene_id = intent.params.get("scene", "").lower()
        
        logger.info(f"Handling lights.scene intent: {scene_id}")
        
        if not scene_id:
            await _say(ctx, "Which scene?")
            return
        
        # Check if scene exists
        scene = SCENES.get(scene_id)
        if scene is None:
            await _say(ctx, f"I don't know the {scene_id} scene.")
            return
        
        # Apply scene
        success = ctx.led_controller.set_scene(scene_id)
        
        if success:
            # Use scene-specific voice response
            voice = scene.get("voice", f"{scene_id.title()} mode.")
            await _say(ctx, voice)
        else:
            await _say(ctx, "Something went wrong.")
    
    @router.handler("status.get")
    async def handle_status_get(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'status' command."""
        logger.info("Handling status.get intent")
        
        # Build status message
        state = ctx.state_manager.get_state().value if ctx.state_manager else "unknown"
        lights = "on" if ctx.led_controller.is_on else "off"
        scene = ctx.led_controller.current_scene
        
        if scene:
            response = f"Room is {state}. Lights are in {scene} mode."
        else:
            response = f"Room is {state}. Lights are {lights}."
        
        await _say(ctx, response)
    
    @router.handler("timer.set")
    async def handle_timer_set(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'set timer' command."""
        minutes = intent.params.get("minutes", 5)
        
        logger.info(f"Handling timer.set intent: {minutes} minutes")
        
        # TODO: Implement actual timer in future story
        await _say(ctx, f"Timer set for {minutes} minutes.")
    
    @router.handler("clarify")
    async def handle_clarify(intent: Intent, ctx: HandlerContext) -> None:
        """Handle unclear commands."""
        message = intent.params.get("message", "I didn't catch that.")
        
        logger.info(f"Handling clarify intent: {message}")
        
        await _say(ctx, message)
    
    logger.info(f"Registered {len(router.registered_actions)} light handlers")


async def _say(ctx: HandlerContext, text: str) -> None:
    """Helper to speak via audio controller."""
    if ctx.audio_controller:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            ctx.audio_controller.say,
            text
        )

