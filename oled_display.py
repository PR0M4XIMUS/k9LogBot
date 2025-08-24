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
                    self._draw_retro_sunset_screen()
                
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
    
    def _draw_retro_sunset_screen(self):
        """Draw a cute pixel art retro sunset screen."""
        with canvas(self.device) as draw:
            # Title
            draw.text((0, 0), "RETRO SUNSET", fill="white")
            draw.text((0, 12), "=" * 14, fill="white")
            
            # Draw sky layers (horizontal lines for gradient effect)
            for y in range(15, 25):
                draw.line([(0, y), (127, y)], fill="white")
            
            # Draw sun (circle in upper part)
            sun_center_x, sun_center_y = 100, 20
            sun_radius = 6
            for angle in range(0, 360, 30):  # Draw sun as points in circle
                x = sun_center_x + int(sun_radius * math.cos(math.radians(angle)))
                y = sun_center_y + int(sun_radius * math.sin(math.radians(angle)))
                if 0 <= x <= 127 and 0 <= y <= 63:
                    draw.point((x, y), fill="white")
            
            # Draw sun center
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) + abs(dy) <= 2:
                        x, y = sun_center_x + dx, sun_center_y + dy
                        if 0 <= x <= 127 and 0 <= y <= 63:
                            draw.point((x, y), fill="white")
            
            # Draw mountain/hills silhouette
            mountain_points = [
                (0, 35), (20, 30), (40, 25), (60, 30), (80, 28), (100, 32), (127, 35)
            ]
            for i in range(len(mountain_points) - 1):
                draw.line([mountain_points[i], mountain_points[i + 1]], fill="white")
            
            # Fill area below mountains
            for y in range(36, 50):
                draw.line([(0, y), (127, y)], fill="white")
            
            # Draw stylized palm tree on the left
            # Tree trunk
            draw.line([(15, 40), (15, 48)], fill="white")
            draw.line([(16, 40), (16, 48)], fill="white")
            
            # Palm fronds (simple lines radiating from top)
            palm_top = (15, 40)
            frond_points = [(5, 35), (10, 32), (20, 32), (25, 35), (12, 30), (18, 30)]
            for point in frond_points:
                draw.line([palm_top, point], fill="white")
            
            # Add some stars in the sky
            stars = [(30, 18), (50, 16), (75, 19), (10, 17), (120, 16)]
            for star in stars:
                if 0 <= star[0] <= 127 and 0 <= star[1] <= 63:
                    draw.point(star, fill="white")
            
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