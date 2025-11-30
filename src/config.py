"""
Arvis Configuration Module

Paths, thresholds, API keys, and room layout zones.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# =============================================================================
# Paths
# =============================================================================
PROJECT_ROOT = Path(__file__).parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FX_DIR = ASSETS_DIR / "fx"
LOGS_DIR = PROJECT_ROOT / "logs"

# =============================================================================
# API Keys (loaded from .env)
# =============================================================================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

# =============================================================================
# Audio Settings
# =============================================================================
SAMPLE_RATE = 16000  # 16kHz for speech
CHANNELS = 1
CHUNK_SIZE = 1024

# Wake word
WAKE_WORD = "arvis"

# =============================================================================
# Presence Detection
# =============================================================================
# PIR sensor settings
PIR_GPIO_PIN = 17  # BCM pin number
ROOM_EMPTY_TIMEOUT_MINUTES = 10  # Minutes of no motion before room is EMPTY

# =============================================================================
# Wake Word Detection
# =============================================================================
WAKE_WORD_SENSITIVITY = 0.5  # 0.0-1.0, balanced detection

# =============================================================================
# Vision Settings
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
LED_COUNT = 60
LED_PIN = 18  # GPIO pin (PWM)
LED_BRIGHTNESS = 255

# =============================================================================
# Scenes
# =============================================================================
SCENES = {
    "entry": {
        "lights": {"state": "on", "color": [255, 180, 100], "brightness": 200},
        "fx": "welcome",
        "voice": "Welcome back, Arman.",
    },
    "focus": {
        "lights": {"state": "on", "color": [255, 255, 255], "brightness": 255},
        "spotify_playlist": "focus_playlist_id",
    },
    "cozy": {
        "lights": {"state": "on", "color": [255, 120, 50], "brightness": 150},
    },
    "sleep": {
        "lights": {"state": "off"},
        "fx": "sleep_chime",
    },
    "wake": {
        "lights": {"state": "on", "color": [255, 200, 150], "brightness": 100},
        "fx": "wake_tone",
    },
}

# =============================================================================
# LLM Settings
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
# Room State
# =============================================================================
class RoomState:
    EMPTY = "EMPTY"
    OCCUPIED = "OCCUPIED"
    SLEEP = "SLEEP"
    WAKE = "WAKE"

class Posture:
    LYING = "lying"
    SITTING = "sitting"
    STANDING = "standing"
    UNKNOWN = "unknown"

