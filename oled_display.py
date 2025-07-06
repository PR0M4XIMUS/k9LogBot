# oled_display.py
import threading
import time
import logging
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import os

# Setup logging
logger = logging.getLogger(__name__)

class OLEDDisplayManager:
    """
    Thread-safe OLED display manager for K9LogBot.
    Handles 4 rotating screens and temporary notifications.
    """
    
    def __init__(self, width=128, height=64, address=0x3C):
        self.width = width
        self.height = height
        self.address = address
        self.device = None
        self.display_lock = threading.Lock()
        self.running = False
        self.display_thread = None
        self.start_time = datetime.now()
        
        # Screen rotation variables
        self.current_screen = 0
        self.last_screen_change = time.time()
        self.screen_interval = 5  # seconds
        
        # Notification variables
        self.notification_text = None
        self.notification_end_time = None
        self.notification_duration = 3  # seconds
        
        # Statistics cache
        self.stats_cache = {
            'total_walks': 0,
            'walks_today': 0,
            'total_earned': 0.0,
            'current_balance': 0.0,
            'last_update': datetime.now()
        }
        
        # Initialize display
        self._init_display()
    
    def _init_display(self):
        """Initialize the OLED display with graceful fallback."""
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            
            # Try different I2C addresses
            addresses = [self.address, 0x3D, 0x3C]
            
            for addr in addresses:
                try:
                    serial = i2c(port=1, address=addr)
                    self.device = ssd1306(serial, width=self.width, height=self.height)
                    logger.info(f"OLED display initialized successfully at address 0x{addr:02X}")
                    return
                except Exception as e:
                    logger.debug(f"Failed to initialize OLED at address 0x{addr:02X}: {e}")
                    continue
            
            raise Exception("No OLED display found at any address")
            
        except Exception as e:
            logger.warning(f"OLED display initialization failed: {e}")
            logger.warning("Running in display-disabled mode")
            self.device = None
    
    def start(self):
        """Start the display thread."""
        if self.running:
            return
            
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        logger.info("OLED display thread started")
    
    def stop(self):
        """Stop the display thread."""
        self.running = False
        if self.display_thread:
            self.display_thread.join(timeout=2)
        logger.info("OLED display thread stopped")
    
    def update_stats(self, stats):
        """Update statistics cache."""
        with self.display_lock:
            self.stats_cache.update(stats)
            self.stats_cache['last_update'] = datetime.now()
    
    def show_notification(self, text, duration=3):
        """Show a temporary notification."""
        with self.display_lock:
            self.notification_text = text
            self.notification_end_time = time.time() + duration
            logger.info(f"Notification: {text}")
    
    def _display_loop(self):
        """Main display loop running in separate thread."""
        while self.running:
            try:
                if self.device:
                    self._update_display()
                time.sleep(0.1)  # Small delay to prevent excessive CPU usage
            except Exception as e:
                logger.error(f"Display loop error: {e}")
                time.sleep(1)
    
    def _update_display(self):
        """Update the display content."""
        if not self.device:
            return
            
        try:
            with self.display_lock:
                # Check if we should show a notification
                current_time = time.time()
                if self.notification_text and current_time < self.notification_end_time:
                    image = self._create_notification_screen()
                else:
                    # Clear expired notification
                    if self.notification_text and current_time >= self.notification_end_time:
                        self.notification_text = None
                        self.notification_end_time = None
                    
                    # Show rotating screens
                    if current_time - self.last_screen_change >= self.screen_interval:
                        self.current_screen = (self.current_screen + 1) % 4
                        self.last_screen_change = current_time
                    
                    image = self._create_screen(self.current_screen)
                
                # Display the image
                self.device.display(image)
                
        except Exception as e:
            logger.error(f"Display update error: {e}")
    
    def _create_screen(self, screen_num):
        """Create a screen based on the screen number."""
        if screen_num == 0:
            return self._create_status_screen()
        elif screen_num == 1:
            return self._create_balance_screen()
        elif screen_num == 2:
            return self._create_statistics_screen()
        elif screen_num == 3:
            return self._create_time_screen()
        else:
            return self._create_status_screen()
    
    def _create_status_screen(self):
        """Create bot status and uptime screen."""
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        # Calculate uptime
        uptime = datetime.now() - self.start_time
        uptime_str = self._format_uptime(uptime)
        
        # Title
        draw.text((2, 2), "K9LogBot Status", fill=1)
        draw.line([(0, 12), (self.width, 12)], fill=1)
        
        # Status
        draw.text((2, 16), "Status: ONLINE", fill=1)
        draw.text((2, 28), f"Uptime: {uptime_str}", fill=1)
        draw.text((2, 40), f"Display: {'ON' if self.device else 'OFF'}", fill=1)
        draw.text((2, 52), f"DB: CONNECTED", fill=1)
        
        return image
    
    def _create_balance_screen(self):
        """Create balance screen with large text."""
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        balance = self.stats_cache.get('current_balance', 0.0)
        
        # Title
        draw.text((2, 2), "Current Balance", fill=1)
        draw.line([(0, 12), (self.width, 12)], fill=1)
        
        # Balance with large text
        balance_text = f"{balance:.2f}"
        draw.text((10, 20), balance_text, fill=1)
        draw.text((10, 40), "MDL", fill=1)
        
        # Status indicator
        if balance > 0:
            draw.text((2, 52), "They owe you", fill=1)
        elif balance < 0:
            draw.text((2, 52), "You owe them", fill=1)
        else:
            draw.text((2, 52), "Balance zero", fill=1)
        
        return image
    
    def _create_statistics_screen(self):
        """Create statistics screen."""
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        # Title
        draw.text((2, 2), "Statistics", fill=1)
        draw.line([(0, 12), (self.width, 12)], fill=1)
        
        # Statistics
        total_walks = self.stats_cache.get('total_walks', 0)
        walks_today = self.stats_cache.get('walks_today', 0)
        total_earned = self.stats_cache.get('total_earned', 0.0)
        
        draw.text((2, 16), f"Total walks: {total_walks}", fill=1)
        draw.text((2, 28), f"Today: {walks_today}", fill=1)
        draw.text((2, 40), f"Total: {total_earned:.2f} MDL", fill=1)
        
        # Last update
        last_update = self.stats_cache.get('last_update', datetime.now())
        update_str = last_update.strftime("%H:%M")
        draw.text((2, 52), f"Updated: {update_str}", fill=1)
        
        return image
    
    def _create_time_screen(self):
        """Create current date and time screen."""
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        now = datetime.now()
        
        # Date
        date_str = now.strftime("%Y-%m-%d")
        draw.text((2, 2), date_str, fill=1)
        
        # Time (large)
        time_str = now.strftime("%H:%M:%S")
        draw.text((10, 20), time_str, fill=1)
        
        # Day of week
        day_str = now.strftime("%A")
        draw.text((2, 40), day_str, fill=1)
        
        # Week number
        week_str = f"Week {now.strftime('%U')}"
        draw.text((2, 52), week_str, fill=1)
        
        return image
    
    def _create_notification_screen(self):
        """Create notification screen."""
        image = Image.new('1', (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)
        
        # Title
        draw.text((2, 2), "Notification", fill=1)
        draw.line([(0, 12), (self.width, 12)], fill=1)
        
        # Notification text (wrapped)
        lines = self._wrap_text(self.notification_text, 18)
        y = 20
        for line in lines[:3]:  # Max 3 lines
            draw.text((2, y), line, fill=1)
            y += 12
        
        return image
    
    def _format_uptime(self, uptime):
        """Format uptime duration."""
        total_seconds = int(uptime.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def _wrap_text(self, text, max_width):
        """Wrap text to fit within specified width."""
        if not text:
            return []
        
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word[:max_width])
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

# Global instance
oled_manager = None

def init_oled_display():
    """Initialize the global OLED display manager."""
    global oled_manager
    if oled_manager is None:
        oled_manager = OLEDDisplayManager()
        oled_manager.start()
    return oled_manager

def get_oled_manager():
    """Get the global OLED display manager."""
    return oled_manager

def shutdown_oled_display():
    """Shutdown the global OLED display manager."""
    global oled_manager
    if oled_manager:
        oled_manager.stop()
        oled_manager = None