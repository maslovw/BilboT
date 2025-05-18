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

from PIL import Image, ImageDraw, ImageFont
import ollama

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "qwen2.5vl:7b"  # Default model name for Ollama

# Define data models for structured output
class ReceiptItem(BaseModel):
    item: str = Field(..., description="The name of the purchased item")
    price: float = Field(..., description="The price of the item")
    bbox_2d: Optional[Tuple[int, int, int, int]] = Field(
        None, description="Bounding box coordinates for the item in the image (x1, y1, x2, y2)"
    )

class ReceiptData(BaseModel):
    items: List[ReceiptItem] = Field(default_factory=list, description="List of items and their prices")
    purchase_date: Optional[str] = Field(None, description="Purchase date (format: DD.MM.YYYY)")
    purchase_time: Optional[str] = Field(None, description="Purchase time (format: HH:MM:SS)")
    store: Optional[str] = Field(None, description="Name of the store")
    payment_method: Optional[str] = Field(None, description="Method of payment (cash, card, etc.)")
    total_amount: Optional[float] = Field(None, description="Summary/Total amount paid")
    currency: Optional[str] = Field(None, description="Currency used for the transaction (USD, EUR, etc.)")
    is_valid: Optional[bool] = Field(None, description="Whether the receipt is valid or not")
    total_amount_validated: Optional[bool] = Field(None, description="Whether the total amount matches sum of items")

class OllamaImageProcessor:
    """
    Process receipt images using Ollama and the specified vision model.
    """
    
    def __init__(self, model_name: str = DEFAULT_MODEL, max_context_length: int = 1024*10):
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
    
    def _format_schema_with_descriptions(self, model_class: type) -> str:
        """
        Format the schema of a Pydantic model with field descriptions to provide better context.
        
        Args:
            model_class: The Pydantic model class
            
        Returns:
            str: A formatted string with field descriptions
        """
        schema = model_class.model_json_schema()
        formatted_output = ""
        
        # Format the main model properties
        if "properties" in schema:
            for prop_name, prop_info in schema["properties"].items():
                description = prop_info.get("description", "")
                formatted_output += f"- {prop_name}: {description}\n"
                
                # Handle nested models (like ReceiptItem in items array)
                if prop_name == "items" and "items" in prop_info:
                    if "properties" in prop_info["items"]:
                        formatted_output += "  Each item contains:\n"
                        for item_prop, item_info in prop_info["items"]["properties"].items():
                            item_desc = item_info.get("description", "")
                            formatted_output += f"  - {item_prop}: {item_desc}\n"
        
        return formatted_output
        
        try:
            # Log the Ollama library version being used
            ollama_version = getattr(ollama, "__version__", "unknown")
            logger.info(f"Initialized Ollama image processor with model: {model_name}")
            logger.info(f"Using Ollama Python library version: {ollama_version}")
            logger.debug(f"Max context length: {max_context_length}")
        except Exception as e:
            logger.warning(f"Error getting Ollama version: {e}")
    
    async def process_image(self, image_path: str, draw_boxes: bool = False) -> Optional[ReceiptData]:
        """
        Process a receipt image and extract structured data.
        
        Args:
            image_path: Path to the receipt image
            draw_boxes: Whether to draw bounding boxes on the image and save for debugging
            
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
            
            # Draw bounding boxes if requested and we have valid data
            if draw_boxes:
                try:
                    annotated_path = self.draw_bounding_boxes(receipt_data, image_path)
                    items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
                    logger.info(f"Created annotated image with {items_with_bbox} bounding boxes at: {annotated_path}")
                except Exception as draw_error:
                    logger.error(f"Failed to draw bounding boxes: {draw_error}")
            
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
        """
        try:
            # Set options with context length
            options = {
                "num_ctx": self.max_context_length,
                "temperature": 0  # Set to 0 for more deterministic output
            }
            
            # Save the timestamp for storing responses
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create an async client instance
            client = ollama.AsyncClient(host="http://localhost:11434")
            
            # Call Ollama API with chat method and format parameter
            response = await client.chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                    },
                    {
                        "role": "user",
                        "content": "Analyze this receipt image and export to json, add bbox_2d where required\n"
                                  "Extract the following information:\n" + 
                                  self._format_schema_with_descriptions(ReceiptData),
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
            # Validate total_amount by comparing with calculated total
            elif receipt_data.total_amount is not None and receipt_data.items:
                calculated_total = sum(item.price for item in receipt_data.items)
                total_difference = abs(receipt_data.total_amount - calculated_total)
                # Log the calculated total for comparison
                logger.info(f"Provided total_amount: {receipt_data.total_amount}, Calculated total: {calculated_total}")
                # Check if the totals are significantly different
                if total_difference > 0.01:  # Allow for small rounding differences
                    logger.warning(
                        f"Total amount mismatch: provided={receipt_data.total_amount}, calculated={calculated_total}, "
                        f"difference={total_difference:.2f} {receipt_data.currency or ''}"
                    )
                    # Optionally, we could add a flag to indicate the mismatch
                    receipt_data.total_amount_validated = False
                else:
                    logger.info("Total amount validated successfully")
                    receipt_data.total_amount_validated = True
            
            # Log extraction results
            logger.info(f"Extracted {len(receipt_data.items)} items from receipt")
            items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
            logger.info(f"Items with bounding box data: {items_with_bbox}/{len(receipt_data.items)}")
            
            # Log bbox quality metrics if there are any items with bboxes
            if items_with_bbox > 0:
                quality_metrics = self._evaluate_bbox_quality(receipt_data)
                logger.info(f"Bounding box detection rate: {quality_metrics['detection_rate']:.1f}%")
                logger.info(f"Overlapping boxes detected: {quality_metrics['has_overlapping_boxes']}")
            
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

    def _analyze_missing_bboxes(self, receipt_data: ReceiptData) -> str:
        """
        Analyze why some items might be missing bounding box data and suggest improvements.
        
        Args:
            receipt_data: The receipt data with items
            
        Returns:
            str: A string explaining possible reasons and suggestions
        """
        items_count = len(receipt_data.items)
        items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
        
        # Evaluate bounding box quality
        quality_metrics = self._evaluate_bbox_quality(receipt_data)
        
        # Start with total amount validation info if available
        result = ""
        if receipt_data.total_amount is not None and receipt_data.items:
            calculated_total = sum(item.price for item in receipt_data.items)
            if receipt_data.total_amount_validated is not None:
                if receipt_data.total_amount_validated:
                    result += f"Total amount validation: PASSED\n"
                    result += f"Receipt total ({receipt_data.total_amount:.2f}) matches sum of items ({calculated_total:.2f}).\n\n"
                else:
                    result += f"Total amount validation: FAILED\n"
                    difference = abs(receipt_data.total_amount - calculated_total)
                    result += f"Receipt total ({receipt_data.total_amount:.2f}) differs from sum of items ({calculated_total:.2f}).\n"
                    result += f"Difference: {difference:.2f} {receipt_data.currency or ''}\n"
                    result += "This could indicate missing items or errors in price extraction.\n\n"
        
        # Continue with bounding box analysis
        if items_with_bbox == items_count:
            result += "All items have bounding box data. Great!"
            
            # Add warning if there are overlapping boxes
            if quality_metrics["has_overlapping_boxes"]:
                result += "\nWarning: Some bounding boxes overlap significantly, which may indicate detection issues."
                
            return result
            
        if items_with_bbox == 0:
            return (
                "No bounding boxes were detected. This could be due to:\n"
                "1. The model may not support bounding box detection\n"
                "2. Poor image quality or resolution\n"
                "3. Unusual receipt format or font\n"
                "Try using a higher quality image, a different model, or manually annotating items."
            )
        
        # Some items have bounding boxes, others don't
        percentage = quality_metrics["detection_rate"]
        confidence = quality_metrics["confidence_score"]
        has_overlaps = quality_metrics["has_overlapping_boxes"]
        
        result = ""
        
        if percentage > 70:
            result = (
                f"{items_with_bbox} out of {items_count} items have bounding boxes ({percentage:.1f}%).\n"
                "For the remaining items, the model might have had difficulty identifying their locations.\n"
                "This could be due to unclear text, overlapping items, or unusual formatting."
            )
        else:
            result = (
                f"Only {items_with_bbox} out of {items_count} items have bounding boxes ({percentage:.1f}%).\n"
                "This suggests the model had significant trouble with this receipt. Consider:\n"
                "1. Using a higher resolution image\n"
                "2. Ensuring the receipt is well-lit and not skewed\n"
                "3. Trying a different vision model with better object detection capabilities"
            )
            
        # Add warning about overlapping boxes if applicable
        if has_overlaps:
            result += "\n\nWarning: Some bounding boxes overlap significantly, which may indicate detection issues."
            
        return result

    def draw_bounding_boxes(self, receipt_data: ReceiptData, image_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Draw bounding boxes on the original receipt image for visualization.
        
        Args:
            receipt_data: The extracted ReceiptData containing items with bounding boxes
            image_path: Path to the original receipt image
            output_path: Path where to save the annotated image. If None, a default path will be used.
            
        Returns:
            Path: The path to the saved annotated image
        """
        if not output_path:
            # Create a default output path in the data directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            output_path = data_dir / f"annotated_receipt_{timestamp}.png"
        
        try:
            # Open the original image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            # Try to get a font, use default if not available
            font = None
            try:
                # Try to use a default system font if available
                font_size = 14
                font = ImageFont.truetype("Arial", font_size)
            except IOError:
                logger.debug("Could not load Arial font, using default font")
                font = ImageFont.load_default()
            
            # Draw bounding boxes and item labels for each item with bbox information
            items_with_bbox = 0
            items_without_bbox = 0
            
            # Define a list of distinct colors for boxes
            box_colors = [
                (255, 0, 0),    # Red
                (0, 128, 0),    # Green
                (0, 0, 255),    # Blue
                (255, 165, 0),  # Orange
                (128, 0, 128),  # Purple
                (0, 128, 128),  # Teal
                (255, 0, 255),  # Magenta
                (128, 128, 0),  # Olive
            ]
            
            for i, item in enumerate(receipt_data.items):
                if item.bbox_2d:
                    items_with_bbox += 1
                    # Extract coordinates
                    x1, y1, x2, y2 = item.bbox_2d
                    
                    # Choose a color for this item (cycle through available colors)
                    box_color = box_colors[i % len(box_colors)]
                    
                    # Draw rectangle
                    draw.rectangle([x1, y1, x2, y2], outline=box_color, width=2)
                    
                    # Prepare label text with item number for better reference
                    label_text = f"#{i+1}: {item.item}: {item.price}"
                    
                    # Draw text background
                    text_width = font.getbbox(label_text)[2] if hasattr(font, 'getbbox') else len(label_text) * 7
                    text_height = 20
                    draw.rectangle(
                        [x1, y1 - text_height, x1 + text_width, y1],
                        fill=(255, 255, 255, 180)
                    )
                    
                    # Draw item text
                    text_color = box_color  # Use the same color as the box for consistency
                    draw.text((x1, y1 - text_height), label_text, fill=text_color, font=font)
                    
                    logger.debug(f"Drew bounding box for item #{i+1}: {item.item}")
                else:
                    items_without_bbox += 1
                    logger.debug(f"No bounding box available for item #{i+1}: {item.item}")
            
            # Log statistics
            logger.info(f"Drew {items_with_bbox} bounding boxes. {items_without_bbox} items had no bbox data.")
            
            # Draw total amount if available
            y_pos = 10
            if receipt_data.total_amount:
                total_text = f"Total: {receipt_data.total_amount} {receipt_data.currency or ''}"
                draw.text((10, y_pos), total_text, fill=(0, 0, 255), font=font)
                y_pos += 20
                
                # Draw validation status if available
                if receipt_data.total_amount_validated is not None:
                    calculated_total = sum(item.price for item in receipt_data.items)
                    if receipt_data.total_amount_validated:
                        validation_text = f"✓ Total validated (matches {calculated_total:.2f})"
                        validation_color = (0, 128, 0)  # Green
                    else:
                        validation_text = f"⚠ Total mismatch! Calculated: {calculated_total:.2f}"
                        validation_color = (255, 0, 0)  # Red
                    draw.text((10, y_pos), validation_text, fill=validation_color, font=font)
                    y_pos += 20
            
            # Draw store name if available
            if receipt_data.store:
                store_text = f"Store: {receipt_data.store}"
                draw.text((10, y_pos), store_text, fill=(0, 0, 255), font=font)
                y_pos += 20
            
            # Draw date if available
            if receipt_data.purchase_date:
                date_text = f"Date: {receipt_data.purchase_date}"
                draw.text((10, y_pos), date_text, fill=(0, 0, 255), font=font)
                y_pos += 20
            
            # List items without bounding boxes at the top of the image
            items_without_bbox = [(i, item) for i, item in enumerate(receipt_data.items) if not item.bbox_2d]
            if items_without_bbox:
                draw.text((10, y_pos), "Items without bounding boxes:", fill=(255, 0, 0), font=font)
                y_pos += 20
                
                for idx, (i, item) in enumerate(items_without_bbox):
                    # Choose a color for this item (cycle through available colors)
                    text_color = box_colors[(len(receipt_data.items) + idx) % len(box_colors)]
                    
                    item_text = f"#{i+1}: {item.item}: {item.price}"
                    draw.text((20, y_pos), item_text, fill=text_color, font=font)
                    y_pos += 20
                    if y_pos > image.height - 50:  # Avoid drawing off the bottom of the image
                        draw.text((20, y_pos), "... and more", fill=(0, 0, 0), font=font)
                        break
            
            # Add diagnostic information at the bottom of the image
            diagnostic_text = self._analyze_missing_bboxes(receipt_data)
            
            # Draw a semi-transparent background for the diagnostic text
            text_lines = diagnostic_text.split('\n')
            text_height = len(text_lines) * 20 + 10
            text_width = max(len(line) * 7 for line in text_lines)
            
            # Position at the bottom of the image
            text_y = max(10, image.height - text_height - 10)
            
            # Draw background box
            draw.rectangle(
                [10, text_y, 10 + text_width, text_y + text_height],
                fill=(0, 0, 0, 128)
            )
            
            # Draw diagnostic text
            current_y = text_y + 5
            for line in text_lines:
                draw.text((15, current_y), line, fill=(255, 255, 255), font=font)
                current_y += 20
            
            # Save the annotated image
            image.save(output_path)
            logger.info(f"Saved annotated receipt image to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error drawing bounding boxes: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            
            # Return the original path if we couldn't draw boxes
            return image_path

    def _evaluate_bbox_quality(self, receipt_data: ReceiptData) -> Dict[str, float]:
        """
        Evaluate the quality of bounding box detection.
        
        Args:
            receipt_data: The receipt data with items
            
        Returns:
            Dict[str, float]: Metrics for bbox detection quality
        """
        total_items = len(receipt_data.items)
        if total_items == 0:
            return {
                "detection_rate": 0.0,
                "confidence_score": 0.0,
                "has_overlapping_boxes": False
            }
            
        # Count items with bounding boxes
        items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
        detection_rate = (items_with_bbox / total_items) * 100
        
        # Calculate a confidence score (simplified)
        confidence_score = detection_rate / 100
        
        # Check for overlapping boxes (which might indicate detection issues)
        has_overlapping_boxes = False
        
        # Get all items with bounding boxes
        bbox_items = [item for item in receipt_data.items if item.bbox_2d]
        
        # Check for overlapping boxes
        for i, item1 in enumerate(bbox_items):
            for j, item2 in enumerate(bbox_items):
                if i >= j:  # Skip self and already checked pairs
                    continue
                    
                # Get bounding boxes
                box1 = item1.bbox_2d
                box2 = item2.bbox_2d
                
                # Check if boxes overlap significantly (simple check)
                if (box1 and box2 and
                    box1[0] < box2[2] and box1[2] > box2[0] and
                    box1[1] < box2[3] and box2[3] > box2[1]):
                    
                    # Calculate overlap area
                    overlap_width = min(box1[2], box2[2]) - max(box1[0], box2[0])
                    overlap_height = min(box1[3], box2[3]) - max(box1[1], box2[1])
                    overlap_area = overlap_width * overlap_height
                    
                    # Calculate box areas
                    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
                    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
                    
                    # If overlap is more than 30% of either box, consider it significant
                    if (overlap_area > 0.3 * box1_area or overlap_area > 0.3 * box2_area):
                        has_overlapping_boxes = True
                        logger.debug(f"Found overlapping boxes: {item1.item} and {item2.item}")
                        break
            
            if has_overlapping_boxes:
                break
        
        return {
            "detection_rate": detection_rate,
            "confidence_score": confidence_score,
            "has_overlapping_boxes": has_overlapping_boxes
        }

# Helper functions to use in other modules
async def process_receipt_image(image_path: str, draw_boxes: bool = False, model_name: str = DEFAULT_MODEL) -> Optional[Dict]:
    """
    Process a receipt image and return structured data.
    
    Args:
        image_path: Path to the receipt image
        draw_boxes: Whether to draw bounding boxes on the image and save for debugging
        model_name: The name of the Ollama model to use
        
    Returns:
        Optional[Dict]: Structured data extracted from the receipt, or None if processing failed
    """
    processor = OllamaImageProcessor(model_name=model_name)
    logger.info(f"Processing image: {image_path}")
    logger.info(f"Using Ollama model: {processor.model_name}")
    receipt_data = await processor.process_image(image_path, draw_boxes=draw_boxes)
    
    if receipt_data:
        result = receipt_data.model_dump()
        
        # Add additional validation info if not already included
        if receipt_data.items and 'total_amount' in result and result['total_amount'] is not None:
            # Check if total_amount_validated is already set
            if 'total_amount_validated' not in result or result['total_amount_validated'] is None:
                calculated_total = sum(item.price for item in receipt_data.items)
                total_difference = abs(receipt_data.total_amount - calculated_total)
                
                # Add validation status
                result['total_amount_validated'] = (total_difference <= 0.01)  # Allow for small rounding differences
                
                # Add calculated total for comparison
                result['calculated_total'] = calculated_total
                result['total_difference'] = total_difference
                
                # Log the validation results
                if result['total_amount_validated']:
                    logger.info(f"Total amount validated successfully: {receipt_data.total_amount} matches {calculated_total:.2f}")
                else:
                    logger.warning(
                        f"Total amount mismatch: provided={receipt_data.total_amount}, calculated={calculated_total:.2f}, "
                        f"difference={total_difference:.2f} {receipt_data.currency or ''}"
                    )
                
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
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model name to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: print to stdout)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--draw", action="store_true", help="Draw bounding boxes on the image and save for debugging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Process the image
        processor = OllamaImageProcessor(model_name=args.model)
            
        print(f"Processing image: {args.image_path}")
        print(f"Using Ollama model: {processor.model_name}")
        print("This may take a minute, processing image...")
        
        receipt_data = await processor.process_image(args.image_path, draw_boxes=args.draw)
        
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
            
            # Count items with bounding boxes
            items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
            print(f"Items found: {len(receipt_data.items)}")
            print(f"Items with bounding boxes: {items_with_bbox}/{len(receipt_data.items)}")
            print(f"Total amount: {receipt_data.total_amount} {receipt_data.currency or ''}")
            
            # Show total amount validation status if available
            if receipt_data.total_amount_validated is not None:
                if receipt_data.total_amount_validated:
                    print("✅ Total amount matches sum of items")
                else:
                    # Calculate the total to display it
                    calculated_total = sum(item.price for item in receipt_data.items)
                    print(f"⚠️ Total amount mismatch: {receipt_data.total_amount} (stated) vs {calculated_total:.2f} (calculated)")
            elif receipt_data.items:
                calculated_total = sum(item.price for item in receipt_data.items)
                print(f"Total from items: {calculated_total:.2f} {receipt_data.currency or ''}")
            
            # Mention the annotated image if it was created
            if args.draw:
                items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
                if items_with_bbox > 0:
                    print(f"\nAn annotated image with {items_with_bbox} bounding boxes was saved in the 'data' directory.")
                    if items_with_bbox < len(receipt_data.items):
                        print(f"Note: {len(receipt_data.items) - items_with_bbox} items did not have bounding box coordinates.")
                else:
                    print("\nNo bounding boxes were detected for any items. The annotated image was still saved but may not be useful.")
                    print("Try using a different model or improving the image quality for better detection.")
        else:
            print(json.dumps(result, indent=2))
            
            # Show total amount validation status if available
            if receipt_data.total_amount is not None and receipt_data.items:
                calculated_total = sum(item.price for item in receipt_data.items)
                if receipt_data.total_amount_validated is not None:
                    if receipt_data.total_amount_validated:
                        print(f"\n✅ Total amount matches sum of items")
                    else:
                        print(f"\n⚠️ Total amount mismatch: {receipt_data.total_amount} (stated) vs {calculated_total:.2f} (calculated)")
                else:
                    print(f"\nTotal from items: {calculated_total:.2f} {receipt_data.currency or ''}")
            
            # Mention the annotated image if it was created
            if args.draw:
                items_with_bbox = sum(1 for item in receipt_data.items if item.bbox_2d)
                if items_with_bbox > 0:
                    print(f"\nAn annotated image with {items_with_bbox} bounding boxes was saved in the 'data' directory.")
                    if items_with_bbox < len(receipt_data.items):
                        print(f"Note: {len(receipt_data.items) - items_with_bbox} items did not have bounding box coordinates.")
                else:
                    print("\nNo bounding boxes were detected for any items. The annotated image was still saved but may not be useful.")
                    print("Try using a different model or improving the image quality for better detection.")
            
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
