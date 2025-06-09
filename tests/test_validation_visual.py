#!/usr/bin/env python3
"""
Test script for total_amount validation with a mismatch case,
including visual representation in an image.
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
# Ensure project root on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bilbot.utils.ollama_processor import ReceiptData, ReceiptItem, OllamaImageProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("validation_test")

async def test_validation_with_image():
    """
    Test total amount validation and create a visual representation.
    """
    print("Starting validation test with visual output...")
    
    # Create a synthetic receipt data with a mismatch
    receipt_data = ReceiptData(
        items=[
            ReceiptItem(item="Coffee", price=3.50),
            ReceiptItem(item="Sandwich", price=6.99),
            ReceiptItem(item="Bottled Water", price=1.99),
            ReceiptItem(item="Chocolate Bar", price=2.49),
        ],
        purchase_date="18.05.2025",
        purchase_time="22:30:00",
        store="Cafe Express",
        payment_method="Credit Card",
        currency="USD",
        # Set a total that doesn't match the sum of items (14.97)
        total_amount=19.99,
        is_valid=True
    )
    
    # Create a processor instance
    processor = OllamaImageProcessor()
    
    # Manually validate the total amount
    calculated_total = sum(item.price for item in receipt_data.items)
    total_difference = abs(receipt_data.total_amount - calculated_total)
    
    logger.info(f"Provided total_amount: {receipt_data.total_amount}, Calculated total: {calculated_total}")
    
    # Check if the totals are significantly different
    if total_difference > 0.01:  # Allow for small rounding differences
        logger.warning(
            f"Total amount mismatch: provided={receipt_data.total_amount}, calculated={calculated_total}, "
            f"difference={total_difference:.2f} {receipt_data.currency or ''}"
        )
        receipt_data.total_amount_validated = False
    else:
        logger.info("Total amount validated successfully")
        receipt_data.total_amount_validated = True
    
    # Print the results for verification
    print("\nValidation Test Results:")
    print(f"Items: {len(receipt_data.items)} items found")
    for i, item in enumerate(receipt_data.items, 1):
        print(f"  Item {i}: {item.item} - {item.price} {receipt_data.currency}")
    
    print(f"Stated total amount: {receipt_data.total_amount} {receipt_data.currency}")
    print(f"Calculated total from items: {calculated_total:.2f} {receipt_data.currency}")
    print(f"Difference: {total_difference:.2f} {receipt_data.currency}")
    
    if receipt_data.total_amount_validated:
        print("✅ Total amount validation: PASSED")
    else:
        print("⚠️ Total amount validation: FAILED")
    
    # Save the result to a file
    result = receipt_data.model_dump()
    with open("data/validation_test_visual.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nFull result saved to data/validation_test_visual.json")
    
    # Run through the diagnostic analysis
    diagnostic_text = processor._analyze_missing_bboxes(receipt_data)
    print("\nDiagnostic Analysis:")
    print(diagnostic_text)
    
    # Create a visual representation of the receipt with validation information
    create_visual_receipt(receipt_data)

def create_visual_receipt(receipt_data):
    """
    Create a visual representation of the receipt data with validation information.
    """
    print("Creating visual receipt representation...")
    
    # Create a blank image
    width, height = 400, 600
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    # Try to get a font
    try:
        font = ImageFont.truetype("Arial", 16)
        small_font = ImageFont.truetype("Arial", 12)
        print("Using Arial font")
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        print("Using default font")
    
    # Draw receipt header
    draw.text((20, 20), "Test Receipt", fill=(0, 0, 0), font=font)
    draw.text((20, 50), f"Store: {receipt_data.store}", fill=(0, 0, 0), font=font)
    draw.text((20, 70), f"Date: {receipt_data.purchase_date}", fill=(0, 0, 0), font=font)
    draw.text((20, 90), f"Time: {receipt_data.purchase_time}", fill=(0, 0, 0), font=font)
    
    # Draw a line
    draw.line([(20, 120), (width-20, 120)], fill=(0, 0, 0), width=1)
    
    # Draw items
    y_pos = 140
    for i, item in enumerate(receipt_data.items):
        item_text = f"{item.item}"
        draw.text((30, y_pos), item_text, fill=(0, 0, 0), font=font)
        price_text = f"{item.price:.2f} {receipt_data.currency}"
        # Get text width for right alignment
        try:
            if hasattr(font, 'getbbox'):
                price_width = font.getbbox(price_text)[2]
            else:
                price_width = len(price_text) * 8
        except Exception as e:
            print(f"Error calculating text width: {e}")
            price_width = len(price_text) * 8
        draw.text((width - 30 - price_width, y_pos), price_text, fill=(0, 0, 0), font=font)
        y_pos += 30
    
    # Draw a line
    draw.line([(20, y_pos), (width-20, y_pos)], fill=(0, 0, 0), width=1)
    y_pos += 20
    
    # Draw calculated total
    calculated_total = sum(item.price for item in receipt_data.items)
    calc_text = f"Calculated Total: {calculated_total:.2f} {receipt_data.currency}"
    # Calculate text width
    try:
        if hasattr(font, 'getbbox'):
            calc_width = font.getbbox(calc_text)[2]
        else:
            calc_width = len(calc_text) * 8
    except Exception as e:
        print(f"Error calculating text width: {e}")
        calc_width = len(calc_text) * 8
    draw.text((width - 30 - calc_width, y_pos), calc_text, fill=(0, 0, 255), font=font)
    y_pos += 30
    
    # Draw stated total
    total_text = f"Stated Total: {receipt_data.total_amount:.2f} {receipt_data.currency}"
    # Calculate text width
    try:
        if hasattr(font, 'getbbox'):
            total_width = font.getbbox(total_text)[2]
        else:
            total_width = len(total_text) * 8
    except Exception as e:
        print(f"Error calculating text width: {e}")
        total_width = len(total_text) * 8
    draw.text((width - 30 - total_width, y_pos), total_text, fill=(0, 0, 0), font=font)
    y_pos += 40
    
    # Draw validation status
    if receipt_data.total_amount_validated:
        validation_text = "✓ Total Validated"
        color = (0, 128, 0)  # Green
    else:
        difference = abs(receipt_data.total_amount - calculated_total)
        validation_text = f"⚠ Total Mismatch: {difference:.2f} {receipt_data.currency}"
        color = (255, 0, 0)  # Red
    draw.text((30, y_pos), validation_text, fill=color, font=font)
    
    # Save the image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"data/test_receipt_visual_{timestamp}.png"
    try:
        image.save(output_path)
        print(f"Visual receipt saved to {output_path}")
    except Exception as e:
        print(f"Error saving image: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(test_validation_with_image())
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
