"""
Ollama image processing module for extracting structured data from receipt images.
"""

import io
import json
import logging
import os
import sys
import asyncio
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
from pydantic import BaseModel, Field

from PIL import Image
import ollama

logger = logging.getLogger(__name__)

# Define data models for structured output
class ReceiptItem(BaseModel):
    item: str = Field(..., description="The name of the purchased item")
    price: float = Field(..., description="The price of the item")

class ReceiptData(BaseModel):
    items: List[ReceiptItem] = Field(default_factory=list, description="List of items and their prices")
    purchase_date: Optional[str] = Field(None, description="Date of purchase")
    purchase_time: Optional[str] = Field(None, description="Time of purchase")
    store: Optional[str] = Field(None, description="Name of the store")
    payment_method: Optional[str] = Field(None, description="Method of payment (cash, card, etc.)")
    total_amount: Optional[float] = Field(None, description="Total amount paid")
    currency: Optional[str] = Field(None, description="Currency used for the transaction (USD, EUR, etc.)")

class OllamaImageProcessor:
    """
    Process receipt images using Ollama and the specified vision model.
    """
    
    def __init__(self, model_name: str = "qwen2.5vl:32b", max_context_length: int = 8192):
        """
        Initialize the Ollama image processor.
        
        Args:
            model_name: The name of the Ollama model to use
            max_context_length: Maximum context length for the model
        """
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.system_prompt = (
            "You are a receipt analysis assistant. Analyze receipt images to extract structured data."
        )
        
        try:
            # Log the Ollama library version being used
            ollama_version = getattr(ollama, "__version__", "unknown")
            logger.info(f"Initialized Ollama image processor with model: {model_name}")
            logger.info(f"Using Ollama Python library version: {ollama_version}")
            logger.debug(f"Max context length: {max_context_length}")
        except Exception as e:
            logger.warning(f"Error getting Ollama version: {e}")
    
    async def process_image(self, image_path: str) -> Optional[ReceiptData]:
        """
        Process a receipt image and extract structured data.
        
        Args:
            image_path: Path to the receipt image
            
        Returns:
            ReceiptData: Structured data extracted from the receipt, or None if processing failed
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                logger.error(f"Image not found at path: {image_path}")
                return None
                
            # Load and prepare the image
            image_path = Path(image_path)
            
            # Process with Ollama chat API
            receipt_data = await self._process_with_chat(image_path)
            
            logger.info(f"Successfully processed receipt image: {image_path}")
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            return None
    
    async def _process_with_chat(self, image_path: Path) -> ReceiptData:
        """
        Process a receipt image using the ollama.chat API with format parameter.
        
        Args:
            image_path: Path to the receipt image
            
        Returns:
            ReceiptData: Structured data extracted from the receipt
        """
        try:
            logger.debug(f"Processing image with ollama.chat: {image_path}")
            
            # Set options with context length
            options = {
                "num_ctx": self.max_context_length,
                "temperature": 0  # Set to 0 for more deterministic output
            }
            
            # Save the timestamp for storing responses
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Call Ollama API with chat method and format parameter
            response = await ollama.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": "Please analyze this receipt image and extract the following information:\n"
                                  "1. List all items and their prices\n"
                                  "2. Purchase date (format: DD.MM.YYYY)\n"
                                  "3. Purchase time (format: HH:MM:SS)\n"
                                  "4. Store name\n"
                                  "5. Payment method used\n"
                                  "6. Currency used (USD, EUR, etc.)\n"
                                  "7. Total amount paid",
                        "images": [image_path]
                    }
                ],
                format=ReceiptData.model_json_schema(),  # Pass schema for structured output
                options=options
            )
            
            # Save raw response for debugging
            data_dir = "data"
            os.makedirs(data_dir, exist_ok=True)
            raw_response_path = os.path.join(data_dir, f"response_{timestamp}_raw.json")
            with open(raw_response_path, 'w') as f:
                f.write(json.dumps(response.model_dump(), indent=2))
            
            # Save the processed message content
            processed_response_path = os.path.join(data_dir, f"response_{timestamp}_processed.txt")
            with open(processed_response_path, 'w') as f:
                f.write(response.message.content)
            
            logger.debug(f"Saved raw response to {raw_response_path}")
            logger.debug(f"Saved processed response to {processed_response_path}")
            
            # Parse the response directly as a ReceiptData object
            try:
                receipt_data = ReceiptData.model_validate_json(response.message.content)
                logger.info("Successfully validated response JSON against ReceiptData model")
            except Exception as validate_error:
                logger.error(f"Failed to validate response JSON: {validate_error}")
                logger.debug(f"Response content: {response.message.content[:200]}...")
                return ReceiptData()  # Return empty model on validation failure
            
            # Check if we need to calculate total_amount
            if receipt_data.total_amount is None and receipt_data.items:
                calculated_total = sum(item.price for item in receipt_data.items)
                receipt_data.total_amount = calculated_total
                logger.info(f"Calculated missing total_amount: {calculated_total}")
            
            # Log extraction results
            logger.info(f"Extracted {len(receipt_data.items)} items from receipt")
            if receipt_data.store:
                logger.info(f"Store identified as: {receipt_data.store}")
            if receipt_data.total_amount:
                logger.info(f"Total amount: {receipt_data.total_amount} {receipt_data.currency or ''}")
            
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error in _process_with_chat: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            # Return an empty ReceiptData object in case of failure
            return ReceiptData()

# Helper functions to use in other modules
async def process_receipt_image(image_path: str) -> Optional[Dict]:
    """
    Process a receipt image and return structured data.
    
    Args:
        image_path: Path to the receipt image
        
    Returns:
        Optional[Dict]: Structured data extracted from the receipt, or None if processing failed
    """
    processor = OllamaImageProcessor()
    receipt_data = await processor.process_image(image_path)
    
    if receipt_data:
        result = receipt_data.model_dump()
        return result
    return None

# CLI for testing
async def cli_main():
    """Command line interface for testing the Ollama image processor."""
    import argparse
    import sys
    import asyncio
    
    parser = argparse.ArgumentParser(description="Process receipt images using Ollama")
    parser.add_argument("image_path", help="Path to the receipt image file")
    parser.add_argument("--model", default="qwen2.5vl:32b", help="Ollama model name to use")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: print to stdout)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Process the image
        if args.model != "qwen2.5vl:32b":
            processor = OllamaImageProcessor(model_name=args.model)
        else:
            processor = OllamaImageProcessor()
            
        print(f"Processing image: {args.image_path}")
        print(f"Using Ollama model: {processor.model_name}")
        print("This may take a minute, processing image...")
        
        receipt_data = await processor.process_image(args.image_path)
        
        if not receipt_data:
            print("ERROR: Failed to process the receipt image", file=sys.stderr)
            sys.exit(1)
        
        # If no items were extracted, warn the user
        if not receipt_data.items:
            print("WARNING: No items were extracted from the receipt", file=sys.stderr)
            
        # Convert to dict for JSON serialization
        result = receipt_data.model_dump()
        
        # Output the result
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {args.output}")
            
            # Print a summary
            print("\nExtracted information summary:")
            if receipt_data.store:
                print(f"Store: {receipt_data.store}")
            if receipt_data.purchase_date:
                print(f"Date: {receipt_data.purchase_date}")
            print(f"Items found: {len(receipt_data.items)}")
            print(f"Total amount: {receipt_data.total_amount} {receipt_data.currency or ''}")
        else:
            print(json.dumps(result, indent=2))
            
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1
            
        # Convert to dict for JSON serialization
        result = receipt_data.model_dump()
        
        # Output the result
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {args.output}")
        else:
            print(json.dumps(result, indent=2))
            
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Run the CLI main function
    import asyncio
    import sys
    exit_code = asyncio.run(cli_main())
    sys.exit(exit_code)
