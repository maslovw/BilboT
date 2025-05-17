"""
Database manager for BilboT
"""

import sqlite3
import logging
import os
from datetime import datetime

from bilbot.utils.config import get_database_path

logger = logging.getLogger(__name__)

def init_database():
    """
    Initialize the SQLite database with necessary tables if they don't exist.
    """
    conn = None
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create chats table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            chat_type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create receipts table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id INTEGER,
            user_id INTEGER,
            chat_id INTEGER,
            image_path TEXT,
            received_date TIMESTAMP,
            receipt_date TIMESTAMP,
            comments TEXT,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (chat_id) REFERENCES chats (chat_id)
        )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
    finally:
        if conn:
            conn.close()

def save_user(user_id, username=None, first_name=None, last_name=None):
    """
    Save or update user information in the database.
    
    Args:
        user_id (int): Telegram user ID
        username (str): Telegram username
        first_name (str): User's first name
        last_name (str): User's last name
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Error saving user: {e}")
        return False
    finally:
        if conn:
            conn.close()

def save_chat(chat_id, chat_title=None, chat_type=None):
    """
    Save or update chat information in the database.
    
    Args:
        chat_id (int): Telegram chat ID
        chat_title (str): Title of the chat/group
        chat_type (str): Type of chat (private, group, etc.)
        
    Returns:
        bool: True if successful, False otherwise
    """
    conn = None
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO chats (chat_id, chat_title, chat_type)
        VALUES (?, ?, ?)
        ''', (chat_id, chat_title, chat_type))
        
        conn.commit()
        return True
        
    except sqlite3.Error as e:
        logger.error(f"Error saving chat: {e}")
        return False
    finally:
        if conn:
            conn.close()

def save_receipt(message_id, user_id, chat_id, image_path, received_date=None, receipt_date=None, comments=None):
    """
    Save receipt information in the database.
    
    Args:
        message_id (int): Telegram message ID
        user_id (int): User who sent the receipt
        chat_id (int): Chat where the receipt was sent
        image_path (str): Path to the stored image
        received_date (datetime): When the receipt was received
        receipt_date (datetime): Date on the receipt (to be extracted later)
        comments (str): Any comments provided with the receipt
        
    Returns:
        int: ID of the inserted receipt record, or None if failed
    """
    conn = None
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        if received_date is None:
            received_date = datetime.now()
        
        cursor.execute('''
        INSERT INTO receipts (message_id, user_id, chat_id, image_path, received_date, receipt_date, comments)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (message_id, user_id, chat_id, image_path, received_date, receipt_date, comments))
        
        receipt_id = cursor.lastrowid
        conn.commit()
        return receipt_id
        
    except sqlite3.Error as e:
        logger.error(f"Error saving receipt: {e}")
        return None
    finally:
        if conn:
            conn.close()

def get_user_receipts(user_id):
    """
    Get all receipts for a specific user.
    
    Args:
        user_id (int): Telegram user ID
        
    Returns:
        list: List of receipt records
    """
    conn = None
    try:
        db_path = get_database_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT r.*, c.chat_title
        FROM receipts r
        JOIN chats c ON r.chat_id = c.chat_id
        WHERE r.user_id = ?
        ORDER BY r.received_date DESC
        ''', (user_id,))
        
        receipts = [dict(row) for row in cursor.fetchall()]
        return receipts
        
    except sqlite3.Error as e:
        logger.error(f"Error retrieving receipts: {e}")
        return []
    finally:
        if conn:
            conn.close()
