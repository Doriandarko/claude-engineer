import os
from anthropic import Anthropic
import openai
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

class Adapter:
    def __init__(self):
        self.client = self.get_client()

    def get_client(self):
        options = ["Anthropic", "Open Router"]
        completer = WordCompleter(options, ignore_case=True)
        choice = prompt("Select the AI provider (Anthropic/Open Router): ", completer=completer).strip()

        if choice.lower() == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            return Anthropic(api_key=api_key)
        elif choice.lower() == "open router":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
            openai.api_base = "https://openrouter.ai/api/v1"
            openai.api_key = api_key
            return openai
        else:
            raise ValueError("Invalid choice. Please select either 'Anthropic' or 'Open Router'.")

    def get_model(self):
        if isinstance(self.client, Anthropic):
            return "claude-3-sonnet-20240229"
        else:
            return "openai/gpt-4o-mini"

    @staticmethod
    def get_openai_tools(tools):
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "parameters": tool["input_schema"],
                    "description": tool["description"]
                }
            })
        return openai_tools

    Anthropic = Anthropic
import os
from anthropic import Anthropic
import openai
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

def get_client():
    options = ["Anthropic", "Open Router"]
    completer = WordCompleter(options, ignore_case=True)
    choice = prompt("Select the AI provider (Anthropic/Open Router): ", completer=completer).strip()

    if choice.lower() == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
        return Anthropic(api_key=api_key)
    elif choice.lower() == "open router":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        openai.api_base = "https://openrouter.ai/api/v1"
        openai.api_key = api_key
        return openai
    else:
        raise ValueError("Invalid choice. Please select either 'Anthropic' or 'Open Router'.")

def get_openai_tools(tools):
    openai_tools = []
    for tool in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool["name"],
                "parameters": tool["input_schema"],
                "description": tool["description"]
            }
        })
    return openai_tools
import os
from anthropic import Anthropic
import openai

class Adapter:
    def __init__(self, use_openai=False):
        self.use_openai = use_openai
        if self.use_openai:
            self.client = openai
            self.client.api_key = os.getenv("OPENROUTER_API_KEY")
            self.client.api_base = "https://openrouter.ai/api/v1"
        else:
            self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def get_client(self):
        return self.client

    def get_model(self):
        return "openai/gpt-4o-mini" if self.use_openai else "claude-3-5-sonnet-20240620"
