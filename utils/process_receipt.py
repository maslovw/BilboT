#!/usr/bin/env python3
"""
Example script showing how to use the receipt processor CLI.
This is just a wrapper around the actual CLI in the ollama_processor.py file.
"""

if __name__ == "__main__":
    import sys
    import os
    # Ensure project root is on the path for local imports
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    from bilbot.utils.ollama_processor import cli_main
    import asyncio
    
    # Run the CLI
    exit_code = asyncio.run(cli_main())
    sys.exit(exit_code)
