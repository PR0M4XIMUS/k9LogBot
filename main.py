# main.py
from telegram.ext import Application, ApplicationBuilder
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import time
import logging

# Import configuration details and bot's logic functions
from config import TELEGRAM_BOT_TOKEN, YOUR_TELEGRAM_CHAT_ID
from database import init_db, get_current_balance, get_all_transactions_for_report
from bot_logic import setup_handlers, send_scheduled_report, error
from oled_display import OLEDDisplayManager

# Set up Logging for the Main Script
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

class BotStatsManager:
    def __init__(self):
        self.start_time = datetime.now()
        self.bot_running = False
        self.last_activity = datetime.now()
        self.message_count = 0
        
    def get_stats(self):
        """Get current bot statistics for display."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Get database stats
        transactions = get_all_transactions_for_report()
        total_walks = len([t for t in transactions if t[2] == 'walk'])
        total_earned = sum([t[1] for t in transactions if t[2] == 'walk'])
        
        # Walks today
        today = datetime.now().date()
        walks_today = len([t for t in transactions if t[2] == 'walk' and 
                          datetime.fromisoformat(t[0]).date() == today])
        
        return {
            'bot_running': self.bot_running,
            'uptime': uptime,
            'current_balance': get_current_balance(),
            'total_walks': total_walks,
            'walks_today': walks_today,
            'total_earned': total_earned,
            'message_count': self.message_count,
            'last_activity': self.last_activity
        }
    
    def record_activity(self):
        """Record bot activity."""
        self.last_activity = datetime.now()
        self.message_count += 1

# Global stats manager
stats_manager = BotStatsManager()

def main():
    """
    This is the main function that starts the bot, scheduler, and OLED display.
    """
    logger.info("Initializing K9LogBot...")
    
    # Initialize database
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized.")
    
    # Initialize OLED display
    logger.info("Initializing OLED display...")
    oled_display = OLEDDisplayManager(stats_manager.get_stats)
    oled_display.start()
    
    # Build the Telegram Application
    logger.info("Building Telegram Application...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    logger.info("Telegram Application built.")
    
    # Set up Bot Command Handlers
    logger.info("Setting up bot command handlers...")
    setup_handlers(application, stats_manager, oled_display)
    application.add_error_handler(error)
    logger.info("Bot command handlers and error handler set up.")
    
    # Setup APScheduler for Weekly Reports
    logger.info("Setting up weekly report scheduler...")
    scheduler = BackgroundScheduler()
    
    # Schedule the weekly report job if a chat ID is provided
    if YOUR_TELEGRAM_CHAT_ID:
        scheduler.add_job(
            send_scheduled_report,
            'cron',
            day_of_week='sun',
            hour=20,
            minute=0,
            args=[application.bot]
        )
        logger.info(f"Weekly report scheduled for Sundays at 20:00 to chat ID: {YOUR_TELEGRAM_CHAT_ID}")
    else:
        logger.warning("YOUR_TELEGRAM_CHAT_ID is not set. Weekly reports will not be sent.")
    
    scheduler.start()
    logger.info("Scheduler started.")
    
    # Show startup notification on display
    oled_display.show_notification("Bot Starting Up!", 3)
    
    try:
        # Start the Telegram Bot
        logger.info("Starting Telegram bot polling...")
        stats_manager.bot_running = True
        oled_display.show_notification("Bot Online!", 2)
        
        # This call blocks until you stop the script
        application.run_polling()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        oled_display.show_notification(f"Bot Error: {str(e)[:20]}", 5)
    finally:
        # Clean up
        logger.info("Telegram bot stopped.")
        stats_manager.bot_running = False
        oled_display.show_notification("Bot Shutting Down", 2)
        
        scheduler.shutdown()
        logger.info("Scheduler shut down.")
        
        oled_display.stop()
        logger.info("OLED display stopped.")

if __name__ == '__main__':
    main()
