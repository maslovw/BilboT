"""
Rate limiter functionality for BilboT

This module provides rate limiting capabilities to prevent abuse
by limiting the number of messages a user can send in a given time period,
as well as overall message rate for the bot.
"""

import time
import logging
from collections import defaultdict
from datetime import datetime
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from bilbot.utils.config import load_config

logger = logging.getLogger(__name__)

# Load configuration
config = load_config()
rate_limit_config = config.get('rate_limiting', {})
RATE_LIMIT_ENABLED = rate_limit_config.get('enabled', True)
PER_USER_LIMIT_SECONDS = rate_limit_config.get('per_user_seconds', 10)
GLOBAL_LIMIT_PER_MINUTE = rate_limit_config.get('global_per_minute', 60)

class RateLimiter:
    """
    Rate limiter for Telegram messages
    
    Provides per-user and global rate limiting
    """
    
    def __init__(self, per_user_limit_seconds=PER_USER_LIMIT_SECONDS, 
                 global_limit_per_minute=GLOBAL_LIMIT_PER_MINUTE,
                 enabled=RATE_LIMIT_ENABLED):
        """
        Initialize the rate limiter
        
        Args:
            per_user_limit_seconds (int): Minimum seconds between messages for a single user
            global_limit_per_minute (int): Maximum number of messages allowed per minute across all users
            enabled (bool): Whether rate limiting is enabled
        """
        self.per_user_limit_seconds = per_user_limit_seconds
        self.global_limit_per_minute = global_limit_per_minute
        self.enabled = enabled
        
        # Track last message time for each user
        self.user_last_message = defaultdict(float)
        
        # Track global message timestamps for the last minute
        self.global_messages = []
        
        logger.info(f"Rate limiter initialized: per user: {per_user_limit_seconds}s, " 
                    f"global: {global_limit_per_minute}/min, enabled: {enabled}")
    
    def _clean_expired_global_messages(self):
        """Remove message timestamps older than 1 minute"""
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # Keep only messages from the last minute
        self.global_messages = [t for t in self.global_messages if t > one_minute_ago]
    
    def check_user_limit(self, user_id):
        """
        Check if a user has exceeded their rate limit
        
        Args:
            user_id (int): Telegram user ID
            
        Returns:
            tuple: (allowed, time_to_wait)
                - allowed (bool): Whether the message is allowed
                - time_to_wait (float): Seconds to wait before next message is allowed
        """
        current_time = time.time()
        last_message_time = self.user_last_message.get(user_id, 0)
        time_since_last = current_time - last_message_time
        
        if time_since_last < self.per_user_limit_seconds:
            time_to_wait = self.per_user_limit_seconds - time_since_last
            return False, time_to_wait
        
        # Update last message time for this user
        self.user_last_message[user_id] = current_time
        return True, 0
    
    def check_global_limit(self):
        """
        Check if the global rate limit has been exceeded
        
        Returns:
            bool: Whether the message is allowed
        """
        # Clean up expired timestamps
        self._clean_expired_global_messages()
        
        # Check if we've hit the global limit
        if len(self.global_messages) >= self.global_limit_per_minute:
            return False
        
        # Add current timestamp to global messages
        self.global_messages.append(time.time())
        return True

# Create a singleton instance
rate_limiter = RateLimiter()

async def check_rate_limit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check if a message should be rate limited
    
    Args:
        update (Update): The Telegram update
        context (ContextTypes.DEFAULT_TYPE): The context object
        
    Returns:
        bool: True if message is allowed, False if rate limited
    """
    # If rate limiting is disabled, always allow messages
    if not rate_limiter.enabled:
        return True
        
    user = update.effective_user
    chat = update.effective_chat
    
    # Check user-specific rate limit
    user_allowed, wait_time = rate_limiter.check_user_limit(user.id)
    if not user_allowed:
        logger.info(f"Rate limiting user {user.id} ({user.username}). Must wait {wait_time:.1f} seconds.")
        
        # Notify user they're being rate limited
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=update.effective_message.message_id,
            text=f"You're sending messages too quickly. Please wait {int(wait_time)} seconds before sending another message."
        )
        return False
    
    # Check global rate limit
    global_allowed = rate_limiter.check_global_limit()
    if not global_allowed:
        logger.info(f"Global rate limit exceeded. Limiting user {user.id} ({user.username}).")
        
        # Notify user about global rate limit
        await context.bot.send_message(
            chat_id=chat.id,
            reply_to_message_id=update.effective_message.message_id,
            text="The bot is currently receiving too many messages. Please try again later."
        )
        return False
    
    # All rate limits passed
    return True
