"""
Unit tests for SmartPlugController.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the kasa module to avoid import issues in test environment
sys.modules['kasa'] = MagicMock()
sys.modules['kasa.discover'] = MagicMock()

from src.controllers.smart_plug_controller import SmartPlugController


class TestSmartPlugController:
    """Test cases for SmartPlugController."""

    def test_init_mock_mode(self):
        """Test initialization in mock mode."""
        controller = SmartPlugController(mock_mode=True)
        assert controller._mock_mode is True
        assert controller._plugs == {}

    def test_init_real_mode(self):
        """Test initialization in real mode."""
        with patch('asyncio.create_task') as mock_task:
            controller = SmartPlugController(mock_mode=False)
            assert controller._mock_mode is False
            mock_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_turn_on_mock_mode(self):
        """Test turn_on in mock mode."""
        controller = SmartPlugController(mock_mode=True)
        result = await controller.turn_on("test_device")
        assert result is True

    @pytest.mark.asyncio
    async def test_turn_off_mock_mode(self):
        """Test turn_off in mock mode."""
        controller = SmartPlugController(mock_mode=True)
        result = await controller.turn_off("test_device")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_on_mock_mode(self):
        """Test is_on in mock mode."""
        controller = SmartPlugController(mock_mode=True)
        result = await controller.is_on("test_device")
        assert result is None

    def test_list_devices_empty(self):
        """Test list_devices with no devices."""
        controller = SmartPlugController(mock_mode=True)
        devices = controller.list_devices()
        assert devices == []

    @pytest.mark.asyncio
    async def test_register_device_mock_mode(self):
        """Test register_device in mock mode."""
        controller = SmartPlugController(mock_mode=True)
        result = await controller.register_device("test_device", "192.168.1.100")
        assert result is True
        # Device should not be added in mock mode
        assert "test_device" not in controller._plugs

    @pytest.mark.asyncio
    async def test_register_device_real_mode(self):
        """Test register_device in real mode."""
        controller = SmartPlugController(mock_mode=False)

        # Mock the kasa SmartPlug
        with patch('src.controllers.smart_plug_controller.SmartPlug') as mock_smart_plug:
            mock_plug_instance = AsyncMock()
            mock_smart_plug.return_value = mock_plug_instance
            mock_plug_instance.update = AsyncMock()

            result = await controller.register_device("test_device", "192.168.1.100")

            assert result is True
            assert "test_device" in controller._plugs
            mock_smart_plug.assert_called_once_with("192.168.1.100")
            mock_plug_instance.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_device_real_mode_failure(self):
        """Test register_device failure in real mode."""
        controller = SmartPlugController(mock_mode=False)

        # Mock the kasa SmartPlug to raise an exception
        with patch('src.controllers.smart_plug_controller.SmartPlug') as mock_smart_plug:
            mock_smart_plug.side_effect = Exception("Connection failed")

            result = await controller.register_device("test_device", "192.168.1.100")

            assert result is False
            assert "test_device" not in controller._plugs
