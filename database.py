# database.py
import sqlite3
import os
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

def add_walk():
    """Add a dog walk transaction (75 MDL)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Add transaction
        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, 75.0, 'walk', 'Dog walk'))
        
        # Update balance
        cursor.execute('UPDATE balance SET current_balance = current_balance + 75.0 WHERE id = 1')
        conn.commit()

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
        
        # Add transaction
        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, amount, 'initial_balance', f'Initial balance set to {amount:.2f} MDL'))
        
        # Update balance
        cursor.execute('UPDATE balance SET current_balance = ? WHERE id = 1', (amount,))
        conn.commit()

def record_payment(amount, description):
    """Record a payment (reduces balance)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Add transaction (negative amount for payment)
        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, -amount, 'payment', description))
        
        # Update balance
        cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))
        conn.commit()

def record_credit_given(amount, description):
    """Record credit given (reduces balance)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        # Add transaction (negative amount for credit given)
        cursor.execute('''
            INSERT INTO transactions (timestamp, amount, transaction_type, description)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, -amount, 'credit_given', description))
        
        # Update balance
        cursor.execute('UPDATE balance SET current_balance = current_balance - ? WHERE id = 1', (amount,))
        conn.commit()

def get_weekly_report_data():
    """Get data for weekly reports."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get walk count and total
        cursor.execute('''
            SELECT COUNT(*), SUM(amount) 
            FROM transactions 
            WHERE transaction_type = 'walk' 
            AND date(timestamp) >= date('now', '-7 days')
        ''')
        walk_data = cursor.fetchone()
        walk_count = walk_data[0] if walk_data[0] else 0
        walk_total = walk_data[1] if walk_data[1] else 0.0
        
        # Get payment/credit total
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
    """Get all transactions for detailed report."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, amount, transaction_type, description 
            FROM transactions 
            ORDER BY timestamp DESC
        ''')
        return cursor.fetchall()

def get_stats_summary():
    """Get optimized statistics summary without loading all transactions."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get total walk count and earnings
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE transaction_type = 'walk'
        ''')
        walk_data = cursor.fetchone()
        total_walks = walk_data[0] if walk_data[0] else 0
        total_earned = walk_data[1] if walk_data[1] else 0.0
        
        # Get walks today
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
