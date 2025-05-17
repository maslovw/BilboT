"""
Script to update the database schema with new tables for receipt items and additional receipt data fields.
"""

import os
import sqlite3
import logging
from bilbot.utils.config import get_database_path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def update_database_schema():
    """
    Update the SQLite database with new tables and fields for receipt processing.
    """
    try:
        # Connect to the database
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if receipt_items table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='receipt_items'")
        if not cursor.fetchone():
            # Create receipt_items table
            cursor.execute('''
            CREATE TABLE receipt_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                item_price REAL NOT NULL,
                FOREIGN KEY (receipt_id) REFERENCES receipts (id)
            )
            ''')
            logger.info("Created receipt_items table")
        
        # Check if we need to add new columns to receipts table
        def column_exists(table, column):
            cursor.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cursor.fetchall())
        
        # Add new columns to receipts table if they don't exist
        new_columns = [
            ("store", "TEXT"),
            ("payment_method", "TEXT"),
            ("total_amount", "REAL"),
            ("processed", "INTEGER DEFAULT 0"),  # Boolean flag for whether image was processed
            ("extracted_data", "TEXT")  # JSON string of extracted data
        ]
        
        for column_name, column_type in new_columns:
            if not column_exists("receipts", column_name):
                cursor.execute(f"ALTER TABLE receipts ADD COLUMN {column_name} {column_type}")
                logger.info(f"Added column {column_name} to receipts table")
        
        # Commit changes
        conn.commit()
        logger.info("Database schema update completed successfully")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_database_schema()
