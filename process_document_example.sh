#!/bin/bash
# filepath: /Users/viacheslav.maslov/EDF/tools/BilboT/process_document_example.sh

# Exit on error
set -e

# Check if image path is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <image_path> [--model <model_name>]"
    echo "Example: $0 path/to/document.jpg"
    echo "Example with custom model: $0 path/to/document.jpg --model qwen2.5vl:7b"
    exit 1
fi

# Image path is the first argument
IMAGE_PATH="$1"
shift

# Default model
MODEL="qwen2.5vl:3b"

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --model)
            MODEL="$2"
            shift
            shift
            ;;
        *)
            # Unknown option
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Check if image exists
if [ ! -f "$IMAGE_PATH" ]; then
    echo "Error: Image file not found: $IMAGE_PATH"
    exit 1
fi

echo "Processing document: $IMAGE_PATH"
echo "Using model: $MODEL"

# Create data directory if it doesn't exist
mkdir -p data

# Generate timestamp for output files
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="data/document_corners_${TIMESTAMP}.json"

# Run the processor with visualization
python3 process_document_corners.py "$IMAGE_PATH" --model "$MODEL" --output "$OUTPUT_FILE" --visualize

# Check if processing was successful
if [ $? -eq 0 ]; then
    echo "Document processed successfully!"
    echo "Results saved to: $OUTPUT_FILE"
    
    # Extract the deskewed image path from the JSON file
    if command -v jq &> /dev/null; then
        DESKEWED_IMAGE=$(jq -r '.deskewed_image' "$OUTPUT_FILE")
        VISUALIZATION=$(jq -r '.visualization // "none"' "$OUTPUT_FILE")
        
        echo "Deskewed image: $DESKEWED_IMAGE"
        
        if [ "$VISUALIZATION" != "none" ]; then
            echo "Visualization: $VISUALIZATION"
        fi
    else
        echo "Install jq for better output parsing"
    fi
else
    echo "Error processing document. Check logs for details."
    exit 1
fi

echo "Done!"
