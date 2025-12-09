"""
LLM Backend using OpenAI GPT-4o-mini.

Extracts user intent from transcribed text.
"""

import json
import time
from datetime import datetime
from typing import Optional

from loguru import logger
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError

from src.config import OPENAI_API_KEY, LLM_MODEL
from src.core.models import Intent, RoomState


# System prompt for intent extraction
# Note: Double braces {{ }} are escaped braces in Python .format()
SYSTEM_PROMPT = """You are Arvis, a room assistant. Extract the user's intent from their voice command.

Current room state: {state}
Current time: {time}

Return a JSON object with:
- action: the intent action (e.g., "lights.on", "lights.scene", "timer.set", "chat.response")
- params: action-specific parameters

Known actions:
- lights.on, lights.off
- lights.scene (params: scene = "focus" | "night" | "wake")
- device.on (params: device = "record_player" | "lamp" | "fan" | ...)
- device.off (params: device = "record_player" | "lamp" | "fan" | ...)
- device.status (params: device = "record_player" | ...)
- timer.set (params: minutes)
- alarm.set (params: time in HH:MM)
- alarm.stop
- status.get
- room.cancel_sleep (when user says "I'm still awake")
- chat.response (params: message = "Yes, I can hear you." | "I'm here." | etc.) - Use this for conversational queries like "Can you hear me?", "Are you there?", greetings, or casual questions

For conversational queries (greetings, status checks, casual questions), use chat.response with a brief, natural response.

If you cannot understand the command, return:
{{"action": "clarify", "params": {{"message": "I didn't catch that."}}}}

IMPORTANT: Return ONLY valid JSON, no additional text."""


class LLMBackend:
    """Handles intent extraction using OpenAI GPT-4o-mini."""
    
    def __init__(self, mock_mode: bool = False):
        """
        Initialize LLM backend.
        
        Args:
            mock_mode: If True, return mock intents
        """
        self._mock_mode = mock_mode
        self._client: Optional[OpenAI] = None
        
        if not mock_mode:
            if not OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set in environment")
            self._client = OpenAI(api_key=OPENAI_API_KEY)
        
        logger.info(f"LLMBackend initialized (mock_mode={mock_mode})")
    
    def extract_intent(
        self, 
        text: str, 
        room_state: RoomState = RoomState.OCCUPIED
    ) -> Intent:
        """
        Extract intent from user text.
        
        Args:
            text: Transcribed user command
            room_state: Current state of the room
            
        Returns:
            Intent object with action and params
            
        Raises:
            RuntimeError: If intent extraction fails
        """
        if self._mock_mode:
            return self._mock_extract_intent(text)
        
        return self._real_extract_intent(text, room_state)
    
    def _mock_extract_intent(self, text: str) -> Intent:
        """Return mock intent for testing."""
        logger.debug(f"Mock extract intent: '{text}'")
        time.sleep(0.1)
        
        # Simple keyword matching for mock mode
        text_lower = text.lower()

        if "light" in text_lower and "on" in text_lower:
            return Intent(action="lights.on", params={}, raw_text=text)
        elif "light" in text_lower and "off" in text_lower:
            return Intent(action="lights.off", params={}, raw_text=text)
        elif "focus" in text_lower:
            return Intent(action="lights.scene", params={"scene": "focus"}, raw_text=text)
        elif "night" in text_lower:
            return Intent(action="lights.scene", params={"scene": "night"}, raw_text=text)
        elif "turn on" in text_lower or "turn on the" in text_lower:
            # Extract device name
            device = None
            if "record player" in text_lower:
                device = "record_player"
            elif "lamp" in text_lower:
                device = "lamp"
            elif "light" in text_lower:
                device = "lamp"
            if device:
                return Intent(action="device.on", params={"device": device}, raw_text=text)
        elif "turn off" in text_lower or "turn off the" in text_lower:
            # Extract device name
            device = None
            if "record player" in text_lower:
                device = "record_player"
            elif "lamp" in text_lower:
                device = "lamp"
            elif "light" in text_lower:
                device = "lamp"
            if device:
                return Intent(action="device.off", params={"device": device}, raw_text=text)
        elif "is" in text_lower and ("on" in text_lower or "off" in text_lower):
            # Extract device name
            device = None
            if "record player" in text_lower:
                device = "record_player"
            elif "lamp" in text_lower:
                device = "lamp"
            elif "light" in text_lower:
                device = "lamp"
            if device:
                return Intent(action="device.status", params={"device": device}, raw_text=text)
        elif "timer" in text_lower:
            return Intent(action="timer.set", params={"minutes": 5}, raw_text=text)
        elif "status" in text_lower:
            return Intent(action="status.get", params={}, raw_text=text)
        else:
            return Intent(
                action="clarify",
                params={"message": "I didn't catch that."},
                raw_text=text
            )
    
    def _real_extract_intent(self, text: str, room_state: RoomState) -> Intent:
        """Extract intent using OpenAI GPT-4o-mini."""
        start_time = time.time()
        
        # Format system prompt with context
        current_time = datetime.now().strftime("%H:%M")
        prompt = SYSTEM_PROMPT.format(
            state=room_state.value,
            time=current_time
        )
        
        try:
            logger.debug(f"Sending to LLM: '{text}'")
            
            response = self._client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f'User said: "{text}"'}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Low temperature for consistent parsing
                max_tokens=150
            )
            
            elapsed = time.time() - start_time
            
            # Parse JSON response
            content = response.choices[0].message.content
            logger.debug(f"LLM raw response: {content}")
            
            data = json.loads(content)
            logger.debug(f"LLM parsed data: {data}")
            
            # Handle both "action" at top level and nested structures
            if isinstance(data, dict):
                action = data.get("action", "clarify")
                params = data.get("params", {})
                # Ensure params is a dict
                if not isinstance(params, dict):
                    params = {}
            else:
                logger.warning(f"LLM returned non-dict: {type(data)}")
                action = "clarify"
                params = {"message": "I didn't catch that."}
            
            intent = Intent(action=action, params=params, raw_text=text)
            
            logger.info(f"LLM intent extracted: {action} ({elapsed:.2f}s)")
            logger.debug(f"Intent params: {params}")
            
            return intent
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM returned invalid JSON: {content} - {e}")
            return Intent(
                action="clarify",
                params={"message": "I didn't catch that."},
                raw_text=text
            )
            
        except KeyError as e:
            logger.error(f"LLM response missing key: {e}, data: {data if 'data' in dir() else 'N/A'}")
            return Intent(
                action="clarify",
                params={"message": "I didn't catch that."},
                raw_text=text
            )
            
        except APITimeoutError as e:
            logger.error(f"LLM timeout: {e}")
            raise RuntimeError("Intent extraction timed out") from e
            
        except APIConnectionError as e:
            logger.error(f"LLM connection error: {e}")
            raise RuntimeError("Cannot connect to AI service") from e
            
        except APIError as e:
            logger.error(f"LLM API error: {e}")
            raise RuntimeError(f"Intent extraction failed: {e}") from e
            
        except Exception as e:
            logger.error(f"LLM unexpected error: {e}")
            raise RuntimeError(f"Intent extraction failed: {e}") from e

