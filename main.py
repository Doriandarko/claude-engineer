from colorama import init
from agent import ClaudeAgent

# Initialize colorama
init()

if __name__ == "__main__":
    claude = ClaudeAgent()
    claude.conversation()
