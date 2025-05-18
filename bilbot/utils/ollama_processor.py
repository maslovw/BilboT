"""
Ollama image processing module for extracting structured data from receipt images.
"""

import base64
import json
import logging
import os
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
    Process receipt images using Ollama and the Qwen2.5vl:32b model.
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
        self.prompt_template = (
            "Please analyze this receipt image and extract the following information in a structured format:\n"
            "1. List all items and their prices in the format [item: price]\n"
            "2. Purchase date (format: DD.MM.YYYY)\n"
            "3. Purchase time (format: HH:MM:SS)\n"
            "4. Store name\n"
            "5. Payment method used\n"
            "6. Currency used (USD, EUR, etc.)\n"
            "7. Total amount paid\n\n"
            "Return only the extracted information in a structured JSON format with fields: items, purchase_date, purchase_time, store_name, payment_method, currency, total_amount."
        )
        logger.info(f"Initialized Ollama image processor with model: {model_name}")
    
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
                
            # Load and encode the image
            with Image.open(image_path) as img:
                # Resize image if needed to fit context length
                img_bytes = self._prepare_image(img)
            
            # Process with Ollama
            response = await self._call_ollama_api(img_bytes)

            
            # Parse the response
            receipt_data = self._parse_response(response)
            
            logger.info(f"Successfully processed receipt image: {image_path}")
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error processing receipt image: {e}")
            return None
    
    def _prepare_image(self, img: Image.Image) -> bytes:
        """
        Prepare the image for processing by resizing if necessary.
        
        Args:
            img: PIL Image object
            
        Returns:
            bytes: Image byte data
        """
        # Calculate if image needs resizing based on estimated context length
        max_size = 1200  # Max dimension to keep context length manageable
        
        # Resize if needed
        if img.width > max_size or img.height > max_size:
            ratio = min(max_size / img.width, max_size / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            
        # Save to bytes
        import io
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        return img_byte_arr.getvalue()
    
    async def _call_ollama_api(self, img_bytes: bytes) -> str:
        """
        Call the Ollama API to process the image.
        
        Args:
            img_bytes: Image byte data
            
        Returns:
            str: Response from the Ollama API
        """
        try:
            # Initialize async Ollama client
            client = ollama.AsyncClient(host="http://localhost:11434")
            
            # Set options with context length
            options = {
                "num_ctx": self.max_context_length
            }
            
            # Call Ollama API with streaming to collect the response
            full_response = ""
            raw_response = []
            
            # Stream the response
            async for chunk in await client.generate(
                model=self.model_name,
                prompt=self.prompt_template,
                images=[img_bytes],  # Pass bytes directly, ollama library handles encoding
                stream=False,
                options=options
            ):
                # Collect raw response for debugging
                raw_response.append(chunk.model_dump())
                
                # Accumulate the response text
                if hasattr(chunk, "response"):
                    full_response += chunk.response
                
            # Save both raw and processed responses for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save raw response
            response_file_path = f"data/response_{timestamp}_raw.json"
            with open(response_file_path, 'w') as f:
                f.write(json.dumps(raw_response, indent=2))
            
            # Save processed response
            processed_file_path = f"data/response_{timestamp}_processed.txt"
            with open(processed_file_path, 'w') as f:
                f.write(full_response)
            
            # Log the full processed response for debugging
            logger.debug(f"Full processed response: {full_response[:200]}...")
            
            return full_response
            
        except Exception as e:
            logger.error(f"Error calling Ollama API: {e}")
            return ""
    
    def _parse_response(self, response: str) -> ReceiptData:
        """
        Parse the Ollama API response into structured data.
        
        Args:
            response: Text response from Ollama
            
        Returns:
            ReceiptData: Structured receipt data
        """
        receipt_data = ReceiptData()
        
        try:
            # Log the start of parsing
            logger.debug(f"Starting to parse response: {response[:100]}...")
            
            # Try to extract JSON data from the response
            # Look for JSON-like patterns or try to parse the whole response
            json_str = self._extract_json_from_text(response)
            
            if json_str:
                logger.info(f"Successfully extracted JSON from response (length: {len(json_str)})")
                data = json.loads(json_str)
                
                # Extract items and prices
                if "items" in data:
                    for item_data in data["items"]:
                        if isinstance(item_data, dict) and "item" in item_data and "price" in item_data:
                            # Already in the right format
                            price = self._parse_price(item_data["price"])
                            receipt_data.items.append(ReceiptItem(item=item_data["item"], price=price))
                            logger.debug(f"Added item: {item_data['item']} (${price})")
                        elif isinstance(item_data, str):
                            # Format might be "item: price"
                            item, price = self._parse_item_string(item_data)
                            if item and price is not None:
                                receipt_data.items.append(ReceiptItem(item=item, price=price))
                                logger.debug(f"Added parsed item: {item} (${price})")
                
                # Extract other fields
                receipt_data.purchase_date = data.get("purchase_date") or data.get("date")
                receipt_data.purchase_time = data.get("purchase_time") or data.get("time")
                
                # Handle combined purchase_date_time field (e.g., "28.04.2025 12:01:24 Uhr")
                if (not receipt_data.purchase_date or not receipt_data.purchase_time) and "purchase_date_time" in data:
                    date_time_str = data.get("purchase_date_time")
                    logger.debug(f"Found purchase_date_time: {date_time_str}")
                    if date_time_str:
                        # Try to split date and time
                        parts = date_time_str.split()
                        if len(parts) >= 2:
                            # First part is likely the date
                            if not receipt_data.purchase_date:
                                receipt_data.purchase_date = parts[0]
                                logger.debug(f"Extracted date from purchase_date_time: {receipt_data.purchase_date}")
                            # Second part is likely the time
                            if not receipt_data.purchase_time:
                                receipt_data.purchase_time = parts[1]
                                logger.debug(f"Extracted time from purchase_date_time: {receipt_data.purchase_time}")
                
                receipt_data.store = data.get("store") or data.get("store_name") or data.get("merchant")
                receipt_data.payment_method = data.get("payment_method") or data.get("payment")
                receipt_data.total_amount = self._parse_price(data.get("total_amount") or data.get("total") or data.get("total_amount_paid"))
                
                # Extract currency
                receipt_data.currency = data.get("currency") or self._extract_currency_from_text(response)
                
                # Log extracted fields
                logger.debug(f"Extracted fields: store={receipt_data.store}, date={receipt_data.purchase_date}, total={receipt_data.total_amount}, currency={receipt_data.currency}")
            else:
                logger.warning("Failed to extract JSON from response")
            
            # If JSON parsing failed, try to extract information from text
            if not receipt_data.items and not receipt_data.store:
                logger.info("JSON parsing did not yield results, trying text extraction")
                self._extract_data_from_text(response, receipt_data)
            
            # If currency is still not identified but we have price strings, try to extract from them
            if not receipt_data.currency and (receipt_data.items or receipt_data.total_amount):
                receipt_data.currency = self._extract_currency_from_text(response)
                
            # If total amount is still missing but we have items, calculate it
            if receipt_data.total_amount is None and receipt_data.items:
                receipt_data.total_amount = sum(item.price for item in receipt_data.items)
                logger.debug(f"Calculated total amount: {receipt_data.total_amount}")
            
            # Final check - log success or failure
            if receipt_data.items:
                logger.info(f"Successfully parsed receipt with {len(receipt_data.items)} items")
            else:
                logger.warning("No items were extracted from the receipt")
                
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {e}")
            logger.error(f"Response was: {response[:500]}...")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return receipt_data
    
    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON from text which might contain additional content.
        
        Args:
            text: The text to extract JSON from
            
        Returns:
            str: The extracted JSON string, or empty string if no JSON found
        """
        # Remove markdown code block delimiters if present
        cleaned_text = text
        # Check for markdown code blocks (```json...```)
        if cleaned_text.startswith('```'):
            # Find the first newline after the opening backticks
            first_newline = cleaned_text.find('\n', 3)
            if first_newline != -1:
                # Find the closing backticks
                closing_ticks = cleaned_text.rfind('```')
                if closing_ticks > first_newline:
                    # Extract the content between the backticks
                    cleaned_text = cleaned_text[first_newline+1:closing_ticks].strip()
                    logger.debug(f"Extracted JSON from markdown code block: {cleaned_text[:100]}...")
        
        # Try to find JSON markers
        try:
            # First, try to see if the whole response is valid JSON
            json.loads(cleaned_text)
            return cleaned_text
        except:
            logger.debug("Failed to parse entire text as JSON, attempting to extract JSON object")
        
        # Try to extract JSON objects
        try:
            start_idx = cleaned_text.find('{')
            end_idx = cleaned_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_candidate = cleaned_text[start_idx:end_idx+1]
                # Validate it's proper JSON
                json.loads(json_candidate)
                logger.debug(f"Successfully extracted JSON object: {json_candidate[:50]}...")
                return json_candidate
        except Exception as e:
            logger.debug(f"Failed to extract JSON object: {e}")
        
        # Try to extract JSON arrays
        try:
            start_idx = cleaned_text.find('[')
            end_idx = cleaned_text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_candidate = cleaned_text[start_idx:end_idx+1]
                # Validate it's proper JSON
                json.loads(json_candidate)
                logger.debug(f"Successfully extracted JSON array: {json_candidate[:50]}...")
                return json_candidate
        except Exception as e:
            logger.debug(f"Failed to extract JSON array: {e}")
        
        logger.warning(f"Could not extract JSON from response: {cleaned_text[:100]}...")
        return ""
    
    def _extract_data_from_text(self, text: str, receipt_data: ReceiptData) -> None:
        """
        Extract structured data from unstructured text response.
        
        Args:
            text: Response text from Ollama
            receipt_data: ReceiptData object to populate
        """
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Look for item: price patterns
            if ': ' in line or ' - ' in line:
                item, price = self._parse_item_string(line)
                if item and price is not None:
                    receipt_data.items.append(ReceiptItem(item=item, price=price))
                    continue
            
            # Look for other data
            lower_line = line.lower()
            if any(keyword in lower_line for keyword in ["date:", "date of purchase:", "purchased on:"]):
                receipt_data.purchase_date = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["time:", "time of purchase:"]):
                receipt_data.purchase_time = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["date and time:", "date time:", "datetime:", "purchase_date_time:"]):
                # Handle combined date/time format
                value = self._extract_value(line)
                if value:
                    parts = value.split()
                    if len(parts) >= 2:
                        receipt_data.purchase_date = parts[0]
                        receipt_data.purchase_time = parts[1]
                        logger.debug(f"Split date/time: {receipt_data.purchase_date} / {receipt_data.purchase_time}")
            elif any(keyword in lower_line for keyword in ["store:", "merchant:", "vendor:"]):
                receipt_data.store = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["payment:", "payment method:", "paid with:", "paid by:"]):
                receipt_data.payment_method = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["total:", "total amount:", "amount:", "sum:", "total paid:"]):
                value = self._extract_value(line)
                receipt_data.total_amount = self._parse_price(value) if value else None
            elif any(keyword in lower_line for keyword in ["currency:", "currency used:", "currency type:"]):
                receipt_data.currency = self._extract_value(line)
                
        # If currency is still not detected, try to extract it from the text
        if receipt_data.currency is None:
            receipt_data.currency = self._extract_currency_from_text(text)
    
    def _parse_item_string(self, text: str) -> Tuple[str, Optional[float]]:
        """
        Parse an item string in the format "item: price" or "item - price".
        
        Args:
            text: The text string to parse
            
        Returns:
            Tuple[str, Optional[float]]: The item name and price, or (item, None) if parsing failed
        """
        separator = ': ' if ': ' in text else ' - '
        parts = text.split(separator, 1)
        
        if len(parts) == 2:
            item = parts[0].strip()
            price_str = parts[1].strip()
            
            # Check for currency in the price string
            currency = self._extract_currency_from_text(price_str)
            if currency and not hasattr(self, '_detected_currency'):
                setattr(self, '_detected_currency', currency)
                
            price = self._parse_price(price_str)
            return item, price
        
        return text, None
    
    def _parse_price(self, price_str: Optional[Union[str, float, int]]) -> Optional[float]:
        """
        Parse a price string into a float.
        
        Args:
            price_str: The price string to parse
            
        Returns:
            Optional[float]: The parsed price, or None if parsing failed
        """
        if price_str is None:
            return None
            
        if isinstance(price_str, (float, int)):
            return float(price_str)
            
        try:
            # Store the original string for currency detection later
            original_price = price_str
            
            # Remove currency symbols and other non-digit characters except dots and commas
            digits_only = ''.join(c for c in price_str if c.isdigit() or c in '.,')
            
            # Replace comma with dot for decimal
            clean_str = digits_only.replace(',', '.')
            
            # Handle multiple dots (take last as decimal point)
            if clean_str.count('.') > 1:
                parts = clean_str.split('.')
                clean_str = ''.join(parts[:-1]) + '.' + parts[-1]
                
            return float(clean_str)
        except:
            return None
            
    def _extract_currency_from_text(self, text: str) -> Optional[str]:
        """
        Extract currency information from text.
        
        Args:
            text: The text to extract currency from
            
        Returns:
            Optional[str]: The identified currency code or symbol, or None if not found
        """
        # Common currency symbols and codes
        currency_patterns = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₹': 'INR',
            '₽': 'RUB',
            '₩': 'KRW',
            '₿': 'BTC',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP',
            'JPY': 'JPY',
            'INR': 'INR',
            'RUB': 'RUB',
            'KRW': 'KRW',
            'AUD': 'AUD',
            'CAD': 'CAD',
            'CHF': 'CHF',
            'CNY': 'CNY',
            'HKD': 'HKD',
            'NZD': 'NZD',
            'SEK': 'SEK',
            'SGD': 'SGD',
            'THB': 'THB',
            'ZAR': 'ZAR',
        }
        
        # Check for explicit currency mentions
        lower_text = text.lower()
        
        # Look for "currency: XYZ" patterns
        for term in ["currency", "currency used", "paid in", "in", "currency is"]:
            if term in lower_text:
                idx = lower_text.find(term)
                if idx != -1:
                    # Get text after the term
                    after_term = text[idx + len(term):].strip()
                    if after_term.startswith(':') or after_term.startswith('-') or after_term.startswith('='):
                        after_term = after_term[1:].strip()
                    
                    # Take first word as potential currency
                    potential_currency = after_term.split()[0] if after_term.split() else ""
                    
                    # Check if it's a recognized currency code
                    potential_currency = potential_currency.upper()
                    if potential_currency in currency_patterns:
                        return potential_currency
        
        # Look for currency symbols in the text
        for symbol, code in currency_patterns.items():
            if symbol in text:
                return code
                
        # Look for price patterns like $10.99
        price_patterns = [
            r'\$\d+',           # $10
            r'€\d+',           # €10
            r'£\d+',           # £10
            r'\d+\s*USD',      # 10 USD
            r'\d+\s*EUR',      # 10 EUR
            r'\d+\s*GBP',      # 10 GBP
        ]
        
        for pattern in price_patterns:
            if any(p in text for p in pattern if not p.isalnum()):
                for char in pattern:
                    if not char.isalnum() and char in currency_patterns:
                        return currency_patterns[char]
        
        return None
    
    def _extract_value(self, text: str) -> Optional[str]:
        """
        Extract a value from a line of text after a colon or similar separator.
        
        Args:
            text: The text string to extract from
            
        Returns:
            Optional[str]: The extracted value, or None if extraction failed
        """
        for separator in [':', '-', '=']:
            if separator in text:
                parts = text.split(separator, 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None

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
        # Ensure total amount and currency are included in the result
        if receipt_data.total_amount is None and receipt_data.items:
            result['total_amount'] = sum(item.price for item in receipt_data.items)
            
        if not receipt_data.currency and hasattr(processor, '_detected_currency'):
            result['currency'] = getattr(processor, '_detected_currency')
            
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
        
        receipt_data = await processor.process_image(args.image_path)
        
        if not receipt_data:
            print("ERROR: Failed to process the receipt image", file=sys.stderr)
            sys.exit(1)
            
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
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Run the CLI main function
    import asyncio
    exit_code = asyncio.run(cli_main())
    import sys
    sys.exit(exit_code)
