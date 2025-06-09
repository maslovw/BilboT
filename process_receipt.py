#!/usr/bin/env python3
"""Example script for running the receipt processor using the configured AI
backend."""

if __name__ == "__main__":
    import asyncio
    import sys

    from bilbot.utils.config import get_ai_provider

    if get_ai_provider().lower() == "chatgpt":
        from bilbot.utils.chatgpt_processor import cli_main
    else:
        from bilbot.utils.ollama_processor import cli_main

    exit_code = asyncio.run(cli_main())
    sys.exit(exit_code)
