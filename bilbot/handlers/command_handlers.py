"""
Command handlers for BilboT
"""

import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bilbot.database.db_manager import (
    get_user_receipts, save_user, save_chat, 
    get_receipt_items
)
from bilbot.utils.rate_limiter import check_rate_limit

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command to introduce the bot and its functionality.
    
    Args:
        update (Update): The update containing the command
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Save user and chat info to database
    save_user(user.id, user.username, user.first_name, user.last_name)
    save_chat(chat.id, chat.title, chat.type)
    
    # Create welcome message
    welcome_text = (
        f"👋 Hello, {user.first_name}!\n\n"
        f"I'm *BilboT*, your receipt management assistant. "
        f"I can help you store and organize your receipt images.\n\n"
        f"*How to use me:*\n"
        f"• Send me a photo of a receipt to store it\n"
        f"• Add a caption to include notes about the receipt\n"
        f"• I'll automatically extract items, prices, store info, and payment method\n"
        f"• Use /receipts to see your stored receipts\n"
        f"• Use /details <receipt_id> to see detailed receipt information\n"
        f"• Use /help to see all available commands\n\n"
        f"Let's get started! 📸"
    )
    
    # Send the welcome message
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /help command to show available bot commands.
    
    Args:
        update (Update): The update containing the command
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
        
    help_text = (
        "*BilboT - Receipt Management Bot*\n\n"
        "*Available Commands:*\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/receipts - List your stored receipts\n"
        "/details <receipt_id> - View detailed information for a specific receipt\n\n"
        "*How to use:*\n"
        "• Simply send a photo of a receipt to store it\n"
        "• Add a caption to include notes about the receipt\n"
        "• I'll automatically extract items, prices, store name, and payment method\n"
        "• All receipts are stored securely for future reference\n"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_receipts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /receipts command to show the user's stored receipts.
    
    Args:
        update (Update): The update containing the command
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
        
    user = update.effective_user
    
    # Get the user's receipts from the database
    receipts = get_user_receipts(user.id)
    
    if not receipts:
        await update.message.reply_text("You don't have any stored receipts yet. Send me a photo of a receipt to get started!")
        return
    
    # Create a summary of receipts
    receipts_text = f"*Your Receipts ({len(receipts)}):*\n\n"
    
    for i, receipt in enumerate(receipts, 1):
        receipt_id = receipt['id']
        received_date = receipt['received_date']
        chat_title = receipt['chat_title'] or 'Private Chat'
        store = receipt.get('store', 'Unknown store')
        total = f"${receipt['total_amount']:.2f}" if receipt.get('total_amount') else "Unknown amount"
        processed = "✅ Processed" if receipt.get('processed') else "⏳ Not processed"
        
        receipts_text += (
            f"*{i}.* ID: {receipt_id}\n"
            f"📅 Received: {received_date}\n"
            f"🏪 Store: {store}\n"
            f"💰 Total: {total}\n"
            f"Status: {processed}\n"
            f"Use /details_{receipt_id} for more information\n\n"
        )
        
        # Telegram message length limit is 4096 characters
        if len(receipts_text) > 3800:  # Leave some buffer
            receipts_text += "...\nToo many receipts to display. Please use /details_<receipt_id> to view specific receipts."
            break
    
    await update.message.reply_text(receipts_text, parse_mode='Markdown')

async def receipt_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /details_<receipt_id> command to show detailed receipt information.
    
    Args:
        update (Update): The update containing the command
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
    
    user = update.effective_user
    command_text = update.message.text.strip()
    
    # Extract receipt ID from command
    try:
        if command_text.startswith('/details_'):
            receipt_id = int(command_text.split('_')[1])
        elif command_text.startswith('/details'):
            parts = command_text.split()
            if len(parts) < 2:
                await update.message.reply_text(
                    "Please specify a receipt ID. Example: `/details 123`", 
                    parse_mode='Markdown'
                )
                return
            receipt_id = int(parts[1])
        else:
            await update.message.reply_text("Invalid command format. Use `/details <receipt_id>`", parse_mode='Markdown')
            return
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Invalid receipt ID. Please use a valid numeric ID.", 
            parse_mode='Markdown'
        )
        return
    
    # Get the user's receipts from the database
    receipts = get_user_receipts(user.id)
    
    # Find the specific receipt
    receipt = None
    for r in receipts:
        if r['id'] == receipt_id:
            receipt = r
            break
    
    if not receipt:
        await update.message.reply_text(
            "Receipt not found. Please check the ID and try again.", 
            parse_mode='Markdown'
        )
        return
    
    # Get receipt items
    items = get_receipt_items(receipt_id)
    
    # Create the detailed receipt view
    details_text = f"*Receipt Details (ID: {receipt_id})*\n\n"
    
    # Basic receipt info
    received_date = receipt['received_date']
    receipt_date = receipt.get('receipt_date', 'Unknown')
    chat_title = receipt['chat_title'] or 'Private Chat'
    comments = receipt['comments'] or 'No comments'
    store = receipt.get('store', 'Unknown store')
    payment_method = receipt.get('payment_method', 'Unknown payment method')
    total_amount = receipt.get('total_amount')
    processed = receipt.get('processed', 0) == 1
    
    details_text += (
        f"📅 *Date Received*: {received_date}\n"
        f"🛒 *Purchase Date*: {receipt_date}\n"
        f"🏪 *Store*: {store}\n"
        f"💳 *Payment Method*: {payment_method}\n"
    )
    
    if total_amount is not None:
        details_text += f"💰 *Total Amount*: ${total_amount:.2f}\n"
    else:
        details_text += f"💰 *Total Amount*: Unknown\n"
    
    details_text += f"📝 *Comments*: {comments}\n\n"
    
    # Receipt items
    if items:
        details_text += "*Items*:\n"
        for i, item in enumerate(items, 1):
            details_text += f"{i}. {item['item_name']}: ${item['item_price']:.2f}\n"
    else:
        if processed:
            details_text += "*Items*: No items detected in the receipt.\n"
        else:
            details_text += "*Items*: Receipt has not been processed yet.\n"
    
    # Add receipt processing status
    details_text += f"\n*Status*: {'✅ Processed' if processed else '⏳ Not processed'}"
    
    # Send the detailed information
    await update.message.reply_text(details_text, parse_mode='Markdown')
