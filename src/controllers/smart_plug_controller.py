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
            from kasa import SmartPlug, Discover, SmartDevice

            logger.info("Discovering Kasa smart plugs...")
            try:
                # Add timeout to discovery
                devices = await asyncio.wait_for(Discover.discover(), timeout=10.0)
                logger.info(f"Discovered {len(devices)} device(s) total")
            except asyncio.TimeoutError:
                logger.error("Device discovery timed out after 10 seconds")
                return
            except Exception as e:
                logger.error(f"Discovery failed: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                return

            for addr, dev in devices.items():
                try:
                    logger.info(f"Processing device: {addr}, type: {type(dev).__name__}, alias: {getattr(dev, 'alias', None)}")
                    
                    # Check if device has plug capabilities (can turn on/off)
                    has_turn_on = hasattr(dev, 'turn_on')
                    has_turn_off = hasattr(dev, 'turn_off')
                    logger.info(f"  Device {addr} - has turn_on: {has_turn_on}, has turn_off: {has_turn_off}")
                    
                    if not has_turn_on or not has_turn_off:
                        logger.info(f"  Skipping device {addr} - doesn't have plug capabilities")
                        continue

                    # Use the discovered device directly if it has plug capabilities
                    # No need to reconnect - the device is already discovered and connected
                    plug = dev
                    
                    # Try to update device info to get alias/model, but don't fail if it errors
                    alias = None
                    model = None
                    try:
                        await plug.update()
                        alias = plug.alias
                        model = getattr(plug, 'model', None)
                        logger.info(f"  Updated device {addr} - alias: {alias}, model: {model}")
                    except Exception as e:
                        logger.warning(f"Failed to update device {addr} (will use fallback name): {e}")
                        # Try to get model/alias without update
                        alias = getattr(plug, 'alias', None)
                        model = getattr(plug, 'model', None)

                    # Use device alias/name you set in Kasa app, or model name as fallback
                    if not alias:
                        alias = model or f"device_{addr.replace('.', '_')}"
                    # Normalize: lowercase, remove hyphens/spaces, convert spaces to underscores
                    device_id = alias.lower().replace("-", "").replace(" ", "_")
                    # "Record Player" → "record_player"
                    # "KP125M" → "kp125m"
                    # "KP-125M" → "kp125m"
                    # "device_10_0_0_95" → "device_10_0_0_95"

                    self._plugs[device_id] = plug
                    logger.info(
                        f"✅ Found smart plug: {alias} ({addr}) → {device_id}"
                    )
                except Exception as e:
                    logger.error(f"Error processing device {addr}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue

            if not self._plugs:
                logger.warning("No Kasa smart plugs found on network")
            else:
                logger.info(f"Discovered {len(self._plugs)} smart plug(s)")

        except ImportError:
            logger.error("python-kasa not available - cannot control smart plugs")
            logger.error("Install with: pip install python-kasa")
            # Don't change mock_mode - let it fail explicitly if hardware is expected
        except Exception as e:
            logger.error(f"Failed to discover smart plugs: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            # Don't change mock_mode - discovery failure doesn't mean we should mock

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
