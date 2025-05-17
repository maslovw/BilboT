# BilboT
## Telegram Receipt Management Bot

BilboT is a Telegram bot that helps you manage receipts by storing photos and associated metadata for future analysis. It can differentiate users across different chat groups and store all receipt information in a local SQLite database.

## Features

- Receive and store receipt images from Telegram
- Recognize users across different chat groups
- Store images in a configurable local folder
- Save metadata in SQLite database including:
  - Date and time of the message
  - User information (name, ID)
  - Chat/group information
  - Comments attached to images
- Secure token storage using system keyring

## Setup

### Prerequisites

- Python 3.6+
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

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

### Running the Bot

Start the bot with:
```bash
python bilbot.py
```

## Usage

- Send a photo of a receipt to the bot
- Optionally add a caption to include notes about the receipt
- Use `/list` to see your stored receipts
- Use `/help` to see all available commands

## Project Structure

- `bilbot.py`: Main bot script
- `bilbot/`: Core module
  - `database/`: Database operations
  - `handlers/`: Telegram message and command handlers
  - `utils/`: Utility functions
- `data/`: Storage for database and images
- `doc/`: Documentation including To-Do list

## License

See the [LICENSE](LICENSE) file for details.
