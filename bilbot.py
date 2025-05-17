#!/usr/bin/env python3
"""
BilboT - Telegram Receipt Bot

A bot that receives photos of receipts, stores them locally, and manages receipt information
in a SQLite database.
"""

import logging
import socket
import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Local imports
from bilbot.utils.config import get_bot_token, load_config
from bilbot.handlers.command_handlers import start, help_command, list_receipts, receipt_details
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

async def main():
    """Start the bot."""
    # Get the bot token from keyring
    token = get_bot_token()
    
    if not token:
        logger.error("Failed to retrieve bot token from keyring")
        return

    # Create the Application and pass it the bot token
    application = Application.builder().token(token).build()

    # Initialize the database
    init_database()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("receipts", list_receipts))
    application.add_handler(CommandHandler("list", list_receipts))  # Keep for backward compatibility
    
    # Handler for receipt details command with ID in format /details_123 or /details 123
    application.add_handler(CommandHandler("details", receipt_details))
    # Also catch details_<id> pattern
    application.add_handler(MessageHandler(
        filters.Regex(r'^/details_\d+$') & filters.COMMAND, 
        receipt_details
    ))

    # Register message handlers
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot and wait for termination signal
    logger.info("Starting bot...")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    logger.info("Bot started. Press Ctrl+C to stop.")
    
    # Simple way to keep the bot running
    try:
        # Keep the program running until user interrupts
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("User requested shutdown...")
    finally:
        # Properly shutdown bot
        logger.info("Shutting down...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("Bot stopped!")

if __name__ == '__main__':
    asyncio.run(main())
