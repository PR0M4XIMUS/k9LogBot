# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get environment variables with validation
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

try:
    YOUR_TELEGRAM_CHAT_ID = int(os.getenv("YOUR_TELEGRAM_CHAT_ID", "0"))
except (ValueError, TypeError):
    YOUR_TELEGRAM_CHAT_ID = 0
    print("Warning: YOUR_TELEGRAM_CHAT_ID is not set or invalid. Weekly reports will not be sent.")

# OLED Display Configuration
OLED_ENABLED = os.getenv("OLED_ENABLED", "true").lower() == "true"
OLED_WIDTH = int(os.getenv("OLED_WIDTH", "128"))
OLED_HEIGHT = int(os.getenv("OLED_HEIGHT", "64"))
OLED_ADDRESS = int(os.getenv("OLED_ADDRESS", "0x3C"), 16)  # Support hex format
OLED_SCREEN_INTERVAL = int(os.getenv("OLED_SCREEN_INTERVAL", "5"))  # seconds
