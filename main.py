# main.py
from telegram.ext import Application, ApplicationBuilder
from telegram.constants import ParseMode
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import time
import logging

# Import configuration details and bot's logic functions
from config import TELEGRAM_BOT_TOKEN, YOUR_TELEGRAM_CHAT_ID, STATS_CACHE_DURATION, AUTO_CLEANUP_DAY, AUTO_CLEANUP_MONTHS_TO_KEEP, AUTO_CLEANUP_ENABLED
from database import init_db, get_current_balance, get_all_transactions_for_report, get_stats_summary, auto_cleanup_old_records
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
        # Cache for database stats to reduce query frequency
        self._stats_cache = {}
        self._last_cache_update = None
        self._cache_duration = STATS_CACHE_DURATION  # Configurable cache duration
        
    def get_stats(self):
        """Get current bot statistics for display."""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Use cached database stats to reduce load
        now = datetime.now()
        if (self._last_cache_update is None or 
            (now - self._last_cache_update).total_seconds() > self._cache_duration):
            
            # Update cache with optimized database query
            self._stats_cache = get_stats_summary()
            self._stats_cache['current_balance'] = get_current_balance()
            self._last_cache_update = now
        
        return {
            'bot_running': self.bot_running,
            'uptime': uptime,
            'current_balance': self._stats_cache.get('current_balance', 0.0),
            'total_walks': self._stats_cache.get('total_walks', 0),
            'walks_today': self._stats_cache.get('walks_today', 0),
            'total_earned': self._stats_cache.get('total_earned', 0.0),
            'message_count': self.message_count,
            'last_activity': self.last_activity
        }
    
    def record_activity(self):
        """Record bot activity."""
        self.last_activity = datetime.now()
        self.message_count += 1
        # Invalidate cache when activity occurs
        self._last_cache_update = None

# Global stats manager
stats_manager = BotStatsManager()

async def run_auto_cleanup(bot, months_to_keep=1):
    """
    Automatic monthly cleanup function.
    Deletes old transaction records without affecting balance.
    Sends notification to admin when cleanup is performed.
    """
    logger.info("Running automatic monthly cleanup...")
    
    try:
        result = auto_cleanup_old_records(months_to_keep)
        
        if result["success"]:
            deleted_count = result["deleted_count"]
            cutoff_date = result["cutoff_date"]
            
            logger.info(f"Auto-cleanup completed: Deleted {deleted_count} records older than {cutoff_date}")
            
            # Send notification to admin
            if YOUR_TELEGRAM_CHAT_ID:
                notification = (
                    f"🧹 *Auto-Cleanup Completed*\n\n"
                    f"✅ Deleted {deleted_count} old records\n"
                    f"📅 Records older than: {cutoff_date}\n"
                    f"💾 Kept: Current month records\n"
                    f"⚖️ Balance: Unchanged\n\n"
                    f"_Automatic database maintenance_"
                )
                await bot.send_message(
                    chat_id=YOUR_TELEGRAM_CHAT_ID,
                    text=notification,
                    parse_mode=ParseMode.MARKDOWN
                )
                logger.info("Sent auto-cleanup notification to admin")
        else:
            error_msg = result.get("error", "Unknown error")
            logger.error(f"Auto-cleanup failed: {error_msg}")
            
            if YOUR_TELEGRAM_CHAT_ID:
                await bot.send_message(
                    chat_id=YOUR_TELEGRAM_CHAT_ID,
                    text=f"❌ *Auto-Cleanup Failed*\n\nError: {error_msg}",
                    parse_mode=ParseMode.MARKDOWN
                )
    except Exception as e:
        logger.error(f"Auto-cleanup exception: {e}")
        if YOUR_TELEGRAM_CHAT_ID:
            await bot.send_message(
                chat_id=YOUR_TELEGRAM_CHAT_ID,
                text=f"❌ *Auto-Cleanup Error*\n\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )

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

    # Schedule automatic monthly cleanup (runs on specified day of each month)
    if AUTO_CLEANUP_ENABLED:
        scheduler.add_job(
            run_auto_cleanup,
            'cron',
            day=AUTO_CLEANUP_DAY,
            hour=3,
            minute=0,
            args=[application.bot, AUTO_CLEANUP_MONTHS_TO_KEEP]
        )
        logger.info(f"Auto-cleanup scheduled for day {AUTO_CLEANUP_DAY} of each month at 03:00 (keeping {AUTO_CLEANUP_MONTHS_TO_KEEP} month(s) of records)")
    else:
        logger.info("Auto-cleanup is disabled")
    
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
