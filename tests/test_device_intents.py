"""
Unit tests for device intent handlers.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.core.models import Intent
from src.core.intent_router import IntentRouter, HandlerContext
from src.intents.devices import register_device_handlers


class TestDeviceIntentHandlers:
    """Test cases for device intent handlers."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create mock components
        self.mock_smart_plug_controller = MagicMock()
        self.mock_audio_controller = MagicMock()
        self.mock_state_manager = MagicMock()
        self.mock_event_bus = MagicMock()

        # Create handler context
        self.context = HandlerContext(
            led_controller=None,
            audio_controller=self.mock_audio_controller,
            state_manager=self.mock_state_manager,
            event_bus=self.mock_event_bus,
            smart_plug_controller=self.mock_smart_plug_controller,
        )

        # Create intent router and register handlers
        self.router = IntentRouter(self.mock_event_bus, self.context)
        register_device_handlers(self.router)

    @pytest.mark.asyncio
    async def test_device_on_success(self):
        """Test successful device.on intent."""
        # Setup mock
        self.mock_smart_plug_controller.turn_on = AsyncMock(return_value=True)
        self.mock_audio_controller.say = MagicMock()

        # Create intent
        intent = Intent(action="device.on", params={"device": "lamp"}, raw_text="turn on the lamp")

        # Route intent
        result = await self.router.route(intent)

        # Verify
        assert result is True
        self.mock_smart_plug_controller.turn_on.assert_called_once_with("lamp")
        self.mock_audio_controller.say.assert_called_once_with("Lamp on.")

    @pytest.mark.asyncio
    async def test_device_on_no_device(self):
        """Test device.on intent with no device specified."""
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.on", params={}, raw_text="turn on")

        result = await self.router.route(intent)

        assert result is True  # Handler executed but returned early
        self.mock_audio_controller.say.assert_called_once_with("Which device?")
        self.mock_smart_plug_controller.turn_on.assert_not_called()

    @pytest.mark.asyncio
    async def test_device_on_no_controller(self):
        """Test device.on intent with no smart plug controller."""
        # Remove smart plug controller from context
        self.context.smart_plug_controller = None
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.on", params={"device": "lamp"}, raw_text="turn on the lamp")

        result = await self.router.route(intent)

        assert result is True
        self.mock_audio_controller.say.assert_called_once_with("Smart plugs not configured.")

    @pytest.mark.asyncio
    async def test_device_on_failure(self):
        """Test device.on intent when turn_on fails."""
        self.mock_smart_plug_controller.turn_on = AsyncMock(return_value=False)
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.on", params={"device": "lamp"}, raw_text="turn on the lamp")

        result = await self.router.route(intent)

        assert result is True
        self.mock_smart_plug_controller.turn_on.assert_called_once_with("lamp")
        self.mock_audio_controller.say.assert_called_once_with("Couldn't find lamp.")

    @pytest.mark.asyncio
    async def test_device_off_success(self):
        """Test successful device.off intent."""
        self.mock_smart_plug_controller.turn_off = AsyncMock(return_value=True)
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.off", params={"device": "record_player"}, raw_text="turn off the record player")

        result = await self.router.route(intent)

        assert result is True
        self.mock_smart_plug_controller.turn_off.assert_called_once_with("record_player")
        self.mock_audio_controller.say.assert_called_once_with("Record player off.")

    @pytest.mark.asyncio
    async def test_device_status_on(self):
        """Test device.status intent when device is on."""
        self.mock_smart_plug_controller.is_on = AsyncMock(return_value=True)
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.status", params={"device": "lamp"}, raw_text="is the lamp on")

        result = await self.router.route(intent)

        assert result is True
        self.mock_smart_plug_controller.is_on.assert_called_once_with("lamp")
        self.mock_audio_controller.say.assert_called_once_with("Lamp is on.")

    @pytest.mark.asyncio
    async def test_device_status_off(self):
        """Test device.status intent when device is off."""
        self.mock_smart_plug_controller.is_on = AsyncMock(return_value=False)
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.status", params={"device": "lamp"}, raw_text="is the lamp on")

        result = await self.router.route(intent)

        assert result is True
        self.mock_smart_plug_controller.is_on.assert_called_once_with("lamp")
        self.mock_audio_controller.say.assert_called_once_with("Lamp is off.")

    @pytest.mark.asyncio
    async def test_device_status_not_found(self):
        """Test device.status intent when device is not found."""
        self.mock_smart_plug_controller.is_on = AsyncMock(return_value=None)
        self.mock_audio_controller.say = MagicMock()

        intent = Intent(action="device.status", params={"device": "unknown_device"}, raw_text="is the unknown device on")

        result = await self.router.route(intent)

        assert result is True
        self.mock_smart_plug_controller.is_on.assert_called_once_with("unknown_device")
        self.mock_audio_controller.say.assert_called_once_with("Couldn't find unknown_device.")

    def test_handler_registration(self):
        """Test that handlers are properly registered."""
        registered_actions = self.router.registered_actions
        assert "device.on" in registered_actions
        assert "device.off" in registered_actions
        assert "device.status" in registered_actions
