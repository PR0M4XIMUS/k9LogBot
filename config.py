# config.py
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

try:
    YOUR_TELEGRAM_CHAT_ID = int(os.getenv("YOUR_TELEGRAM_CHAT_ID", "0"))
except (ValueError, TypeError):
    YOUR_TELEGRAM_CHAT_ID = 0
    print("Warning: YOUR_TELEGRAM_CHAT_ID is not set or invalid. Weekly reports will not be sent.")

# --- Admin support ---
ADMIN_CHAT_IDS = [864342269]  # You can add more admin IDs here if needed

# --- Performance Configuration ---
# OLED display update interval (seconds) - higher values reduce CPU usage
DISPLAY_UPDATE_INTERVAL = int(os.getenv("DISPLAY_UPDATE_INTERVAL", "10"))
# Stats cache duration (seconds) - higher values reduce database queries
STATS_CACHE_DURATION = int(os.getenv("STATS_CACHE_DURATION", "30"))

# --- Auto Cleanup Configuration ---
# Day of month to run automatic cleanup (1-28)
# Cleanup removes records from months older than the current month
AUTO_CLEANUP_DAY = int(os.getenv("AUTO_CLEANUP_DAY", "10"))
# Number of months of records to keep (default: 1 = keep current month only)
AUTO_CLEANUP_MONTHS_TO_KEEP = int(os.getenv("AUTO_CLEANUP_MONTHS_TO_KEEP", "1"))
# Enable/disable automatic cleanup
AUTO_CLEANUP_ENABLED = os.getenv("AUTO_CLEANUP_ENABLED", "true").lower() == "true"

def is_admin(chat_id):
    return chat_id in ADMIN_CHAT_IDS

def get_role(chat_id):
    return "admin" if is_admin(chat_id) else "user"
