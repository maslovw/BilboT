"""
Ollama image processing module for extracting structured data from receipt images.
"""

import base64
import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime
import aiohttp
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
            "2. Purchase date and time\n"
            "3. Store name\n"
            "4. Payment method used\n\n"
            "Return only the extracted information in a structured JSON format."
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
        # Encode image to base64
        base64_image = base64.b64encode(img_bytes).decode('utf-8')
        
        try:
            # Construct request
            request_data = {
                "model": self.model_name,
                "prompt": self.prompt_template,
                "images": [base64_image],
                "options": {
                    "num_ctx": self.max_context_length
                }
            }
            
            # Call Ollama API (using separate function to allow for local/remote configuration)
            async with aiohttp.ClientSession() as session:
                async with session.post('http://localhost:11434/api/generate', json=request_data) as resp:
                    if resp.status != 200:
                        logger.error(f"Ollama API error: {resp.status}")
                        return ""
                    
                    # Stream and collect the response
                    full_response = ""
                    async for line in resp.content:
                        data = json.loads(line)
                        if "response" in data:
                            full_response += data["response"]
                        if data.get("done", False):
                            break
                    
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
            # Try to extract JSON data from the response
            # Look for JSON-like patterns or try to parse the whole response
            json_str = self._extract_json_from_text(response)
            
            if json_str:
                data = json.loads(json_str)
                
                # Extract items and prices
                if "items" in data:
                    for item_data in data["items"]:
                        if isinstance(item_data, dict) and "item" in item_data and "price" in item_data:
                            # Already in the right format
                            price = self._parse_price(item_data["price"])
                            receipt_data.items.append(ReceiptItem(item=item_data["item"], price=price))
                        elif isinstance(item_data, str):
                            # Format might be "item: price"
                            item, price = self._parse_item_string(item_data)
                            if item and price is not None:
                                receipt_data.items.append(ReceiptItem(item=item, price=price))
                
                # Extract other fields
                receipt_data.purchase_date = data.get("purchase_date") or data.get("date")
                receipt_data.purchase_time = data.get("purchase_time") or data.get("time")
                receipt_data.store = data.get("store") or data.get("store_name") or data.get("merchant")
                receipt_data.payment_method = data.get("payment_method") or data.get("payment")
                receipt_data.total_amount = self._parse_price(data.get("total_amount") or data.get("total"))
            
            # If JSON parsing failed, try to extract information from text
            if not receipt_data.items and not receipt_data.store:
                self._extract_data_from_text(response, receipt_data)
            
            return receipt_data
            
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {e}")
            logger.debug(f"Response was: {response}")
            return receipt_data
    
    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON from text which might contain additional content.
        
        Args:
            text: The text to extract JSON from
            
        Returns:
            str: The extracted JSON string, or empty string if no JSON found
        """
        # Try to find JSON markers
        try:
            # First, try to see if the whole response is valid JSON
            json.loads(text)
            return text
        except:
            pass
        
        # Try to extract JSON objects
        try:
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_candidate = text[start_idx:end_idx+1]
                # Validate it's proper JSON
                json.loads(json_candidate)
                return json_candidate
        except:
            pass
        
        # Try to extract JSON arrays
        try:
            start_idx = text.find('[')
            end_idx = text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_candidate = text[start_idx:end_idx+1]
                # Validate it's proper JSON
                json.loads(json_candidate)
                return json_candidate
        except:
            pass
        
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
            elif any(keyword in lower_line for keyword in ["store:", "merchant:", "vendor:"]):
                receipt_data.store = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["payment:", "payment method:", "paid with:", "paid by:"]):
                receipt_data.payment_method = self._extract_value(line)
            elif any(keyword in lower_line for keyword in ["total:", "total amount:", "amount:", "sum:"]):
                value = self._extract_value(line)
                receipt_data.total_amount = self._parse_price(value) if value else None
    
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
        return receipt_data.dict()
    return None
