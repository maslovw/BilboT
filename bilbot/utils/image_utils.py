"""
Image utilities for BilboT
"""

import os
from datetime import datetime
from PIL import Image  # Using Pillow for potential image processing in the future
import logging
import json

from bilbot.utils.config import get_image_storage_path
from bilbot.utils.ollama_processor import process_receipt_image
from bilbot.database.db_manager import update_receipt_with_extracted_data, save_receipt_items

logger = logging.getLogger(__name__)

async def save_receipt_image(file_obj, user_id, chat_id, message_id):
    """
    Save a receipt image to the local storage with organized folder structure.
    
    Args:
        file_obj: File object from telegram API
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
            await file_obj.download_to_drive(full_path)
            
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

async def process_and_save_receipt_data(receipt_id, image_path):
    """
    Process a receipt image with Ollama and save the extracted data to the database.
    
    Args:
        receipt_id (int): ID of the receipt in the database
        image_path (str): Path to the receipt image
        
    Returns:
        bool: True if processing was successful, False otherwise
    """
    try:
        logger.info(f"Processing receipt image for receipt_id {receipt_id}: {image_path}")
        
        # Process the image using Ollama
        receipt_data = await process_receipt_image(image_path)
        
        if not receipt_data:
            logger.error(f"Failed to extract data from receipt image: {image_path}")
            return False
            
        # Save items to database
        if receipt_data.get('items'):
            save_receipt_items(receipt_id, receipt_data['items'])
            
        # Parse date and time
        receipt_date = None
        if receipt_data.get('purchase_date') or receipt_data.get('purchase_time'):
            date_str = receipt_data.get('purchase_date', '')
            time_str = receipt_data.get('purchase_time', '')
            
            # Clean up time string - remove "Uhr" or other text
            if time_str:
                # Remove non-numeric parts except colon and period
                time_str = ' '.join([part for part in time_str.split() if any(c.isdigit() for c in part)])
                logger.debug(f"Cleaned time string: {time_str}")
            
            # Try to parse the date
            try:
                # Try common date formats
                date_formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M',
                    '%Y-%m-%d',
                    '%d/%m/%Y %H:%M:%S',
                    '%d/%m/%Y %H:%M',
                    '%d/%m/%Y',
                    '%m/%d/%Y %H:%M:%S',
                    '%m/%d/%Y %H:%M',
                    '%m/%d/%Y',
                    '%d.%m.%Y %H:%M:%S',
                    '%d.%m.%Y %H:%M',
                    '%d.%m.%Y',
                ]
                
                # First try with both date and time
                if date_str and time_str:
                    datetime_str = f"{date_str} {time_str}"
                    logger.debug(f"Attempting to parse datetime: {datetime_str}")
                    for fmt in date_formats:
                        try:
                            receipt_date = datetime.strptime(datetime_str, fmt)
                            logger.info(f"Successfully parsed date/time with format {fmt}: {receipt_date}")
                            break
                        except ValueError:
                            continue
                
                # If that fails, try just the date
                if receipt_date is None and date_str:
                    logger.debug(f"Attempting to parse date only: {date_str}")
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d.%m.%Y']:
                        try:
                            receipt_date = datetime.strptime(date_str, fmt)
                            logger.info(f"Successfully parsed date with format {fmt}: {receipt_date}")
                            break
                        except ValueError:
                            continue
                    
                # If we still don't have a date but we have a time, use today's date with the time
                if receipt_date is None and time_str:
                    try:
                        # Try to parse just the time and combine with today's date
                        for time_fmt in ['%H:%M:%S', '%H:%M']:
                            try:
                                time_obj = datetime.strptime(time_str, time_fmt).time()
                                today = datetime.today().date()
                                receipt_date = datetime.combine(today, time_obj)
                                logger.info(f"Using today's date with parsed time: {receipt_date}")
                                break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Failed to parse time: {e}")
            except Exception as e:
                logger.warning(f"Could not parse receipt date: {e}")
                # Try one more approach - look for patterns like DD.MM.YYYY directly
                if receipt_date is None and date_str:
                    try:
                        import re
                        # Look for date patterns in the format DD.MM.YYYY or similar
                        date_pattern = re.compile(r'(\d{1,2})[.-/](\d{1,2})[.-/](\d{2,4})')
                        match = date_pattern.search(date_str)
                        if match:
                            day, month, year = match.groups()
                            # Handle 2-digit years
                            if len(year) == 2:
                                year = '20' + year
                            receipt_date = datetime(int(year), int(month), int(day))
                            logger.info(f"Parsed date using regex: {receipt_date}")
                    except Exception as e:
                        logger.warning(f"Failed to parse date with regex: {e}")
                
        # Update receipt with extracted data
        success = update_receipt_with_extracted_data(
            receipt_id=receipt_id,
            store=receipt_data.get('store'),
            payment_method=receipt_data.get('payment_method'),
            total_amount=receipt_data.get('total_amount'),
            currency=receipt_data.get('currency'),
            receipt_date=receipt_date,
            extracted_data=json.dumps(receipt_data)
        )
        
        logger.info(f"Receipt data processed and saved successfully: {receipt_id}")
        return success
        
    except Exception as e:
        logger.error(f"Error in processing and saving receipt data: {e}")
        return False
