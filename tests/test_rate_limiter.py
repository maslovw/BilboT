#!/usr/bin/env python3
"""
A simple test script for the rate limiter functionality.
Simulates sending multiple messages to test the rate limiting.
"""

import asyncio
import logging
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from bilbot.utils.rate_limiter import rate_limiter, check_rate_limit

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MockUser:
    def __init__(self, user_id, username):
        self.id = user_id
        self.username = username
        self.first_name = f"User{user_id}"
        self.last_name = "Test"

class MockChat:
    def __init__(self, chat_id, chat_type="private"):
        self.id = chat_id
        self.title = None if chat_type == "private" else f"Group{chat_id}"
        self.type = chat_type

class MockMessage:
    def __init__(self, message_id, user_id, chat_id):
        self.message_id = message_id
        self.from_user = MockUser(user_id, f"user{user_id}")
        self.chat = MockChat(chat_id)

class MockUpdate:
    def __init__(self, update_id, user_id, chat_id, message_id):
        self.update_id = update_id
        self.effective_user = MockUser(user_id, f"user{user_id}")
        self.effective_chat = MockChat(chat_id)
        self.effective_message = MockMessage(message_id, user_id, chat_id)

class MockContext:
    def __init__(self):
        self.bot = AsyncMock()
        self.bot.send_message = AsyncMock(return_value=None)

async def test_per_user_rate_limit():
    """Test the per-user rate limiting"""
    logger.info("Testing per-user rate limiting...")
    
    # Create a mock context
    context = MockContext()
    
    # Set up test parameters
    user_id = 12345
    chat_id = 67890
    
    # Try to send messages rapidly from the same user
    for i in range(5):
        update = MockUpdate(i, user_id, chat_id, i)
        allowed = await check_rate_limit(update, context)
        
        logger.info(f"Message {i+1}: {'Allowed' if allowed else 'Rate limited'}")
        
        # Don't wait between messages to trigger rate limiting
        if i < 4:  # Don't sleep after the last message
            await asyncio.sleep(0.1)  # Very small delay to simulate rapid messages
    
    logger.info("Per-user rate limit test completed.")

async def test_global_rate_limit():
    """Test the global rate limiting"""
    logger.info("Testing global rate limiting...")
    
    # Create a mock context
    context = MockContext()
    
    # Send messages from different users to trigger global rate limit
    for i in range(70):  # Send more than the global limit (60/minute)
        # Use a different user ID for each message
        user_id = 10000 + i
        chat_id = 50000 + i
        update = MockUpdate(i, user_id, chat_id, i)
        
        allowed = await check_rate_limit(update, context)
        
        if i % 10 == 0:  # Log every 10th message to reduce output
            logger.info(f"Message {i+1} (User {user_id}): {'Allowed' if allowed else 'Rate limited'}")
        
        # Small delay to prevent the test from taking too long
        await asyncio.sleep(0.01)
    
    logger.info("Global rate limit test completed.")

async def test_with_disabled_rate_limiting():
    """Test with rate limiting disabled"""
    logger.info("Testing with rate limiting disabled...")
    
    # Save original enabled state and temporarily disable rate limiting
    original_enabled = rate_limiter.enabled
    rate_limiter.enabled = False
    
    # Create a mock context
    context = MockContext()
    
    # Try to send messages rapidly from the same user (should all be allowed)
    user_id = 12345
    chat_id = 67890
    
    for i in range(5):
        update = MockUpdate(i, user_id, chat_id, i)
        allowed = await check_rate_limit(update, context)
        
        logger.info(f"Message {i+1}: {'Allowed' if allowed else 'Rate limited'}")
        
        # Don't wait between messages
        if i < 4:  # Don't sleep after the last message
            await asyncio.sleep(0.01)
    
    # Restore original state
    rate_limiter.enabled = original_enabled
    logger.info("Disabled rate limiting test completed.")

async def main():
    """Run all the tests"""
    logger.info("Starting rate limiter tests...")
    
    # Test per-user rate limiting
    await test_per_user_rate_limit()
    
    # Wait a bit between tests
    logger.info("Waiting between tests...")
    await asyncio.sleep(2)
    
    # Test global rate limiting
    await test_global_rate_limit()
    
    # Wait a bit between tests
    logger.info("Waiting between tests...")
    await asyncio.sleep(2)
    
    # Test with rate limiting disabled
    await test_with_disabled_rate_limiting()
    
    logger.info("All rate limiter tests completed.")

if __name__ == "__main__":
    asyncio.run(main())
