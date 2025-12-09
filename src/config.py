"""
Arvis Configuration Module

Paths, thresholds, API keys, and room layout zones.
All configuration is centralized here for easy modification.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# =============================================================================
# Debug & Mock Settings
# =============================================================================
DEBUG = os.getenv("ARVIS_DEBUG", "false").lower() == "true"
MOCK_HARDWARE = os.getenv("ARVIS_MOCK_HARDWARE", "true").lower() == "true"

# =============================================================================
# Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
SRC_DIR = PROJECT_ROOT / "src"
ASSETS_DIR = PROJECT_ROOT / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)
SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# API Keys (loaded from .env)
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "")  # Not needed - using OpenWakeWord
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

# =============================================================================
# Audio Settings
# =============================================================================
SAMPLE_RATE = 16000  # 16kHz for speech recognition
CHANNELS = 1         # Mono
CHUNK_SIZE = 1024    # Audio buffer size

# Recording settings
MAX_RECORDING_SECONDS = 10  # Max recording duration after wake word
SILENCE_THRESHOLD = 500     # Energy threshold for silence detection
SILENCE_DURATION = 3.0      # Seconds of silence before stopping recording

# =============================================================================
# Wake Word Detection (OpenWakeWord)
# =============================================================================
WAKE_WORD = "arvis"
WAKE_WORD_SENSITIVITY = 0.5  # 0.0-1.0, threshold for detection

# Custom wake word model path (.onnx file)
# Trained via OpenWakeWord Colab notebook
# Set to None to use pre-trained "hey_jarvis" model
WAKE_WORD_MODEL_PATH = ASSETS_DIR / "wake_words" / "arvis.onnx"

# =============================================================================
# Presence Detection (PIR Sensor)
# =============================================================================
PIR_GPIO_PIN = 17  # BCM pin number (GPIO17 = physical pin 11)
PIR_DEBOUNCE_SECONDS = 2.0  # Minimum time between motion events
ROOM_EMPTY_TIMEOUT_MINUTES = 10  # Minutes of no motion before room is EMPTY

# =============================================================================
# Vision Settings (Camera)
# =============================================================================
CAMERA_INDEX = 0  # Default camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 15

# Sleep detection
SLEEP_DETECTION_MINUTES = 10  # Minutes of lying still before SLEEP state

# Zone definitions (normalized coordinates 0-1)
# Adjust these based on your camera angle and room layout
ZONES = {
    "bed": {"x_min": 0.0, "x_max": 0.5, "y_min": 0.5, "y_max": 1.0},
    "floor": {"x_min": 0.0, "x_max": 1.0, "y_min": 0.0, "y_max": 0.5},
    "desk": {"x_min": 0.5, "x_max": 1.0, "y_min": 0.5, "y_max": 1.0},
}

# =============================================================================
# LED Settings
# =============================================================================
LED_COUNT = 300       # Total LEDs in strip (5m * 60 LED/m)
LED_PIN = 18          # GPIO pin (PWM)
LED_BRIGHTNESS = 255  # Max brightness (0-255)
LED_FREQ_HZ = 800000  # LED signal frequency

# =============================================================================
# Smart Plug Device Mapping
# =============================================================================
# Map device IP addresses or MAC addresses to friendly names
# Format: "ip_address": "friendly_name" or "mac_address": "friendly_name"
# If a device isn't in this map, it will use its Kasa app alias or model name
# If multiple devices have the same name, they'll be numbered (e.g., "kp125m_1", "kp125m_2")
DEVICE_NAME_MAP = {
    # Example mappings (update with your actual device IPs):
    # "10.0.0.95": "light",
    # "10.0.0.93": "air_purifier",
    # Or use MAC addresses:
    # "AA:BB:CC:DD:EE:FF": "record_player",
    "10.0.0.95": "air_purifier",  # Swapped - this IP is actually the air purifier
    "10.0.0.93": "light",         # Swapped - this IP is actually the light
}

# =============================================================================
# LLM / AI Settings
# =============================================================================
LLM_MODEL = "gpt-4o-mini"
STT_MODEL = "whisper-1"
TTS_MODEL = "tts-1"
TTS_VOICE = "onyx"  # Deep, calm male voice

# Latency targets (seconds)
VOICE_ROUNDTRIP_TARGET = 2.5
PIR_RESPONSE_TARGET = 0.5
VISION_ALARM_TARGET = 1.0

# =============================================================================
# Scene Definitions
# =============================================================================
# Colors in hex format
SCENES = {
    "welcome": {
        "color": "#FFD700",      # Gold
        "brightness": 0.7,
        "animation": "golden_shimmer",
        "voice": "Welcome back, Arman.",
    },
    "focus": {
        "color": "#FFFFFF",      # Cool white
        "brightness": 1.0,
        "animation": None,
        "voice": "Focus mode.",
    },
    "night": {
        "color": "#FFB347",      # Warm amber
        "brightness": 0.3,
        "animation": None,
        "voice": "Night mode.",
    },
    "sleep": {
        "color": "#000000",      # Off
        "brightness": 0.0,
        "animation": "fade_out",
        "voice": None,           # Silent transition
    },
    "wake": {
        "color": "#FFECD2",      # Warm sunrise
        "brightness": 0.5,
        "animation": "sunrise",
        "voice": "Good morning, Arman.",
    },
    "exit": {
        "color": "#000000",      # Off
        "brightness": 0.0,
        "animation": "fade_out",
        "voice": "Goodbye.",
    },
}

# =============================================================================
# Smart Plug Configuration
# =============================================================================
# Devices will auto-discover, but you can manually register by IP if needed
SMART_PLUG_DEVICES = {
    # "record_player": {
    #     "ip": "192.168.1.100",  # Optional: specify IP if auto-discovery fails
    #     "alias": "Record Player",  # Friendly name in Kasa app
    # },
    # "lamp": {
    #     "ip": "192.168.1.101",
    #     "alias": "Lamp",
    # },
}

# =============================================================================
# Error Messages (Arvis persona - minimal, calm)
# =============================================================================
ERROR_MESSAGES = {
    "not_understood": "I didn't catch that.",
    "offline": "I'm offline.",
    "not_supported": "I can't do that.",
    "error": "Something went wrong.",
    "back_online": "I'm back online.",
}

# =============================================================================
# Posture Detection
# =============================================================================
class Posture:
    """Posture states detected by vision system."""
    LYING = "lying"
    SITTING = "sitting"
    STANDING = "standing"
    UNKNOWN = "unknown"
