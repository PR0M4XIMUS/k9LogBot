# oled_display.py
import threading
import time
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont
import logging

logger = logging.getLogger(__name__)

class OLEDDisplayManager:
    def __init__(self, get_stats_callback):
        """
        Initialize OLED display manager.
        get_stats_callback: Function that returns bot statistics
        """
        self.get_stats_callback = get_stats_callback
        self.device = None
        self.running = False
        self.display_thread = None
        self.current_screen = 0
        self.last_update = datetime.now()
        
        # Try to initialize display
        try:
            serial = i2c(port=1, address=0x3C)  # Common I2C address for OLED
            self.device = ssd1306(serial, width=128, height=64)
            logger.info("OLED display initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OLED display: {e}")
            self.device = None
    
    def start(self):
        """Start the display update thread."""
        if self.device is None:
            logger.warning("OLED display not available, skipping display updates")
            return
        
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        logger.info("OLED display thread started")
    
    def stop(self):
        """Stop the display update thread."""
        self.running = False
        if self.display_thread:
            self.display_thread.join()
        if self.device:
            self.device.cleanup()
        logger.info("OLED display stopped")
    
    def _display_loop(self):
        """Main display loop that cycles through different screens."""
        while self.running:
            try:
                if self.current_screen == 0:
                    self._draw_status_screen()
                elif self.current_screen == 1:
                    self._draw_chisinau_time_screen()
                elif self.current_screen == 2:
                    self._draw_pixel_city_screen()
                
                # Cycle through screens every 5 seconds
                time.sleep(5)
                self.current_screen = (self.current_screen + 1) % 3
                
            except Exception as e:
                logger.error(f"Error in display loop: {e}")
                time.sleep(1)
    
    def _draw_status_screen(self):
        """Draw bot status screen."""
        with canvas(self.device) as draw:
            # Title
            draw.text((0, 0), "K9 LOG BOT", fill="white")
            draw.text((0, 12), "=" * 16, fill="white")
            
            # Status
            stats = self.get_stats_callback()
            status = "ONLINE" if stats['bot_running'] else "OFFLINE"
            draw.text((0, 24), f"Status: {status}", fill="white")
            
            # Uptime
            uptime = stats.get('uptime', 0)
            hours = int(uptime // 3600)
            minutes = int((uptime % 3600) // 60)
            draw.text((0, 36), f"Uptime: {hours:02d}:{minutes:02d}", fill="white")
            
            # Screen indicator
            draw.text((90, 54), "Screen 1/3", fill="white")
    
    def _draw_chisinau_time_screen(self):
        """Draw time and date screen for Chisinau, Moldova."""
        with canvas(self.device) as draw:
            # Get current time in Chisinau timezone
            chisinau_tz = ZoneInfo("Europe/Chisinau")
            now = datetime.now(chisinau_tz)
            
            # Title
            draw.text((0, 0), "CHISINAU TIME", fill="white")
            draw.text((0, 12), "=" * 16, fill="white")
            
            # Date
            date_str = now.strftime("%Y-%m-%d")
            draw.text((0, 26), date_str, fill="white")
            
            # Time
            time_str = now.strftime("%H:%M:%S")
            draw.text((0, 38), time_str, fill="white")
            
            # Day of week
            day_str = now.strftime("%A")
            draw.text((0, 50), day_str, fill="white")
            
            draw.text((90, 54), "Screen 2/3", fill="white")
    
    def _draw_pixel_city_screen(self):
        """Draw a nice pixel art city skyline screen."""
        with canvas(self.device) as draw:
            # Title
            draw.text((0, 0), "PIXEL CITY", fill="white")
            draw.text((0, 12), "=" * 14, fill="white")
            
            # Draw pixel art buildings with different heights
            buildings = [
                {"x": 5, "width": 8, "height": 25, "windows": [(1, 3), (5, 3), (1, 8), (5, 8)]},
                {"x": 18, "width": 12, "height": 30, "windows": [(2, 5), (8, 5), (2, 12), (8, 12), (2, 18), (8, 18)]},
                {"x": 35, "width": 6, "height": 20, "windows": [(1, 3), (4, 3), (1, 8)]},
                {"x": 46, "width": 10, "height": 35, "windows": [(2, 4), (6, 4), (2, 12), (6, 12), (2, 20), (6, 20), (2, 28), (6, 28)]},
                {"x": 61, "width": 8, "height": 22, "windows": [(1, 3), (5, 3), (1, 10), (5, 10)]},
                {"x": 74, "width": 14, "height": 28, "windows": [(2, 4), (6, 4), (10, 4), (2, 12), (6, 12), (10, 12), (2, 20), (6, 20), (10, 20)]},
                {"x": 93, "width": 7, "height": 18, "windows": [(1, 3), (4, 3), (1, 9)]},
                {"x": 105, "width": 11, "height": 32, "windows": [(2, 4), (7, 4), (2, 12), (7, 12), (2, 20), (7, 20), (2, 28), (7, 28)]},
                {"x": 121, "width": 6, "height": 15, "windows": [(1, 3), (4, 3)]}
            ]
            
            # Draw buildings
            for building in buildings:
                x, width, height = building["x"], building["width"], building["height"]
                base_y = 50
                # Draw building outline (pixelated style)
                for i in range(0, width, 2):  # Pixelated edges
                    for j in range(0, height, 2):
                        px, py = x + i, base_y - j
                        if 0 <= px <= 127 and 0 <= py <= 63:
                            if i == 0 or i >= width-2 or j == 0 or j >= height-2:
                                draw.point((px, py), fill="white")
                
                # Draw windows
                for wx, wy in building["windows"]:
                    window_x, window_y = x + wx, base_y - wy - 2
                    if 0 <= window_x <= 126 and 0 <= window_y <= 62:
                        # 2x2 pixel windows
                        draw.point((window_x, window_y), fill="white")
                        draw.point((window_x+1, window_y), fill="white")
                        draw.point((window_x, window_y+1), fill="white")
                        draw.point((window_x+1, window_y+1), fill="white")
            
            # Draw pixelated stars in the sky
            stars = [(15, 18), (35, 16), (58, 19), (85, 17), (110, 15), (25, 20), (95, 18)]
            for sx, sy in stars:
                # Make stars look pixelated
                if 0 <= sx <= 126 and 0 <= sy <= 62:
                    draw.point((sx, sy), fill="white")
                    draw.point((sx+1, sy), fill="white")
                    draw.point((sx, sy+1), fill="white")
                    draw.point((sx+1, sy+1), fill="white")
            
            # Draw ground line
            draw.line([(0, 51), (127, 51)], fill="white")
            
            draw.text((90, 54), "Screen 3/3", fill="white")
    
    def show_notification(self, message, duration=3):
        """Show a temporary notification."""
        if self.device is None:
            return
        
        def show_temp_message():
            with canvas(self.device) as draw:
                draw.text((0, 0), "NOTIFICATION", fill="white")
                draw.text((0, 12), "=" * 16, fill="white")
                
                # Word wrap for long messages
                words = message.split()
                lines = []
                current_line = ""
                
                for word in words:
                    if len(current_line + word) < 16:
                        current_line += word + " "
                    else:
                        lines.append(current_line.strip())
                        current_line = word + " "
                
                if current_line:
                    lines.append(current_line.strip())
                
                # Display up to 3 lines
                for i, line in enumerate(lines[:3]):
                    draw.text((0, 24 + i * 10), line, fill="white")
            
            time.sleep(duration)
        
        # Show notification in a separate thread
        notification_thread = threading.Thread(target=show_temp_message, daemon=True)
        notification_thread.start()