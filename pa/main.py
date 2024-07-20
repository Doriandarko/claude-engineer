import os
from dotenv import load_dotenv
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from tavily import TavilyClient
from rich.console import Console
from anthropic import Anthropic
import openai

# Load environment variables from .env file
load_dotenv()

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()

def get_client():
    options = ["Anthropic", "Open Router"]
    completer = WordCompleter(options, ignore_case=True)
    
    while True:
        choice = prompt("Select the AI provider (Anthropic/Open Router): ", completer=completer).strip().lower()
        
        if choice == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
            return Anthropic(api_key=api_key)
        elif choice == "open router":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY not found in environment variables")
            openai.api_base = "https://openrouter.ai/api/v1"
            openai.api_key = api_key
            return openai
        else:
            console.print("Invalid choice. Please select either 'Anthropic' or 'Open Router'.", style="bold red")

def main():
    client = get_client()
    console.print("Client initialized successfully.", style="bold green")
    
    if isinstance(client, Anthropic):
        console.print("Using Anthropic API", style="bold blue")
    else:
        console.print("Using Open Router API", style="bold blue")

    while True:
        user_input = input("Enter your prompt (or 'exit' to quit): ")
        if user_input.lower() == 'exit':
            break

        try:
            if isinstance(client, Anthropic):
                response = client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": user_input}]
                )
                console.print(response.content[0].text, style="green")
            else:
                response = client.ChatCompletion.create(
                    model="openai/gpt-4-turbo-preview",
                    messages=[{"role": "user", "content": user_input}]
                )
                console.print(response.choices[0].message.content, style="green")
        except Exception as e:
            console.print(f"Error: {str(e)}", style="bold red")

if __name__ == "__main__":
    main()
import os
from dotenv import load_dotenv
from adapter import Adapter
from tavily import TavilyClient
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import asyncio
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style

# Load environment variables from .env file
load_dotenv()

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()

async def get_user_input(prompt="You: "):
    style = Style.from_dict({
        'prompt': 'cyan bold',
    })
    session = PromptSession(style=style)
    return await session.prompt_async(prompt, multiline=False)

async def main():
    console.print(Panel("Welcome to the AI Assistant!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")

    # Initialize the AI client
    adapter = Adapter()
    client = adapter.get_client()
    model = adapter.get_model()

    console.print(f"Using model: {model}")

    while True:
        user_input = await get_user_input()

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title="Goodbye", style="bold green"))
            break

        try:
            if isinstance(client, Adapter.Anthropic):
                response = client.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": user_input}]
                )
                assistant_response = response.content[0].text
            else:
                response = client.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "user", "content": user_input}]
                )
                assistant_response = response.choices[0].message.content

            console.print(Panel(Markdown(assistant_response), title="AI Response", border_style="blue"))

        except Exception as e:
            console.print(Panel(f"Error: {str(e)}", title="Error", style="bold red"))

if __name__ == "__main__":
    asyncio.run(main())
