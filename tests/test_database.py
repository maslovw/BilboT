#!/usr/bin/env python3
"""
Test script for BilboT telegram bot
This script tests core functionality without requiring an actual Telegram connection
"""

import os
import unittest
import sqlite3
from datetime import datetime
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bilbot.utils.config import get_image_storage_path, get_database_path
from bilbot.database.db_manager import init_database, save_user, save_chat, save_receipt


class BilbotTests(unittest.TestCase):
    def setUp(self):
        # Use in-memory database for testing
        self.original_db_path = get_database_path
        
        # Mock the database path function to use in-memory database
        def mock_db_path():
            return ':memory:'
            
        # Replace the real function with our mock
        import bilbot.database.db_manager as db_manager
        db_manager.get_database_path = mock_db_path
        
        # Important: With SQLite in-memory database, we need to keep the connection
        # open for the lifetime of the test and share it with all database operations
        
        # Create a connection and store it globally
        db_manager.conn = sqlite3.connect(':memory:')
        db_manager.conn.row_factory = sqlite3.Row
        
        # Initialize the database tables using this connection
        init_database()
        
        # Use the same connection for the test
        self.conn = db_manager.conn
        self.cursor = self.conn.cursor()
        
    def tearDown(self):
        # Close the connection
        if self.conn:
            self.conn.close()
            
        # Restore original function
        import bilbot.database.db_manager as db_manager
        db_manager.get_database_path = self.original_db_path
        
    def test_user_save_retrieve(self):
        """Test saving and retrieving a user"""
        # Test data
        user_id = 123456789
        username = "testuser"
        first_name = "Test"
        last_name = "User"
        
        # Save user
        result = save_user(user_id, username, first_name, last_name)
        self.assertTrue(result)
        
        # Retrieve user
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cursor.fetchone()
        
        # Verify
        self.assertIsNotNone(user)
        self.assertEqual(user[0], user_id)
        self.assertEqual(user[1], username)
        self.assertEqual(user[2], first_name)
        self.assertEqual(user[3], last_name)
        
    def test_chat_save_retrieve(self):
        """Test saving and retrieving a chat"""
        # Test data
        chat_id = -100123456789
        chat_title = "Test Chat"
        chat_type = "group"
        
        # Save chat
        result = save_chat(chat_id, chat_title, chat_type)
        self.assertTrue(result)
        
        # Retrieve chat
        self.cursor.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
        chat = self.cursor.fetchone()
        
        # Verify
        self.assertIsNotNone(chat)
        self.assertEqual(chat[0], chat_id)
        self.assertEqual(chat[1], chat_title)
        self.assertEqual(chat[2], chat_type)
        
    def test_receipt_save_retrieve(self):
        """Test saving and retrieving a receipt"""
        # First create user and chat
        user_id = 123456789
        chat_id = -100123456789
        save_user(user_id, "testuser", "Test", "User")
        save_chat(chat_id, "Test Chat", "group")
        
        # Test data for receipt
        message_id = 1001
        image_path = "/path/to/test/image.jpg"
        received_date = datetime.now()
        comments = "Test receipt comments"
        
        # Save receipt
        receipt_id = save_receipt(
            message_id, user_id, chat_id, image_path, 
            received_date=received_date, receipt_date=None, 
            comments=comments
        )
        
        self.assertIsNotNone(receipt_id)
        
        # Retrieve receipt
        self.cursor.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,))
        receipt = self.cursor.fetchone()
        
        # Verify
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt[1], message_id)  # message_id is at index 1
        self.assertEqual(receipt[2], user_id)     # user_id is at index 2
        self.assertEqual(receipt[3], chat_id)     # chat_id is at index 3
        self.assertEqual(receipt[4], image_path)  # image_path is at index 4
        self.assertEqual(receipt[6], None)        # receipt_date is at index 6
        self.assertEqual(receipt[7], comments)    # comments is at index 7
        
    def test_image_storage_path(self):
        """Test that image storage path exists and is correct"""
        path = get_image_storage_path()
        self.assertTrue(os.path.exists(path))
        self.assertTrue(os.path.isdir(path))


if __name__ == "__main__":
    unittest.main()
