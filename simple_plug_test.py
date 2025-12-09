#!/usr/bin/env python3
"""
Simple smart plug test - just test discovery and basic control.
"""

import asyncio
import sys
import os

async def test_discovery():
    """Test just the discovery part."""
    print("🔍 Testing Kasa device discovery...")

    try:
        # Try to import kasa directly
        import kasa
        from kasa import Discover
        print("✅ Kasa library imported successfully")

        print("📡 Broadcasting discovery request...")
        devices = await Discover.discover()

        print(f"📋 Found {len(devices)} device(s)")
        for addr, dev in devices.items():
            print(f"  • {dev.alias} ({addr}) - {type(dev).__name__}")

        if devices:
            print("✅ Discovery successful!")
            return True
        else:
            print("⚠️  No devices found")
            print("Make sure your smart plug is:")
            print("  - Powered on")
            print("  - On the same Wi-Fi network")
            print("  - Set up in the Kasa app")
            return False

    except ImportError:
        print("❌ Kasa library not available")
        print("This is expected if we're in the wrong Python environment")
        return False
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        return False

async def main():
    print("🧪 Simple Smart Plug Test")
    print("=" * 30)

    success = await test_discovery()

    print("\n" + "=" * 30)
    if success:
        print("✅ Your smart plug is discoverable!")
        print("🎉 Ready for Arvis integration!")
    else:
        print("❌ Issues found. Check setup and try again.")

if __name__ == "__main__":
    asyncio.run(main())
