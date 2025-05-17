"""
Message handlers for BilboT
"""

import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from bilbot.utils.config import get_image_storage_path
from bilbot.utils.image_utils import save_receipt_image
from bilbot.database.db_manager import save_user, save_chat, save_receipt

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming photos, save them locally, and store metadata in the database.
    
    Args:
        update (Update): The update containing the photo
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Get user information
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    
    # Save user and chat info to database
    save_user(user.id, user.username, user.first_name, user.last_name)
    save_chat(chat.id, chat.title, chat.type)
    
    # Get the photo with the best quality (highest resolution)
    photo = message.photo[-1]
    
    # Get the image file
    image_file = await context.bot.get_file(photo.file_id)
    
    # Save the image using our utility function
    now = datetime.now()
    file_path = await save_receipt_image(image_file, user.id, chat.id, message.message_id)
    
    if not file_path:
        # Failed to save the image
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=message.message_id,
            text="Failed to save receipt image. Please try again."
        )
        return
    
    # Extract caption as comments if available
    comments = message.caption if message.caption else None
    
    # Save receipt information to database
    receipt_id = save_receipt(
        message.message_id,
        user.id,
        chat.id,
        file_path,
        received_date=datetime.now(),
        receipt_date=None,  # Will be extracted later
        comments=comments
    )
    
    if receipt_id:
        # Send confirmation message
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=message.message_id,
            text=f"Receipt saved! ID: {receipt_id}"
        )
    else:
        # Send error message
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=message.message_id,
            text="Failed to save receipt. Please try again."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle text messages (could be comments for receipts or general messages).
    
    Args:
        update (Update): The update containing the message
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # For now, just log the message
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    logger.info(f"Received message from {user.username} in {chat.title if chat.title else 'private chat'}: {message_text}")
    
    # In the future, this could handle adding comments to previously sent receipts
    # or other functionality
