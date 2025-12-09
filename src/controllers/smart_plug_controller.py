"""
Smart Plug Controller for TP-Link Kasa devices.

Controls smart plugs via local network API using python-kasa.
"""

import asyncio
from typing import Dict, Optional, Any
from loguru import logger

from src.config import MOCK_HARDWARE, DEVICE_NAME_MAP


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
        self._device_ips: Dict[str, str] = {}  # device_id -> IP address (for reconnection)
        self._discovery_complete = asyncio.Event()  # Signal when discovery is done
        self._discovery_task: Optional[asyncio.Task] = None

        if not mock_mode:
            # Discover plugs asynchronously on init
            self._discovery_task = asyncio.create_task(self._discover_plugs())

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
                self._discovery_complete.set()  # Signal completion even on timeout
                return
            except Exception as e:
                logger.error(f"Discovery failed: {e}")
                import traceback
                logger.debug(traceback.format_exc())
                self._discovery_complete.set()  # Signal completion even on error
                return

            # Track device names to handle duplicates
            device_name_counts: Dict[str, int] = {}
            discovered_devices: list[tuple[str, Any, str, str]] = []  # (device_id, plug, display_name, ip_address)
            
            # First pass: collect all devices and determine their names
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

                    plug = dev
                    
                    # Try to update device info to get alias/model, but don't fail if it errors
                    alias = None
                    model = None
                    mac = None
                    try:
                        await plug.update()
                        alias = plug.alias
                        model = getattr(plug, 'model', None)
                        mac = getattr(plug, 'mac', None)
                        logger.info(f"  Updated device {addr} - alias: {alias}, model: {model}, mac: {mac}")
                    except Exception as e:
                        logger.warning(f"Failed to update device {addr} (will use fallback name): {e}")
                        alias = getattr(plug, 'alias', None)
                        model = getattr(plug, 'model', None)
                        mac = getattr(plug, 'mac', None)

                    # Check for configured friendly name (by IP or MAC)
                    friendly_name = None
                    if addr in DEVICE_NAME_MAP:
                        friendly_name = DEVICE_NAME_MAP[addr]
                        logger.info(f"  Using configured name from IP: {friendly_name}")
                    elif mac and mac in DEVICE_NAME_MAP:
                        friendly_name = DEVICE_NAME_MAP[mac]
                        logger.info(f"  Using configured name from MAC: {friendly_name}")
                    
                    # Use friendly name, Kasa app alias, or model name as fallback
                    if friendly_name:
                        base_name = friendly_name
                    elif alias:
                        base_name = alias
                    else:
                        base_name = model or f"device_{addr.replace('.', '_')}"
                    
                    # Normalize: lowercase, remove hyphens/spaces, convert spaces to underscores
                    base_device_id = base_name.lower().replace("-", "").replace(" ", "_")
                    
                    # Track this base name
                    device_name_counts[base_device_id] = device_name_counts.get(base_device_id, 0) + 1
                    
                    display_name = friendly_name or alias or model or base_device_id
                    discovered_devices.append((base_device_id, plug, display_name, addr))
                    
                except Exception as e:
                    logger.error(f"Error processing device {addr}: {e}")
                    import traceback
                    logger.debug(traceback.format_exc())
                    continue
            
            # Second pass: assign final device IDs, handling duplicates
            seen_base_names: Dict[str, int] = {}
            for base_device_id, plug, display_name, addr in discovered_devices:
                # If we have duplicates of this name, number them
                if device_name_counts[base_device_id] > 1:
                    # Count how many of this base name we've seen so far
                    seen_count = seen_base_names.get(base_device_id, 0) + 1
                    seen_base_names[base_device_id] = seen_count
                    device_id = f"{base_device_id}_{seen_count}"
                else:
                    device_id = base_device_id
                
                self._plugs[device_id] = plug
                self._device_ips[device_id] = addr  # Store IP for reconnection
                logger.info(f"✅ Found smart plug: {display_name} ({addr}) → {device_id}")

            if not self._plugs:
                logger.warning("No Kasa smart plugs found on network")
            else:
                logger.info(f"Discovered {len(self._plugs)} smart plug(s)")
            
            # Signal that discovery is complete
            self._discovery_complete.set()

        except ImportError:
            logger.error("python-kasa not available - cannot control smart plugs")
            logger.error("Install with: pip install python-kasa")
            self._discovery_complete.set()  # Signal completion even on error
        except Exception as e:
            logger.error(f"Failed to discover smart plugs: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            self._discovery_complete.set()  # Signal completion even on error

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
            self._device_ips[device_id] = ip_address  # Store IP for reconnection
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

        # Wait for discovery to complete (with timeout)
        if not self._discovery_complete.is_set():
            logger.info(f"Waiting for device discovery to complete...")
            try:
                await asyncio.wait_for(self._discovery_complete.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Device discovery timed out, proceeding anyway")

        device_ip = self._device_ips.get(device_id)
        if device_ip is None:
            logger.error(f"Smart plug not found: {device_id}. Available: {list(self._plugs.keys())}")
            return False

        try:
            # Get device info for logging
            device_model = 'Unknown'
            try:
                old_plug = self._plugs.get(device_id)
                if old_plug:
                    device_model = getattr(old_plug, 'model', 'Unknown')
            except:
                pass
            
            logger.info(f"  Controlling device: {device_id} @ {device_ip} ({device_model})")
            
            # Try using discovered device first (it connects via UDP discovery)
            plug = self._plugs.get(device_id)
            if plug:
                try:
                    logger.info(f"  Using discovered device object for {device_id}")
                    await asyncio.wait_for(plug.update(), timeout=5.0)
                    logger.info(f"  Connected to device {device_id} @ {device_ip}")
                    fresh_plug = plug
                except Exception as e:
                    logger.warning(f"  Discovered device failed: {e}, trying SmartPlug connection")
                    plug = None
            
            # If discovered device doesn't work, try creating SmartPlug connection
            if not plug:
                logger.info(f"  Creating SmartPlug connection to {device_id} @ {device_ip}")
                from kasa import SmartPlug
                fresh_plug = SmartPlug(device_ip)
                
                try:
                    await asyncio.wait_for(fresh_plug.update(), timeout=5.0)
                    logger.info(f"  Connected to device {device_id} @ {device_ip}")
                except asyncio.TimeoutError:
                    logger.error(f"  Connection to {device_id} @ {device_ip} timed out")
                    logger.error(f"  This usually means the device is unreachable or on a different network")
                    return False
                except Exception as conn_error:
                    logger.error(f"  Failed to connect to {device_id} @ {device_ip}: {conn_error}")
                    logger.error(f"  Make sure the device is on the same network and port 9999 is not blocked")
                    return False
            
            # Get current state before turning on
            was_on = fresh_plug.is_on
            logger.info(f"  Device {device_id} current state: {'ON' if was_on else 'OFF'}")
            
            # Turn on the device
            logger.info(f"  Sending turn_on() command to {device_id}...")
            try:
                await fresh_plug.turn_on()
                logger.info(f"  turn_on() command completed")
            except Exception as cmd_error:
                logger.error(f"  Failed to execute turn_on() command: {cmd_error}")
                return False
            
            # Verify the device actually turned on
            await asyncio.sleep(1.5)  # Give device more time to respond
            try:
                await fresh_plug.update()
                is_now_on = fresh_plug.is_on
                logger.info(f"  Device {device_id} state after command: {'ON' if is_now_on else 'OFF'}")
            except Exception as verify_error:
                logger.error(f"  Failed to verify state: {verify_error}")
                is_now_on = None
            
            # Update the stored plug reference
            self._plugs[device_id] = fresh_plug
            
            if is_now_on:
                logger.info(f"🔌 Turned ON: {device_id} (verified: was {'ON' if was_on else 'OFF'} → now ON)")
                return True
            else:
                logger.warning(f"⚠️ Turn ON command sent to {device_id}, but device is still OFF (was {'ON' if was_on else 'OFF'})")
                logger.warning(f"  Device IP: {device_ip}, Model: {device_model}")
                logger.warning(f"  This might indicate a network issue or device unresponsiveness")
                return False
        except Exception as e:
            logger.error(f"Failed to turn on {device_id}: {e}")
            logger.error(f"  Device IP: {device_ip if 'device_ip' in locals() else 'Unknown'}")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    async def turn_off(self, device_id: str) -> bool:
        """Turn off a smart plug."""
        if self._mock_mode:
            logger.info(f"🔌 [MOCK] Turn OFF: {device_id}")
            return True

        # Wait for discovery to complete (with timeout)
        if not self._discovery_complete.is_set():
            logger.info(f"Waiting for device discovery to complete...")
            try:
                await asyncio.wait_for(self._discovery_complete.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Device discovery timed out, proceeding anyway")

        device_ip = self._device_ips.get(device_id)
        if device_ip is None:
            logger.error(f"Smart plug not found: {device_id}. Available: {list(self._plugs.keys())}")
            return False

        try:
            # Get device info for logging
            device_model = 'Unknown'
            try:
                old_plug = self._plugs.get(device_id)
                if old_plug:
                    device_model = getattr(old_plug, 'model', 'Unknown')
            except:
                pass
            
            logger.info(f"  Controlling device: {device_id} @ {device_ip} ({device_model})")
            
            # Try using discovered device first (it connects via UDP discovery)
            plug = self._plugs.get(device_id)
            if plug:
                try:
                    logger.info(f"  Using discovered device object for {device_id}")
                    await asyncio.wait_for(plug.update(), timeout=5.0)
                    logger.info(f"  Connected to device {device_id} @ {device_ip}")
                    fresh_plug = plug
                except Exception as e:
                    logger.warning(f"  Discovered device failed: {e}, trying SmartPlug connection")
                    plug = None
            
            # If discovered device doesn't work, try creating SmartPlug connection
            if not plug:
                logger.info(f"  Creating SmartPlug connection to {device_id} @ {device_ip}")
                from kasa import SmartPlug
                fresh_plug = SmartPlug(device_ip)
                
                try:
                    await asyncio.wait_for(fresh_plug.update(), timeout=5.0)
                    logger.info(f"  Connected to device {device_id} @ {device_ip}")
                except asyncio.TimeoutError:
                    logger.error(f"  Connection to {device_id} @ {device_ip} timed out")
                    logger.error(f"  This usually means the device is unreachable or on a different network")
                    return False
                except Exception as conn_error:
                    logger.error(f"  Failed to connect to {device_id} @ {device_ip}: {conn_error}")
                    logger.error(f"  Make sure the device is on the same network and port 9999 is not blocked")
                    return False
            
            # Get current state before turning off
            was_on = fresh_plug.is_on
            logger.info(f"  Device {device_id} current state: {'ON' if was_on else 'OFF'}")
            
            # Turn off the device
            logger.info(f"  Sending turn_off() command to {device_id}...")
            try:
                await fresh_plug.turn_off()
                logger.info(f"  turn_off() command completed")
            except Exception as cmd_error:
                logger.error(f"  Failed to execute turn_off() command: {cmd_error}")
                return False
            
            # Verify the device actually turned off
            await asyncio.sleep(1.5)  # Give device more time to respond
            try:
                await fresh_plug.update()
                is_now_on = fresh_plug.is_on
                logger.info(f"  Device {device_id} state after command: {'ON' if is_now_on else 'OFF'}")
            except Exception as verify_error:
                logger.error(f"  Failed to verify state: {verify_error}")
                is_now_on = None
            
            # Update the stored plug reference
            self._plugs[device_id] = fresh_plug
            
            if not is_now_on:
                logger.info(f"🔌 Turned OFF: {device_id} (verified: was {'ON' if was_on else 'OFF'} → now OFF)")
                return True
            else:
                logger.warning(f"⚠️ Turn OFF command sent to {device_id}, but device is still ON (was {'ON' if was_on else 'OFF'})")
                logger.warning(f"  Device IP: {device_ip}, Model: {device_model}")
                logger.warning(f"  This might indicate a network issue or device unresponsiveness")
                return False
        except Exception as e:
            logger.error(f"Failed to turn off {device_id}: {e}")
            logger.error(f"  Device IP: {device_ip if 'device_ip' in locals() else 'Unknown'}")
            import traceback
            logger.debug(traceback.format_exc())
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
