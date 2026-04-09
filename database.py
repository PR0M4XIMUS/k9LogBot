# database.py
import sqlite3
import os
import calendar
from datetime import datetime

# Database file path - using a data directory that can be mounted as a volume
DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'k9_log.db')

def ensure_data_directory():
    """Ensure the data directory exists."""
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

def get_db_connection():
    """Get a database connection with performance optimizations."""
    ensure_data_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Performance optimizations for SQLite
    conn.execute('PRAGMA journal_mode=WAL')  # Write-Ahead Logging for better concurrency
    conn.execute('PRAGMA synchronous=NORMAL')  # Balance between safety and performance
    conn.execute('PRAGMA temp_store=MEMORY')  # Use memory for temp tables
    conn.execute('PRAGMA mmap_size=268435456')  # 256MB memory map

    return conn

def init_db():
    """Initialize the database with required tables."""
    ensure_data_directory()
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL,
                description TEXT
            )
        ''')

        # Add notes column to transactions if it doesn't exist
        try:
            cursor.execute('ALTER TABLE transactions ADD COLUMN notes TEXT')
        except Exception:
            pass  # Column already exists

        # Create balance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS balance (
                id INTEGER PRIMARY KEY,
                current_balance REAL NOT NULL DEFAULT 0.0
            )
        ''')

        # Initialize balance if it doesn't exist
        cursor.execute('SELECT COUNT(*) FROM balance')
        if cursor.fetchone()[0] == 0:
            cursor.execute('INSERT INTO balance (id, current_balance) VALUES (1, 0.0)')

        # Create settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        # Insert default walk rate if not present
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('walk_rate', '75.0')
        ''')

        # Create users table for broadcast
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_seen TEXT NOT NULL
            )
        ''')

        # Create user_settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                weekly_goal INTEGER DEFAULT 0,
                reminder_time TEXT,
                reminder_enabled INTEGER DEFAULT 0
            )
        ''')

        # Create indexes for better query performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_transaction_type
            ON transactions(transaction_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON transactions(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_type_timestamp
            ON transactions(transaction_type, timestamp)
        ''')

        conn.commit()

# --- Settings ---

def get_walk_rate():
    """Get the current walk rate from settings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'walk_rate'")
        row = cursor.fetchone()
        return float(row[0]) if row else 75.0

def set_walk_rate(amount):
    """Set the walk rate in settings."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('walk_rate', ?)",
            (str(float(amount)),)
        )
        conn.commit()

# --- Users ---

def register_user(user_id, username=None):
    """Register a user (INSERT OR IGNORE)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_seen) VALUES (?, ?, ?)",
            (user_id, username, datetime.now().isoformat())
        )
        conn.commit()

def get_all_user_ids():
    """Get all registered user IDs."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in cursor.fetchall()]

# --- Walk operations ---

def add_walk(notes=None):
    """Add a dog walk transaction using the current walk rate.

    Returns:
        (walk_id, rate) tuple
    """
    rate = get_walk_rate()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, rate, 'walk', 'Dog walk', notes))

        walk_id = cursor.lastrowid

        # Update balance
        cursor.execute('UPDATE balance SET current_balance = current_balance + ? WHERE id = 1', (rate,))
        conn.commit()

    return walk_id, rate

def update_walk_note(transaction_id, note):
    """Update the note on an existing walk transaction."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE transactions SET notes = ? WHERE id = ?",
            (note, transaction_id)
        )
        conn.commit()

# --- Balance ---

def get_current_balance():
    """Get the current balance."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT current_balance FROM balance WHERE id = 1')
        result = cursor.fetchone()
        return result[0] if result else 0.0

def set_initial_balance(amount):
    """Set the initial balance."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, amount, 'initial_balance', f'Initial balance set to {amount:.2f} MDL'))

        cursor.execute('UPDATE balance SET current_balance = ? WHERE id = 1', (amount,))
        conn.commit()

def record_payment(amount, description):
    """Record a payment (reduces balance)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, -amount, 'payment', description))

        cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))
        conn.commit()

def record_credit_given(amount, description):
    """Record credit given (reduces balance)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, -amount, 'credit_given', description))

        cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))
        conn.commit()

# --- Reports ---

def get_weekly_report_data():
    """Get data for weekly reports."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*), SUM(amount)
            FROM transactions
            WHERE transaction_type = 'walk'
            AND date(timestamp) >= date('now', '-7 days')
        ''')
        walk_data = cursor.fetchone()
        walk_count = walk_data[0] if walk_data[0] else 0
        walk_total = walk_data[1] if walk_data[1] else 0.0

        cursor.execute('''
            SELECT SUM(ABS(amount))
            FROM transactions
            WHERE transaction_type IN ('payment', 'credit_given')
            AND date(timestamp) >= date('now', '-7 days')
        ''')
        payment_result = cursor.fetchone()
        payment_total = payment_result[0] if payment_result[0] else 0.0

        return walk_count, walk_total, payment_total

def get_all_transactions_for_report():
    """Get all transactions for detailed report (includes notes)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, amount, transaction_type, description, COALESCE(notes, '')
            FROM transactions
            ORDER BY timestamp DESC
        ''')
        return cursor.fetchall()

def get_transactions_with_ids(limit=None, offset=0):
    """Get transactions with their IDs.

    Args:
        limit: Optional limit on number of transactions to return
        offset: Number of records to skip (for pagination)

    Returns:
        List of tuples: (id, timestamp, amount, transaction_type, description, notes)
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if limit:
            cursor.execute('''
                SELECT id, timestamp, amount, transaction_type, description, COALESCE(notes, '')
                FROM transactions
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        else:
            cursor.execute('''
                SELECT id, timestamp, amount, transaction_type, description, COALESCE(notes, '')
                FROM transactions
                ORDER BY timestamp DESC
            ''')
        return cursor.fetchall()

def delete_transaction_by_id(transaction_id):
    """Delete a single transaction by its ID and adjust balance accordingly.

    Returns:
        dict: {"success": bool, "amount": float, "transaction_type": str, "error": str or None}
    """
    result = {
        "success": False,
        "amount": 0.0,
        "transaction_type": None,
        "error": None
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                'SELECT amount, transaction_type FROM transactions WHERE id = ?',
                (transaction_id,)
            )
            row = cursor.fetchone()

            if not row:
                result["error"] = "Transaction not found"
                return result

            amount, transaction_type = row[0], row[1]

            if transaction_type == 'walk':
                cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))
            elif transaction_type in ('payment', 'credit_given'):
                cursor.execute('UPDATE balance SET current_balance = current_balance + ? WHERE id = 1', (abs(amount),))
            elif transaction_type == 'initial_balance':
                cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))

            cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
            conn.commit()

            result["success"] = True
            result["amount"] = amount
            result["transaction_type"] = transaction_type
            return result

    except Exception as e:
        result["error"] = str(e)
        return result

def get_transaction_count():
    """Get total count of transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM transactions')
        return cursor.fetchone()[0]

# --- Streak & Goals ---

def get_streak():
    """Return the current consecutive-day walk streak."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT date(timestamp, 'localtime') as walk_date
            FROM transactions WHERE transaction_type = 'walk'
            ORDER BY walk_date DESC
        """)
        dates = [row[0] for row in cursor.fetchall()]
    if not dates:
        return 0
    from datetime import date, timedelta
    today = date.today()
    most_recent = date.fromisoformat(dates[0])
    if most_recent < today - timedelta(days=1):
        return 0  # streak broken
    streak = 0
    expected = most_recent
    for d in dates:
        walk_date = date.fromisoformat(d)
        if walk_date == expected:
            streak += 1
            expected -= timedelta(days=1)
        else:
            break
    return streak

def get_walks_this_week():
    """Return the count of walks since last Monday (inclusive)."""
    from datetime import date, timedelta
    today = date.today()
    week_start = (today - timedelta(days=today.weekday())).isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE transaction_type = 'walk'
            AND date(timestamp, 'localtime') >= ?
        """, (week_start,))
        return cursor.fetchone()[0]

def get_weekly_goal(user_id):
    """Return the weekly walk goal for a user (0 if not set)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT weekly_goal FROM user_settings WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        return row[0] if row else 0

def set_weekly_goal(user_id, goal):
    """Set (UPSERT) the weekly walk goal for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_settings (user_id, weekly_goal)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET weekly_goal = excluded.weekly_goal
        """, (user_id, goal))
        conn.commit()

# --- Reminders ---

def get_user_reminder(user_id):
    """Return {'time': str|None, 'enabled': bool} for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT reminder_time, reminder_enabled FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {'time': row[0], 'enabled': bool(row[1])}
        return {'time': None, 'enabled': False}

def set_user_reminder(user_id, time_str, enabled):
    """UPSERT reminder settings for a user."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_settings (user_id, reminder_time, reminder_enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                reminder_time = excluded.reminder_time,
                reminder_enabled = excluded.reminder_enabled
        """, (user_id, time_str, 1 if enabled else 0))
        conn.commit()

def get_users_with_reminders():
    """Return list of dicts for users with reminders enabled."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.user_id, us.reminder_time
            FROM users u
            JOIN user_settings us ON u.user_id = us.user_id
            WHERE us.reminder_enabled = 1 AND us.reminder_time IS NOT NULL
        """)
        return [{'user_id': row[0], 'reminder_time': row[1]} for row in cursor.fetchall()]

# --- Forecast ---

def get_earnings_forecast():
    """Return projected month earnings based on pace so far."""
    from datetime import date
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    day_of_month = today.day
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM transactions
            WHERE transaction_type = 'walk'
            AND strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now', 'localtime')
        """)
        earned = cursor.fetchone()[0]
    if day_of_month == 0:
        return earned
    return round((earned / day_of_month) * days_in_month, 2)

# --- Today's walks ---

def get_walks_today():
    """Return the count of walks logged today (localtime)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE transaction_type = 'walk'
            AND date(timestamp, 'localtime') = date('now', 'localtime')
        """)
        return cursor.fetchone()[0]

# --- Cleanup ---

def auto_cleanup_old_records(months_to_keep=1):
    """
    Automatically delete old transaction records without affecting balance.

    Args:
        months_to_keep: Number of months of records to keep (default: 1)

    Returns:
        dict: {"success": bool, "deleted_count": int, "cutoff_date": str, "error": str or None}
    """
    result = {
        "success": False,
        "deleted_count": 0,
        "cutoff_date": None,
        "error": None
    }

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            from datetime import datetime as _dt
            today = _dt.now()

            cutoff_date = today.replace(day=1)
            for _ in range(months_to_keep - 1):
                if cutoff_date.month == 1:
                    cutoff_date = cutoff_date.replace(year=cutoff_date.year - 1, month=12)
                else:
                    cutoff_date = cutoff_date.replace(month=cutoff_date.month - 1)

            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            result["cutoff_date"] = cutoff_str

            cursor.execute(
                'SELECT COUNT(*) FROM transactions WHERE date(timestamp) < ?',
                (cutoff_str,)
            )
            count_before = cursor.fetchone()[0]

            cursor.execute(
                'DELETE FROM transactions WHERE date(timestamp) < ?',
                (cutoff_str,)
            )

            conn.commit()

            result["success"] = True
            result["deleted_count"] = count_before
            return result

    except Exception as e:
        result["error"] = str(e)
        return result

def get_stats_summary():
    """Get optimized statistics summary without loading all transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions
            WHERE transaction_type = 'walk'
        ''')
        walk_data = cursor.fetchone()
        total_walks = walk_data[0] if walk_data[0] else 0
        total_earned = walk_data[1] if walk_data[1] else 0.0

        cursor.execute('''
            SELECT COUNT(*)
            FROM transactions
            WHERE transaction_type = 'walk'
            AND date(timestamp) = date('now', 'localtime')
        ''')
        walks_today_result = cursor.fetchone()
        walks_today = walks_today_result[0] if walks_today_result else 0

        return {
            'total_walks': total_walks,
            'total_earned': total_earned,
            'walks_today': walks_today
        }
