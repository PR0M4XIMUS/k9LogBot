# report_cleanup.py

import sqlite3
from datetime import datetime
import os

DB_PATH = os.getenv("DB_PATH", "k9logbot.sqlite")  # Use your actual DB filename

def validate_date(date_text):
    """Validates that the date string is in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Incorrect date format for '{date_text}', should be YYYY-MM-DD")

def clean_detailed_report(from_date, to_date):
    """
    Removes all detailed report entries between two dates (inclusive).
    Dates should be in 'YYYY-MM-DD' format.

    Returns:
        dict: {
            "success": bool,
            "deleted_count": int,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "deleted_count": 0,
        "error": None
    }
    try:
        # Validate dates
        start_dt = validate_date(from_date)
        end_dt = validate_date(to_date)
        if start_dt > end_dt:
            raise ValueError("from_date must be before or equal to to_date")

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        # Get count before delete
        c.execute(
            "SELECT COUNT(*) FROM transactions WHERE DATE(date) >= ? AND DATE(date) <= ?",
            (from_date, to_date)
        )
        count_before = c.fetchone()[0]

        # Delete
        c.execute(
            "DELETE FROM transactions WHERE DATE(date) >= ? AND DATE(date) <= ?",
            (from_date, to_date)
        )
        conn.commit()

        result["success"] = True
        result["deleted_count"] = count_before
        conn.close()
        return result

    except Exception as e:
        result["error"] = str(e)
        return result

def get_report_entries(from_date, to_date):
    """
    Retrieve all transactions in the date range for reporting purposes.
    Returns a list of dicts: [{date, amount, type, description}, ...]
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT date, amount, type, description FROM transactions WHERE DATE(date) >= ? AND DATE(date) <= ? ORDER BY date ASC",
            (from_date, to_date)
        )
        rows = c.fetchall()
        conn.close()
        return [
            {
                "date": row[0], "amount": row[1], "type": row[2], "description": row[3]
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[get_report_entries] Error: {e}")
        return []

def get_total_transactions_count():
    """Returns the total number of transactions in the DB."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM transactions")
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        print(f"[get_total_transactions_count] Error: {e}")
        return 0

def get_transaction_table_structure():
    """
    Returns the schema of the transactions table for debugging/documentation.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("PRAGMA table_info(transactions)")
        info = c.fetchall()
        conn.close()
        return info
    except Exception as e:
        print(f"[get_transaction_table_structure] Error: {e}")
        return []

def get_recent_entries(count=10):
    """
    Retrieve the most recent N transactions.
    Returns a list of dicts with transaction details including IDs.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT id, date, amount, type, description FROM transactions ORDER BY date DESC, id DESC LIMIT ?",
            (count,)
        )
        rows = c.fetchall()
        conn.close()
        return [
            {
                "id": row[0], "date": row[1], "amount": row[2], 
                "type": row[3], "description": row[4]
            }
            for row in rows
        ]
    except Exception as e:
        print(f"[get_recent_entries] Error: {e}")
        return []

def clean_specific_entries(entry_ids):
    """
    Remove specific transactions by their IDs.
    
    Args:
        entry_ids: List of transaction IDs to delete
        
    Returns:
        dict: {
            "success": bool,
            "deleted_count": int,
            "error": str or None
        }
    """
    result = {
        "success": False,
        "deleted_count": 0,
        "error": None
    }
    
    if not entry_ids:
        result["error"] = "No entries specified for deletion"
        return result
        
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?'] * len(entry_ids))
        
        # Get count before delete
        c.execute(f"SELECT COUNT(*) FROM transactions WHERE id IN ({placeholders})", entry_ids)
        count_before = c.fetchone()[0]
        
        # Delete the entries
        c.execute(f"DELETE FROM transactions WHERE id IN ({placeholders})", entry_ids)
        conn.commit()
        
        result["success"] = True
        result["deleted_count"] = count_before
        conn.close()
        return result
        
    except Exception as e:
        result["error"] = str(e)
        return result