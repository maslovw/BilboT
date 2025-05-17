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
    get_receipt_items, user_exists
)
from bilbot.utils.rate_limiter import check_rate_limit
from bilbot.utils.currency_utils import get_currency_symbol
from bilbot.utils.config import is_debug_mode

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
    
    # Check debug authorization
    if not await check_debug_authorization(update, context):
        return  # User not authorized in debug mode
    
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
    
    # Check debug authorization
    if not await check_debug_authorization(update, context):
        return  # User not authorized in debug mode
        
    help_text = (
        "*BilboT - Receipt Management Bot*\n\n"
        "*Available Commands:*\n"
        "/start - Start the bot and see welcome message\n"
        "/help - Show this help message\n"
        "/receipts - List your stored receipts\n"
        "/details <receipt_id> - View detailed information for a specific receipt\n"
    )
    
    # Add debug mode commands if in debug mode
    if is_debug_mode():
        help_text += (
            "\n*Debug Mode Commands:*\n"
            "/add_debug_user <user_id> [username] [first_name] [last_name] - Add a user to the database\n"
            "\n⚠️ *Debug Mode is ENABLED* - Only authorized users can interact with the bot.\n"
        )
    
    help_text += (
        "\n*How to use:*\n"
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
    
    # Check debug authorization
    if not await check_debug_authorization(update, context):
        return  # User not authorized in debug mode
        
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
        currency = receipt.get('currency', 'USD')
        currency_symbol = get_currency_symbol(currency)
        total = f"{currency_symbol}{receipt['total_amount']:.2f} {currency}" if receipt.get('total_amount') else "Unknown amount"
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
    
    # Check debug authorization
    if not await check_debug_authorization(update, context):
        return  # User not authorized in debug mode
    
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
    currency = receipt.get('currency', 'USD')
    processed = receipt.get('processed', 0) == 1
    
    details_text += (
        f"📅 *Date Received*: {received_date}\n"
        f"🛒 *Purchase Date*: {receipt_date}\n"
        f"🏪 *Store*: {store}\n"
        f"💳 *Payment Method*: {payment_method}\n"
    )
    
    if total_amount is not None:
        currency_symbol = get_currency_symbol(currency)
        details_text += f"💰 *Total Amount*: {currency_symbol}{total_amount:.2f} {currency}\n"
    else:
        details_text += f"💰 *Total Amount*: Unknown\n"
    
    details_text += f"📝 *Comments*: {comments}\n\n"
    
    # Receipt items
    if items:
        details_text += "*Items*:\n"
        currency_symbol = get_currency_symbol(currency)
        for i, item in enumerate(items, 1):
            details_text += f"{i}. {item['item_name']}: {currency_symbol}{item['item_price']:.2f}\n"
    else:
        if processed:
            details_text += "*Items*: No items detected in the receipt.\n"
        else:
            details_text += "*Items*: Receipt has not been processed yet.\n"
    
    # Add receipt processing status
    details_text += f"\n*Status*: {'✅ Processed' if processed else '⏳ Not processed'}"
    
    # Send the detailed information
    await update.message.reply_text(details_text, parse_mode='Markdown')

async def check_debug_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check if the user is authorized to use the bot in debug mode.
    
    Args:
        update (Update): The update object
        context (ContextTypes.DEFAULT_TYPE): The context object
        
    Returns:
        bool: True if the user is authorized, False otherwise
    """
    if not is_debug_mode():
        # Debug mode is disabled, all users are authorized
        return True
        
    user = update.effective_user
    chat = update.effective_chat
    message = update.effective_message
    
    # In debug mode, check if the user is in the database
    if not user_exists(user.id):
        logger.warning(f"Debug mode: Blocking command from unknown user {user.id} ({user.username})")
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=message.message_id,
            text="⚠️ Debug mode is enabled. Only authorized users can use this command."
        )
        return False
        
    logger.info(f"Debug mode: Allowing command from known user {user.id} ({user.username})")
    return True

async def add_debug_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /add_debug_user command to add a user to the database in debug mode.
    This command can only be run by users already in the database.
    
    Args:
        update (Update): The update containing the command
        context (ContextTypes.DEFAULT_TYPE): The context object
    """
    # Check rate limits before processing
    if not await check_rate_limit(update, context):
        return  # Message was rate limited
    
    # Make sure the command issuer is authorized
    if not await check_debug_authorization(update, context):
        return  # User not authorized in debug mode
    
    # Get arguments
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(
            "Please provide a user ID to add to the debug users list.\n"
            "Usage: /add_debug_user <user_id> [username] [first_name] [last_name]"
        )
        return
    
    try:
        user_id = int(args[0])
        username = args[1] if len(args) > 1 else None
        first_name = args[2] if len(args) > 2 else "Debug"
        last_name = args[3] if len(args) > 3 else "User"
        
        # Check if user already exists
        if user_exists(user_id):
            await update.message.reply_text(f"User with ID {user_id} is already in the database.")
            return
        
        # Add the user to the database
        success = save_user(user_id, username, first_name, last_name)
        
        if success:
            await update.message.reply_text(
                f"✅ Successfully added user to the database:\n"
                f"ID: {user_id}\n"
                f"Username: {username or 'Not provided'}\n"
                f"Name: {first_name} {last_name}"
            )
        else:
            await update.message.reply_text("❌ Failed to add user to the database. Please check the logs.")
            
    except ValueError:
        await update.message.reply_text("Invalid user ID. Please provide a numeric user ID.")
        return
