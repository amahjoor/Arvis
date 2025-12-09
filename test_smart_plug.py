#!/usr/bin/env python3
"""
Simple test script for smart plug functionality.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Test just the core components without full imports
async def test_basic_functionality():
    """Test basic smart plug functionality."""
    print("Testing basic smart plug functionality...")

    try:
        # Test python-kasa import
        from kasa import Discover
        print("✓ python-kasa import successful")

        # Test mock SmartPlugController
        from src.controllers.smart_plug_controller import SmartPlugController
        print("✓ SmartPlugController import successful")

        controller = SmartPlugController(mock_mode=True)
        print("✓ SmartPlugController initialization successful")

        # Test device handlers
        from src.intents.devices import register_device_handlers
        print("✓ Device handlers import successful")

        print("\n✅ All basic imports and initializations successful!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_basic_functionality())
