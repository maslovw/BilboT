# BilboT
## Telegram Receipt Management Bot

BilboT is a Telegram bot that helps you manage receipts by storing photos and associated metadata for future analysis. It can differentiate users across different chat groups and store all receipt information in a local SQLite database.

## Features

- Receive and store receipt images from Telegram
- Automatic receipt data extraction using AI:
  - List of items and their prices
  - Store name
  - Purchase date and time
  - Payment method
- Recognize users across different chat groups
- Store images in a configurable local folder
- Save metadata in SQLite database including:
  - Date and time of the message
  - User information (name, ID)
  - Chat/group information
  - Comments attached to images
  - Extracted receipt data
- View receipt details with simple commands
- Secure token storage using system keyring
- Rate limiting to prevent abuse:
  - Per-user limit: 1 message per 10 seconds
  - Global limit: 60 messages per minute across all users
- Debug mode for restricted access and development

## Setup

### Prerequisites

- Python 3.6+
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))
- [Ollama](https://ollama.ai/download) installed locally for AI image processing

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/BilboT.git
   cd BilboT
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Store your Telegram bot token in the system keyring:
   ```bash
   python -c "import keyring; keyring.set_password('telegram_bilbo', __import__('socket').gethostname(), 'YOUR_BOT_TOKEN')"
   ```

4. Pull the required Ollama model:
   ```bash
   ollama pull qwen2.5vl:32b
   ```

5. Update the database schema:
   ```bash
   python patch_db_schema.py
   ```

### Running the Bot

Start the bot with:
```bash
python bilbot.py
```

## Usage

### Commands

- `/start` - Start the bot and see the welcome message
- `/help` - Show help information and available commands
- `/receipts` - List all your stored receipts
- `/details <receipt_id>` - View detailed information for a specific receipt

### How to Use

1. Start a chat with the bot and send the `/start` command to get started
2. Send a photo of a receipt to the bot
3. The bot will save the image and automatically extract information like:
   - Items and their prices
   - Store name
   - Total amount
   - Purchase date
   - Payment method
4. Use `/receipts` to see a list of all your stored receipts
5. Use `/details <receipt_id>` to view detailed information about a specific receipt

## AI Image Processing

BilboT uses Ollama with the Qwen2.5vl:32b model for receipt image processing. This allows the bot to:

1. Extract text from receipt images
2. Identify individual items and their prices
3. Recognize store names and payment methods
4. Structure the data for easy retrieval

The AI processing happens automatically when you send a receipt image. The structured data is then stored in the database for future reference.

## Project Structure

- `bilbot.py`: Main bot script
- `bilbot/`: Core module
  - `database/`: Database operations
  - `handlers/`: Telegram message and command handlers
  - `utils/`: Utility functions
    - `rate_limiter.py`: Rate limiting functionality
- `data/`: Storage for database and images
- `doc/`: Documentation including To-Do list
- `tests/`: Test scripts and modules

## Configuration

Configuration is stored in `config.json` and includes the following sections:

- `bot_name`: The name of the bot
- `image_storage`: Settings for storing receipt images
- `database`: Database configuration
- `logging`: Logging settings
- `rate_limiting`: Rate limiting configuration
  - `per_user_seconds`: Minimum seconds between messages for a single user (default: 10)
  - `global_per_minute`: Maximum messages allowed per minute across all users (default: 60)
  - `enabled`: Whether rate limiting is enabled (default: true)
- `debug`: Enable debug mode to restrict access to authorized users

### Debug Mode

BilboT includes a debug mode that can be enabled by setting `"debug": true` in the `config.json` file. When debug mode is enabled:

- Only users who already exist in the database can interact with the bot
- New users will receive a message that they are not authorized
- The `/add_debug_user` command becomes available to add new authorized users
- The `/help` command will show additional debug-specific commands and indicate that debug mode is active

To add a new authorized user in debug mode:

```bash
/add_debug_user <user_id> [username] [first_name] [last_name]
```

This feature is useful for testing and development or in situations where you want to restrict access to the bot.

## License

See the [LICENSE](LICENSE) file for details.
