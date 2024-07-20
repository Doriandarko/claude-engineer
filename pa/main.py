import os
from dotenv import load_dotenv
from adapter import Adapter
from prompt_toolkit import prompt
from adapter import get_client, get_openai_tools
from tavily import TavilyClient
from rich.console import Console

# Load environment variables from .env file
load_dotenv()

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()

# Initialize the AI client
client = get_client()

# Example usage of the client
def main():
    console.print("Client initialized successfully.")
    # Add your code here to interact with the client

if __name__ == "__main__":
    main()
import os
from dotenv import load_dotenv
from adapter import get_client, get_openai_tools
from tavily import TavilyClient
from rich.console import Console

# Load environment variables from .env file
load_dotenv()

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()

# Initialize the AI client
client = get_client()

# Example usage of the client
def main():
    console.print("Client initialized successfully.")
    # Add your code here to interact with the client

if __name__ == "__main__":
    main()
