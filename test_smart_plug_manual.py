#!/usr/bin/env python3
"""
Manual test script for smart plug functionality with real hardware.
Run this to test your Kasa smart plug integration.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_kasa_discovery():
    """Test Kasa device discovery."""
    print("🔍 Testing Kasa device discovery...")

    try:
        from kasa import Discover
        print("✅ Kasa library imported successfully")

        print("📡 Broadcasting discovery request...")
        devices = await Discover.discover()
        print(f"📋 Found {len(devices)} device(s)")

        for addr, dev in devices.items():
            print(f"  • {dev.alias} ({addr}) - Type: {type(dev).__name__}")

        if not devices:
            print("⚠️  No devices found. Make sure:")
            print("   - Your smart plug is powered on")
            print("   - It's on the same Wi-Fi network as this computer")
            print("   - It's set up in the Kasa app")
            return False

        return True

    except ImportError as e:
        print(f"❌ Failed to import Kasa library: {e}")
        print("Run: pip install python-kasa")
        return False
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return False

async def test_smart_plug_controller():
    """Test SmartPlugController with real hardware."""
    print("\n🔧 Testing SmartPlugController...")

    try:
        from src.controllers.smart_plug_controller import SmartPlugController
        print("✅ SmartPlugController imported successfully")

        # Create controller (will auto-discover)
        print("🏗️  Initializing SmartPlugController...")
        controller = SmartPlugController(mock_mode=False)

        # Wait a bit for discovery to complete
        print("⏳ Waiting for device discovery...")
        await asyncio.sleep(3)

        devices = controller.list_devices()
        print(f"📋 Controller found {len(devices)} device(s): {devices}")

        if not devices:
            print("⚠️  No devices in controller. Discovery may have failed.")
            return False

        # Test the first device
        device_id = devices[0]
        print(f"🧪 Testing device: {device_id}")

        # Test status check
        print("📊 Checking device status...")
        is_on = await controller.is_on(device_id)
        if is_on is not None:
            print(f"   Status: {'ON' if is_on else 'OFF'}")
        else:
            print("   Status: Unknown (device not found)")

        # Test turn on
        print("🔄 Testing turn ON...")
        result = await controller.turn_on(device_id)
        print(f"   Turn ON result: {'SUCCESS' if result else 'FAILED'}")

        await asyncio.sleep(2)  # Wait a bit

        # Test status again
        is_on_after = await controller.is_on(device_id)
        if is_on_after is not None:
            print(f"   Status after ON: {'ON' if is_on_after else 'OFF'}")

        # Test turn off
        print("🔄 Testing turn OFF...")
        result = await controller.turn_off(device_id)
        print(f"   Turn OFF result: {'SUCCESS' if result else 'FAILED'}")

        await asyncio.sleep(2)  # Wait a bit

        # Final status check
        is_on_final = await controller.is_on(device_id)
        if is_on_final is not None:
            print(f"   Final status: {'ON' if is_on_final else 'OFF'}")

        return True

    except Exception as e:
        print(f"❌ SmartPlugController test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_intent_handlers():
    """Test device intent handlers."""
    print("\n🎯 Testing device intent handlers...")

    try:
        from src.core.intent_router import IntentRouter, HandlerContext
        from src.intents.devices import register_device_handlers
        from src.core.models import Intent

        # Mock components for testing
        class MockAudioController:
            def __init__(self):
                self.messages = []
            def say(self, text):
                self.messages.append(text)
                print(f"🗣️  Audio: {text}")

        class MockEventBus:
            def subscribe(self, *args): pass
            def publish(self, *args): pass

        # Create real SmartPlugController
        from src.controllers.smart_plug_controller import SmartPlugController
        controller = SmartPlugController(mock_mode=False)
        await asyncio.sleep(3)  # Wait for discovery

        devices = controller.list_devices()
        if not devices:
            print("⚠️  No devices found for intent testing")
            return False

        # Setup intent router
        audio = MockAudioController()
        context = HandlerContext(
            led_controller=None,
            audio_controller=audio,
            state_manager=None,
            event_bus=MockEventBus(),
            smart_plug_controller=controller,
        )

        router = IntentRouter(MockEventBus(), context)
        register_device_handlers(router)

        # Test intents
        device_id = devices[0]
        test_intents = [
            Intent(action="device.on", params={"device": device_id}, raw_text=f"turn on the {device_id}"),
            Intent(action="device.status", params={"device": device_id}, raw_text=f"is the {device_id} on"),
            Intent(action="device.off", params={"device": device_id}, raw_text=f"turn off the {device_id}"),
        ]

        for intent in test_intents:
            print(f"🎯 Testing intent: {intent.action} for {device_id}")
            result = await router.route(intent)
            print(f"   Result: {'SUCCESS' if result else 'FAILED'}")
            await asyncio.sleep(1)  # Brief pause between tests

        print("📝 Audio messages sent:")
        for msg in audio.messages:
            print(f"   • {msg}")

        return True

    except Exception as e:
        print(f"❌ Intent handler test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests."""
    print("🚀 Smart Plug Integration Test")
    print("=" * 50)

    # Test 1: Kasa library and discovery
    discovery_ok = await test_kasa_discovery()

    if not discovery_ok:
        print("\n❌ Discovery test failed. Cannot continue with other tests.")
        return

    # Test 2: SmartPlugController
    controller_ok = await test_smart_plug_controller()

    # Test 3: Intent handlers
    if controller_ok:
        await test_intent_handlers()

    print("\n" + "=" * 50)
    print("🏁 Testing complete!")

    if discovery_ok and controller_ok:
        print("✅ Basic functionality tests passed!")
        print("🎉 Your smart plug is ready to use with Arvis!")
    else:
        print("❌ Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    asyncio.run(main())
