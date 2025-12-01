"""
LED Controller for WS2812B addressable LED strips.

Controls lighting via GPIO on Raspberry Pi, with mock mode for development.
"""

import math
from typing import Optional, Tuple
from loguru import logger

from src.config import (
    LED_COUNT, LED_PIN, LED_BRIGHTNESS, LED_FREQ_HZ,
    SCENES, MOCK_HARDWARE
)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class LEDController:
    """
    Controls WS2812B LED strip.
    
    In mock mode, logs actions instead of controlling hardware.
    In real mode, uses rpi_ws281x library.
    """
    
    def __init__(self, mock_mode: bool = MOCK_HARDWARE):
        """
        Initialize LED controller.
        
        Args:
            mock_mode: If True, log actions instead of GPIO control
        """
        self._mock_mode = mock_mode
        self._strip = None
        self._on = False
        self._current_color = (255, 255, 255)  # White
        self._current_brightness = 1.0
        self._current_scene: Optional[str] = None
        
        if not mock_mode:
            self._init_strip()
        
        logger.info(
            f"LEDController initialized (mock_mode={mock_mode}, "
            f"count={LED_COUNT}, pin={LED_PIN})"
        )
    
    def _init_strip(self) -> None:
        """Initialize the physical LED strip."""
        try:
            from rpi_ws281x import PixelStrip, Color
            
            self._strip = PixelStrip(
                LED_COUNT,
                LED_PIN,
                LED_FREQ_HZ,
                10,  # DMA channel
                False,  # Invert signal
                LED_BRIGHTNESS,
                0  # Channel
            )
            self._strip.begin()
            logger.info("LED strip initialized")
            
        except ImportError:
            logger.warning("rpi_ws281x not available, falling back to mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to initialize LED strip: {e}")
            self._mock_mode = True
    
    def set_on(self) -> None:
        """Turn lights on (restore last color/brightness)."""
        self._on = True
        self._apply_color(self._current_color, self._current_brightness)
        logger.info("💡 Lights ON")
    
    def set_off(self) -> None:
        """Turn lights off."""
        self._on = False
        self._apply_color((0, 0, 0), 0)
        logger.info("💡 Lights OFF")
    
    def set_color(
        self, 
        r: int, 
        g: int, 
        b: int, 
        brightness: float = 1.0
    ) -> None:
        """
        Set LED color and brightness.
        
        Args:
            r: Red (0-255)
            g: Green (0-255)
            b: Blue (0-255)
            brightness: Brightness (0.0-1.0)
        """
        self._current_color = (r, g, b)
        self._current_brightness = max(0.0, min(1.0, brightness))
        self._on = brightness > 0
        
        self._apply_color(self._current_color, self._current_brightness)
        
        logger.info(
            f"💡 Set color: RGB({r},{g},{b}) @ {self._current_brightness:.0%}"
        )
    
    def set_scene(self, scene_id: str) -> bool:
        """
        Apply a predefined scene.
        
        Args:
            scene_id: Scene identifier (e.g., "focus", "night")
            
        Returns:
            True if scene was found and applied, False otherwise
        """
        scene = SCENES.get(scene_id)
        
        if scene is None:
            logger.warning(f"Unknown scene: {scene_id}")
            return False
        
        color = hex_to_rgb(scene["color"])
        brightness = scene.get("brightness", 1.0)
        
        self._current_scene = scene_id
        self.set_color(*color, brightness)
        
        logger.info(f"💡 Scene applied: {scene_id}")
        return True
    
    def _apply_color(
        self, 
        color: Tuple[int, int, int], 
        brightness: float
    ) -> None:
        """Apply color to the LED strip."""
        r, g, b = color
        
        # Apply brightness
        r = int(r * brightness)
        g = int(g * brightness)
        b = int(b * brightness)
        
        if self._mock_mode:
            logger.debug(
                f"[MOCK LED] Setting {LED_COUNT} LEDs to "
                f"RGB({r},{g},{b}) @ {brightness:.0%}"
            )
            return
        
        # Real hardware
        try:
            from rpi_ws281x import Color
            
            color_value = Color(r, g, b)
            
            for i in range(self._strip.numPixels()):
                self._strip.setPixelColor(i, color_value)
            
            self._strip.show()
            
        except Exception as e:
            logger.error(f"Failed to set LED color: {e}")
    
    def animate_golden_shimmer(self, duration: float = 3.0) -> None:
        """
        Play golden shimmer animation.
        
        Used for welcome scene.
        """
        if self._mock_mode:
            logger.info(f"[MOCK LED] Golden shimmer animation ({duration}s)")
            return
        
        # TODO: Implement actual animation on Pi
        # For now, just set to gold
        self.set_color(255, 215, 0, 0.7)
    
    def animate_sunrise(self, duration: float = 5.0) -> None:
        """
        Play sunrise animation.
        
        Gradual warm color fade-in.
        """
        if self._mock_mode:
            logger.info(f"[MOCK LED] Sunrise animation ({duration}s)")
            return
        
        # TODO: Implement actual animation on Pi
        self.set_color(255, 236, 210, 0.5)
    
    def animate_fade_out(self, duration: float = 2.0) -> None:
        """
        Fade out to off.
        
        Used for sleep/exit scenes.
        """
        if self._mock_mode:
            logger.info(f"[MOCK LED] Fade out animation ({duration}s)")
            self.set_off()
            return
        
        # TODO: Implement actual fade animation on Pi
        self.set_off()
    
    def animate_listening(self) -> None:
        """
        Play "listening" animation when wake word detected.
        
        A gentle cyan/blue pulse that signals Arvis is ready to hear.
        Inspired by Siri's edge glow effect.
        """
        if self._mock_mode:
            logger.info("💫 [MOCK LED] Listening animation (cyan pulse)")
            return
        
        # TODO: Implement actual animation on Pi
        # For now, set to a soft cyan glow
        import time
        import threading
        
        def pulse():
            try:
                from rpi_ws281x import Color
                
                # Soft cyan color
                base_r, base_g, base_b = 0, 200, 255
                
                # Quick pulse up
                for i in range(5):
                    brightness = 0.3 + (i * 0.14)  # 0.3 to 1.0
                    r = int(base_r * brightness)
                    g = int(base_g * brightness)
                    b = int(base_b * brightness)
                    
                    color = Color(r, g, b)
                    for j in range(self._strip.numPixels()):
                        self._strip.setPixelColor(j, color)
                    self._strip.show()
                    time.sleep(0.05)
                
                # Hold at full brightness
                time.sleep(0.2)
                
                # Fade back down
                for i in range(5, -1, -1):
                    brightness = 0.3 + (i * 0.14)
                    r = int(base_r * brightness)
                    g = int(base_g * brightness)
                    b = int(base_b * brightness)
                    
                    color = Color(r, g, b)
                    for j in range(self._strip.numPixels()):
                        self._strip.setPixelColor(j, color)
                    self._strip.show()
                    time.sleep(0.05)
                    
            except Exception as e:
                logger.error(f"Listening animation error: {e}")
        
        # Run in background thread to not block
        threading.Thread(target=pulse, daemon=True).start()
    
    def animate_processing(self) -> None:
        """
        Play "processing" animation while STT/LLM working.
        
        A subtle breathing effect to show Arvis is thinking.
        """
        if self._mock_mode:
            logger.info("🔄 [MOCK LED] Processing animation (breathing)")
            return
        
        # TODO: Implement on Pi - gentle breathing in soft white/cyan
        pass
    
    def animate_success(self) -> None:
        """
        Play quick success flash when command executed.
        """
        if self._mock_mode:
            logger.info("✨ [MOCK LED] Success flash (green)")
            return
        
        # TODO: Implement on Pi - quick green flash
        pass
    
    def animate_golden_shimmer(self, duration: float = 3.0) -> None:
        """
        Play golden shimmer animation for welcome scene.
        
        Warm gold pulse that says "welcome home".
        Color: #FFD700 (gold) with brightness oscillation.
        """
        if self._mock_mode:
            logger.info(f"✨ [MOCK LED] Golden shimmer animation ({duration}s)")
            return
        
        import time
        import threading
        
        def shimmer():
            try:
                from rpi_ws281x import Color
                
                # Gold color
                base_r, base_g, base_b = 255, 215, 0
                
                steps = int(duration * 10)  # 10 steps per second
                
                for i in range(steps):
                    # Oscillate brightness 0.4 → 1.0 → 0.4
                    phase = (i / steps) * 2 * 3.14159
                    brightness = 0.4 + 0.6 * abs(math.sin(phase * 2))
                    
                    r = int(base_r * brightness)
                    g = int(base_g * brightness)
                    b = int(base_b * brightness)
                    
                    color = Color(r, g, b)
                    for j in range(self._strip.numPixels()):
                        self._strip.setPixelColor(j, color)
                    self._strip.show()
                    time.sleep(0.1)
                
                # End with warm glow
                color = Color(int(base_r * 0.7), int(base_g * 0.7), int(base_b * 0.7))
                for j in range(self._strip.numPixels()):
                    self._strip.setPixelColor(j, color)
                self._strip.show()
                
            except Exception as e:
                logger.error(f"Golden shimmer error: {e}")
        
        threading.Thread(target=shimmer, daemon=True).start()
    
    @property
    def is_on(self) -> bool:
        """Check if lights are currently on."""
        return self._on
    
    @property
    def current_scene(self) -> Optional[str]:
        """Get the current scene ID, if any."""
        return self._current_scene
    
    @property
    def current_color(self) -> Tuple[int, int, int]:
        """Get the current RGB color."""
        return self._current_color
    
    @property
    def current_brightness(self) -> float:
        """Get the current brightness (0.0-1.0)."""
        return self._current_brightness

