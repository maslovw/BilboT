"""
Test script to visualize the effects of image preprocessing for OCR.
"""

import os
import sys
import argparse
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bilbot.utils.image_preprocessing import preprocess_image
from bilbot.utils.config import get_image_storage_path

def create_comparison_image(original_path, preprocessed_path, output_path=None):
    """
    Create a side-by-side comparison of original and preprocessed images.
    
    Args:
        original_path (str): Path to the original image
        preprocessed_path (str): Path to the preprocessed image
        output_path (str, optional): Path to save the comparison image
    
    Returns:
        str: Path to the comparison image
    """
    # Open images
    original = Image.open(original_path)
    preprocessed = Image.open(preprocessed_path)
    
    # Resize images to same height for fair comparison
    max_height = 800
    aspect_ratio = original.width / original.height
    new_width = int(max_height * aspect_ratio)
    original = original.resize((new_width, max_height), Image.LANCZOS)
    
    aspect_ratio = preprocessed.width / preprocessed.height
    new_width = int(max_height * aspect_ratio)
    preprocessed = preprocessed.resize((new_width, max_height), Image.LANCZOS)
    
    # Create a new image with both images side by side
    total_width = original.width + preprocessed.width + 20  # 20px padding between images
    comparison = Image.new('RGB', (total_width, max_height + 50), color=(255, 255, 255))
    
    # Paste images
    comparison.paste(original, (0, 0))
    comparison.paste(preprocessed, (original.width + 20, 0))
    
    # Add labels
    draw = ImageDraw.Draw(comparison)
    try:
        # Try to use a default font
        font = ImageFont.truetype("Arial", 20)
    except:
        # Fall back to default font
        font = ImageFont.load_default()
        
    draw.text((10, max_height + 10), "Original", fill=(0, 0, 0), font=font)
    draw.text((original.width + 30, max_height + 10), "Preprocessed", fill=(0, 0, 0), font=font)
    
    # Generate output path if not provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"image_comparison_{timestamp}.png"
        output_path = os.path.join("data", filename)
        
    # Save comparison image
    comparison.save(output_path)
    print(f"Comparison image saved to: {output_path}")
    
    return output_path

def main():
    parser = argparse.ArgumentParser(description="Test image preprocessing for OCR")
    parser.add_argument("image_path", help="Path to the receipt image to preprocess")
    parser.add_argument("--allow-rotation", action="store_true", help="Allow image rotation/deskewing")
    args = parser.parse_args()
    
    if not os.path.exists(args.image_path):
        print(f"Error: Image not found at {args.image_path}")
        return
    
    print(f"Processing image: {args.image_path}")
    
    # Apply preprocessing directly without deskewing step unless explicitly allowed
    print("Enhancing image...")
    preprocessed_path = preprocess_image(args.image_path, allow_rotation=args.allow_rotation)
    
    # Create comparison
    print("Creating comparison image...")
    comparison_path = create_comparison_image(args.image_path, preprocessed_path)
    
    print("Done!")
    print(f"Original image: {args.image_path}")
    print(f"Preprocessed image: {preprocessed_path}")
    print(f"Comparison image: {comparison_path}")
    print(f"Comparison image: {comparison_path}")

if __name__ == "__main__":
    main()
