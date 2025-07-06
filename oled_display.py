# oled_display.py
import threading
import time
from datetime import datetime
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
                    self._draw_balance_screen()
                elif self.current_screen == 2:
                    self._draw_stats_screen()
                elif self.current_screen == 3:
                    self._draw_time_screen()
                
                # Cycle through screens every 5 seconds
                time.sleep(5)
                self.current_screen = (self.current_screen + 1) % 4
                
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
            draw.text((0, 54), "Screen 1/4", fill="white")
    
    def _draw_balance_screen(self):
        """Draw current balance screen."""
        with canvas(self.device) as draw:
            stats = self.get_stats_callback()
            balance = stats.get('current_balance', 0)
            
            # Title
            draw.text((0, 0), "CURRENT BALANCE", fill="white")
            draw.text((0, 12), "=" * 16, fill="white")
            
            # Balance with large font
            balance_text = f"{balance:.2f} MDL"
            draw.text((0, 28), balance_text, fill="white")
            
            # Status
            if balance > 0:
                status = "They owe you"
            elif balance < 0:
                status = "You owe them"
            else:
                status = "All settled"
            
            draw.text((0, 42), status, fill="white")
            draw.text((0, 54), "Screen 2/4", fill="white")
    
    def _draw_stats_screen(self):
        """Draw statistics screen."""
        with canvas(self.device) as draw:
            stats = self.get_stats_callback()
            
            # Title
            draw.text((0, 0), "STATISTICS", fill="white")
            draw.text((0, 12), "=" * 16, fill="white")
            
            # Stats
            total_walks = stats.get('total_walks', 0)
            walks_today = stats.get('walks_today', 0)
            total_earned = stats.get('total_earned', 0)
            
            draw.text((0, 24), f"Total Walks: {total_walks}", fill="white")
            draw.text((0, 34), f"Today: {walks_today}", fill="white")
            draw.text((0, 44), f"Earned: {total_earned:.0f} MDL", fill="white")
            
            draw.text((0, 54), "Screen 3/4", fill="white")
    
    def _draw_time_screen(self):
        """Draw time and date screen."""
        with canvas(self.device) as draw:
            now = datetime.now()
            
            # Title
            draw.text((0, 0), "DATE & TIME", fill="white")
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
            
            draw.text((90, 54), "Screen 4/4", fill="white")
    
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