#!/bin/bash
# BilboT setup script

set -e  # Exit on error

echo "Setting up BilboT - Telegram Receipt Bot"
echo "========================================"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

# Check Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
required_version="3.6"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "Error: Python $required_version or higher is required (you have $python_version)"
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Dependencies installed"

# Create necessary directories
echo "Creating directories..."
mkdir -p data/images

echo "✅ Directories created"

# Run tests
echo "Running tests..."
python -m unittest discover -s tests

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Set up your bot token using: ./setup_token.py"
echo "2. Run the bot using: ./bilbot.py"
echo "3. For development mode with auto-reload: ./run_dev.py"
echo ""
echo "Enjoy using BilboT!"
