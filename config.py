"""
Configuration settings for the Claude Engineer project.
This module contains all the configuration variables, initialization functions, and logging setup.
"""

import os
import logging
from dotenv import load_dotenv
from colorama import init as colorama_init

# Load environment variables from .env file
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Claude AI Model
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"

# Conversation Settings
MAX_TOKENS = 4000
MAX_CONTINUATION_ITERATIONS = 25
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"

# Color Settings
USER_COLOR = "\033[37m"  # White
CLAUDE_COLOR = "\033[34m"  # Blue
TOOL_COLOR = "\033[33m"  # Yellow
RESULT_COLOR = "\033[32m"  # Green

# File Paths
PROMPTS_DIR = "prompts"
SYSTEM_PROMPT_TEMPLATE = "swe.jinja"

# Image Processing
MAX_IMAGE_SIZE = (1024, 1024)

# Logging Configuration
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'claude_engineer.log'

def init_colorama():
    """
    Initialize colorama for cross-platform colored terminal text.
    """
    colorama_init()

def setup_logger(name):
    """
    Set up a logger with the specified name.
    
    Args:
        name (str): The name of the logger.
    
    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)

    # Create handlers
    file_handler = logging.FileHandler(LOG_FILE)
    console_handler = logging.StreamHandler()

    # Create formatters and add it to handlers
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Initialize colorama when the config module is imported
init_colorama()

# Create a global logger instance
logger = setup_logger('claude_engineer')