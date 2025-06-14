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
min_version="3.6"
recommended_max="3.12"

if [ "$(printf '%s\n' "$min_version" "$python_version" | sort -V | head -n1)" != "$min_version" ]; then
    echo "Error: Python $min_version or higher is required (you have $python_version)"
    exit 1
fi

if [ "$(printf '%s\n' "$recommended_max" "$python_version" | sort -V | head -n1)" != "$python_version" ]; then
    echo "⚠️  Warning: You're using Python $python_version, which is newer than the recommended maximum ($recommended_max)"
    echo "    The application may work, but hasn't been extensively tested with this version."
    echo "    Proceed with caution and report any issues."
    # Give the user a chance to abort
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
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
echo "1. Set up your bot token using: ./utils/setup_token.py"
echo "2. Run the bot using: ./bilbot.py"
echo "3. For development mode with auto-reload: ./utils/run_dev.py"
echo ""
echo "Enjoy using BilboT!"
