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
from config import YOUR_TELEGRAM_CHAT_ID, is_admin, ADMIN_CHAT_IDS
from report_cleanup import clean_detailed_report, get_report_entries

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for Conversation Handlers
ASK_CREDIT_AMOUNT, RECEIVE_CREDIT_AMOUNT = range(2)
ASK_CASHOUT_TYPE, ASK_MANUAL_CASHOUT_AMOUNT, RECEIVE_MANUAL_CASHOUT_AMOUNT = range(3)
ASK_CLEANUP_START_DATE, ASK_CLEANUP_END_DATE, CONFIRM_CLEANUP = range(3)

# Keyboard Definitions (Admin gets cleanup button)
def get_main_keyboard(chat_id):
    buttons = [
        [KeyboardButton("➕ Add Walk"), KeyboardButton("💰 Current Balance")],
        [KeyboardButton("📊 Detailed Report"), KeyboardButton("❓ Help")],
        [KeyboardButton("💳 Give Credit"), KeyboardButton("💸 Cash Out")]
    ]
    if is_admin(chat_id):
        buttons.append([KeyboardButton("🗑️ Cleanup Detailed Report")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_cashout_inline_keyboard(balance):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💸 Pay Out All ({balance:.2f} MDL)", callback_data="cashout_all")],
        [InlineKeyboardButton("✏️ Manual Amount", callback_data="cashout_manual")]
    ])

# --- Conversation Handlers ---

async def credit_start(update, context):
    await update.message.reply_text("Please enter the credit amount (in MDL).")
    return ASK_CREDIT_AMOUNT

async def receive_credit_amount(update, context):
    if global_stats_manager:
        global_stats_manager.record_activity()
    try:
        amount = float(update.message.text)
        if amount <= 0:
            await update.message.reply_text("Credit amount must be positive. Please try again.")
            return ASK_CREDIT_AMOUNT
        record_credit_given(amount, f"Credit (advance) of {amount:.2f} MDL")
        current_balance = get_current_balance()
        if global_oled_display:
            global_oled_display.show_notification(f"Credit: -{amount:.0f} MDL", 3)
        await update.message.reply_text(
            f"✅ Credit of *{amount:.2f} MDL* recorded. "
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(update.effective_chat.id)
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
    await update.message.reply_text('Operation "Give Credit" cancelled.', reply_markup=get_main_keyboard(update.effective_chat.id))
    return ConversationHandler.END

async def cashout_start(update, context):
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
        if global_oled_display:
            global_oled_display.show_notification(f"Paid Out: {current_balance:.0f}", 3)
        await query.edit_message_text(
            f"✅ *{current_balance:.2f} MDL* was paid out.\n"
            f"Current balance: *{new_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=None
        )
        await query.message.reply_text("Operation completed.", reply_markup=get_main_keyboard(query.message.chat.id))
        return ConversationHandler.END
    elif query.data == "cashout_manual":
        await query.edit_message_text("Please enter the amount to pay out (in MDL).")
        return ASK_MANUAL_CASHOUT_AMOUNT

async def receive_manual_cashout_amount(update, context):
    if global_stats_manager:
        global_stats_manager.record_activity()
    try:
        amount = float(update.message.text)
        if amount == 0:
            await update.message.reply_text("Amount must be greater than zero. Please try again.")
            return ASK_MANUAL_CASHOUT_AMOUNT
        record_payment(amount, f"Manual cash out of {amount:.2f} MDL")
        current_balance = get_current_balance()
        if global_oled_display:
            global_oled_display.show_notification(f"Cash Out: {amount:.0f}", 3)
        await update.message.reply_text(
            f"✅ Recorded payout of *{amount:.2f} MDL*.\n"
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(update.effective_chat.id)
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
    await update.message.reply_text('Operation "Cash Out" cancelled.', reply_markup=get_main_keyboard(update.effective_chat.id))
    return ConversationHandler.END

# --- Enhanced Detailed Report Command ---
async def detailed_report_command(update, context):
    chat_id = update.effective_chat.id
    transactions = get_all_transactions_for_report()
    walk_count = len([t for t in transactions if t[2] == 'walk'])
    walk_total_amount = sum([t[1] for t in transactions if t[2] == 'walk'])
    current_balance = get_current_balance()
    total_payment_credit_amount = sum([t[1] for t in transactions if t[2] in ('credit', 'payment')])
    walks = [t for t in transactions if t[2] == 'walk']
    walk_details = "\n".join([f"{t[0][:10]} - {t[1]:.2f} MDL" for t in walks]) or "No walks recorded."

    report_message = (
        f"*Detailed Report ({datetime.now().strftime('%Y-%m-%d')})*\n\n"
        f"Walks completed: *{walk_count}*\n"
        f"Total amount earned from walks: *{walk_total_amount:.2f} MDL*\n"
        f"Current outstanding balance: *{current_balance:.2f} MDL*\n"
        f"Total payments/credits received: *{total_payment_credit_amount:.2f} MDL*\n\n"
        f"*Walks:*\n{walk_details}"
    )
    await update.message.reply_text(report_message, parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(chat_id))
    if is_admin(chat_id):
        keyboard = [
            [InlineKeyboardButton("🗑️ Cleanup Detailed Report", callback_data="cleanup_start")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Admin: You can clean up the detailed report for a date range.",
            reply_markup=reply_markup
        )

# --- Cleanup Conversation (Admin Only) ---
async def cleanup_start_callback(update, context):
    query = update.callback_query
    chat_id = query.message.chat.id
    if not is_admin(chat_id):
        await query.answer("Access denied.", show_alert=True)
        return ConversationHandler.END
    await query.message.reply_text("Enter START date for cleanup (YYYY-MM-DD):")
    context.user_data.clear()
    return ASK_CLEANUP_START_DATE

async def cleanup_get_start_date(update, context):
    context.user_data["cleanup_start_date"] = update.message.text.strip()
    await update.message.reply_text("Enter END date for cleanup (YYYY-MM-DD):")
    return ASK_CLEANUP_END_DATE

async def cleanup_get_end_date(update, context):
    context.user_data["cleanup_end_date"] = update.message.text.strip()
    from_date = context.user_data["cleanup_start_date"]
    to_date = context.user_data["cleanup_end_date"]
    entries = get_report_entries(from_date, to_date)
    walks = [e for e in entries if e["type"] == "walk"]
    if walks:
        summary = "\n".join([f"{w['date'][:10]} - {w['amount']:.2f} MDL" for w in walks])
        msg = (
            f"Walks from {from_date} to {to_date}:\n"
            f"{summary}\n"
            f"Total walks: {len(walks)}\n"
            "Confirm cleanup?"
        )
    else:
        msg = f"No walks found between {from_date} and {to_date}. Cancelled."
        await update.message.reply_text(msg)
        return ConversationHandler.END
    await update.message.reply_text(
        msg,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Yes", callback_data="cleanup_yes"),
             InlineKeyboardButton("❌ No", callback_data="cleanup_no")]
        ])
    )
    context.user_data["cleanup_walk_count"] = len(walks)
    return CONFIRM_CLEANUP

async def cleanup_confirm(update, context):
    query = update.callback_query
    chat_id = query.message.chat.id
    if not is_admin(chat_id):
        await query.answer("Access denied.", show_alert=True)
        return ConversationHandler.END
    if query.data == "cleanup_yes":
        from_date = context.user_data["cleanup_start_date"]
        to_date = context.user_data["cleanup_end_date"]
        result = clean_detailed_report(from_date, to_date)
        if result["success"]:
            await query.edit_message_text(
                f"Deleted {result['deleted_count']} entries (including {context.user_data['cleanup_walk_count']} walks) from {from_date} to {to_date}.",
                reply_markup=get_main_keyboard(chat_id)
            )
        else:
            await query.edit_message_text(f"Failed: {result['error']}", reply_markup=get_main_keyboard(chat_id))
    else:
        await query.edit_message_text("Cleanup cancelled.", reply_markup=get_main_keyboard(chat_id))
    return ConversationHandler.END

# --- Other Standard Commands ---
async def start(update, context):
    await update.message.reply_text(
        "Welcome to k9LogBot! Use the buttons below or commands to interact.",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def help_command(update, context):
    await update.message.reply_text(
        "Available commands:\n"
        "/addwalk - Add a walk\n"
        "/balance - Show current balance\n"
        "/setinitial - Set initial balance\n"
        "/report - Show detailed report\n"
        "Or use the buttons below.",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def add_walk_command(update, context):
    add_walk()
    current_balance = get_current_balance()
    await update.message.reply_text(
        f"✅ Walk recorded. Current balance: *{current_balance:.2f} MDL*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def balance_command(update, context):
    current_balance = get_current_balance()
    await update.message.reply_text(
        f"Current balance: *{current_balance:.2f} MDL*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def set_initial_balance_command(update, context):
    await update.message.reply_text("Please enter the initial balance (in MDL).")
    context.user_data["await_initial_balance"] = True

async def receive_initial_balance(update, context):
    try:
        amount = float(update.message.text)
        set_initial_balance(amount)
        await update.message.reply_text(
            f"Initial balance set to *{amount:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(update.effective_chat.id)
        )
    except Exception:
        await update.message.reply_text("Invalid amount. Please enter a number.")
    finally:
        context.user_data["await_initial_balance"] = False

# Global Error Handler
async def error(update, context):
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.effective_message:
        await update.effective_message.reply_text("Oops! Something went wrong. Please try again or use /help.")

# Handler Setup
def setup_handlers(application, stats_manager=None, oled_display=None):
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

    # --- Admin Cleanup ConversationHandler ---
    cleanup_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(cleanup_start_callback, pattern="^cleanup_start$"),
                     MessageHandler(filters.Regex("^🗑️ Cleanup Detailed Report$"), cleanup_start_callback)],
        states={
            ASK_CLEANUP_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cleanup_get_start_date)],
            ASK_CLEANUP_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cleanup_get_end_date)],
            CONFIRM_CLEANUP: [CallbackQueryHandler(cleanup_confirm, pattern="^cleanup_yes$|^cleanup_no$")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        allow_reentry=True
    )
    application.add_handler(cleanup_conv_handler)

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

    # Set initial balance entry handler
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(r"^\d+(\.\d+)?$"),
        receive_initial_balance
    ))

    application.add_error_handler(error)

# Scheduled Report Function
async def send_scheduled_report(bot_instance):
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

    if global_oled_display:
        global_oled_display.show_notification("Weekly Report Sent", 3)
