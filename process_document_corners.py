#!/usr/bin/env python3
# filepath: /Users/viacheslav.maslov/EDF/tools/BilboT/process_document_corners.py
"""
Example script for detecting document corners and deskewing documents.
"""

import argparse
import asyncio
import logging
import sys
import json
from pathlib import Path

from bilbot.utils.ollama_corners_processor import detect_and_process_document

def parse_args():
    parser = argparse.ArgumentParser(description="Detect document corners and deskew using Ollama")
    parser.add_argument("image_path", help="Path to the image file containing a document")
    parser.add_argument("--model", default="qwen2.5vl:3b", help="Ollama model name to use (default: qwen2.5vl:3b)")
    parser.add_argument("--output", "-o", help="Output JSON file path (default: print to stdout)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--visualize", action="store_true", help="Create visualization of detected corners")
    
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    try:
        print(f"Processing image: {args.image_path}")
        print(f"Using Ollama model: {args.model}")
        
        # Process the document
        result = await detect_and_process_document(
            args.image_path,
            visualize=args.visualize,
            model_name=args.model
        )
        
        # Output the result
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"Results saved to: {args.output}")
            
            # Print summary
            if result["success"]:
                print("\nDocument Processing Results:")
                print(f"- Original image: {result['original_image']}")
                print(f"- Deskewed image: {result['deskewed_image']}")
                if args.visualize and "visualization" in result:
                    print(f"- Visualization: {result['visualization']}")
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")
        else:
            print(json.dumps(result, indent=2))
        
        return 0 if result["success"] else 1
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
