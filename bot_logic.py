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
from report_cleanup import clean_detailed_report, get_report_entries, get_recent_entries, clean_specific_entries

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# States for Conversation Handlers
ASK_CREDIT_AMOUNT, RECEIVE_CREDIT_AMOUNT = range(2)
ASK_CASHOUT_TYPE, ASK_MANUAL_CASHOUT_AMOUNT, RECEIVE_MANUAL_CASHOUT_AMOUNT = range(3)
ASK_CLEANUP_OPTION, ASK_CLEANUP_START_DATE, ASK_CLEANUP_END_DATE, CONFIRM_CLEANUP = range(4)

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
    chat_id = query.message.chat.id if query else update.message.chat.id
    
    if not is_admin(chat_id):
        if query:
            await query.answer("Access denied.", show_alert=True)
        else:
            await update.message.reply_text("Access denied.")
        return ConversationHandler.END
    
    # Clear any previous data
    context.user_data.clear()
    
    # Show preset cleanup options
    keyboard = [
        [InlineKeyboardButton("📅 Last Week", callback_data="cleanup_preset_week")],
        [InlineKeyboardButton("📆 Last Month", callback_data="cleanup_preset_month")],
        [InlineKeyboardButton("📋 Last 10 Entries", callback_data="cleanup_preset_10")],
        [InlineKeyboardButton("🎯 Custom Date Range", callback_data="cleanup_custom")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cleanup_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message = (
        "🗑️ *Admin Cleanup Options*\n\n"
        "Choose a cleanup option:\n"
        "• Last Week: Delete entries from the past 7 days\n"
        "• Last Month: Delete entries from the past 30 days\n"
        "• Last 10 Entries: Delete the most recent 10 transactions\n"
        "• Custom: Specify your own date range\n"
        "• Cancel: Exit cleanup"
    )
    
    if query:
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
    
    return ASK_CLEANUP_OPTION

async def cleanup_option_chosen(update, context):
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("Access denied.", show_alert=True)
        return ConversationHandler.END
    
    if query.data == "cleanup_cancel":
        await query.edit_message_text("Cleanup cancelled.", reply_markup=get_main_keyboard(chat_id))
        return ConversationHandler.END
    
    from datetime import datetime, timedelta
    today = datetime.now()
    
    if query.data == "cleanup_preset_week":
        from_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        context.user_data["cleanup_start_date"] = from_date
        context.user_data["cleanup_end_date"] = to_date
        context.user_data["cleanup_type"] = "Last Week"
        return await show_cleanup_preview(update, context)
        
    elif query.data == "cleanup_preset_month":
        from_date = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        to_date = today.strftime("%Y-%m-%d")
        context.user_data["cleanup_start_date"] = from_date
        context.user_data["cleanup_end_date"] = to_date
        context.user_data["cleanup_type"] = "Last Month"
        return await show_cleanup_preview(update, context)
        
    elif query.data == "cleanup_preset_10":
        # For last 10 entries, we'll use a special handler
        context.user_data["cleanup_type"] = "Last 10 Entries"
        return await show_last_entries_preview(update, context, 10)
        
    elif query.data == "cleanup_custom":
        await query.edit_message_text(
            "📅 Enter START date for cleanup (YYYY-MM-DD):\n\n"
            "Example: 2024-01-15\n"
            "Type /cancel to exit.",
            reply_markup=None
        )
        context.user_data["cleanup_type"] = "Custom Range"
        return ASK_CLEANUP_START_DATE

async def show_last_entries_preview(update, context, count):
    """Show preview for cleaning up last N entries"""
    query = update.callback_query
    
    try:
        # Get last N transactions
        entries = get_recent_entries(count)
        if not entries:
            await query.edit_message_text(
                "No entries found to cleanup.",
                reply_markup=get_main_keyboard(query.message.chat.id)
            )
            return ConversationHandler.END
        
        # Format the preview
        entry_lines = []
        total_amount = 0
        walk_count = 0
        
        for entry in entries:
            date_str = entry["date"][:10] if len(entry["date"]) > 10 else entry["date"]
            entry_lines.append(f"• {date_str} - {entry['type'].title()}: {entry['amount']:.2f} MDL")
            total_amount += entry["amount"]
            if entry["type"] == "walk":
                walk_count += 1
        
        preview_text = "\n".join(entry_lines[:10])  # Limit display
        if len(entry_lines) > 10:
            preview_text += f"\n... and {len(entry_lines) - 10} more"
        
        message = (
            f"🗑️ *Last {count} Entries Preview*\n\n"
            f"{preview_text}\n\n"
            f"📊 *Summary:*\n"
            f"• Total entries: {len(entries)}\n"
            f"• Walks: {walk_count}\n"
            f"• Total amount: {total_amount:.2f} MDL\n\n"
            f"⚠️ **Are you sure you want to delete these entries?**"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete", callback_data="cleanup_confirm_entries")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cleanup_cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data["cleanup_entries"] = entries
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return CONFIRM_CLEANUP
        
    except Exception as e:
        logger.error(f"Error in show_last_entries_preview: {e}")
        await query.edit_message_text(
            f"Error retrieving entries: {str(e)}",
            reply_markup=get_main_keyboard(query.message.chat.id)
        )
        return ConversationHandler.END

async def show_cleanup_preview(update, context):
    """Show preview of what will be cleaned up"""
    query = update.callback_query
    from_date = context.user_data["cleanup_start_date"]
    to_date = context.user_data["cleanup_end_date"]
    cleanup_type = context.user_data["cleanup_type"]
    
    try:
        entries = get_report_entries(from_date, to_date)
        if not entries:
            await query.edit_message_text(
                f"No entries found for {cleanup_type} ({from_date} to {to_date}).",
                reply_markup=get_main_keyboard(query.message.chat.id)
            )
            return ConversationHandler.END
        
        # Categorize entries
        walks = [e for e in entries if e["type"] == "walk"]
        credits = [e for e in entries if e["type"] == "credit"]
        payments = [e for e in entries if e["type"] == "payment"]
        
        walk_total = sum([w["amount"] for w in walks])
        credit_total = sum([c["amount"] for c in credits])
        payment_total = sum([p["amount"] for p in payments])
        
        # Create summary
        summary_lines = []
        if walks:
            summary_lines.append(f"🐕 Walks: {len(walks)} entries ({walk_total:.2f} MDL)")
        if credits:
            summary_lines.append(f"💳 Credits: {len(credits)} entries ({credit_total:.2f} MDL)")  
        if payments:
            summary_lines.append(f"💰 Payments: {len(payments)} entries ({payment_total:.2f} MDL)")
        
        summary_text = "\n".join(summary_lines) if summary_lines else "No entries"
        
        # Show recent walks preview
        recent_walks = walks[-5:] if len(walks) > 5 else walks
        walk_preview = ""
        if recent_walks:
            walk_lines = [f"• {w['date'][:10]} - {w['amount']:.2f} MDL" for w in recent_walks]
            if len(walks) > 5:
                walk_preview = f"\n\n📝 *Recent walks preview:*\n" + "\n".join(walk_lines) + f"\n... and {len(walks) - 5} more"
            else:
                walk_preview = f"\n\n📝 *Walks to delete:*\n" + "\n".join(walk_lines)
        
        message = (
            f"🗑️ *{cleanup_type} Cleanup Preview*\n"
            f"📅 Period: {from_date} to {to_date}\n\n"
            f"📊 *Summary:*\n{summary_text}\n"
            f"📈 Total entries: {len(entries)}\n"
            f"{walk_preview}\n\n"
            f"⚠️ **Are you sure you want to delete these {len(entries)} entries?**"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete All", callback_data="cleanup_yes")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cleanup_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data["cleanup_walk_count"] = len(walks)
        context.user_data["cleanup_total_entries"] = len(entries)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
        return CONFIRM_CLEANUP
        
    except Exception as e:
        logger.error(f"Error in show_cleanup_preview: {e}")
        await query.edit_message_text(
            f"Error: {str(e)}",
            reply_markup=get_main_keyboard(query.message.chat.id)
        )
        return ConversationHandler.END

async def cleanup_get_start_date(update, context):
    """Handle custom start date input with validation"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("Access denied.")
        return ConversationHandler.END
    
    date_text = update.message.text.strip()
    
    try:
        # Validate date format
        from report_cleanup import validate_date
        validate_date(date_text)
        context.user_data["cleanup_start_date"] = date_text
        await update.message.reply_text(
            f"✅ Start date set: {date_text}\n\n"
            f"📅 Now enter END date for cleanup (YYYY-MM-DD):\n\n"
            f"Example: 2024-01-31\n"
            f"Type /cancel to exit."
        )
        return ASK_CLEANUP_END_DATE
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid date format: {str(e)}\n\n"
            f"Please enter date in YYYY-MM-DD format.\n"
            f"Example: 2024-01-15\n\n"
            f"Type /cancel to exit."
        )
        return ASK_CLEANUP_START_DATE

async def cleanup_get_end_date(update, context):
    """Handle custom end date input with validation"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("Access denied.")
        return ConversationHandler.END
    
    date_text = update.message.text.strip()
    
    try:
        # Validate date format and logic
        from report_cleanup import validate_date
        end_dt = validate_date(date_text)
        start_dt = validate_date(context.user_data["cleanup_start_date"])
        
        if start_dt > end_dt:
            await update.message.reply_text(
                f"❌ End date ({date_text}) must be after start date ({context.user_data['cleanup_start_date']}).\n\n"
                f"Please enter a valid END date (YYYY-MM-DD):\n"
                f"Type /cancel to exit."
            )
            return ASK_CLEANUP_END_DATE
        
        context.user_data["cleanup_end_date"] = date_text
        return await show_cleanup_preview_text(update, context)
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid date format: {str(e)}\n\n"
            f"Please enter date in YYYY-MM-DD format.\n"
            f"Example: 2024-01-31\n\n"
            f"Type /cancel to exit."
        )
        return ASK_CLEANUP_END_DATE

async def show_cleanup_preview_text(update, context):
    """Show cleanup preview from text input (not callback)"""
    from_date = context.user_data["cleanup_start_date"]
    to_date = context.user_data["cleanup_end_date"]
    cleanup_type = context.user_data["cleanup_type"]
    
    try:
        entries = get_report_entries(from_date, to_date)
        if not entries:
            await update.message.reply_text(
                f"No entries found for {cleanup_type} ({from_date} to {to_date}).\n"
                f"Cleanup cancelled.",
                reply_markup=get_main_keyboard(update.effective_chat.id)
            )
            return ConversationHandler.END
        
        # Categorize entries
        walks = [e for e in entries if e["type"] == "walk"]
        credits = [e for e in entries if e["type"] == "credit"]
        payments = [e for e in entries if e["type"] == "payment"]
        
        walk_total = sum([w["amount"] for w in walks])
        
        # Show recent walks preview
        recent_walks = walks[-3:] if len(walks) > 3 else walks
        walk_preview = ""
        if recent_walks:
            walk_lines = [f"• {w['date'][:10]} - {w['amount']:.2f} MDL" for w in recent_walks]
            if len(walks) > 3:
                walk_preview = f"\n📝 Recent walks preview:\n" + "\n".join(walk_lines) + f"\n... and {len(walks) - 3} more"
            else:
                walk_preview = f"\n📝 Walks to delete:\n" + "\n".join(walk_lines)
        
        message = (
            f"🗑️ {cleanup_type} Cleanup Preview\n"
            f"📅 Period: {from_date} to {to_date}\n\n"
            f"📊 Summary:\n"
            f"• Total entries: {len(entries)}\n"
            f"• Walks: {len(walks)} ({walk_total:.2f} MDL)\n"
            f"• Credits: {len(credits)}\n"
            f"• Payments: {len(payments)}\n"
            f"{walk_preview}\n\n"
            f"⚠️ Are you sure you want to delete these {len(entries)} entries?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, Delete All", callback_data="cleanup_yes")],
            [InlineKeyboardButton("❌ No, Cancel", callback_data="cleanup_no")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        context.user_data["cleanup_walk_count"] = len(walks)
        context.user_data["cleanup_total_entries"] = len(entries)
        
        await update.message.reply_text(message, reply_markup=reply_markup)
        return CONFIRM_CLEANUP
        
    except Exception as e:
        logger.error(f"Error in show_cleanup_preview_text: {e}")
        await update.message.reply_text(
            f"Error: {str(e)}",
            reply_markup=get_main_keyboard(update.effective_chat.id)
        )
        return ConversationHandler.END

async def cleanup_confirm(update, context):
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("Access denied.", show_alert=True)
        return ConversationHandler.END
    
    if query.data in ["cleanup_yes", "cleanup_confirm_entries"]:
        try:
            if query.data == "cleanup_confirm_entries":
                # Handle cleanup of specific entries (last N entries)
                entries = context.user_data.get("cleanup_entries", [])
                if not entries:
                    await query.edit_message_text("No entries to delete.", reply_markup=get_main_keyboard(chat_id))
                    return ConversationHandler.END
                
                # Delete entries by ID (this will need a new function in report_cleanup.py)
                result = clean_specific_entries([e["id"] for e in entries if "id" in e])
                deleted_count = len(entries)
                walks_deleted = len([e for e in entries if e["type"] == "walk"])
                
                if result.get("success", False):
                    await query.edit_message_text(
                        f"✅ Successfully deleted {deleted_count} entries (including {walks_deleted} walks).",
                        reply_markup=get_main_keyboard(chat_id)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Failed to delete entries: {result.get('error', 'Unknown error')}",
                        reply_markup=get_main_keyboard(chat_id)
                    )
            else:
                # Handle date range cleanup
                from_date = context.user_data["cleanup_start_date"]
                to_date = context.user_data["cleanup_end_date"]
                cleanup_type = context.user_data.get("cleanup_type", "Date Range")
                
                result = clean_detailed_report(from_date, to_date)
                if result["success"]:
                    walk_count = context.user_data.get("cleanup_walk_count", 0)
                    total_entries = context.user_data.get("cleanup_total_entries", result["deleted_count"])
                    
                    await query.edit_message_text(
                        f"✅ **{cleanup_type} Cleanup Complete**\n\n"
                        f"Deleted {total_entries} entries (including {walk_count} walks)\n"
                        f"Date range: {from_date} to {to_date}",
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=get_main_keyboard(chat_id)
                    )
                else:
                    await query.edit_message_text(
                        f"❌ **Cleanup Failed**\n\n{result['error']}", 
                        parse_mode=ParseMode.MARKDOWN,
                        reply_markup=get_main_keyboard(chat_id)
                    )
                    
        except Exception as e:
            logger.error(f"Error in cleanup_confirm: {e}")
            await query.edit_message_text(
                f"❌ Cleanup failed: {str(e)}", 
                reply_markup=get_main_keyboard(chat_id)
            )
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
            ASK_CLEANUP_OPTION: [CallbackQueryHandler(cleanup_option_chosen, pattern="^cleanup_")],
            ASK_CLEANUP_START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cleanup_get_start_date)],
            ASK_CLEANUP_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, cleanup_get_end_date)],
            CONFIRM_CLEANUP: [CallbackQueryHandler(cleanup_confirm, pattern="^cleanup_yes$|^cleanup_no$|^cleanup_confirm_entries$|^cleanup_cancel$")],
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
