#!/usr/bin/env python3
"""
Quick microphone test script.

Run this to verify your mic is working before testing wake word.

Usage:
    python scripts/test_mic.py
"""

import sys
sys.path.insert(0, ".")

import sounddevice as sd
import numpy as np

print("🎤 Microphone Test")
print("=" * 40)

# List audio devices
print("\nAvailable audio devices:")
print(sd.query_devices())

print("\n" + "=" * 40)
print("Recording 3 seconds of audio...")
print("Speak now!")

# Record
duration = 3  # seconds
sample_rate = 16000
audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype=np.int16)
sd.wait()

# Analyze
energy = np.abs(audio).mean()
max_amplitude = np.abs(audio).max()

print(f"\n✅ Recording complete!")
print(f"   Average energy: {energy:.1f}")
print(f"   Max amplitude: {max_amplitude}")
print(f"   Samples: {len(audio)}")

if energy < 100:
    print("\n⚠️  Audio seems quiet. Check your microphone!")
else:
    print("\n🎉 Microphone working! Ready for Arvis.")

