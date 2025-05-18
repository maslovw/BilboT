#!/bin/zsh

# Batch process receipts
# Usage: ./batch_process_receipts.sh <images_dir> <output_dir>

# Check if two arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <images_dir> <output_dir>"
    exit 1
fi

IMAGES_DIR="$1"
OUTPUT_DIR="$2"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Count images
IMAGE_COUNT=$(find "$IMAGES_DIR" -name "*.jpg" | wc -l)
echo "Found $IMAGE_COUNT images to process"

# Process each image
COUNTER=0
for IMAGE_PATH in $(find "$IMAGES_DIR" -name "*.jpg"); do
    COUNTER=$((COUNTER+1))
    IMAGE_BASENAME=$(basename "$IMAGE_PATH" .jpg)
    OUTPUT_FILE="$OUTPUT_DIR/${IMAGE_BASENAME}.json"
    
    echo "[$COUNTER/$IMAGE_COUNT] Processing: $IMAGE_PATH"
    python -m bilbot.utils.ollama_processor "$IMAGE_PATH" --output "$OUTPUT_FILE"
    
    if [ $? -eq 0 ]; then
        echo "  ✓ Receipt processed successfully: $OUTPUT_FILE"
    else
        echo "  ✗ Receipt processing failed"
    fi
done

echo "Batch processing complete. Processed $COUNTER images."
