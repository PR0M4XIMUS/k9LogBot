# main.py
from telegram.ext import Application, ApplicationBuilder  # For building and running the bot
from apscheduler.schedulers.background import BackgroundScheduler  # For scheduling automated tasks
from datetime import datetime  # For handling dates and times (used by scheduler)

# Import configuration details and bot's logic functions
from config import TELEGRAM_BOT_TOKEN, YOUR_TELEGRAM_CHAT_ID, OLED_ENABLED
from database import init_db, get_statistics  # To set up the database when the bot starts
from bot_logic import setup_handlers, send_scheduled_report, error  # Bot's main logic and error handler
from oled_display import init_oled_display, get_oled_manager, shutdown_oled_display  # OLED display support

import logging  # For showing messages about the bot's operation
import signal  # For handling shutdown signals
import sys  # For system operations

# --- Set up Logging for the Main Script ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Global variables for cleanup
scheduler = None
oled_manager = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global scheduler, oled_manager
    logger.info("Received shutdown signal. Cleaning up...")
    
    if scheduler:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
    
    if oled_manager:
        shutdown_oled_display()
        logger.info("OLED display shut down.")
    
    sys.exit(0)

def update_oled_stats():
    """Update OLED display statistics."""
    global oled_manager
    if oled_manager:
        try:
            stats = get_statistics()
            oled_manager.update_stats(stats)
        except Exception as e:
            logger.error(f"Error updating OLED stats: {e}")

def main():
    """
    This is the main function that starts the bot and the scheduler.
    """
    global scheduler, oled_manager
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Initializing database...")
    init_db()  # Call the function to create the database tables if they don't exist
    logger.info("Database initialized.")

    # --- Initialize OLED Display ---
    if OLED_ENABLED:
        logger.info("Initializing OLED display...")
        try:
            oled_manager = init_oled_display()
            logger.info("OLED display initialized.")
            # Update initial statistics
            update_oled_stats()
        except Exception as e:
            logger.error(f"Failed to initialize OLED display: {e}")
            logger.warning("Continuing without OLED display.")
            oled_manager = None
    else:
        logger.info("OLED display disabled in configuration.")

    # --- Build the Telegram Application ---
    logger.info("Building Telegram Application...")
    # ApplicationBuilder helps us set up the bot with its token.
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    logger.info("Telegram Application built.")

    # --- Set up Bot Command Handlers ---
    logger.info("Setting up bot command handlers...")
    setup_handlers(application)  # Call the function from bot_logic.py to add all command/message handlers
    application.add_error_handler(error)  # Register the global error handler for the bot
    logger.info("Bot command handlers and error handler set up.")

    # --- Setup APScheduler for Weekly Reports ---
    logger.info("Setting up weekly report scheduler...")
    scheduler = BackgroundScheduler()  # Create a scheduler that runs in the background

    # Schedule the weekly report job if a chat ID is provided in config.py
    if YOUR_TELEGRAM_CHAT_ID:
        scheduler.add_job(
            send_scheduled_report,  # The function to run (from bot_logic.py)
            'cron',  # Schedule using cron-like syntax (for repeating jobs)
            day_of_week='sun',  # Run on Sunday
            hour=20,  # At 8 PM (20:00)
            minute=0,  # At 0 minutes (on the hour)
            args=[application.bot]  # Pass the bot instance so send_scheduled_report can send messages
        )
        logger.info(f"Weekly report scheduled for Sundays at 20:00 to chat ID: {YOUR_TELEGRAM_CHAT_ID}")
    else:
        logger.warning("YOUR_TELEGRAM_CHAT_ID is not set or is 0 in config.py. Weekly reports will not be sent.")

    # Schedule OLED statistics updates if OLED is enabled
    if oled_manager:
        scheduler.add_job(
            update_oled_stats,
            'interval',
            seconds=30,  # Update every 30 seconds
            id='oled_stats_update'
        )
        logger.info("OLED statistics update scheduled every 30 seconds.")

    scheduler.start()  # Start the scheduler so it begins monitoring scheduled jobs
    logger.info("Scheduler started.")

    # --- Start the Telegram Bot ---
    logger.info("Starting Telegram bot polling...")
    # application.run_polling() starts the bot and listens for messages.
    # This call blocks (runs continuously) until you stop the script (e.g., with Ctrl+C).
    application.run_polling()

    logger.info("Telegram bot stopped.")

    # --- Clean up after the Bot Stops ---
    # This code runs when application.run_polling() finishes (e.g., user presses Ctrl+C).
    if scheduler:
        scheduler.shutdown()  # Stop the scheduler cleanly
        logger.info("Scheduler shut down.")
    
    if oled_manager:
        shutdown_oled_display()
        logger.info("OLED display shut down.")


# This ensures main() is called only when the script is run directly.
if __name__ == '__main__':
    main()