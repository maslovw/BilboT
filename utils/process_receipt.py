#!/usr/bin/env python3
"""Example script for running the receipt processor using the configured AI
backend."""

if __name__ == "__main__":
    import sys
    import os
    # Ensure project root is on the path for local imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    from bilbot.utils.ollama_processor import cli_main
    import asyncio

    from bilbot.utils.config import get_ai_provider

    if get_ai_provider().lower() == "chatgpt":
        from bilbot.utils.chatgpt_processor import cli_main
    else:
        from bilbot.utils.ollama_processor import cli_main

    exit_code = asyncio.run(cli_main())
    sys.exit(exit_code)
