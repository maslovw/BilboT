"""
Message handlers for BilboT
"""

import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from bilbot.utils.config import get_image_storage_path, is_debug_mode
from bilbot.utils.image_utils import save_receipt_image, process_and_save_receipt_data
from bilbot.utils.rate_limiter import check_rate_limit
from bilbot.database.db_manager import save_user, save_chat, save_receipt, get_receipt_items, user_exists

logger = logging.getLogger(__name__)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle incoming photos, save them locally, and store metadata in the database.
    
    Args:
        update (Update): The update containing the photo
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
    
    # Get user information
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    
    # In debug mode, check if the user is in the database
    if is_debug_mode():
        if not user_exists(user.id):
            logger.warning(f"Debug mode: Blocking message from unknown user {user.id} ({user.username})")
            await context.bot.send_message(
                chat_id=chat.id,
                reply_to_message_id=message.message_id,
                text="⚠️ Debug mode is enabled. Only authorized users can submit receipts."
            )
            return
        logger.info(f"Debug mode: Allowing message from known user {user.id} ({user.username})")
    
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
        # Send initial confirmation message
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=message.message_id,
            text=f"Receipt saved! ID: {receipt_id}\n\nProcessing receipt to extract data..."
        )
        
        # Process the receipt image to extract structured data
        process_success = await process_and_save_receipt_data(receipt_id, file_path)
        
        if process_success:
            # Get the extracted items
            items = get_receipt_items(receipt_id)
            
            if items:
                # Format the extracted items nicely
                items_text = "\n".join([f"• {item['item_name']}: ${item['item_price']:.2f}" for item in items])
                
                await context.bot.send_message(
                    chat_id=chat.id,
                    reply_to_message_id=message.message_id,
                    text=f"✅ Receipt processed successfully!\n\n"
                         f"Items detected:\n{items_text}\n\n"
                         f"You can view complete details later by using the /receipts command."
                )
            else:
                await context.bot.send_message(
                    chat_id=chat.id,
                    reply_to_message_id=message.message_id,
                    text="✅ Receipt processed, but no items were detected. "
                         "You can view any available details later using the /receipts command."
                )
        else:
            # Processing failed but the receipt was still saved
            await context.bot.send_message(
                chat_id=chat.id,
                reply_to_message_id=message.message_id,
                text="⚠️ Receipt was saved, but automatic processing couldn't extract all the details. "
                     "You can still view the receipt using the /receipts command."
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
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
    
    # Get user information
    user = update.effective_user
    chat = update.effective_chat
    message = update.message
    message_text = message.text
    
    # In debug mode, check if the user is in the database
    if is_debug_mode():
        if not user_exists(user.id):
            logger.warning(f"Debug mode: Blocking message from unknown user {user.id} ({user.username})")
            await context.bot.send_message(
                chat_id=chat.id,
                reply_to_message_id=message.message_id,
                text="⚠️ Debug mode is enabled. Only authorized users can interact with the bot."
            )
            return
        logger.info(f"Debug mode: Allowing message from known user {user.id} ({user.username})")
    
    # Save user and chat info to database
    save_user(user.id, user.username, user.first_name, user.last_name)
    save_chat(chat.id, chat.title, chat.type)
    
    # For now, just log the message
    logger.info(f"Received message from {user.username} in {chat.title if chat.title else 'private chat'}: {message_text}")
    
    # In the future, this could handle adding comments to previously sent receipts
    # or other functionality
