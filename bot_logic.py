# bot_logic.py
from telegram.ext import (
    CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime

from database import (
    init_db, add_walk, get_current_balance,
    set_initial_balance, record_payment, record_credit_given,
    get_weekly_report_data, get_all_transactions_for_report
)
from config import YOUR_TELEGRAM_CHAT_ID

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for Conversation Handlers
ASK_CREDIT_AMOUNT, RECEIVE_CREDIT_AMOUNT = range(2)
ASK_CASHOUT_TYPE, ASK_MANUAL_CASHOUT_AMOUNT, RECEIVE_MANUAL_CASHOUT_AMOUNT = range(3)

# Keyboard Definitions
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("➕ Add Walk"), KeyboardButton("💰 Current Balance")],
    [KeyboardButton("💳 Give Credit"), KeyboardButton("💸 Cash Out")],
    [KeyboardButton("📊 Detailed Report"), KeyboardButton("❓ Help")],
], resize_keyboard=True, one_time_keyboard=False)

def get_cashout_inline_keyboard(current_balance):
    """Creates an inline keyboard for the Cash Out process."""
    keyboard = [
        [InlineKeyboardButton(f"Pay All ({current_balance:.2f} MDL)", callback_data="cashout_all")],
        [InlineKeyboardButton("Enter Amount Manually", callback_data="cashout_manual")],
    ]
    return InlineKeyboardMarkup(keyboard)

# Global references (will be set in setup_handlers)
global_stats_manager = None
global_oled_display = None

# Command Handlers
async def start(update, context):
    """Sends a welcome message and displays the main keyboard buttons."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    message = (
        "Hello! I'm your dog walking payment tracker bot.\n\n"
        "Use the buttons below for quick actions, or type a command.\n\n"
        "Available commands:\n"
        "/addwalk - Records a dog walk (75 MDL).\n"
        "/balance - Shows your current balance.\n"
        "/credit - Records credit given (e.g., Nana pays you an advance).\n"
        "/cashout - Records money you pay out (e.g., to Nana).\n"
        "/report - Get a detailed report of all transactions.\n"
        "/setinitial <amount> - Set the initial balance.\n"
        "/help - Shows this message again."
    )
    await update.message.reply_text(message, reply_markup=MAIN_KEYBOARD)

async def add_walk_command(update, context):
    """Records a dog walk and updates the balance."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    add_walk()
    current_balance = get_current_balance()
    
    # Show notification on OLED
    if global_oled_display:
        global_oled_display.show_notification("Walk Added! +75 MDL", 3)
    
    await update.message.reply_text(
        f"✅ Walk recorded! Current balance: *{current_balance:.2f} MDL*",
        parse_mode=ParseMode.MARKDOWN
    )

async def balance_command(update, context):
    """Shows the current outstanding balance with clear labels."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    current_balance = get_current_balance()
    if current_balance > 0:
        status_text = f"Current Balance: *{current_balance:.2f} MDL* (They owe you)"
    elif current_balance < 0:
        status_text = f"Current Balance: *{abs(current_balance):.2f} MDL* (You owe them)"
    else:
        status_text = "Current Balance: *0.00 MDL* (Balance is zero)"

    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

async def help_command(update, context):
    """Sends the help message."""
    await start(update, context)

async def set_initial_balance_command(update, context):
    """Sets an initial balance manually."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    try:
        if not context.args:
            await update.message.reply_text(
                "Please provide an amount. Usage: `/setinitial <amount>`\n"
                "Example: `/setinitial 0` (reset), `/setinitial -150` (overpaid)",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        amount = float(context.args[0])
        set_initial_balance(amount)
        current_balance = get_current_balance()
        
        # Show notification on OLED
        if global_oled_display:
            global_oled_display.show_notification(f"Balance Set: {amount:.0f}", 3)
        
        await update.message.reply_text(
            f"Initial balance set to *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:
        await update.message.reply_text("Invalid amount. Please enter a number.")
    except Exception as e:
        logger.error(f"Error setting initial balance: {e}")
        await update.message.reply_text("An error occurred while setting the initial balance.")

async def detailed_report_command(update, context):
    """Provides a detailed report of all financial transactions."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    transactions = get_all_transactions_for_report()
    current_balance = get_current_balance()

    if not transactions:
        report_message = "No transactions found."
    else:
        report_message = "*Detailed Transaction Report:*\n\n"
        for ts, amount, tr_type, desc in transactions:
            timestamp = datetime.fromisoformat(ts)
            if tr_type == 'walk':
                type_display = "Walk"
            elif tr_type == 'payment':
                type_display = "Payment"
            elif tr_type == 'credit_given':
                type_display = "Credit Given"
            elif tr_type == 'manual_cashout':
                type_display = "Cash Out"
            else:
                type_display = tr_type

            report_message += f"`{timestamp.strftime('%Y-%m-%d %H:%M')}`: {type_display}: *{amount:.2f} MDL*\n"

        report_message += "\n"
        if current_balance > 0:
            report_message += f"*Total: To Be Paid: {current_balance:.2f} MDL*\n"
        elif current_balance < 0:
            report_message += f"*Total: Overpaid: {abs(current_balance):.2f} MDL*\n"
        else:
            report_message += "*Total: Balance is Zero: 0.00 MDL*\n"

    await update.message.reply_text(report_message, parse_mode=ParseMode.MARKDOWN)

# Conversation Handler Functions for "Give Credit"
async def credit_start(update, context):
    """Starts the 'Give Credit' conversation."""
    await update.message.reply_text("Please enter the credit amount (in MDL).")
    return ASK_CREDIT_AMOUNT

async def receive_credit_amount(update, context):
    """Receives the credit amount and records the transaction."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Credit amount must be positive. Please try again.")
            return ASK_CREDIT_AMOUNT

        record_credit_given(amount, f"Credit (advance) of {amount:.2f} MDL")
        current_balance = get_current_balance()
        
        # Show notification on OLED
        if global_oled_display:
            global_oled_display.show_notification(f"Credit: -{amount:.0f} MDL", 3)
        
        await update.message.reply_text(
            f"✅ Credit of *{amount:.2f} MDL* recorded. "
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Invalid amount format. Please enter a number.")
        return ASK_CREDIT_AMOUNT
    except Exception as e:
        logger.error(f"Error in receive_credit_amount: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

async def credit_cancel(update, context):
    """Cancels the 'Give Credit' conversation."""
    await update.message.reply_text('Operation "Give Credit" cancelled.', reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

# Conversation Handler Functions for "Cash Out"
async def cashout_start(update, context):
    """Starts the 'Cash Out' conversation."""
    current_balance = get_current_balance()
    keyboard = get_cashout_inline_keyboard(current_balance)
    await update.message.reply_text(
        f"Current amount to be paid out: *{current_balance:.2f} MDL*.\n"
        "What do you want to do?",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_CASHOUT_TYPE

async def cashout_type_chosen(update, context):
    """Handles the choice between full cash out or manual amount."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    query = update.callback_query
    await query.answer()

    if query.data == "cashout_all":
        current_balance = get_current_balance()
        if current_balance <= 0:
            await query.edit_message_text(
                f"Balance: *{current_balance:.2f} MDL*. Nothing to pay out.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=None
            )
            return ConversationHandler.END

        record_payment(current_balance, "Full settlement")
        new_balance = get_current_balance()
        
        # Show notification on OLED
        if global_oled_display:
            global_oled_display.show_notification(f"Paid Out: {current_balance:.0f}", 3)
        
        await query.edit_message_text(
            f"✅ *{current_balance:.2f} MDL* was paid out.\n"
            f"Current balance: *{new_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=None
        )
        await query.message.reply_text("Operation completed.", reply_markup=MAIN_KEYBOARD)
        return ConversationHandler.END

    elif query.data == "cashout_manual":
        await query.edit_message_text("Please enter the amount to pay out (in MDL).")
        return ASK_MANUAL_CASHOUT_AMOUNT

async def receive_manual_cashout_amount(update, context):
    """Receives the manual cash out amount and records the payment."""
    if global_stats_manager:
        global_stats_manager.record_activity()
    
    try:
        amount = float(update.message.text)
        if amount == 0:
            await update.message.reply_text("Amount must be greater than zero. Please try again.")
            return ASK_MANUAL_CASHOUT_AMOUNT

        record_payment(amount, f"Manual cash out of {amount:.2f} MDL")
        current_balance = get_current_balance()
        
        # Show notification on OLED
        if global_oled_display:
            global_oled_display.show_notification(f"Cash Out: {amount:.0f}", 3)
        
        await update.message.reply_text(
            f"✅ Recorded payout of *{amount:.2f} MDL*.\n"
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KEYBOARD
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Invalid amount format. Please enter a number.")
        return ASK_MANUAL_CASHOUT_AMOUNT
    except Exception as e:
        logger.error(f"Error in receive_manual_cashout_amount: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

async def cashout_cancel(update, context):
    """Cancels the 'Cash Out' conversation."""
    await update.message.reply_text('Operation "Cash Out" cancelled.', reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END

# Global Error Handler
async def error(update, context):
    """Logs errors and sends a friendly message."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("Oops! Something went wrong. Please try again or use /help.")

# Setup Handlers for the Application
def setup_handlers(application, stats_manager=None, oled_display=None):
    """Sets up all handlers for the Telegram Application."""
    global global_stats_manager, global_oled_display
    global_stats_manager = stats_manager
    global_oled_display = oled_display
    
    # Conversation Handlers
    credit_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("credit", credit_start),
            MessageHandler(filters.Regex("^💳 Give Credit$"), credit_start)
        ],
        states={
            ASK_CREDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_credit_amount)],
        },
        fallbacks=[CommandHandler("cancel", credit_cancel), MessageHandler(filters.COMMAND, credit_cancel)],
        allow_reentry=True
    )
    application.add_handler(credit_conv_handler)

    cashout_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("cashout", cashout_start),
            MessageHandler(filters.Regex("^💸 Cash Out$"), cashout_start)
        ],
        states={
            ASK_CASHOUT_TYPE: [CallbackQueryHandler(cashout_type_chosen)],
            ASK_MANUAL_CASHOUT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_cashout_amount)],
        },
        fallbacks=[CommandHandler("cancel", cashout_cancel), MessageHandler(filters.COMMAND, cashout_cancel)],
        allow_reentry=True
    )
    application.add_handler(cashout_conv_handler)

    # Regular Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addwalk", add_walk_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("setinitial", set_initial_balance_command))
    application.add_handler(CommandHandler("report", detailed_report_command))

    # Message Handlers for Reply Keyboard Buttons
    application.add_handler(MessageHandler(filters.Regex("^➕ Add Walk$"), add_walk_command))
    application.add_handler(MessageHandler(filters.Regex("^💰 Current Balance$"), balance_command))
    application.add_handler(MessageHandler(filters.Regex("^📊 Detailed Report$"), detailed_report_command))
    application.add_handler(MessageHandler(filters.Regex("^❓ Help$"), help_command))

    application.add_error_handler(error)

# Scheduled Report Function
async def send_scheduled_report(bot_instance):
    """Sends a weekly report to the configured chat."""
    walk_count, walk_total_amount, total_payment_credit_amount = get_weekly_report_data()
    current_balance = get_current_balance()

    report_message = (
        f"*Weekly Report (Week ending {datetime.now().strftime('%Y-%m-%d')})*\n\n"
        f"Walks completed this week: *{walk_count}*\n"
        f"Total amount earned from walks: *{walk_total_amount:.2f} MDL*\n"
        f"Current outstanding balance: *{current_balance:.2f} MDL*\n"
        f"Total payments/credits received: *{total_payment_credit_amount:.2f} MDL*\n\n"
        "For a detailed report, use the '📊 Detailed Report' button or the `/report` command."
    )

    await bot_instance.send_message(
        chat_id=YOUR_TELEGRAM_CHAT_ID,
        text=report_message,
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info("Sent weekly report.")
    
    # Show notification on OLED
    if global_oled_display:
        global_oled_display.show_notification("Weekly Report Sent", 3)
