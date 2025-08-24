# oled_display.py
import threading
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
import logging
from config import DISPLAY_UPDATE_INTERVAL

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
        # Performance optimization: configurable update interval
        self.update_interval = DISPLAY_UPDATE_INTERVAL
        # Notification management
        self.notification_active = False
        self.notification_end_time = None
        self.notification_message = ""
        
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
                # Check if notification should be shown
                if self.notification_active and datetime.now() < self.notification_end_time:
                    self._draw_notification_screen()
                elif self.notification_active:
                    # Notification expired
                    self.notification_active = False
                    self.notification_message = ""
                    self.notification_end_time = None
                else:
                    # Show normal screens
                    if self.current_screen == 0:
                        self._draw_status_screen()
                    elif self.current_screen == 1:
                        self._draw_chisinau_time_screen()
                    elif self.current_screen == 2:
                        self._draw_simple_info_screen()  # Simplified instead of complex pixel city
                    
                    # Only cycle screens when not showing notification
                    # Performance optimization: longer sleep interval
                    time.sleep(self.update_interval)
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
    
    def _draw_simple_info_screen(self):
        """Draw a simple information screen (performance optimized)."""
        with canvas(self.device) as draw:
            # Title
            draw.text((0, 0), "BOT INFO", fill="white")
            draw.text((0, 12), "=" * 12, fill="white")
            
            # Get stats for additional info
            stats = self.get_stats_callback()
            
            # Show total walks and earnings
            draw.text((0, 24), f"Total walks: {stats.get('total_walks', 0)}", fill="white")
            draw.text((0, 36), f"Today: {stats.get('walks_today', 0)} walks", fill="white")
            draw.text((0, 48), f"Balance: {stats.get('current_balance', 0):.1f} MDL", fill="white")
            
            draw.text((90, 54), "Screen 3/3", fill="white")
    
    def _draw_notification_screen(self):
        """Draw notification screen."""
        with canvas(self.device) as draw:
            draw.text((0, 0), "NOTIFICATION", fill="white")
            draw.text((0, 12), "=" * 16, fill="white")
            
            # Word wrap for long messages
            words = self.notification_message.split()
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
    
    def show_notification(self, message, duration=3):
        """Show a temporary notification (optimized to avoid thread creation)."""
        if self.device is None:
            return
        
        # Set notification state instead of creating new thread
        self.notification_message = message
        self.notification_active = True
        self.notification_end_time = datetime.now() + timedelta(seconds=duration)