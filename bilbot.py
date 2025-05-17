#!/usr/bin/env python3
"""
BilboT - Telegram Receipt Bot

A bot that receives photos of receipts, stores them locally, and manages receipt information
in a SQLite database.
"""

import logging
import socket
import os
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Local imports
from bilbot.utils.config import get_bot_token, load_config
from bilbot.handlers.command_handlers import start, help_command, list_receipts
from bilbot.handlers.message_handlers import handle_photo, handle_message
from bilbot.database.db_manager import init_database

# Load configuration
config = load_config()
logging_config = config.get('logging', {})

# Configure logging
logging.basicConfig(
    format=logging_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
    level=getattr(logging, logging_config.get('level', 'INFO'))
)
logger = logging.getLogger(__name__)

def main():
    """Start the bot."""
    # Get the bot token from keyring
    token = get_bot_token()
    
    if not token:
        logger.error("Failed to retrieve bot token from keyring")
        return

    # Create the Updater and pass it the bot token
    updater = Updater(token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Initialize the database
    init_database()

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("list", list_receipts))

    # Register message handlers
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_photo))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
