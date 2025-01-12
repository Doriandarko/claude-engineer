from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # API Configuration
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    
    # Model Configuration
    USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'false').lower() == 'true'
    MODEL = "anthropic/claude-3.5-sonnet:beta" if USE_OPENROUTER else "claude-3-5-sonnet-20241022"
    MAX_TOKENS = 8000
    MAX_CONVERSATION_TOKENS = 200000  # Maximum tokens per conversation

    # OpenRouter Configuration
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    APP_NAME = os.getenv('APP_NAME', 'Claude Engineer')
    APP_URL = os.getenv('APP_URL', 'http://localhost:5000')

    # Paths
    BASE_DIR = Path(__file__).parent
    TOOLS_DIR = BASE_DIR / "tools"
    PROMPTS_DIR = BASE_DIR / "prompts"

    # Assistant Configuration
    ENABLE_THINKING = True
    SHOW_TOOL_USAGE = True
    DEFAULT_TEMPERATURE = 0.7
