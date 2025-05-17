#!/usr/bin/env python3
"""
Development script for BilboT

This script provides a convenient way to run the bot in development mode
with logging and automatic reloading when files change.
"""

import os
import sys
import time
import logging
import subprocess
import argparse
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Path to the main bot script
BOT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bilbot.py")

class BotRunner:
    def __init__(self, debug=False):
        self.debug = debug
        self.process = None
        self.is_running = False
        
    def start(self):
        """Start the bot process"""
        if self.is_running:
            logger.info("Bot is already running. Stopping first.")
            self.stop()
            
        logger.info("Starting BilboT...")
        
        cmd = [sys.executable, BOT_SCRIPT]
        if self.debug:
            env = os.environ.copy()
            env["PYTHONDEBUG"] = "1"
            self.process = subprocess.Popen(cmd, env=env)
        else:
            self.process = subprocess.Popen(cmd)
            
        self.is_running = True
        logger.info("BilboT started")
        
    def stop(self):
        """Stop the bot process"""
        if not self.is_running:
            logger.info("Bot is not running")
            return
            
        logger.info("Stopping BilboT...")
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning("Bot did not terminate gracefully, killing")
                self.process.kill()
            
        self.is_running = False
        self.process = None
        logger.info("BilboT stopped")
        
    def restart(self):
        """Restart the bot process"""
        logger.info("Restarting BilboT...")
        self.stop()
        time.sleep(1)  # Small delay to ensure clean shutdown
        self.start()

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, bot_runner):
        self.bot_runner = bot_runner
        self.last_restart = time.time()
        self.cooldown = 2  # Seconds between restarts
        
    def on_any_event(self, event):
        # Skip if it's a directory or a non-Python file
        if event.is_directory or not event.src_path.endswith('.py'):
            return
            
        # Avoid restarting too frequently
        now = time.time()
        if now - self.last_restart < self.cooldown:
            return
            
        logger.info(f"Detected change in {event.src_path}")
        self.bot_runner.restart()
        self.last_restart = now

def run_dev_server(debug=False, watch=True):
    """Run the bot in development mode with auto-reloading"""
    bot_runner = BotRunner(debug=debug)
    
    try:
        bot_runner.start()
        
        if watch:
            # Set up file watching for auto-reload
            event_handler = FileChangeHandler(bot_runner)
            observer = Observer()
            
            # Watch the bot script directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            observer.schedule(event_handler, base_dir, recursive=True)
            
            # Also watch the bilbot module directory
            module_dir = os.path.join(base_dir, "bilbot")
            if os.path.exists(module_dir):
                observer.schedule(event_handler, module_dir, recursive=True)
                
            observer.start()
            
            logger.info("Watching for file changes (press Ctrl+C to stop)")
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Stopping development server")
                observer.stop()
                
            observer.join()
        else:
            # Just run the bot without watching for changes
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Stopping BilboT")
    finally:
        bot_runner.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run BilboT in development mode")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--no-watch", dest="watch", action="store_false", 
                        help="Disable auto-reload on file changes")
    
    args = parser.parse_args()
    
    run_dev_server(debug=args.debug, watch=args.watch)
