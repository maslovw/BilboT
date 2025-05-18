#!/usr/bin/env python
"""
Test script to verify receipt image parsing with the updated code.
"""

import asyncio
import os
import logging
import json
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the receipt processing function
from bilbot.utils.ollama_processor import process_receipt_image

async def test_receipt_parsing():
    """Test parsing a receipt image with the updated code."""
    # Find a receipt image to test
    images_dir = "data/images/2025/05/17"
    
    # Use the most recent receipt as a test
    image_files = sorted([f for f in os.listdir(images_dir) if f.startswith("receipt_")])
    
    if not image_files:
        print("No receipt images found in", images_dir)
        return
    
    # Test with the most recent receipt
    test_image = os.path.join(images_dir, image_files[-1])
    print(f"Testing with image: {test_image}")
    
    # Process the receipt
    receipt_data = await process_receipt_image(test_image)
    
    # Check the results
    if receipt_data:
        print("\nReceipt data extracted successfully:")
        print(f"Items: {len(receipt_data.get('items', []))} items found")
        
        # Print each item
        for i, item in enumerate(receipt_data.get('items', []), 1):
            print(f"  Item {i}: {item.get('item')} - {item.get('price')}")
        
        # Print date and time fields
        print(f"Purchase date: {receipt_data.get('purchase_date')}")
        print(f"Purchase time: {receipt_data.get('purchase_time')}")
        
        # Format as a datetime if both are present
        if receipt_data.get('purchase_date') and receipt_data.get('purchase_time'):
            try:
                date_str = receipt_data.get('purchase_date')
                time_str = receipt_data.get('purchase_time')
                
                # Simplified version of the parsing in image_utils.py
                time_str = ' '.join([part for part in time_str.split() if any(c.isdigit() for c in part)])
                datetime_str = f"{date_str} {time_str}"
                
                for fmt in ['%d.%m.%Y %H:%M:%S', '%d.%m.%Y %H:%M']:
                    try:
                        dt = datetime.strptime(datetime_str, fmt)
                        print(f"Parsed datetime: {dt}")
                        break
                    except ValueError:
                        continue
            except Exception as e:
                print(f"Error parsing datetime: {e}")
        
        # Print other fields
        print(f"Store: {receipt_data.get('store')}")
        print(f"Payment method: {receipt_data.get('payment_method')}")
        print(f"Currency: {receipt_data.get('currency')}")
        print(f"Total amount: {receipt_data.get('total_amount')}")
        
        # Print total amount validation results if available
        if 'total_amount_validated' in receipt_data:
            if receipt_data['total_amount_validated']:
                print("✅ Total amount validation: PASSED")
            else:
                calculated_total = receipt_data.get('calculated_total')
                difference = receipt_data.get('total_difference')
                print(f"⚠️ Total amount validation: FAILED")
                print(f"   Stated total: {receipt_data['total_amount']}")
                print(f"   Calculated from items: {calculated_total:.2f}")
                print(f"   Difference: {difference:.2f} {receipt_data.get('currency', '')}")
        elif 'items' in receipt_data and receipt_data['items']:
            # Calculate and display total from items if not already provided
            calculated_total = sum(item['price'] for item in receipt_data['items'])
            print(f"Calculated total from items: {calculated_total:.2f}")
            
            if 'total_amount' in receipt_data and receipt_data['total_amount'] is not None:
                difference = abs(receipt_data['total_amount'] - calculated_total)
                if difference <= 0.01:
                    print("✅ Totals match")
                else:
                    print(f"⚠️ Totals differ by {difference:.2f} {receipt_data.get('currency', '')}")
        
        # Save the full response for reference
        with open("data/test_receipt_result.json", "w") as f:
            json.dump(receipt_data, f, indent=2)
        print("\nFull result saved to data/test_receipt_result.json")
    else:
        print("Failed to extract data from receipt image")

if __name__ == "__main__":
    asyncio.run(test_receipt_parsing())
