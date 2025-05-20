#!/usr/bin/env python3
# filepath: /Users/viacheslav.maslov/EDF/tools/BilboT/bilbot/utils/ollama_corners_processor.py
"""
Ollama document corner detection and deskewing module.
Uses Ollama vision models to detect document corners and then crop and deskew based on those points.
"""

import io
import json
import logging
import os
import sys
import asyncio
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import ollama

logger = logging.getLogger(__name__)
DEFAULT_CORNER_MODEL = "qwen2.5vl:3b"  # Default smaller model for just corner detection

# Define data models for structured output
class Point(BaseModel):
    x: int = Field(..., description="X coordinate of the point")
    y: int = Field(..., description="Y coordinate of the point")

class DocumentCorners(BaseModel):
    top_left: Point = Field(..., description="Top left corner point of the document")
    top_right: Point = Field(..., description="Top right corner point of the document")
    bottom_right: Point = Field(..., description="Bottom right corner point of the document")
    bottom_left: Point = Field(..., description="Bottom left corner point of the document")
    
    @model_validator(mode='after')
    def validate_corners(self) -> 'DocumentCorners':
        """Validate that the corners form a proper quadrilateral."""
        # Check if points are too close to each other
        points = [
            (self.top_left.x, self.top_left.y),
            (self.top_right.x, self.top_right.y),
            (self.bottom_right.x, self.bottom_right.y),
            (self.bottom_left.x, self.bottom_left.y)
        ]
        
        # Check for duplicates or points that are too close
        for i in range(4):
            for j in range(i+1, 4):
                dx = points[i][0] - points[j][0]
                dy = points[i][1] - points[j][1]
                distance = (dx**2 + dy**2)**0.5
                
                if distance < 10:  # Arbitrary threshold for "too close"
                    logger.warning(f"Corner points {i} and {j} are very close: {distance:.1f} pixels apart")
        
        return self
    
    def as_np_array(self) -> np.ndarray:
        """Convert corners to numpy array format for OpenCV operations."""
        return np.array([
            [self.top_left.x, self.top_left.y],
            [self.top_right.x, self.top_right.y],
            [self.bottom_right.x, self.bottom_right.y],
            [self.bottom_left.x, self.bottom_left.y]
        ], dtype=np.float32)


class OllamaCornersProcessor:
    """
    Process images using Ollama to detect document corners for cropping and deskewing.
    """
    
    def __init__(self, model_name: str = DEFAULT_CORNER_MODEL, max_context_length: int = 4096):
        """
        Initialize the Ollama document corner detector.
        
        Args:
            model_name: The name of the Ollama model to use
            max_context_length: Maximum context length for the model
        """
        self.model_name = model_name
        self.max_context_length = max_context_length
        self.system_prompt = (
            #"You are a document corner detector. Find the four corners of the main document in the image."
        )
        
        try:
            # Log the Ollama library version being used
            ollama_version = getattr(ollama, "__version__", "unknown")
            logger.info(f"Initialized Ollama corners processor with model: {model_name}")
            logger.info(f"Using Ollama Python library version: {ollama_version}")
            logger.debug(f"Max context length: {max_context_length}")
        except Exception as e:
            logger.warning(f"Error getting Ollama version: {e}")
    
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
                
                # Handle nested models (like Points in corners)
                if "properties" in prop_info:
                    formatted_output += f"  Each {prop_name} contains:\n"
                    for nested_prop, nested_info in prop_info["properties"].items():
                        nested_desc = nested_info.get("description", "")
                        formatted_output += f"  - {nested_prop}: {nested_desc}\n"
        
        return formatted_output
    
    async def detect_corners(self, image_path: str, visualize: bool = False) -> Optional[DocumentCorners]:
        """
        Detect the corners of a document in an image.
        
        Args:
            image_path: Path to the image containing a document
            visualize: Whether to create a visualization of detected corners
            
        Returns:
            DocumentCorners: The detected corner points, or None if detection failed
        """
        try:
            # Check if image exists
            if not os.path.exists(image_path):
                logger.error(f"Image not found at path: {image_path}")
                return None
                
            # Load and prepare the image
            image_path = Path(image_path)
            
            # Process with Ollama chat API
            corners = await self._process_with_chat(image_path)
            
            if corners and visualize:
                self.visualize_corners(image_path, corners)
            
            if corners:
                logger.info(f"Successfully detected document corners in image: {image_path}")
                return corners
            else:
                logger.error(f"Failed to detect document corners in image: {image_path}")
                return None
            
        except Exception as e:
            logger.error(f"Error detecting document corners: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            return None
    
    async def _process_with_chat(self, image_path: Path) -> Optional[DocumentCorners]:
        """
        Process an image using the ollama.chat API with format parameter to detect document corners.
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
                        "content": (
                            "Find the four corners of the document visible in this image.\n\n"
                            "The corners should be provided in this order: top-left, top-right, bottom-right, bottom-left.\n\n"
                            "Please identify the coordinates as precisely as possible and export to JSON with this structure:\n" + 
                            self._format_schema_with_descriptions(DocumentCorners)
                        ),
                        "images": [image_path]
                    }
                ],
                format=DocumentCorners.model_json_schema(),  # Pass schema for structured output
                options=options
            )
            
            # Save raw response for debugging
            data_dir = "data"
            os.makedirs(data_dir, exist_ok=True)
            raw_response_path = os.path.join(data_dir, f"corners_response_{timestamp}_raw.json")
            with open(raw_response_path, 'w') as f:
                f.write(json.dumps(response.model_dump(), indent=2))
            
            # Save the processed message content
            processed_response_path = os.path.join(data_dir, f"corners_response_{timestamp}_processed.txt")
            with open(processed_response_path, 'w') as f:
                f.write(response.message.content)
            
            logger.debug(f"Saved raw response to {raw_response_path}")
            logger.debug(f"Saved processed response to {processed_response_path}")
            
            # Parse the response as a DocumentCorners object
            try:
                corners = DocumentCorners.model_validate_json(response.message.content)
                logger.info("Successfully validated corners JSON against DocumentCorners model")
                
                # Log the detected corner coordinates
                logger.info(f"Top-left: ({corners.top_left.x}, {corners.top_left.y})")
                logger.info(f"Top-right: ({corners.top_right.x}, {corners.top_right.y})")
                logger.info(f"Bottom-right: ({corners.bottom_right.x}, {corners.bottom_right.y})")
                logger.info(f"Bottom-left: ({corners.bottom_left.x}, {corners.bottom_left.y})")
                
                return corners
            except Exception as validate_error:
                logger.error(f"Failed to validate corners JSON: {validate_error}")
                logger.debug(f"Response content: {response.message.content[:200]}...")
                return None
            
        except Exception as e:
            logger.error(f"Error in _process_with_chat: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            return None
    
    def visualize_corners(self, image_path: Path, corners: DocumentCorners) -> Path:
        """
        Create a visualization of the detected corners.
        
        Args:
            image_path: Path to the original image
            corners: The detected document corners
            
        Returns:
            Path: Path to the saved visualization image
        """
        # Create a default output path in the data directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        output_path = data_dir / f"corners_visualization_{timestamp}.png"
        
        try:
            # Open the original image
            image = Image.open(image_path)
            draw = ImageDraw.Draw(image)
            
            # Get corner points
            points = [
                (corners.top_left.x, corners.top_left.y),
                (corners.top_right.x, corners.top_right.y),
                (corners.bottom_right.x, corners.bottom_right.y),
                (corners.bottom_left.x, corners.bottom_left.y),
                (corners.top_left.x, corners.top_left.y)  # Close the polygon
            ]
            
            # Draw the quadrilateral outline
            draw.line(points, fill=(0, 255, 0), width=3)
            
            # Draw corner points with labels
            for i, point in enumerate(points[:-1]):
                # Draw circle at corner
                radius = 10
                draw.ellipse((point[0]-radius, point[1]-radius, point[0]+radius, point[1]+radius), 
                             fill=(255, 0, 0), outline=(0, 0, 0))
                
                # Add corner number
                labels = ["1: Top-Left", "2: Top-Right", "3: Bottom-Right", "4: Bottom-Left"]
                try:
                    font = ImageFont.truetype("Arial", 20)
                except IOError:
                    font = ImageFont.load_default()
                
                draw.text((point[0] + 15, point[1] - 10), labels[i], fill=(255, 0, 0), font=font)
            
            # Save the annotated image
            image.save(output_path)
            logger.info(f"Saved corners visualization to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating corners visualization: {e}")
            return image_path
    
    def crop_and_deskew(self, image_path: Path, corners: DocumentCorners, 
                       output_path: Optional[Path] = None) -> Path:
        """
        Crop and deskew a document based on detected corners.
        
        Args:
            image_path: Path to the original image
            corners: The detected document corners
            output_path: Path to save the processed image (optional)
            
        Returns:
            Path: Path to the processed image
        """
        if not output_path:
            # Create a default output path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            output_path = data_dir / f"deskewed_{timestamp}.png"
        
        try:
            # Read the image with OpenCV
            img = cv2.imread(str(image_path))
            if img is None:
                logger.error(f"Failed to read image at {image_path}")
                return image_path
            
            # Convert corners to np array format required by OpenCV
            src_points = corners.as_np_array()
            
            # Calculate the width and height of the resulting image
            # by finding the maximum distance between opposite corners
            width1 = np.sqrt(((corners.top_right.x - corners.top_left.x) ** 2) + 
                            ((corners.top_right.y - corners.top_left.y) ** 2))
            width2 = np.sqrt(((corners.bottom_right.x - corners.bottom_left.x) ** 2) + 
                            ((corners.bottom_right.y - corners.bottom_left.y) ** 2))
            max_width = max(int(width1), int(width2))
            
            height1 = np.sqrt(((corners.bottom_left.x - corners.top_left.x) ** 2) + 
                             ((corners.bottom_left.y - corners.top_left.y) ** 2))
            height2 = np.sqrt(((corners.bottom_right.x - corners.top_right.x) ** 2) + 
                             ((corners.bottom_right.y - corners.top_right.y) ** 2))
            max_height = max(int(height1), int(height2))
            
            # Define the destination points for a rectangle
            dst_points = np.array([
                [0, 0],
                [max_width - 1, 0],
                [max_width - 1, max_height - 1],
                [0, max_height - 1]
            ], dtype=np.float32)
            
            # Compute the perspective transform matrix
            transform_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            
            # Apply the perspective transformation
            deskewed = cv2.warpPerspective(img, transform_matrix, (max_width, max_height))
            
            # Save the deskewed image
            cv2.imwrite(str(output_path), deskewed)
            logger.info(f"Saved deskewed image to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in crop_and_deskew: {e}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(traceback.format_exc())
            return image_path

# Helper functions to use in other modules
async def detect_and_process_document(image_path: str, 
                                     visualize: bool = False, 
                                     model_name: str = DEFAULT_CORNER_MODEL) -> Dict[str, Any]:
    """
    Detect document corners and perform cropping and deskewing in one step.
    
    Args:
        image_path: Path to the image containing a document
        visualize: Whether to create a visualization of detected corners
        model_name: The name of the Ollama model to use
        
    Returns:
        Dict: Results including corners, paths to output images, and status
    """
    processor = OllamaCornersProcessor(model_name=model_name)
    logger.info(f"Processing image: {image_path}")
    logger.info(f"Using Ollama model: {processor.model_name}")
    
    # Detect corners
    corners = await processor.detect_corners(image_path, visualize=visualize)
    
    result = {
        "success": corners is not None,
        "original_image": image_path,
    }
    
    if corners:
        # Convert corners to dict for the result
        result["corners"] = corners.model_dump()
        
        # Perform cropping and deskewing
        deskewed_path = processor.crop_and_deskew(Path(image_path), corners)
        result["deskewed_image"] = str(deskewed_path)
        
        if visualize:
            viz_path = processor.visualize_corners(Path(image_path), corners)
            result["visualization"] = str(viz_path)
    else:
        result["error"] = "Failed to detect document corners"
    
    return result

# CLI for testing
async def cli_main():
    """Command line interface for testing the Ollama corners processor."""
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="Detect document corners and deskew using Ollama")
    parser.add_argument("image_path", help="Path to the image file containing a document")
    parser.add_argument("--model", default=DEFAULT_CORNER_MODEL, help=f"Ollama model name to use (default: {DEFAULT_CORNER_MODEL})")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: print to stdout)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--visualize", action="store_true", help="Create visualization of detected corners")
    parser.add_argument("--no-deskew", action="store_true", help="Skip the deskewing step")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        # Process the image
        processor = OllamaCornersProcessor(model_name=args.model)
            
        print(f"Processing image: {args.image_path}")
        print(f"Using Ollama model: {processor.model_name}")
        print("This may take a moment, detecting document corners...")
        
        corners = await processor.detect_corners(args.image_path, visualize=args.visualize)
        
        if not corners:
            print("ERROR: Failed to detect document corners", file=sys.stderr)
            sys.exit(1)
        
        # Convert to dict for JSON serialization
        result = {
            "success": True,
            "corners": corners.model_dump(),
            "original_image": args.image_path
        }
        
        # Perform deskewing if requested
        if not args.no_deskew:
            print("Deskewing document based on detected corners...")
            deskewed_path = processor.crop_and_deskew(Path(args.image_path), corners)
            result["deskewed_image"] = str(deskewed_path)
            print(f"Deskewed image saved to: {deskewed_path}")
        
        # Add visualization path if created
        if args.visualize:
            viz_path = processor.visualize_corners(Path(args.image_path), corners)
            result["visualization"] = str(viz_path)
            print(f"Visualization with corner points saved to: {viz_path}")
        
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
