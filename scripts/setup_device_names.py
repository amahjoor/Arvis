#!/usr/bin/env python3
"""
Helper script to discover devices and generate device name mappings.

Run this script to see your discovered devices and get the IP addresses
to add to DEVICE_NAME_MAP in src/config.py
"""

import asyncio
from kasa import Discover


async def discover_devices():
    """Discover all Kasa devices and show their details."""
    print("🔍 Discovering Kasa devices...")
    print("=" * 60)
    
    try:
        devices = await asyncio.wait_for(Discover.discover(), timeout=10.0)
        
        if not devices:
            print("❌ No devices found on network")
            return
        
        print(f"\n✅ Found {len(devices)} device(s):\n")
        
        for addr, dev in devices.items():
            try:
                await dev.update()
                alias = dev.alias or "None"
                model = getattr(dev, 'model', 'Unknown')
                mac = getattr(dev, 'mac', 'Unknown')
                is_on = getattr(dev, 'is_on', None)
                
                print(f"📍 Device: {alias}")
                print(f"   IP Address: {addr}")
                print(f"   MAC Address: {mac}")
                print(f"   Model: {model}")
                print(f"   Status: {'ON' if is_on else 'OFF'}")
                
                # Check if it's a plug
                has_plug = hasattr(dev, 'turn_on') and hasattr(dev, 'turn_off')
                print(f"   Type: {'Smart Plug' if has_plug else 'Other Device'}")
                
                # Suggest friendly name
                if alias and alias != "None":
                    friendly_id = alias.lower().replace("-", "").replace(" ", "_")
                    print(f"   Suggested ID: {friendly_id}")
                else:
                    friendly_id = model.lower().replace("-", "").replace(" ", "_")
                    print(f"   Suggested ID: {friendly_id}")
                
                print(f"\n   Add to DEVICE_NAME_MAP in src/config.py:")
                print(f'   "{addr}": "your_friendly_name",')
                print()
                print("-" * 60)
                print()
                
            except Exception as e:
                print(f"❌ Error processing device {addr}: {e}")
                print()
        
        print("\n💡 Example DEVICE_NAME_MAP configuration:")
        print("=" * 60)
        print("DEVICE_NAME_MAP = {")
        print('    "10.0.0.95": "light",')
        print('    "10.0.0.93": "air_purifier",')
        print("}")
        print()
        print("Then you can say: 'Arvis, turn on the light'")
        
    except asyncio.TimeoutError:
        print("❌ Discovery timed out after 10 seconds")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(discover_devices())

