# main.py
import datetime
import logging

from telegram.ext import ApplicationBuilder, CallbackContext
from telegram.constants import ParseMode

from config import (
    TELEGRAM_BOT_TOKEN, YOUR_TELEGRAM_CHAT_ID, STATS_CACHE_DURATION,
    AUTO_CLEANUP_DAY, AUTO_CLEANUP_MONTHS_TO_KEEP, AUTO_CLEANUP_ENABLED
)
from database import (
    init_db, get_current_balance, get_stats_summary,
    auto_cleanup_old_records, get_users_with_reminders, get_walks_today
)
from bot_logic import setup_handlers, send_scheduled_report
from oled_display import OLEDDisplayManager

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)


class BotStatsManager:
    def __init__(self):
        self.start_time = datetime.datetime.now()
        self.bot_running = False
        self.last_activity = datetime.datetime.now()
        self.message_count = 0
        self._stats_cache = {}
        self._last_cache_update = None
        self._cache_duration = STATS_CACHE_DURATION

    def get_stats(self):
        uptime = (datetime.datetime.now() - self.start_time).total_seconds()
        now = datetime.datetime.now()
        if (self._last_cache_update is None or
                (now - self._last_cache_update).total_seconds() > self._cache_duration):
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
            'last_activity': self.last_activity,
        }

    def record_activity(self):
        self.last_activity = datetime.datetime.now()
        self.message_count += 1
        self._last_cache_update = None


# Global stats manager
stats_manager = BotStatsManager()


# --- Scheduled job callbacks (run inside asyncio via JobQueue) ---

async def weekly_report_job(context: CallbackContext):
    """Send the weekly summary report."""
    await send_scheduled_report(context.bot)


async def auto_cleanup_job(context: CallbackContext):
    """Monthly automatic database cleanup."""
    logger.info("Running automatic monthly cleanup...")
    result = auto_cleanup_old_records(AUTO_CLEANUP_MONTHS_TO_KEEP)
    if result["success"]:
        logger.info(f"Auto-cleanup: deleted {result['deleted_count']} records older than {result['cutoff_date']}")
        if YOUR_TELEGRAM_CHAT_ID:
            await context.bot.send_message(
                chat_id=YOUR_TELEGRAM_CHAT_ID,
                text=(
                    f"🧹 *Auto-Cleanup Completed*\n\n"
                    f"✅ Deleted {result['deleted_count']} old records\n"
                    f"📅 Records older than: {result['cutoff_date']}\n"
                    f"⚖️ Balance: Unchanged"
                ),
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        logger.error(f"Auto-cleanup failed: {result.get('error')}")
        if YOUR_TELEGRAM_CHAT_ID:
            await context.bot.send_message(
                chat_id=YOUR_TELEGRAM_CHAT_ID,
                text=f"❌ *Auto-Cleanup Failed*\n\n{result.get('error', 'Unknown error')}",
                parse_mode=ParseMode.MARKDOWN
            )


async def daily_reminders_job(context: CallbackContext):
    """Send daily reminders to users who haven't logged a walk yet."""
    current_time = datetime.datetime.now().strftime('%H:%M')
    if get_walks_today() > 0:
        return  # walks already logged today, no reminder needed
    for user in get_users_with_reminders():
        if user['reminder_time'] == current_time:
            try:
                await context.bot.send_message(
                    chat_id=user['user_id'],
                    text="🐕 *Daily Reminder*\n\nNo walks logged today yet!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.warning(f"Reminder failed for {user['user_id']}: {e}")


def main():
    logger.info("Initializing K9LogBot...")
    init_db()
    logger.info("Database initialized.")

    oled_display = OLEDDisplayManager(stats_manager.get_stats)
    oled_display.start()

    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    setup_handlers(application, stats_manager, oled_display)

    job_queue = application.job_queue

    if YOUR_TELEGRAM_CHAT_ID:
        job_queue.run_daily(
            weekly_report_job,
            time=datetime.time(hour=20, minute=0),
            days=(6,),  # Sunday (0=Mon … 6=Sun)
            name="weekly_report"
        )
        logger.info("Weekly report scheduled for Sundays at 20:00")
    else:
        logger.warning("YOUR_TELEGRAM_CHAT_ID not set — weekly reports disabled.")

    if AUTO_CLEANUP_ENABLED:
        job_queue.run_monthly(
            auto_cleanup_job,
            when=datetime.time(hour=3, minute=0),
            day=AUTO_CLEANUP_DAY,
            name="auto_cleanup"
        )
        logger.info(f"Auto-cleanup scheduled for day {AUTO_CLEANUP_DAY} of each month at 03:00")
    else:
        logger.info("Auto-cleanup is disabled.")

    # Check reminders every minute
    job_queue.run_repeating(daily_reminders_job, interval=60, name="daily_reminders")

    oled_display.show_notification("Bot Starting Up!", 3)

    try:
        stats_manager.bot_running = True
        oled_display.show_notification("Bot Online!", 2)
        logger.info("Starting Telegram bot polling...")
        application.run_polling()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal.")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        oled_display.show_notification(f"Bot Error: {str(e)[:20]}", 5)
    finally:
        stats_manager.bot_running = False
        oled_display.show_notification("Bot Shutting Down", 2)
        oled_display.stop()
        logger.info("Bot stopped.")


if __name__ == '__main__':
    main()
