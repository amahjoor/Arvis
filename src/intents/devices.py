"""
Device Intent Handlers for Arvis.

Handles voice commands related to smart plug control.
"""

import asyncio
from loguru import logger

from src.core.models import Intent
from src.core.intent_router import HandlerContext, IntentRouter


def register_device_handlers(router: IntentRouter) -> None:
    """
    Register all device-related intent handlers with the router.

    Args:
        router: IntentRouter to register handlers with
    """

    @router.handler("device.on")
    async def handle_device_on(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'turn on [device]' command."""
        # Normalize device name: lowercase, remove hyphens/spaces, convert to underscores
        device_id = intent.params.get("device", "").lower().replace("-", "").replace(" ", "_")

        logger.info(f"Handling device.on intent: {device_id}")

        if not device_id:
            await _say(ctx, "Which device?")
            return

        if not hasattr(ctx, 'smart_plug_controller') or ctx.smart_plug_controller is None:
            await _say(ctx, "Smart plugs not configured.")
            return

        success = await ctx.smart_plug_controller.turn_on(device_id)

        if success:
            device_name = device_id.replace("_", " ")
            await _say(ctx, f"{device_name} on.")
        else:
            await _say(ctx, f"Couldn't find {device_id}.")

    @router.handler("device.off")
    async def handle_device_off(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'turn off [device]' command."""
        # Normalize device name: lowercase, remove hyphens/spaces, convert to underscores
        device_id = intent.params.get("device", "").lower().replace("-", "").replace(" ", "_")

        logger.info(f"Handling device.off intent: {device_id}")

        if not device_id:
            await _say(ctx, "Which device?")
            return

        if not hasattr(ctx, 'smart_plug_controller') or ctx.smart_plug_controller is None:
            await _say(ctx, "Smart plugs not configured.")
            return

        success = await ctx.smart_plug_controller.turn_off(device_id)

        if success:
            device_name = device_id.replace("_", " ")
            await _say(ctx, f"{device_name} off.")
        else:
            await _say(ctx, f"Couldn't find {device_id}.")

    @router.handler("device.status")
    async def handle_device_status(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'is [device] on' command."""
        # Normalize device name: lowercase, remove hyphens/spaces, convert to underscores
        device_id = intent.params.get("device", "").lower().replace("-", "").replace(" ", "_")

        if not device_id:
            await _say(ctx, "Which device?")
            return

        if not hasattr(ctx, 'smart_plug_controller') or ctx.smart_plug_controller is None:
            await _say(ctx, "Smart plugs not configured.")
            return

        is_on = await ctx.smart_plug_controller.is_on(device_id)

        if is_on is None:
            await _say(ctx, f"Couldn't find {device_id}.")
        elif is_on:
            device_name = device_id.replace("_", " ")
            await _say(ctx, f"{device_name} is on.")
        else:
            device_name = device_id.replace("_", " ")
            await _say(ctx, f"{device_name} is off.")

    logger.info("Registered device handlers")


async def _say(ctx: HandlerContext, text: str) -> None:
    """Helper to speak via audio controller."""
    if ctx.audio_controller:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            ctx.audio_controller.say,
            text
        )
