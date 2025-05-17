# BilboT - Telegram Receipt Bot To-Do List

## Core Functionality
- [x] Create project structure
- [x] Set up Telegram bot using python-telegram-bot library
- [x] Implement token retrieval using keyring
- [x] Create handler for receiving and processing photos
- [x] Implement user and group recognition
- [x] Set up local storage for receipt images

## Database
- [x] Create SQLite database schema
- [x] Set up tables for:
  - [x] User information (user_id, username)
  - [x] Chat information (chat_id, chat_title)
  - [x] Receipt records (message_id, user_id, chat_id, image_path, received_date, receipt_date, comments)
- [x] Implement database connection and query functions
- [x] Set up functions for storing and retrieving receipt data

## Image Processing
- [x] Implement receipt image storage with standardized naming
- [x] Create folder structure for organized image storage
- [ ] Future: Implement OCR for extracting receipt data (date, total, items)

## User Interface
- [x] Implement commands (/start, /help)
- [ ] Add functionality for users to add comments to receipts
- [x] Implement status reports for stored receipts
- [x] Add command to retrieve previously stored receipts

## Security & Configuration
- [x] Implement secure token handling via keyring
- [x] Create configuration file for customizable settings
- [x] Set up error handling and logging
- [x] Add input validation and sanitization
- [x] Implement rate limiting to prevent abuse
- [x] Add debug mode to restrict access to authorized users

## Testing
- [x] Create test cases for core functionality
- [x] Test database operations
- [x] Test image storage and retrieval
- [x] Test user recognition across different chats

## Documentation
- [x] Complete README.md with setup instructions
- [x] Document API and data flow
- [x] Add usage examples and command reference
