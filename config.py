# config.py
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
YOUR_TELEGRAM_CHAT_ID = int(os.getenv("YOUR_TELEGRAM_CHAT_ID")) # Ensure it's an integer