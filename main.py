"""
Claude Engineer - An AI-powered software engineering assistant
This script initializes and runs the Claude Agent for interactive conversations.
"""

from agent import ClaudeAgent

if __name__ == "__main__":
    claude = ClaudeAgent()
    claude.conversation()