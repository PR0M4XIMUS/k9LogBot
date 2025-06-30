# bot_logic.py
from telegram.ext import (
    CommandHandler,  # To handle commands like /start, /help
    MessageHandler,  # To handle regular text messages or button presses
    filters,  # To filter which messages a handler should respond to
    ConversationHandler,  # To manage multi-step conversations (like asking for an amount)
    CallbackQueryHandler  # To handle presses of inline buttons (buttons inside messages)
)
from telegram.constants import ParseMode  # For formatting text (e.g., bold, italics)
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, \
    InlineKeyboardButton  # For creating buttons
import logging  # For logging information and errors
from datetime import datetime  # For working with dates and times

# Import functions from our database.py file
from database import (
    init_db, add_walk, get_current_balance,
    set_initial_balance, record_payment, record_credit_given,
    get_weekly_report_data, get_all_transactions_for_report
)
from config import YOUR_TELEGRAM_CHAT_ID  # Import your Telegram chat ID from config.py

# --- Set up Logging ---
# This helps us see what the bot is doing and debug problems.
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- States for Conversation Handlers ---
# These are unique numbers that tell the ConversationHandler what step of the conversation we are in.
ASK_CREDIT_AMOUNT, RECEIVE_CREDIT_AMOUNT = range(2)  # States for the "Credit" conversation
ASK_CASHOUT_TYPE, ASK_MANUAL_CASHOUT_AMOUNT, RECEIVE_MANUAL_CASHOUT_AMOUNT = range(3)  # States for "Cash Out"

# --- Keyboard Definitions ---
# This is the main set of buttons that appear above the user's keyboard.
# Each inner list is a row of buttons.
MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("➕ Add Walk"), KeyboardButton("💰 Current Balance")],
    [KeyboardButton("💳 Give Credit"), KeyboardButton("💸 Cash Out")],
    [KeyboardButton("📊 Detailed Report"), KeyboardButton("❓ Help")],
], resize_keyboard=True, one_time_keyboard=False)  # resize_keyboard makes buttons fit better


def get_cashout_inline_keyboard(current_balance):
    """
    Creates an inline keyboard (buttons directly in the message) for the Cash Out process.
    It shows two options: pay out the full balance or enter a manual amount.
    """
    keyboard = [
        # Callback data is what the bot receives when the button is pressed.
        [InlineKeyboardButton(f"Pay All ({current_balance:.2f} MDL)", callback_data="cashout_all")],
        [InlineKeyboardButton("Enter Amount Manually", callback_data="cashout_manual")],
    ]
    return InlineKeyboardMarkup(keyboard)  # Create the inline keyboard


# --- Command Handlers ---
# These functions define what the bot does when a specific command or button is used.
# All functions that interact with Telegram's API must be 'async def' and use 'await'.

async def start(update, context):
    """Sends a welcome message and displays the main keyboard buttons."""
    message = (
        "Hello! I'm your dog walking payment tracker bot.\n\n"
        "Use the buttons below for quick actions, or type a command.\n\n"
        "Available commands:\n"
        "/addwalk - Records a dog walk (75 MDL).\n"
        "/balance - Shows your current balance.\n"
        "/credit - Records credit given (e.g., Nana pays you an advance).\n"
        "/cashout - Records money you pay out (e.g., to Nana).\n"
        "/report - Get a detailed report of all transactions.\n"
        "/setinitial <amount> - Set the initial balance (e.g., /setinitial -150 for an overpayment).\n"
        "/help - Shows this message again."
    )
    # Send the message and display the MAIN_KEYBOARD.
    await update.message.reply_text(message, reply_markup=MAIN_KEYBOARD)


async def add_walk_command(update, context):
    """Records a dog walk and updates the balance."""
    add_walk()  # Call the database function to add a walk. This is synchronous, no 'await'.
    current_balance = get_current_balance()  # Get the updated balance.
    await update.message.reply_text(
        f"✅ Walk recorded! Current balance: *{current_balance:.2f} MDL*",
        parse_mode=ParseMode.MARKDOWN  # Use Markdown for bold text
    )


async def balance_command(update, context):
    """Shows the current outstanding balance with clear labels."""
    current_balance = get_current_balance()
    if current_balance > 0:
        status_text = f"Current Balance: *{current_balance:.2f} MDL* (They owe you)"
    elif current_balance < 0:
        status_text = f"Current Balance: *{abs(current_balance):.2f} MDL* (You owe them)"
    else:
        status_text = "Current Balance: *0.00 MDL* (Balance is zero)"

    await update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)


async def help_command(update, context):
    """Sends the help message, which also re-displays the main keyboard."""
    await start(update, context)  # Reuse the start function


async def set_initial_balance_command(update, context):
    """Sets an initial balance manually. Usage: /setinitial <amount>"""
    try:
        if not context.args:  # Check if an amount was provided after the command
            await update.message.reply_text(
                "Please provide an amount. Usage: `/setinitial <amount>`\n"
                "Example: `/setinitial 0` (reset), `/setinitial -150` (they overpaid), `/setinitial 200` (they owe you)",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        amount = float(context.args[0])  # Convert the provided text to a number
        set_initial_balance(amount)  # Update the balance in the database
        current_balance = get_current_balance()
        await update.message.reply_text(
            f"Initial balance set to *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN
        )
    except ValueError:  # If the user didn't enter a valid number
        await update.message.reply_text("Invalid amount. Please enter a number.")
    except Exception as e:  # Catch any other unexpected errors
        logger.error(f"Error setting initial balance: {e}")
        await update.message.reply_text("An error occurred while setting the initial balance.")


async def detailed_report_command(update, context):
    """Provides a detailed report of all financial transactions."""
    transactions = get_all_transactions_for_report()  # Get all transactions from the database
    current_balance = get_current_balance()  # Get the current total balance

    if not transactions:
        report_message = "No transactions found."
    else:
        report_message = "*Detailed Transaction Report:*\n\n"
        for ts, amount, tr_type, desc in transactions:
            timestamp = datetime.fromisoformat(ts)  # Convert timestamp string back to datetime object
            # Customize how each transaction type is displayed in the report
            if tr_type == 'walk':
                type_display = "Walk"
            elif tr_type == 'payment':
                type_display = "Payment (Full Settlement)"
            elif tr_type == 'credit_given':
                type_display = "Credit Given (Advance from them)"
            elif tr_type == 'manual_cashout':
                type_display = "Cash Out (Manual)"
            else:
                type_display = tr_type  # Fallback for unknown types

            # Format the transaction line: date, type, amount
            report_message += f"`{timestamp.strftime('%Y-%m-%d %H:%M')}`: {type_display}: *{amount:.2f} MDL*\n"
            if desc and desc != type_display:  # Add description if it's different from the type
                report_message += f"  _({desc})_\n"

        report_message += "\n"  # Add a newline before the final summary
        # Summarize the final balance with clear labels
        if current_balance > 0:
            report_message += f"*Total: To Be Paid: {current_balance:.2f} MDL*\n"
        elif current_balance < 0:
            report_message += f"*Total: Overpaid: {abs(current_balance):.2f} MDL*\n"
        else:
            report_message += "*Total: Balance is Zero: 0.00 MDL*\n"

    await update.message.reply_text(report_message, parse_mode=ParseMode.MARKDOWN)


# --- Conversation Handler Functions: "Give Credit" ---
# This multi-step process asks the user for the credit amount.

async def credit_start(update, context):
    """Starts the 'Give Credit' conversation by asking for the amount."""
    await update.message.reply_text("Please enter the credit amount (in MDL).")
    return ASK_CREDIT_AMOUNT  # Go to the next state in the conversation


async def receive_credit_amount(update, context):
    """Receives the credit amount entered by the user and records the transaction."""
    try:
        amount = float(update.message.text)  # Convert the user's text input to a number
        if amount <= 0:  # Ensure the amount is positive
            await update.message.reply_text("Credit amount must be a positive number. Please try again.")
            return ASK_CREDIT_AMOUNT  # Stay in the same state to ask again

        record_credit_given(amount, f"Credit (advance) of {amount:.2f} MDL")  # Record the credit
        current_balance = get_current_balance()  # Get the new balance
        await update.message.reply_text(
            f"✅ Credit of *{amount:.2f} MDL* recorded. "
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KEYBOARD  # Show the main keyboard again
        )
        return ConversationHandler.END  # End the conversation
    except ValueError:  # If the input was not a valid number
        await update.message.reply_text("Invalid amount format. Please enter a number (e.g., 100.50).")
        return ASK_CREDIT_AMOUNT  # Ask again
    except Exception as e:  # Catch other errors
        logger.error(f"Error in receive_credit_amount: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END  # End the conversation due to error


async def credit_cancel(update, context):
    """Cancels the 'Give Credit' conversation."""
    await update.message.reply_text('Operation "Give Credit" cancelled.', reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END  # End the conversation


# --- Conversation Handler Functions: "Cash Out" ---
# This multi-step process allows choosing full payout or manual amount.

async def cashout_start(update, context):
    """Starts the 'Cash Out' conversation by showing inline options."""
    current_balance = get_current_balance()
    keyboard = get_cashout_inline_keyboard(current_balance)  # Get the inline keyboard with options
    await update.message.reply_text(
        f"Current amount to be paid out: *{current_balance:.2f} MDL*.\n"
        "What do you want to do?",
        reply_markup=keyboard,  # Display the inline keyboard
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_CASHOUT_TYPE  # Go to the next state, waiting for inline button press


async def cashout_type_chosen(update, context):
    """Handles the choice between full cash out or entering a manual amount."""
    query = update.callback_query  # Get the callback query from the inline button press
    await query.answer()  # Tell Telegram that we received the button press (removes loading spinner)

    if query.data == "cashout_all":  # If user chose "Pay All"
        current_balance = get_current_balance()
        if current_balance <= 0:  # If there's nothing to pay out
            await query.edit_message_text(  # Edit the message to show the result
                f"Balance: *{current_balance:.2f} MDL*. Nothing to pay out.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=None  # Remove the inline keyboard
            )
            return ConversationHandler.END  # End the conversation

        record_payment(current_balance, "Full settlement (paid out all balance)")  # Record the full payment
        new_balance = get_current_balance()  # Get the new balance after payout
        await query.edit_message_text(  # Edit the message with the outcome
            f"✅ *{current_balance:.2f} MDL* was paid out.\n"
            f"Current balance: *{new_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=None  # Remove inline keyboard
        )
        await query.message.reply_text("Operation completed.",
                                       reply_markup=MAIN_KEYBOARD)  # Send new message with main keyboard
        return ConversationHandler.END  # End the conversation

    elif query.data == "cashout_manual":  # If user chose "Enter Amount Manually"
        await query.edit_message_text("Please enter the amount to pay out (in MDL).")  # Ask for the amount
        return ASK_MANUAL_CASHOUT_AMOUNT  # Go to the state where we expect a text message with the amount


async def receive_manual_cashout_amount(update, context):
    """Receives the manual cash out amount and records the payment."""
    try:
        amount = float(update.message.text)  # Convert the user's text input to a number
        if amount == 0:  # Amount must be non-zero
            await update.message.reply_text("Amount must be greater than zero. Please try again.")
            return ASK_MANUAL_CASHOUT_AMOUNT  # Ask again

        record_payment(amount, f"Manual cash out of {amount:.2f} MDL")  # Record the payment
        current_balance = get_current_balance()  # Get the new balance
        await update.message.reply_text(
            f"✅ Recorded payout of *{amount:.2f} MDL*.\n"
            f"Current balance: *{current_balance:.2f} MDL*.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=MAIN_KEYBOARD  # Show the main keyboard again
        )
        return ConversationHandler.END  # End the conversation
    except ValueError:  # If input was not a valid number
        await update.message.reply_text("Invalid amount format. Please enter a number (e.g., 100.50).")
        return ASK_MANUAL_CASHOUT_AMOUNT  # Ask again
    except Exception as e:  # Catch other errors
        logger.error(f"Error in receive_manual_cashout_amount: {e}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END  # End the conversation due to error


async def cashout_cancel(update, context):
    """Cancels the 'Cash Out' conversation."""
    await update.message.reply_text('Operation "Cash Out" cancelled.', reply_markup=MAIN_KEYBOARD)
    return ConversationHandler.END  # End the conversation


# --- Global Error Handler ---
async def error(update, context):
    """Logs errors caused by updates and sends a friendly message to the user."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update and update.effective_message:  # Check if there's a message to reply to
        await update.effective_message.reply_text("Oops! Something went wrong. Please try again or use /help.")


# --- Setup Handlers for the Application ---
def setup_handlers(application):
    """
    Sets up all command handlers, message handlers, and conversation handlers
    for the Telegram Application.
    """
    # --- Conversation Handler for "Give Credit" ---
    # Entry points are how the conversation starts (command or button).
    # States define what to do in each step of the conversation.
    # Fallbacks are what to do if the user types something unexpected or cancels.
    credit_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("credit", credit_start),
            MessageHandler(filters.Regex("^💳 Give Credit$"), credit_start)
        ],
        states={
            ASK_CREDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_credit_amount)],
        },
        fallbacks=[CommandHandler("cancel", credit_cancel), MessageHandler(filters.COMMAND, credit_cancel)],
        allow_reentry=True  # Allows starting new conversation even if one is active (though careful with this)
    )
    application.add_handler(credit_conv_handler)  # Add the conversation handler to the bot

    # --- Conversation Handler for "Cash Out" ---
    cashout_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("cashout", cashout_start),
            MessageHandler(filters.Regex("^💸 Cash Out$"), cashout_start)
        ],
        states={
            ASK_CASHOUT_TYPE: [CallbackQueryHandler(cashout_type_chosen)],  # Handles inline button clicks
            ASK_MANUAL_CASHOUT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manual_cashout_amount)],
        },
        fallbacks=[CommandHandler("cancel", cashout_cancel), MessageHandler(filters.COMMAND, cashout_cancel)],
        allow_reentry=True
    )
    application.add_handler(cashout_conv_handler)  # Add the conversation handler to the bot

    # --- Regular Command Handlers ---
    # These respond to specific commands typed by the user.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addwalk", add_walk_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("setinitial", set_initial_balance_command))
    application.add_handler(CommandHandler("report", detailed_report_command))

    # --- Message Handlers for Reply Keyboard Buttons ---
    # These respond when the user presses a button from the main keyboard.
    # filters.Regex matches the exact text on the button.
    application.add_handler(MessageHandler(filters.Regex("^➕ Add Walk$"), add_walk_command))
    application.add_handler(MessageHandler(filters.Regex("^💰 Current Balance$"), balance_command))
    application.add_handler(MessageHandler(filters.Regex("^📊 Detailed Report$"), detailed_report_command))
    application.add_handler(MessageHandler(filters.Regex("^❓ Help$"), help_command))

    # Register the global error handler
    application.add_error_handler(error)


# --- Scheduled Report Function ---
async def send_scheduled_report(bot_instance):
    """
    Function to be called automatically by the scheduler (every Sunday at 8 PM).
    It sends a summary of the past week's activities.
    """
    today = datetime.now()
    report_data = get_weekly_report_data(today)  # Get data for the week that just ended

    walks_count = report_data["walks_count"]
    total_walk_amount = report_data["total_walks_amount"]
    # This will be negative if payments/credits were given to you during the week
    total_payment_credit_amount = report_data["total_payment_credit_amount"]

    week_num = report_data["week_number"]
    year = report_data["year"]

    report_message = (
        f"🗓️ *Weekly Dog Walking Report - Week {week_num}, {year}* 🗓️\n\n"
        f"Total walks this week: *{walks_count}*\n"
        f"Total earnings from walks: *{total_walk_amount:.2f} MDL*\n"
        f"Total payments/credits received from Nana: *{total_payment_credit_amount:.2f} MDL*\n\n"
        "For a detailed report, use the '📊 Detailed Report' button or the `/report` command."
    )

    # Send the scheduled report message to the specific chat ID
    await bot_instance.send_message(
        chat_id=YOUR_TELEGRAM_CHAT_ID,
        text=report_message,
        parse_mode=ParseMode.MARKDOWN
    )
    logger.info("Sent weekly report.")