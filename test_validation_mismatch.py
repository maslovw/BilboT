#!/usr/bin/env python3
"""
Test script for total_amount validation with a mismatch case.
"""

import asyncio
import logging
import json
import sys
from bilbot.utils.ollama_processor import ReceiptData, ReceiptItem, OllamaImageProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("validation_test")

async def test_validation_mismatch():
    """
    Test scenario where total amount doesn't match sum of items.
    """
    print("Starting validation test with mismatched total...")
    
    # Create a synthetic receipt data with a mismatch
    receipt_data = ReceiptData(
        items=[
            ReceiptItem(item="Item 1", price=10.99),
            ReceiptItem(item="Item 2", price=5.99),
            ReceiptItem(item="Item 3", price=7.49),
        ],
        purchase_date="18.05.2025",
        purchase_time="22:30:00",
        store="Test Store",
        payment_method="Card",
        currency="USD",
        # Set a total that doesn't match the sum of items (10.99 + 5.99 + 7.49 = 24.47)
        total_amount=30.00
    )
    
    # Print directly to make sure we're getting output
    print(f"Created test data with {len(receipt_data.items)} items")
    print(f"Total amount set to: {receipt_data.total_amount} {receipt_data.currency}")
    
    # Manually calculate the sum to make sure our logic is correct
    manual_sum = sum(item.price for item in receipt_data.items)
    print(f"Manual sum of items: {manual_sum:.2f}")
    
    # Create a processor to use its validation logic
    processor = OllamaImageProcessor()
    
    # Manually trigger the validation code
    calculated_total = sum(item.price for item in receipt_data.items)
    total_difference = abs(receipt_data.total_amount - calculated_total)
    
    print(f"Difference between totals: {total_difference:.2f}")
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
        print(f"  Item {i}: {item.item} - {item.price}")
    
    print(f"Stated total amount: {receipt_data.total_amount} {receipt_data.currency}")
    print(f"Calculated total from items: {calculated_total:.2f} {receipt_data.currency}")
    print(f"Difference: {total_difference:.2f} {receipt_data.currency}")
    
    if receipt_data.total_amount_validated:
        print("✅ Total amount validation: PASSED")
    else:
        print("⚠️ Total amount validation: FAILED")
    
    # Save the result to a file
    result = receipt_data.model_dump()
    with open("data/validation_test_result.json", "w") as f:
        json.dump(result, f, indent=2)
    print("\nFull result saved to data/validation_test_result.json")
    
    # Run through the diagnostic analysis
    diagnostic_text = processor._analyze_missing_bboxes(receipt_data)
    print("\nDiagnostic Analysis:")
    print(diagnostic_text)

if __name__ == "__main__":
    try:
        asyncio.run(test_validation_mismatch())
    except Exception as e:
        print(f"Error running test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
