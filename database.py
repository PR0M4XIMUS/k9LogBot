# database.py
import sqlite3 # Import the SQLite library for database operations
from datetime import datetime, timedelta # Import datetime for handling dates and times

# Define the name of our database file.
# If running in Docker, this path is inside the Docker volume for persistent storage.
# If running without Docker, change it to "dog_walks.db" to store it in the same folder.
DATABASE_NAME = "/app/data/dog_walks.db"

def init_db():
    """
    Initializes the SQLite database.
    This function creates tables if they don't already exist.
    """
    # Connect to the database file. If it doesn't exist, SQLite will create it.
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor() # A cursor allows us to execute SQL commands

    # --- Create 'transactions' table ---
    # This table will store every financial event (walks, payments, credits).
    # 'id' is a unique number for each entry.
    # 'timestamp' records when the transaction happened.
    # 'amount' stores the money value (positive for money owed to you, negative for money you owe).
    # 'type' categorizes the transaction (e.g., 'walk', 'payment', 'credit_given').
    # 'description' provides more details.
    # 'week_number' and 'year' are for weekly reports.
    cursor.execute("DROP TABLE IF EXISTS walks") # Remove old 'walks' table if it exists (for fresh start)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            amount REAL NOT NULL, -- Real means it can store decimal numbers (like money)
            type TEXT NOT NULL,  -- e.g., 'walk', 'payment', 'credit_given', 'manual_cashout'
            description TEXT,    -- Optional description
            week_number INTEGER NOT NULL,
            year INTEGER NOT NULL
        )
    ''')

    # --- Create 'balances' table ---
    # This table stores the single, current total balance.
    # We only need one row in this table (id = 1).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            current_balance REAL NOT NULL DEFAULT 0.0,
            last_cashout_date TEXT -- To track when the last major cashout happened
        )
    ''')

    # Initialize the 'balances' table with a default balance of 0.0 if it's empty.
    # 'INSERT OR IGNORE' means it only inserts if the row with id=1 doesn't exist.
    cursor.execute("INSERT OR IGNORE INTO balances (id, current_balance) VALUES (1, 0.0)")

    conn.commit() # Save (commit) the changes to the database
    conn.close() # Close the database connection

def _add_transaction(amount, transaction_type, description=None):
    """
    Helper function to record any type of financial transaction.
    It adds an entry to the 'transactions' table and updates the 'current_balance'.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    now = datetime.now() # Get the current date and time
    # Get the ISO week number and year for reporting
    week_number = now.isocalendar()[1]
    year = now.year

    # Insert the new transaction into the 'transactions' table
    cursor.execute(
        "INSERT INTO transactions (timestamp, amount, type, description, week_number, year) VALUES (?, ?, ?, ?, ?, ?)",
        (now.isoformat(), amount, transaction_type, description, week_number, year)
    )
    # Update the overall current balance by adding the transaction amount
    cursor.execute("UPDATE balances SET current_balance = current_balance + ?", (amount,))
    conn.commit() # Save changes
    conn.close() # Close connection
    return True

def add_walk(amount=75.0):
    """Records a single dog walk. Walks increase the balance owed to you."""
    return _add_transaction(amount, 'walk', 'Dog walk')

def record_payment(amount, description="Manual cash out"):
    """
    Records a payment received from Nana. Payments reduce the balance.
    The amount is passed as a positive number (e.g., 100), but stored as negative
    to reflect it decreasing the balance owed to you.
    """
    return _add_transaction(-abs(amount), 'payment', description)

def record_credit_given(amount, description="Advance payment/Credit from Nana"):
    """
    Records money Nana paid you in advance, or money they lent you.
    This reduces the amount they currently owe you (makes your balance lower or more negative).
    Similar to a payment, it's stored as negative.
    """
    return _add_transaction(-abs(amount), 'credit_given', description)

def get_current_balance():
    """Retrieves the current total balance from the 'balances' table."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT current_balance FROM balances WHERE id = 1")
    balance = cursor.fetchone()[0] # Get the first (and only) result
    conn.close()
    return balance

def set_initial_balance(amount):
    """
    Sets the current total balance to a specific amount.
    This is used for commands like /setinitial to adjust the balance manually.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE balances SET current_balance = ?", (amount,))
    conn.commit()
    conn.close()

def get_weekly_report_data(report_for_date=None):
    """
    Generates data for the weekly report.
    By default, it gets data for the week that just ended (last Sunday).
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    if report_for_date:
        # If a specific date is given, use its week number and year
        target_date = report_for_date
    else:
        # Otherwise, calculate the previous Sunday's week
        today = datetime.now()
        # Calculate how many days ago was the last Sunday (weekday Monday=0, Sunday=6)
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)
        target_date = last_sunday

    # Get the week number and year for the report
    report_week_number = target_date.isocalendar()[1]
    report_year = target_date.year

    # Count walks for the specific week
    cursor.execute(
        "SELECT COUNT(*), SUM(amount) FROM transactions WHERE week_number = ? AND year = ? AND type = 'walk'",
        (report_week_number, report_year)
    )
    walks_count, total_walk_amount = cursor.fetchone()

    # Sum up payments/credits for the specific week (these amounts are negative in DB)
    cursor.execute(
        "SELECT SUM(amount) FROM transactions WHERE week_number = ? AND year = ? AND type IN ('payment', 'credit_given')",
        (report_week_number, report_year)
    )
    total_payment_credit_amount = cursor.fetchone()[0]

    # Handle cases where no data is found for the week (return 0 instead of None)
    if walks_count is None: walks_count = 0
    if total_walk_amount is None: total_walk_amount = 0.0
    if total_payment_credit_amount is None: total_payment_credit_amount = 0.0

    conn.close()
    return {
        "week_number": report_week_number,
        "year": report_year,
        "walks_count": walks_count,
        "total_walks_amount": total_walk_amount,
        "total_payment_credit_amount": total_payment_credit_amount # This will be negative if payments happened
    }

def get_all_transactions_for_report():
    """
    Retrieves all recorded transactions for the detailed report.
    It fetches timestamp, amount, type, and description for every transaction.
    """
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Select all details from the 'transactions' table, ordered by time
    cursor.execute("SELECT timestamp, amount, type, description FROM transactions ORDER BY timestamp")
    transactions = cursor.fetchall() # Get all matching rows
    conn.close()
    return transactions