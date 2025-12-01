"""
Presence Agent - Room state management based on PIR motion.

Manages EMPTY ↔ OCCUPIED state transitions:
- Motion detected → EMPTY → OCCUPIED
- Timeout (no motion) → OCCUPIED → EMPTY
"""

import asyncio
import time
from datetime import datetime
from typing import Optional

from loguru import logger

from src.config import ROOM_EMPTY_TIMEOUT_MINUTES
from src.core.event_bus import EventBus
from src.core.state_manager import StateManager
from src.core.models import Event, RoomState


class PresenceAgent:
    """
    Manages room presence state based on PIR sensor events.
    
    State Transitions:
    - EMPTY + motion → OCCUPIED (triggers entry event)
    - OCCUPIED + timeout → EMPTY (triggers exit event)
    - OCCUPIED + motion → OCCUPIED (resets timer)
    """
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: StateManager,
        timeout_minutes: float = ROOM_EMPTY_TIMEOUT_MINUTES,
    ):
        """
        Initialize PresenceAgent.
        
        Args:
            event_bus: EventBus for subscribing/publishing events
            state_manager: StateManager for room state
            timeout_minutes: Minutes of no motion before room is EMPTY
        """
        self.event_bus = event_bus
        self.state_manager = state_manager
        self._timeout_seconds = timeout_minutes * 60
        
        self._running = False
        self._last_motion_time: float = 0
        self._timeout_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"PresenceAgent initialized (timeout={timeout_minutes}min)"
        )
    
    async def start(self) -> None:
        """Start the presence agent."""
        if self._running:
            logger.warning("PresenceAgent already running")
            return
        
        self._running = True
        
        # Subscribe to motion events
        self.event_bus.subscribe(
            "presence.motion_detected",
            self._on_motion_detected
        )
        
        # Start timeout checker
        self._timeout_task = asyncio.create_task(self._timeout_loop())
        
        logger.info("PresenceAgent started")
    
    async def stop(self) -> None:
        """Stop the presence agent."""
        logger.info("Stopping PresenceAgent...")
        
        self._running = False
        
        # Unsubscribe from events
        self.event_bus.unsubscribe(
            "presence.motion_detected",
            self._on_motion_detected
        )
        
        # Cancel timeout task
        if self._timeout_task:
            self._timeout_task.cancel()
            try:
                await self._timeout_task
            except asyncio.CancelledError:
                pass
        
        logger.info("PresenceAgent stopped")
    
    async def _on_motion_detected(self, event: Event) -> None:
        """
        Handle PIR motion detection.
        
        If room was EMPTY, transition to OCCUPIED and fire entry event.
        Always reset the timeout timer.
        """
        self._last_motion_time = time.time()
        current_state = self.state_manager.state
        
        logger.debug(f"Motion detected, current state: {current_state.value}")
        
        if current_state == RoomState.EMPTY:
            # Transition to OCCUPIED
            await self.state_manager.set_state(RoomState.OCCUPIED)
            
            # Fire entry event
            logger.info("🚪 Entry detected! Room now OCCUPIED")
            await self.event_bus.publish(Event(
                type="presence.entry_detected",
                payload={
                    "timestamp": datetime.now().isoformat(),
                    "previous_state": current_state.value,
                },
                source="presence_agent",
            ))
        else:
            # Already occupied, just log
            logger.debug("Motion while OCCUPIED - timer reset")
    
    async def _timeout_loop(self) -> None:
        """
        Background task that checks for room empty timeout.
        
        Runs every 30 seconds to check if enough time has passed
        since last motion to declare room EMPTY.
        """
        logger.debug("Timeout loop started")
        
        while self._running:
            await asyncio.sleep(30)  # Check every 30 seconds
            
            if not self._running:
                break
            
            # Only check timeout if room is OCCUPIED
            if self.state_manager.state != RoomState.OCCUPIED:
                continue
            
            # Check if timeout has elapsed
            if self._last_motion_time == 0:
                continue
            
            elapsed = time.time() - self._last_motion_time
            
            if elapsed >= self._timeout_seconds:
                await self._trigger_exit()
        
        logger.debug("Timeout loop stopped")
    
    async def _trigger_exit(self) -> None:
        """Trigger room exit (OCCUPIED → EMPTY)."""
        current_state = self.state_manager.state
        
        if current_state != RoomState.OCCUPIED:
            return
        
        # Transition to EMPTY
        await self.state_manager.set_state(RoomState.EMPTY)
        
        # Fire exit event
        timeout_min = self._timeout_seconds / 60
        logger.info(f"🚪 Exit detected! No motion for {timeout_min:.0f}min - Room now EMPTY")
        
        await self.event_bus.publish(Event(
            type="presence.exit_detected",
            payload={
                "timestamp": datetime.now().isoformat(),
                "previous_state": current_state.value,
                "timeout_minutes": timeout_min,
            },
            source="presence_agent",
        ))
        
        # Also publish the timeout event for logging
        await self.event_bus.publish(Event(
            type="presence.room_empty_timeout",
            payload={
                "timestamp": datetime.now().isoformat(),
                "elapsed_minutes": timeout_min,
            },
            source="presence_agent",
        ))
    
    async def trigger_mock_exit(self) -> None:
        """
        Manually trigger exit for testing.
        
        Useful when you don't want to wait for the real timeout.
        """
        logger.info("📡 [MOCK] Triggering exit")
        await self._trigger_exit()
    
    @property
    def is_running(self) -> bool:
        """Check if agent is running."""
        return self._running
    
    @property
    def seconds_since_motion(self) -> Optional[float]:
        """Get seconds since last motion, or None if no motion yet."""
        if self._last_motion_time == 0:
            return None
        return time.time() - self._last_motion_time
    
    @property
    def seconds_until_timeout(self) -> Optional[float]:
        """Get seconds until exit timeout, or None if not applicable."""
        if self._last_motion_time == 0:
            return None
        if self.state_manager.state != RoomState.OCCUPIED:
            return None
        
        elapsed = time.time() - self._last_motion_time
        remaining = self._timeout_seconds - elapsed
        return max(0, remaining)

