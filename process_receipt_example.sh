#!/bin/zsh

# Example script to process a receipt image using the configured AI backend
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

# Determine provider from config
PROVIDER=$(python - <<'EOF'
import json;print(json.load(open('config.json')).get('ai_processing', {}).get('provider', 'ollama'))
EOF
)

echo "Processing receipt image: $IMAGE_PATH using $PROVIDER"
if [ "$PROVIDER" = "chatgpt" ]; then
    python -m bilbot.utils.chatgpt_processor "$IMAGE_PATH" $OUTPUT_OPTION
else
    BASE_URL=$(python - <<'EOF'
import json;print(json.load(open('config.json')).get('ai_processing', {}).get('base_url', 'http://localhost:11434'))
EOF
    )
    python -m bilbot.utils.ollama_processor "$IMAGE_PATH" $OUTPUT_OPTION --base-url "$BASE_URL"
fi

# Check the exit code
if [ $? -eq 0 ]; then
    echo "Receipt processing completed successfully."
else
    echo "Receipt processing failed."
    exit 1
fi
