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
