# BilboT Development Guide

This document provides guidance for developers working on the BilboT project.

## Project Structure

```
bilbot.py                 # Main bot script
setup.sh                  # Setup script
utils/setup_token.py      # Token management script
utils/run_dev.py          # Development mode script
config.json               # Configuration file
requirements.txt          # Python dependencies
bilbot/                   # Core module
  ├── database/           # Database operations
  │   └── db_manager.py   # Database functions
  ├── handlers/           # Telegram message handlers
  │   ├── command_handlers.py  # Command handling
  │   └── message_handlers.py  # Message handling
  └── utils/              # Utility functions
      ├── config.py       # Configuration utilities
      ├── image_utils.py  # Image processing utilities
      └── rate_limiter.py # Rate limiting functionality
data/                     # Data storage
  ├── images/             # Receipt images
  └── receipts.db         # SQLite database
doc/                      # Documentation
  └── ToDo.md             # Todo list
tests/                    # Test files
  ├── test_database.py    # Database tests
  └── test_rate_limiter.py # Rate limiter tests
```

## Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests to ensure functionality
5. Create a pull request

## Running in Development Mode

The project includes a development mode script that automatically reloads the bot when files change:

```bash
./utils/run_dev.py --debug
```

Options:
- `--debug`: Enable debug mode
- `--no-watch`: Disable auto-reload on file changes

## Adding New Features

### Adding a New Command

1. Add the command handler in `bilbot/handlers/command_handlers.py`
2. Register the command in `bilbot.py` with `dispatcher.add_handler()`
3. Update the help text in the `help_command` function

Example:

```python
def my_new_command(update: Update, context: CallbackContext):
    """Handle the /mynewcommand command"""
    update.message.reply_text("This is my new command!")

# In bilbot.py:
dispatcher.add_handler(CommandHandler("mynewcommand", my_new_command))
```

### Adding Rate Limiting to a New Handler

When adding a new message handler, make sure to include rate limiting:

1. Import the rate limiter:
   ```python
   from bilbot.utils.rate_limiter import check_rate_limit
   ```

2. Add rate limiting check at the beginning of your handler:
   ```python
   async def my_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
       # Check rate limits before processing
       if not await check_rate_limit(update, context):
           return  # Message was rate limited
           
       # Your handler code here
   ```

### Adding Database Functionality

1. Add new database functions in `bilbot/database/db_manager.py`
2. Add any required tables to the `init_database()` function
3. Create tests in `tests/test_database.py`

### Adding Image Processing Features

1. Add image processing functions in `bilbot/utils/image_utils.py`
2. For OCR or advanced processing, consider adding a separate module

## Configuration

The `config.json` file allows customization of various parameters:

```json
{
    "bot_name": "BilboT",
    "image_storage": {
        "base_path": "data/images",
        "max_size_mb": 50,
        "organize_by_date": true
    },
    "database": {
        "path": "data/receipts.db"
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    },
    "rate_limiting": {
        "per_user_seconds": 10,
        "global_per_minute": 60,
        "enabled": true
    }
}
```

Access configuration in code using the `load_config()` function from `bilbot/utils/config.py`.

## Testing

Run tests with:

```bash
python -m unittest discover -s tests
```

When adding features, include appropriate tests.

## Deployment

For production deployment:

1. Clone the repository on your server
2. Run `./setup.sh` to set up the environment
3. Set up the bot token using `./utils/setup_token.py`
4. Run the bot as a service (systemd, supervisor, etc.)

Example systemd service file:

```
[Unit]
Description=BilboT Telegram Receipt Bot
After=network.target

[Service]
ExecStart=/path/to/BilboT/venv/bin/python /path/to/BilboT/bilbot.py
WorkingDirectory=/path/to/BilboT
User=yourusername
Group=yourusername
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Future Enhancements

See the `doc/ToDo.md` file for planned features and improvements.

## Resources

- [python-telegram-bot documentation](https://python-telegram-bot.readthedocs.io/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
