from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    MODEL = "claude-3-5-sonnet-20241022"
    MAX_TOKENS = 8000
    MAX_CONVERSATION_TOKENS = 200000  # Maximum tokens per conversation

    # Paths
    BASE_DIR = Path(__file__).parent
    TOOLS_DIR = BASE_DIR / "tools"
    PROMPTS_DIR = BASE_DIR / "prompts"

    # Assistant Configuration
    ENABLE_THINKING = True
    SHOW_TOOL_USAGE = True
    DEFAULT_TEMPERATURE = 0.7

    @staticmethod
    def enforce_token_limit(conversation_history, max_tokens):
        total_tokens = sum(len(message['content']) for message in conversation_history)
        while total_tokens > max_tokens:
            conversation_history.pop(0)
            total_tokens = sum(len(message['content']) for message in conversation_history)
        return conversation_history
