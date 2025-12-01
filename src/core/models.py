"""
Arvis Core Data Models

Defines the fundamental data structures used throughout the system:
- RoomState: Enum for room occupancy states
- Event: Sensor/agent-produced events
- Intent: Action requests for the system
- Scene: Lighting/audio scene configurations
- LightConfig: LED strip configuration
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class RoomState(Enum):
    """Room occupancy and activity states."""
    
    EMPTY = "empty"           # No one in room
    OCCUPIED = "occupied"     # Someone present, awake
    SLEEP = "sleep"           # User sleeping
    WAKE = "wake"             # Alarm active, waking up


@dataclass
class Event:
    """
    Represents an event produced by sensors or agents.
    
    Events are immutable once created and flow through the EventBus
    to be processed by subscribers.
    
    Attributes:
        type: Event type in dot notation (e.g., "presence.motion_detected")
        payload: Event-specific data dictionary
        timestamp: When the event occurred
        source: Which agent/component produced the event
    """
    
    type: str
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "unknown"
    
    def __post_init__(self):
        """Ensure payload is a dict."""
        if self.payload is None:
            self.payload = {}


@dataclass
class Intent:
    """
    Represents an action request to be executed.
    
    Intents are produced by the IntentRouter based on events
    and consumed by the ActionExecutor.
    
    Attributes:
        action: Intent action in dot notation (e.g., "lights.on", "audio.say")
        params: Action-specific parameters
        priority: Higher priority intents are executed first (default: 0)
        source: What generated this intent (e.g., "voice", "presence", "vision")
        raw_text: Original transcribed text (for voice intents)
    """
    
    action: str
    params: dict = field(default_factory=dict)
    priority: int = 0
    source: str = "unknown"
    raw_text: Optional[str] = None
    
    def __post_init__(self):
        """Ensure params is a dict."""
        if self.params is None:
            self.params = {}


@dataclass
class LightConfig:
    """
    LED strip configuration.
    
    Attributes:
        color: Hex color string (e.g., "#FFD700") or RGB tuple
        brightness: 0.0 to 1.0
    """
    
    color: str = "#FFFFFF"
    brightness: float = 1.0
    
    def __post_init__(self):
        """Validate brightness range."""
        self.brightness = max(0.0, min(1.0, self.brightness))
    
    @property
    def rgb(self) -> tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        color = self.color.lstrip("#")
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))


@dataclass
class Scene:
    """
    Lighting and audio scene configuration.
    
    Scenes define the state of lights and optional audio
    for specific situations (welcome, focus, sleep, etc.)
    
    Attributes:
        id: Unique scene identifier
        lights: LED configuration
        voice: Optional TTS message to speak
        animation: Optional LED animation name
    """
    
    id: str
    lights: LightConfig = field(default_factory=LightConfig)
    voice: Optional[str] = None
    animation: Optional[str] = None

