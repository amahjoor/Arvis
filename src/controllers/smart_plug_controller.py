"""
Smart Plug Controller for TP-Link Kasa devices.

Controls smart plugs via local network API using python-kasa.
"""

import asyncio
from typing import Dict, Optional, Any
from loguru import logger

from src.config import MOCK_HARDWARE


class SmartPlugController:
    """
    Controls TP-Link Kasa smart plugs.

    In mock mode, logs actions instead of controlling hardware.
    In real mode, uses python-kasa library for local control.
    """

    def __init__(self, mock_mode: bool = MOCK_HARDWARE):
        """
        Initialize smart plug controller.

        Args:
            mock_mode: If True, log actions instead of controlling hardware
        """
        self._mock_mode = mock_mode
        self._plugs: Dict[str, Any] = {}  # device_id -> plug instance

        if not mock_mode:
            # Discover plugs asynchronously on init
            asyncio.create_task(self._discover_plugs())

        logger.info(
            f"SmartPlugController initialized (mock_mode={mock_mode})"
        )

    async def _discover_plugs(self) -> None:
        """Discover Kasa plugs on the network."""
        try:
            from kasa import SmartPlug, Discover

            logger.info("Discovering Kasa smart plugs...")
            devices = await Discover.discover()

            for addr, dev in devices.items():
                if isinstance(dev, SmartPlug):
                    # Use device alias/name you set in Kasa app
                    device_id = dev.alias.lower().replace(" ", "_")
                    # "Record Player" → "record_player"
                    # "Lamp" → "lamp"

                    self._plugs[device_id] = dev
                    logger.info(
                        f"Found smart plug: {dev.alias} ({addr}) → {device_id}"
                    )

            if not self._plugs:
                logger.warning("No Kasa smart plugs found on network")
            else:
                logger.info(f"Discovered {len(self._plugs)} smart plug(s)")

        except ImportError:
            logger.warning("python-kasa not available, falling back to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to discover smart plugs: {e}")
            self._mock_mode = True

    async def register_device(self, device_id: str, ip_address: str) -> bool:
        """
        Manually register a device by IP address.

        Useful if auto-discovery fails or you know the IP.

        Args:
            device_id: Identifier for this device (e.g., "record_player")
            ip_address: IP address of the plug

        Returns:
            True if successful, False otherwise
        """
        if self._mock_mode:
            logger.info(f"[MOCK] Registered device: {device_id} @ {ip_address}")
            return True

        try:
            from kasa import SmartPlug

            plug = SmartPlug(ip_address)
            await plug.update()  # Get device info

            self._plugs[device_id] = plug
            logger.info(f"Registered smart plug: {device_id} @ {ip_address} ({plug.alias})")
            return True
        except Exception as e:
            logger.error(f"Failed to register device {device_id}: {e}")
            return False

    async def turn_on(self, device_id: str) -> bool:
        """
        Turn on a smart plug.

        Args:
            device_id: Device identifier (e.g., "record_player")

        Returns:
            True if successful, False otherwise
        """
        if self._mock_mode:
            logger.info(f"🔌 [MOCK] Turn ON: {device_id}")
            return True

        plug = self._plugs.get(device_id)
        if plug is None:
            logger.error(f"Smart plug not found: {device_id}. Available: {list(self._plugs.keys())}")
            return False

        try:
            await plug.turn_on()
            logger.info(f"🔌 Turned ON: {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to turn on {device_id}: {e}")
            return False

    async def turn_off(self, device_id: str) -> bool:
        """Turn off a smart plug."""
        if self._mock_mode:
            logger.info(f"🔌 [MOCK] Turn OFF: {device_id}")
            return True

        plug = self._plugs.get(device_id)
        if plug is None:
            logger.error(f"Smart plug not found: {device_id}. Available: {list(self._plugs.keys())}")
            return False

        try:
            await plug.turn_off()
            logger.info(f"🔌 Turned OFF: {device_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to turn off {device_id}: {e}")
            return False

    async def is_on(self, device_id: str) -> Optional[bool]:
        """
        Check if a plug is on.

        Returns:
            True/False if device found, None if device not found
        """
        if self._mock_mode:
            return None

        plug = self._plugs.get(device_id)
        if plug is None:
            return None

        try:
            await plug.update()  # Refresh device state
            return plug.is_on
        except Exception as e:
            logger.error(f"Failed to check status of {device_id}: {e}")
            return None

    async def get_energy_usage(self, device_id: str) -> Optional[Dict[str, float]]:
        """
        Get energy usage data (if device supports it).

        Returns:
            Dict with 'power' (watts), 'voltage', 'current', etc. or None
        """
        if self._mock_mode:
            return None

        plug = self._plugs.get(device_id)
        if plug is None:
            return None

        try:
            await plug.update()
            if hasattr(plug, 'emeter_realtime'):
                return {
                    'power': plug.emeter_realtime.get('power', 0),
                    'voltage': plug.emeter_realtime.get('voltage', 0),
                    'current': plug.emeter_realtime.get('current', 0),
                }
        except Exception as e:
            logger.error(f"Failed to get energy usage for {device_id}: {e}")

        return None

    def list_devices(self) -> list:
        """Get list of registered device IDs."""
        return list(self._plugs.keys())
