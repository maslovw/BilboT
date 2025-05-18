#!/bin/zsh

# Example script to process a receipt image with the Ollama processor
# Usage: ./process_receipt_example.sh <image_path> [output_file]

# Check if at least one argument is provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <image_path> [output_file]"
    exit 1
fi

IMAGE_PATH="$1"
OUTPUT_OPTION=""

# If output file is provided, add the --output option
if [ $# -gt 1 ]; then
    OUTPUT_OPTION="--output $2"
fi

# Process the receipt image
echo "Processing receipt image: $IMAGE_PATH"
python -m bilbot.utils.ollama_processor "$IMAGE_PATH" $OUTPUT_OPTION

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Receipt processing completed successfully."
else
    echo "Receipt processing failed."
    exit 1
fi
