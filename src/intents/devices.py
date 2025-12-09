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
        """Handle 'turn on [device]' command. Supports single device or multiple devices."""
        # Check for multiple devices first
        devices = intent.params.get("devices", [])
        device = intent.params.get("device", "")
        
        # If single device, convert to list for unified handling
        if device and not devices:
            devices = [device]
        elif not devices and not device:
            await _say(ctx, "Which device?")
            return

        logger.info(f"Handling device.on intent: {devices}")

        if not hasattr(ctx, 'smart_plug_controller') or ctx.smart_plug_controller is None:
            await _say(ctx, "Smart plugs not configured.")
            return

        # Normalize and control each device
        results = []
        for dev in devices:
            device_id = str(dev).lower().replace("-", "").replace(" ", "_")
            success = await ctx.smart_plug_controller.turn_on(device_id)
            results.append((device_id, success))

        # Generate response
        successful = [d.replace("_", " ") for d, s in results if s]
        failed = [d.replace("_", " ") for d, s in results if not s]
        
        if successful and not failed:
            if len(successful) == 1:
                await _say(ctx, f"{successful[0]} on.")
            else:
                await _say(ctx, f"{', '.join(successful)} on.")
        elif failed:
            await _say(ctx, f"Couldn't find {', '.join(failed)}.")
        else:
            await _say(ctx, "Couldn't find those devices.")

    @router.handler("device.off")
    async def handle_device_off(intent: Intent, ctx: HandlerContext) -> None:
        """Handle 'turn off [device]' command. Supports single device or multiple devices."""
        # Check for multiple devices first
        devices = intent.params.get("devices", [])
        device = intent.params.get("device", "")
        
        # If single device, convert to list for unified handling
        if device and not devices:
            devices = [device]
        elif not devices and not device:
            await _say(ctx, "Which device?")
            return

        logger.info(f"Handling device.off intent: {devices}")

        if not hasattr(ctx, 'smart_plug_controller') or ctx.smart_plug_controller is None:
            await _say(ctx, "Smart plugs not configured.")
            return

        # Normalize and control each device
        results = []
        for dev in devices:
            device_id = str(dev).lower().replace("-", "").replace(" ", "_")
            success = await ctx.smart_plug_controller.turn_off(device_id)
            results.append((device_id, success))

        # Generate response
        successful = [d.replace("_", " ") for d, s in results if s]
        failed = [d.replace("_", " ") for d, s in results if not s]
        
        if successful and not failed:
            if len(successful) == 1:
                await _say(ctx, f"{successful[0]} off.")
            else:
                await _say(ctx, f"{', '.join(successful)} off.")
        elif failed:
            await _say(ctx, f"Couldn't find {', '.join(failed)}.")
        else:
            await _say(ctx, "Couldn't find those devices.")

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
