#!/usr/bin/env python3
"""
Database migration script for BilboT to add currency column to receipts table
"""

import sqlite3
import logging
import os
import sys
import json

# Add the project root to the path so we can import from bilbot
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bilbot.utils.config import get_database_path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def migrate_add_currency_column():
    """
    Add a currency column to the receipts table
    """
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        logger.error(f"Database not found at {db_path}")
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the currency column exists
        cursor.execute("PRAGMA table_info(receipts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'currency' in column_names:
            logger.info("Currency column already exists in receipts table")
            return True
        
        # Add the currency column
        cursor.execute("ALTER TABLE receipts ADD COLUMN currency TEXT")
        
        # Commit changes
        conn.commit()
        
        # Update existing receipts to add currency information from extracted_data
        cursor.execute("SELECT id, extracted_data FROM receipts WHERE extracted_data IS NOT NULL")
        receipts = cursor.fetchall()
        
        for receipt_id, extracted_data in receipts:
            if not extracted_data:
                continue
                
            try:
                data = json.loads(extracted_data)
                currency = data.get('currency')
                
                if currency:
                    cursor.execute(
                        "UPDATE receipts SET currency = ? WHERE id = ?", 
                        (currency, receipt_id)
                    )
            except json.JSONDecodeError:
                logger.warning(f"Could not parse extracted_data for receipt {receipt_id}")
        
        # Set default for remaining records
        cursor.execute(
            "UPDATE receipts SET currency = 'USD' WHERE currency IS NULL"
        )
        
        # Commit changes
        conn.commit()
        
        logger.info("Successfully added currency column and populated data")
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    logger.info("Starting database migration to add currency column")
    success = migrate_add_currency_column()
    
    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
