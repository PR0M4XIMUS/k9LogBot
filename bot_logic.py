# bot_logic.py

from telegram.ext import (
    CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime

import csv
import io
import re

from database import (
    init_db, add_walk, get_current_balance,
    set_initial_balance, record_payment, record_credit_given,
    get_weekly_report_data, get_all_transactions_for_report,
    get_transactions_with_ids, delete_transaction_by_id, get_transaction_count,
    get_walk_rate, set_walk_rate, register_user, get_all_user_ids,
    get_streak, get_walks_this_week, get_weekly_goal, set_weekly_goal,
    get_user_reminder, set_user_reminder, get_earnings_forecast, update_walk_note,
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
CONFIRM_SINGLE_DELETE = 5
ASK_WALK_NOTE = 10
CONFIRM_UNDO = 11
ASK_REMINDER_TIME = 12

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
    await update.message.reply_text(
        "Please enter the credit amount (in MDL).",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )
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
        await query.message.reply_text(
            "👇 Enter amount below or use the menu:",
            reply_markup=get_main_keyboard(query.message.chat.id)
        )
        return ASK_MANUAL_CASHOUT_AMOUNT

async def receive_manual_cashout_amount(update, context):
    if global_stats_manager:
        global_stats_manager.record_activity()
    try:
        amount = float(update.message.text)
        if amount <= 0:
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

# --- Enhanced Detailed Report Command with Visual Improvements ---
async def detailed_report_command(update, context):
    """Enhanced detailed report with better visual presentation and individual delete options."""
    chat_id = update.effective_chat.id
    admin_mode = is_admin(chat_id)
    
    # Get transactions with IDs for individual deletion
    transactions = get_transactions_with_ids(limit=20)  # Show last 20 transactions
    total_count = get_transaction_count()
    
    if not transactions:
        await update.message.reply_text(
            "📊 *No Transactions Yet*\n\n"
            "No walks or transactions recorded yet.\n"
            "Start by adding a walk! 🐕",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(chat_id)
        )
        return
    
    # Calculate statistics
    current_balance = get_current_balance()
    
    walks = [t for t in transactions if t[3] == 'walk']
    payments = [t for t in transactions if t[3] == 'payment']
    credits = [t for t in transactions if t[3] == 'credit_given']
    
    walk_count = len(walks)
    walk_total = sum([t[2] for t in walks])
    payment_total = sum([abs(t[2]) for t in payments])
    credit_total = sum([abs(t[2]) for t in credits])
    
    # Build enhanced report message
    report_text = "📊 *Detailed Activity Report*\n"
    report_text += f"📅 _Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n"
    
    # Summary section with better formatting
    report_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    report_text += "💰 *BALANCE OVERVIEW*\n"
    report_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    report_text += f"Current Balance: *{current_balance:.2f} MDL*\n\n"
    
    report_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    report_text += "📈 *STATISTICS*\n"
    report_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    report_text += f"🐕 Walks (shown): *{walk_count}*\n"
    report_text += f"💵 Earned (shown): *{walk_total:.2f} MDL*\n"
    if payments:
        report_text += f"💸 Payments (shown): *{payment_total:.2f} MDL*\n"
    if credits:
        report_text += f"💳 Credits (shown): *{credit_total:.2f} MDL*\n"
    report_text += f"\n📋 Total records in DB: *{total_count}*\n"
    
    # Recent transactions section
    report_text += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
    report_text += "📝 *RECENT TRANSACTIONS*\n"
    report_text += "━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Format each transaction with emoji based on type
    transaction_lines = []
    for t in transactions[:15]:  # Show 15 most recent in summary
        tid, timestamp, amount, ttype, description, *_ = t
        date_str = timestamp[:16].replace('T', ' ')  # Format: YYYY-MM-DD HH:MM
        
        if ttype == 'walk':
            emoji = "🐕"
            sign = "+"
            display_type = "Walk"
        elif ttype == 'payment':
            emoji = "💸"
            sign = "-"
            display_type = "Payout"
            amount = abs(amount)
        elif ttype == 'credit_given':
            emoji = "💳"
            sign = "-"
            display_type = "Credit"
            amount = abs(amount)
        elif ttype == 'initial_balance':
            emoji = "💰"
            sign = "+"
            display_type = "Initial"
        else:
            emoji = "📝"
            sign = "+"
            display_type = ttype.title()
        
        transaction_lines.append(
            f"{emoji} `{tid}` | {date_str} | {sign}{amount:.2f} MDL ({display_type})"
        )
    
    report_text += "\n".join(transaction_lines)
    
    if len(transactions) > 15:
        report_text += f"\n_... and {len(transactions) - 15} more transactions_"
    
    # Send the main report
    await update.message.reply_text(
        report_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(chat_id)
    )
    
    # For admin: Show inline keyboard with individual delete options
    if admin_mode:
        # Create inline keyboard for individual deletions
        keyboard = []
        
        # Show delete buttons for last 10 transactions
        for t in transactions[:10]:
            tid, timestamp, amount, ttype, description, *_ = t
            date_str = timestamp[:10]
            
            if ttype == 'walk':
                label = f"🐕 #{tid} {amount:.0f} MDL"
            elif ttype == 'payment':
                label = f"💸 #{tid} {abs(amount):.0f} MDL"
            elif ttype == 'credit_given':
                label = f"💳 #{tid} {abs(amount):.0f} MDL"
            else:
                label = f"📝 #{tid}"
            
            keyboard.append([
                InlineKeyboardButton(
                    label,
                    callback_data=f"del_single_{tid}"
                )
            ])
        
        # Add pagination/info buttons if there are more transactions
        if len(transactions) > 10:
            keyboard.append([
                InlineKeyboardButton(
                    f"📋 Show More ({total_count} total)",
                    callback_data="show_more_transactions"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close_report")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 *Admin: Delete Individual Records*\n\n"
            "Tap any transaction above to delete it.\n"
            "_Balance will be adjusted automatically._",
            parse_mode=ParseMode.MARKDOWN,
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
        await query.edit_message_text("Cleanup cancelled.")
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
        await query.message.reply_text(
            "👇 Enter start date below or use the menu:",
            reply_markup=get_main_keyboard(query.message.chat.id)
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
            await query.edit_message_text("No entries found to cleanup.")
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
        await query.edit_message_text(f"Error retrieving entries: {str(e)}")
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
                f"No entries found for {cleanup_type} ({from_date} to {to_date})."
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
        await query.edit_message_text(f"Error: {str(e)}")
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
            f"Type /cancel to exit.",
            reply_markup=get_main_keyboard(update.effective_chat.id)
        )
        return ASK_CLEANUP_END_DATE
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid date format: {str(e)}\n\n"
            f"Please enter date in YYYY-MM-DD format.\n"
            f"Example: 2024-01-15\n\n"
            f"Type /cancel to exit.",
            reply_markup=get_main_keyboard(update.effective_chat.id)
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
                f"Type /cancel to exit.",
                reply_markup=get_main_keyboard(update.effective_chat.id)
            )
            return ASK_CLEANUP_END_DATE
        
        context.user_data["cleanup_end_date"] = date_text
        return await show_cleanup_preview_text(update, context)
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid date format: {str(e)}\n\n"
            f"Please enter date in YYYY-MM-DD format.\n"
            f"Example: 2024-01-31\n\n"
            f"Type /cancel to exit.",
            reply_markup=get_main_keyboard(update.effective_chat.id)
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
                    await query.edit_message_text("No entries to delete.")
                    return ConversationHandler.END
                
                # Delete entries by ID (this will need a new function in report_cleanup.py)
                result = clean_specific_entries([e["id"] for e in entries if "id" in e])
                deleted_count = len(entries)
                walks_deleted = len([e for e in entries if e["type"] == "walk"])
                
                if result.get("success", False):
                    await query.edit_message_text(
                        f"✅ Successfully deleted {deleted_count} entries (including {walks_deleted} walks)."
                    )
                else:
                    await query.edit_message_text(
                        f"❌ Failed to delete entries: {result.get('error', 'Unknown error')}"
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
                    )
                else:
                    await query.edit_message_text(
                        f"❌ **Cleanup Failed**\n\n{result['error']}",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    
        except Exception as e:
            logger.error(f"Error in cleanup_confirm: {e}")
            await query.edit_message_text(f"❌ Cleanup failed: {str(e)}")
    else:
        await query.edit_message_text("Cleanup cancelled.")
    
    return ConversationHandler.END

# --- Other Standard Commands ---
async def start(update, context):
    user = update.effective_user
    register_user(user.id, user.username or user.first_name)
    await update.message.reply_text(
        "Welcome to k9LogBot! Use the buttons below or commands to interact.",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def help_command(update, context):
    chat_id = update.effective_chat.id
    admin_section = ""
    if is_admin(chat_id):
        admin_section = (
            "\n*Admin Commands:*\n"
            f"/setrate <amount> — Change walk rate (now {get_walk_rate():.0f} MDL)\n"
            "/broadcast <msg> — Announce to all users\n"
            "/export — Download transactions as CSV\n"
        )
    await update.message.reply_text(
        "*Available Commands:*\n"
        "/addwalk — Log a walk\n"
        "/balance — Balance, streak & weekly progress\n"
        "/setgoal <n> — Set weekly walk goal\n"
        "/setinitial <amount> — Set starting balance\n"
        "/report — Detailed transaction report\n"
        "/undo — Undo last transaction\n"
        "/reminder HH:MM — Set daily reminder\n"
        "/reminder off — Disable reminder\n"
        f"{admin_section}"
        "Or use the buttons below.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(chat_id)
    )

async def add_walk_command(update, context):
    if global_stats_manager:
        global_stats_manager.record_activity()
    walk_id, rate = add_walk()
    current_balance = get_current_balance()
    note_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Add Note", callback_data=f"add_note_{walk_id}")]
    ])
    await update.message.reply_text(
        f"✅ Walk recorded. +{rate:.0f} MDL\nBalance: *{current_balance:.2f} MDL*.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=note_keyboard
    )

async def balance_command(update, context):
    chat_id = update.effective_chat.id
    current_balance = get_current_balance()
    streak = get_streak()
    walks_week = get_walks_this_week()
    goal = get_weekly_goal(chat_id)
    forecast = get_earnings_forecast()

    msg = f"💰 *Balance: {current_balance:.2f} MDL*\n\n"
    if streak > 0:
        msg += f"🔥 Streak: *{streak} day{'s' if streak != 1 else ''}*\n"
    if goal > 0:
        filled = min(walks_week, goal)
        bar = "█" * filled + "░" * (goal - filled)
        msg += f"🎯 This week: *{walks_week}/{goal}* `[{bar}]`\n"
    else:
        msg += f"🚶 This week: *{walks_week} walk{'s' if walks_week != 1 else ''}*\n"
    msg += f"📈 Month forecast: *~{forecast:.0f} MDL*"

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(chat_id)
    )

async def set_initial_balance_command(update, context):
    await update.message.reply_text(
        "Please enter the initial balance (in MDL).",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )
    context.user_data["await_initial_balance"] = True

async def receive_initial_balance(update, context):
    if not context.user_data.get("await_initial_balance"):
        return
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

# --- Individual Transaction Deletion Handlers (Admin Only) ---
async def delete_single_transaction_callback(update, context):
    """Handle individual transaction deletion requests from admin."""
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("⛔ Access denied. Admin only.", show_alert=True)
        return
    
    # Extract transaction ID from callback data
    callback_data = query.data
    if not callback_data.startswith("del_single_"):
        return
    
    try:
        transaction_id = int(callback_data.replace("del_single_", ""))
    except ValueError:
        await query.answer("❌ Invalid transaction ID", show_alert=True)
        return
    
    # Store in context for confirmation
    context.user_data["delete_transaction_id"] = transaction_id
    
    # Get transaction details for confirmation message
    transactions = get_transactions_with_ids(limit=100)
    transaction = None
    for t in transactions:
        if t[0] == transaction_id:
            transaction = t
            break
    
    if not transaction:
        await query.answer("❌ Transaction not found", show_alert=True)
        return
    
    tid, timestamp, amount, ttype, description, *_ = transaction
    date_str = timestamp[:16].replace('T', ' ')

    if ttype == 'walk':
        emoji = "🐕"
        display_type = "Walk"
    elif ttype == 'payment':
        emoji = "💸"
        display_type = "Payout"
        amount = abs(amount)
    elif ttype == 'credit_given':
        emoji = "💳"
        display_type = "Credit"
        amount = abs(amount)
    else:
        emoji = "📝"
        display_type = ttype.title()

    # Show confirmation keyboard
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_del_{transaction_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_del")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"⚠️ *Confirm Deletion*\n\n"
        f"{emoji} Transaction #{tid}\n"
        f"📅 Date: {date_str}\n"
        f"💰 Amount: {amount:.2f} MDL\n"
        f"📝 Type: {display_type}\n\n"
        f"_This will permanently delete the transaction and adjust the balance._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def confirm_delete_transaction_callback(update, context):
    """Confirm and execute single transaction deletion."""
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    
    callback_data = query.data
    if not callback_data.startswith("confirm_del_"):
        return
    
    try:
        transaction_id = int(callback_data.replace("confirm_del_", ""))
    except ValueError:
        await query.answer("❌ Invalid transaction ID", show_alert=True)
        return
    
    # Perform deletion
    result = delete_transaction_by_id(transaction_id)
    
    if result["success"]:
        amount = result["amount"]
        ttype = result["transaction_type"]
        
        if ttype == 'walk':
            emoji = "🐕"
        elif ttype == 'payment':
            emoji = "💸"
            amount = abs(amount)
        elif ttype == 'credit_given':
            emoji = "💳"
            amount = abs(amount)
        else:
            emoji = "📝"
        
        # Show success message
        await query.edit_message_text(
            f"✅ *Transaction Deleted Successfully*\n\n"
            f"{emoji} Removed: {amount:.2f} MDL\n"
            f"💾 Balance adjusted automatically.\n\n"
            f"_Use /report to see updated transactions._",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Update OLED display if available
        if global_oled_display:
            global_oled_display.show_notification(f"Deleted: {amount:.0f} MDL", 2)
    else:
        await query.edit_message_text(
            f"❌ *Deletion Failed*\n\n"
            f"Error: {result.get('error', 'Unknown error')}",
            parse_mode=ParseMode.MARKDOWN
        )

async def cancel_delete_transaction_callback(update, context):
    """Cancel single transaction deletion."""
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    
    # Clear stored transaction ID
    if "delete_transaction_id" in context.user_data:
        del context.user_data["delete_transaction_id"]
    
    await query.edit_message_text("❌ Deletion cancelled.")

async def show_more_transactions_callback(update, context):
    """Show more transactions with pagination."""
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    
    # Get more transactions (next batch)
    offset = context.user_data.get("transaction_offset", 10)
    transactions = get_transactions_with_ids(limit=10, offset=offset)
    
    if not transactions:
        await query.answer("No more transactions", show_alert=True)
        return
    
    # Build transaction list
    transaction_lines = []
    for t in transactions:
        tid, timestamp, amount, ttype, description, *_ = t
        date_str = timestamp[:10]
        
        if ttype == 'walk':
            emoji = "🐕"
            label = f"{emoji} #{tid} | {date_str} | +{amount:.2f} MDL"
        elif ttype == 'payment':
            emoji = "💸"
            label = f"{emoji} #{tid} | {date_str} | -{abs(amount):.2f} MDL"
        elif ttype == 'credit_given':
            emoji = "💳"
            label = f"{emoji} #{tid} | {date_str} | -{abs(amount):.2f} MDL"
        else:
            emoji = "📝"
            label = f"{emoji} #{tid} | {date_str}"
        
        transaction_lines.append(
            InlineKeyboardButton(label, callback_data=f"del_single_{tid}")
        )
    
    # Advance the offset for the next "Show More" press
    context.user_data["transaction_offset"] = offset + len(transactions)

    # Create keyboard
    keyboard = [[t] for t in transaction_lines]
    keyboard.append([InlineKeyboardButton("❌ Close", callback_data="close_report")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🔧 *More Transactions*\n\n"
        "Tap any to delete it.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

async def close_report_callback(update, context):
    """Close the report/transaction list."""
    query = update.callback_query
    chat_id = query.message.chat.id
    
    if not is_admin(chat_id):
        await query.answer("⛔ Access denied.", show_alert=True)
        return
    
    await query.edit_message_text("📋 Report view closed.")

# --- New Feature Commands ---

async def setrate_command(update, context):
    """Admin: change the per-walk rate."""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text(
            f"Current walk rate: *{get_walk_rate():.2f} MDL*\nUsage: `/setrate <amount>`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(update.effective_chat.id)
        )
        return
    try:
        rate = float(context.args[0])
        if rate <= 0:
            await update.message.reply_text("Rate must be positive.")
            return
        set_walk_rate(rate)
        await update.message.reply_text(
            f"✅ Walk rate updated to *{rate:.2f} MDL* per walk.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(update.effective_chat.id)
        )
    except ValueError:
        await update.message.reply_text("Invalid amount. Usage: `/setrate 80`", parse_mode=ParseMode.MARKDOWN)

async def broadcast_command(update, context):
    """Admin: send a message to all registered users."""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    if not context.args:
        await update.message.reply_text("Usage: `/broadcast <message>`", parse_mode=ParseMode.MARKDOWN)
        return
    message = " ".join(context.args)
    user_ids = get_all_user_ids()
    if not user_ids:
        await update.message.reply_text("No registered users yet.")
        return
    sent = failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 *Admin Announcement*\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"📢 Broadcast complete.\n✅ Sent: {sent}\n❌ Failed: {failed}",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def undo_command(update, context):
    """Show the last transaction with a confirmation button to delete it."""
    transactions = get_transactions_with_ids(limit=1)
    if not transactions:
        await update.message.reply_text("No transactions to undo.")
        return
    tid, timestamp, amount, ttype, description, *_ = transactions[0]
    date_str = timestamp[:16].replace('T', ' ')
    emoji_map = {'walk': '🐕', 'payment': '💸', 'credit_given': '💳', 'initial_balance': '💰'}
    emoji = emoji_map.get(ttype, '📝')
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes, Undo", callback_data=f"undo_confirm_{tid}"),
        InlineKeyboardButton("❌ Cancel", callback_data="undo_cancel")
    ]])
    await update.message.reply_text(
        f"↩️ *Undo Last Transaction?*\n\n"
        f"{emoji} #{tid} | {date_str}\n"
        f"Amount: {abs(amount):.2f} MDL | Type: {ttype.replace('_', ' ').title()}\n\n"
        f"_Balance will be adjusted automatically._",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

async def undo_callback(update, context):
    query = update.callback_query
    await query.answer()
    if query.data == "undo_cancel":
        await query.edit_message_text("↩️ Undo cancelled.")
        return
    tid = int(query.data.replace("undo_confirm_", ""))
    result = delete_transaction_by_id(tid)
    if result["success"]:
        if global_stats_manager:
            global_stats_manager.record_activity()
        new_balance = get_current_balance()
        await query.edit_message_text(
            f"✅ *Transaction Undone*\n\nBalance: *{new_balance:.2f} MDL*",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await query.edit_message_text(f"❌ Undo failed: {result.get('error', 'Unknown error')}")

async def export_command(update, context):
    """Admin: export all transactions as a CSV file."""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    transactions = get_all_transactions_for_report()
    if not transactions:
        await update.message.reply_text("No transactions to export.")
        return
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Timestamp', 'Amount (MDL)', 'Type', 'Description', 'Notes'])
    for row in transactions:
        writer.writerow(row)
    output.seek(0)
    filename = f"k9logbot_{datetime.now().strftime('%Y%m%d')}.csv"
    await update.message.reply_document(
        document=io.BytesIO(output.getvalue().encode('utf-8')),
        filename=filename,
        caption=f"📊 Exported {len(transactions)} transactions",
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )

async def setgoal_command(update, context):
    """Set or view the weekly walk goal."""
    user_id = update.effective_chat.id
    if not context.args:
        goal = get_weekly_goal(user_id)
        walks = get_walks_this_week()
        if goal > 0:
            await update.message.reply_text(
                f"🎯 Weekly goal: *{goal} walks* | Progress: *{walks}/{goal}*\n"
                "Use `/setgoal <n>` to change.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text(
                "No goal set. Use `/setgoal <n>` to set a weekly target.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user_id)
            )
        return
    try:
        goal = int(context.args[0])
        if goal <= 0:
            await update.message.reply_text("Goal must be a positive number.")
            return
        set_weekly_goal(user_id, goal)
        await update.message.reply_text(
            f"🎯 Weekly goal set to *{goal} walks*!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_main_keyboard(user_id)
        )
    except ValueError:
        await update.message.reply_text("Invalid number. Usage: `/setgoal 10`", parse_mode=ParseMode.MARKDOWN)

async def reminder_command(update, context):
    """Set or disable a daily reminder if no walk has been logged."""
    user_id = update.effective_chat.id
    if not context.args:
        current = get_user_reminder(user_id)
        if current['enabled']:
            await update.message.reply_text(
                f"🔔 Reminder set for *{current['time']}*\nUse `/reminder off` to disable.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text(
                "🔕 No reminder set.\nUsage: `/reminder 09:00`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user_id)
            )
        return
    arg = context.args[0].strip()
    if arg.lower() == 'off':
        set_user_reminder(user_id, None, False)
        await update.message.reply_text("🔕 Daily reminder disabled.", reply_markup=get_main_keyboard(user_id))
        return
    if re.match(r'^\d{2}:\d{2}$', arg):
        hour, minute = map(int, arg.split(':'))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            set_user_reminder(user_id, arg, True)
            await update.message.reply_text(
                f"🔔 Reminder set for *{arg}* daily.\nYou'll be reminded if no walk is logged by then.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_main_keyboard(user_id)
            )
        else:
            await update.message.reply_text("Invalid time. Use 00:00–23:59 format.")
    else:
        await update.message.reply_text("Usage: `/reminder 09:00` or `/reminder off`", parse_mode=ParseMode.MARKDOWN)

# --- Walk Note Conversation ---

async def add_note_start(update, context):
    query = update.callback_query
    await query.answer()
    walk_id = int(query.data.replace("add_note_", ""))
    context.user_data["note_walk_id"] = walk_id
    await query.edit_message_text(f"📝 Enter a note for walk #{walk_id} (or /cancel to skip):")
    await query.message.reply_text(
        "👇 Enter your note below or use the menu:",
        reply_markup=get_main_keyboard(query.message.chat.id)
    )
    return ASK_WALK_NOTE

async def receive_walk_note(update, context):
    note = update.message.text.strip()
    walk_id = context.user_data.get("note_walk_id")
    if walk_id:
        update_walk_note(walk_id, note)
    await update.message.reply_text(
        f"✅ Note saved: _{note}_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_keyboard(update.effective_chat.id)
    )
    return ConversationHandler.END

async def note_cancel(update, context):
    await update.message.reply_text("Note skipped.", reply_markup=get_main_keyboard(update.effective_chat.id))
    return ConversationHandler.END

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

    # Individual Transaction Deletion Callback Handlers (Admin Only)
    application.add_handler(CallbackQueryHandler(
        delete_single_transaction_callback,
        pattern="^del_single_"
    ))
    application.add_handler(CallbackQueryHandler(
        confirm_delete_transaction_callback,
        pattern="^confirm_del_"
    ))
    application.add_handler(CallbackQueryHandler(
        cancel_delete_transaction_callback,
        pattern="^cancel_del$"
    ))
    application.add_handler(CallbackQueryHandler(
        show_more_transactions_callback,
        pattern="^show_more_transactions$"
    ))
    application.add_handler(CallbackQueryHandler(
        close_report_callback,
        pattern="^close_report$"
    ))

    # Walk note conversation
    note_conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_note_start, pattern=r"^add_note_\d+$")],
        states={
            ASK_WALK_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_walk_note)],
        },
        fallbacks=[CommandHandler("cancel", note_cancel), MessageHandler(filters.COMMAND, note_cancel)],
        allow_reentry=True
    )
    application.add_handler(note_conv_handler)

    # New commands
    application.add_handler(CommandHandler("setrate", setrate_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("undo", undo_command))
    application.add_handler(CommandHandler("export", export_command))
    application.add_handler(CommandHandler("setgoal", setgoal_command))
    application.add_handler(CommandHandler("reminder", reminder_command))

    # Undo callback
    application.add_handler(CallbackQueryHandler(undo_callback, pattern=r"^undo_confirm_\d+$|^undo_cancel$"))

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
