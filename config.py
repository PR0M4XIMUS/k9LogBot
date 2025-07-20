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

def is_admin(chat_id):
    return chat_id in ADMIN_CHAT_IDS

def get_role(chat_id):
    return "admin" if is_admin(chat_id) else "user"
