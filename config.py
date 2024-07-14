import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25
MAX_TOKENS = 10000
DB_FILE = "conversation_state.db"

# Models
MAINMODEL = "claude-3-5-sonnet-20240620"
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# Validate that API keys are set
if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")
if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY is not set in the environment variables")
