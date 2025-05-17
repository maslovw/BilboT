"""
Configuration utilities for BilboT
"""

import socket
import keyring
import logging
import os
import json

logger = logging.getLogger(__name__)

# Path to the config file
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config.json")

def load_config():
    """
    Load configuration from the config file.
    
    Returns:
        dict: Configuration dictionary
    """
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"Config file not found: {CONFIG_FILE}")
            return {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def get_bot_token():
    """
    Retrieves the Telegram bot token from the system keyring.
    
    The token is expected to be stored under the service name "telegram_bilbo"
    with the hostname as the username.
    
    Returns:
        str: The bot token if found, None otherwise
    """
    try:
        hostname = socket.gethostname()
        token = keyring.get_password("telegram_bilbo", hostname)
        
        if not token:
            logger.warning(f"No token found for hostname {hostname}")
            return None
            
        return token
    except Exception as e:
        logger.error(f"Error retrieving token: {e}")
        return None

def get_image_storage_path():
    """
    Returns the path where receipt images should be stored.
    
    Returns:
        str: Absolute path to the image storage directory
    """
    # Get from config if available
    config = load_config()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Use config path if provided, otherwise default
    image_dir_rel = config.get('image_storage', {}).get('base_path', "data/images")
    image_dir = os.path.join(base_dir, image_dir_rel)
    
    # Create the directory if it doesn't exist
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
        
    return image_dir

def get_database_path():
    """
    Returns the path to the SQLite database file.
    
    Returns:
        str: Absolute path to the database file
    """
    # Get from config if available
    config = load_config()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Use config path if provided, otherwise default
    db_path_rel = config.get('database', {}).get('path', "data/receipts.db")
    db_path = os.path.join(base_dir, db_path_rel)
    
    # Ensure the data directory exists
    data_dir = os.path.dirname(db_path)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        
    return db_path
