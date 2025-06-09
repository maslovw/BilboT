#!/usr/bin/env python3
"""
Setup script for BilboT telegram bot

This script helps set up the bot token in the system keyring
"""

import keyring
import socket
import argparse
import sys


def setup_token(token=None, show=False):
    """
    Set up or display the bot token in the system keyring
    
    Args:
        token (str): The bot token to store
        show (bool): Whether to show the current token
    """
    service_name = "telegram_bilbo"
    username = socket.gethostname()
    
    if show:
        # Display the current token
        current_token = keyring.get_password(service_name, username)
        if current_token:
            print(f"Current token for {service_name} ({username}): {current_token}")
        else:
            print(f"No token found for {service_name} ({username})")
        return
        
    if not token:
        # Prompt for token if not provided
        token = input("Enter your Telegram bot token: ").strip()
        
    if not token:
        print("Error: Token cannot be empty")
        return
        
    # Store the token
    try:
        keyring.set_password(service_name, username, token)
        print(f"Token successfully stored for {service_name} ({username})")
    except Exception as e:
        print(f"Error storing token: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up the BilboT Telegram bot token")
    parser.add_argument("--token", help="The Telegram bot token to store")
    parser.add_argument("--show", action="store_true", help="Show the current stored token")
    
    args = parser.parse_args()
    
    setup_token(token=args.token, show=args.show)
