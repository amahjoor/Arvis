# Arvis Intents Module
# Intent handlers for voice commands

from src.intents.lights import register_light_handlers
from src.intents.presence import register_presence_handlers
from src.intents.chat import register_chat_handlers

__all__ = ["register_light_handlers", "register_presence_handlers", "register_chat_handlers"]
