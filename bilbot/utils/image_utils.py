"""
Image utilities for BilboT
"""

import os
from datetime import datetime
from PIL import Image  # Using Pillow for potential image processing in the future
import logging

from bilbot.utils.config import get_image_storage_path

logger = logging.getLogger(__name__)

def save_receipt_image(file_obj, user_id, chat_id, message_id):
    """
    Save a receipt image to the local storage with organized folder structure.
    
    Args:
        file_obj: File object or path to the image
        user_id (int): ID of the user who sent the image
        chat_id (int): ID of the chat where the image was sent
        message_id (int): ID of the message containing the image
        
    Returns:
        str: Path where the image was saved, or None if there was an error
    """
    try:
        # Get the base storage path
        base_path = get_image_storage_path()
        
        # Create year/month/day folder structure
        now = datetime.now()
        year_folder = str(now.year)
        month_folder = f"{now.month:02d}"
        day_folder = f"{now.day:02d}"
        
        # Format: /data/images/2025/05/17/
        date_path = os.path.join(base_path, year_folder, month_folder, day_folder)
        
        # Create folders if they don't exist
        os.makedirs(date_path, exist_ok=True)
        
        # Create a unique filename with user_id, chat_id, and timestamp
        timestamp = now.strftime("%H%M%S")
        filename = f"receipt_{user_id}_{chat_id}_{message_id}_{timestamp}.jpg"
        
        # Full path to save the image
        full_path = os.path.join(date_path, filename)
        
        # Save the image
        if isinstance(file_obj, str):
            # If file_obj is a path, just copy or rename the file
            os.rename(file_obj, full_path)
        else:
            # If it's a file object, save it
            file_obj.download(full_path)
            
        logger.info(f"Saved receipt image to {full_path}")
        return full_path
        
    except Exception as e:
        logger.error(f"Error saving receipt image: {e}")
        return None
        
def get_receipt_image_path(user_id, chat_id, message_id, received_date):
    """
    Generate the path where a receipt image should be stored.
    
    Args:
        user_id (int): ID of the user who sent the image
        chat_id (int): ID of the chat where the image was sent
        message_id (int): ID of the message containing the image
        received_date (datetime): Date when the message was received
        
    Returns:
        str: Expected path of the image
    """
    base_path = get_image_storage_path()
    
    # Create year/month/day folder structure
    year_folder = str(received_date.year)
    month_folder = f"{received_date.month:02d}"
    day_folder = f"{received_date.day:02d}"
    
    # Format: /data/images/2025/05/17/
    date_path = os.path.join(base_path, year_folder, month_folder, day_folder)
    
    # We don't know the exact timestamp in the filename, so return the directory
    return date_path
