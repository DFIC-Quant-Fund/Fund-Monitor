"""
Simple logging configuration for the Fund Monitor application.

Usage:
from [path] import get_logger
logger = get_logger(__name__)
logger.info("This is an info message")
"""

import logging
import sys

# ANSI color codes
COLORS = {
    "DEBUG": "\033[94m",   # Blue
    "INFO": "\033[92m",    # Green
    "WARNING": "\033[93m", # Yellow
    "ERROR": "\033[91m",   # Red
    "CRITICAL": "\033[95m" # Magenta
}
RESET = "\033[0m"

class ColorFormatter(logging.Formatter):
    def format(self, record):
        level_color = COLORS.get(record.levelname, RESET)
        record.levelname = f"{level_color}{record.levelname}{RESET}"
        return super().format(record)

def setup_logging():
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColorFormatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Suppress verbose third-party library logs
    logging.getLogger('yfinance').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('peewee').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger: 
    """Get a logger instance for the specified module."""
    return logging.getLogger(name)


# Initialize logging when module is imported
setup_logging()