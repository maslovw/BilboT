"""
Command handlers for BilboT
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from bilbot.database.db_manager import get_user_receipts, save_user, save_chat
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
        f"• Use /list to see your stored receipts\n"
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
        "/list - List your stored receipts\n\n"
        "*How to use:*\n"
        "• Simply send a photo of a receipt to store it\n"
        "• Add a caption to include notes about the receipt\n"
        "• All receipts are stored securely for future reference\n"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_receipts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /list command to show the user's stored receipts.
    
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
        received_date = receipt['received_date']
        chat_title = receipt['chat_title'] or 'Private Chat'
        comments = receipt['comments'] or 'No comments'
        
        receipts_text += (
            #f"*{i}.* ID: {receipt['id']}\n"
            f"📅 Received: {received_date}\n"
            f"💬 From: {chat_title}\n"
            f"📝 Comments: {comments[:50]}{'...' if len(comments) > 50 else ''}\n\n"
        )
    
    await update.message.reply_text(receipts_text, parse_mode='Markdown')
