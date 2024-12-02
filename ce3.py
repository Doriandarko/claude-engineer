# assistant.py
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict
import importlib
import inspect
import pkgutil
import os
import json
import sys
from config import Config
from tools.base import BaseTool
from prompt_toolkit import prompt
from prompt_toolkit.styles import Style
from prompts.system_prompts import SystemPrompts

class Assistant:
    def __init__(self):
        if not Config.ANTHROPIC_API_KEY:
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.conversation_history = []
        self.console = Console()
        self.tools = self._load_tools()
        self.thinking_enabled = Config.ENABLE_THINKING
        self.temperature = Config.DEFAULT_TEMPERATURE
        self.total_tokens_used = 0

    def _load_tools(self) -> List[Dict]:
        """Dynamically load all tool classes from the tools directory"""
        tools = []
        tools_path = Config.TOOLS_DIR

        try:
            # Clear module cache for tools to ensure fresh imports
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('tools.') and module_name != 'tools.base':
                    del sys.modules[module_name]

            # Import all modules in the tools directory
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name != 'base':  # Skip base.py
                    try:
                        module = importlib.import_module(f'tools.{module_info.name}')

                        # Find tool classes in the module
                        for name, obj in inspect.getmembers(module):
                            if (inspect.isclass(obj) and
                                issubclass(obj, BaseTool) and
                                obj != BaseTool):
                                try:
                                    tool = obj()
                                    tools.append({
                                        "name": tool.name,
                                        "description": tool.description,
                                        "input_schema": tool.input_schema
                                    })
                                    self.console.print(f"[green]Loaded tool:[/green] {tool.name}")
                                except Exception as tool_error:
                                    self.console.print(f"[red]Error initializing tool {name}:[/red] {str(tool_error)}")
                                    continue

                    except ImportError as e:
                        missing_module = str(e).split("'")[1] if "'" in str(e) else str(e).split("No module named ")[1]
                        self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for {module_info.name}")
                        
                        # Ask user if they want to install the missing dependency
                        user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()
                        
                        if user_response == 'y':
                            # Instead of direct installation, send a message to the assistant
                            installation_message = f"Please install the package '{missing_module}' using UV package manager"
                            try:
                                # Use the existing chat method to handle the installation
                                install_result = self.chat(installation_message)
                                
                                # After installation attempt, try importing the module again
                                try:
                                    module = importlib.import_module(f'tools.{module_info.name}')
                                    for name, obj in inspect.getmembers(module):
                                        if (inspect.isclass(obj) and
                                            issubclass(obj, BaseTool) and
                                            obj != BaseTool):
                                            tool = obj()
                                            tools.append({
                                                "name": tool.name,
                                                "description": tool.description,
                                                "input_schema": tool.input_schema
                                            })
                                            self.console.print(f"[green]Loaded tool:[/green] {tool.name}")
                                except Exception as e:
                                    self.console.print(f"[red]Failed to load tool after installation: {str(e)}[/red]")
                            except Exception as e:
                                self.console.print(f"[red]Error during installation process: {str(e)}[/red]")
                        else:
                            self.console.print(f"[yellow]Skipping tool {module_info.name} due to missing dependency[/yellow]")
                    except Exception as e:
                        self.console.print(f"[red]Error loading module {module_info.name}:[/red] {str(e)}")
                        continue

        except Exception as e:
            self.console.print(f"[red]Error in tool loading process:[/red] {str(e)}")

        return tools

    def refresh_tools(self):
        """Refresh the available tools and only show new additions"""
        # Store current tool names for comparison
        current_tool_names = {tool['name'] for tool in self.tools}

        # Quietly reload tools
        self.tools = self._load_tools()
        new_tool_names = {tool['name'] for tool in self.tools}

        # Find newly added tools
        new_tools = new_tool_names - current_tool_names

        # Only display new tools if any were found
        if new_tools:
            self.console.print("\n")  # Add some spacing
            for tool_name in new_tools:
                tool_info = next(tool for tool in self.tools if tool['name'] == tool_name)
                # Format the description with proper indentation
                description_lines = tool_info['description'].strip().split('\n')
                formatted_description = '\n    '.join(line.strip() for line in description_lines)
                self.console.print(f"[bold green]NEW[/bold green] 🔧 [cyan]{tool_name}[/cyan]:\n    {formatted_description}")
        else:
            self.console.print("\n[yellow]No new tools found[/yellow]")

    def display_available_tools(self):
        """Display the list of available tools"""
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        tool_names = [tool['name'] for tool in self.tools]
        formatted_tools = ", ".join([f"🔧 [cyan]{name}[/cyan]" for name in tool_names])
        self.console.print(formatted_tools)
        self.console.print("\n---")

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: str):
        """Display tool execution details in a clean panel format"""
        if not Config.SHOW_TOOL_USAGE:
            return
        
        # Format the content with proper spacing and layout
        tool_info = f"""[cyan]📥 Input:[/cyan] {json.dumps(input_data, indent=2)}
[cyan]📤 Result:[/cyan] {result}"""

        # Create panel with tool name as title
        panel = Panel(
            tool_info,
            title=f"Tool used: {tool_name}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2)
        )

        self.console.print(panel)

    def _execute_tool(self, tool_use):
        """Execute a tool and return its result"""
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_result = None

        try:
            # Import the tool module
            module = importlib.import_module(f'tools.{tool_name}')

            # Find and instantiate the tool class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseTool) and
                    obj != BaseTool):
                    tool = obj()
                    if tool.name == tool_name:
                        result = tool.execute(**tool_input)
                        # Escape any Rich markup in the result
                        tool_result = result.replace('[', '\\[').replace(']', '\\]')
                        break

            if tool_result is None:
                tool_result = f"Tool not found: {tool_name}"

        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"

        # Display tool execution details if enabled
        if Config.SHOW_TOOL_USAGE:
            self._display_tool_usage(tool_name, tool_input, tool_result)

        return tool_result

    def _display_token_usage(self, usage):
        """Display token usage progress bar"""
        used_percentage = (self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS) * 100
        remaining_tokens = max(0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)
        
        # self.console.print("\n[bold blue]Token Usage:[/bold blue]")
        # self.console.print(f"Current message: {usage.input_tokens + usage.output_tokens} tokens")
        self.console.print(f"\nTotal used: {self.total_tokens_used:,} / {Config.MAX_CONVERSATION_TOKENS:,}")
        
        # Create progress bar
        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        color = "green"
        if used_percentage > 75:
            color = "yellow"
        if used_percentage > 90:
            color = "red"
            
        self.console.print(f"[{color}][{bar}] {used_percentage:.1f}%[/{color}]")
        
        if remaining_tokens < 20000:  # Warning when less than 20k tokens remain
            self.console.print(f"[bold red]Warning: Only {remaining_tokens:,} tokens remaining![/bold red]")
        
        self.console.print("---")

    def _count_tokens(self, messages, system_prompt=None):
        """Count tokens using Anthropic's token counting API"""
        try:
            response = self.client.beta.messages.count_tokens(
                betas=["token-counting-2024-11-01"],
                model=Config.MODEL,
                messages=messages,
                system=system_prompt,
                tools=self.tools
            )
            return response.input_tokens
        except Exception as e:
            # Fallback to rough estimation if token counting fails
            self.console.print(f"[yellow]Warning: Token counting API failed, using estimation.[/yellow]")
            return sum(len(str(m.get('content', ''))) * 0.5 for m in messages)

    def chat(self, user_input: str):
        """Process user input and return assistant's response"""
        if user_input.lower() == 'refresh':
            self.refresh_tools()
            return "Tools refreshed successfully!"

        # Count tokens for the new message
        new_message = {"role": "user", "content": user_input}
        messages_to_check = self.conversation_history + [new_message]
        estimated_tokens = self._count_tokens(
            messages=messages_to_check,
            system_prompt=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
        )
        
        # Check if adding this message would exceed the token limit
        if (self.total_tokens_used + estimated_tokens) >= Config.MAX_CONVERSATION_TOKENS:
            self.console.print("\n[bold red]Token limit approaching! Please reset the conversation.[/bold red]")
            return "Token limit approaching! Please type 'reset' to start a new conversation."

        self.conversation_history.append(new_message)

        try:
            spinner = Spinner('dots', 
                            text='Thinking...' if Config.ENABLE_THINKING else '', 
                            style="cyan")

            while True:  # Loop to handle multiple tool uses
                # Check token limit before making each request
                if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS * 0.9:  # 90% of limit
                    self.console.print("\n[bold yellow]Warning: Approaching token limit![/bold yellow]")
                
                with Live(spinner, refresh_per_second=10, transient=True) as live:
                    response = self.client.messages.create(
                        model=Config.MODEL,
                        max_tokens=min(Config.MAX_TOKENS, 
                                     Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used),
                        temperature=self.temperature,
                        tools=self.tools,
                        messages=self.conversation_history,
                        system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
                    )
                    
                    # Update token usage with actual usage from response
                    message_tokens = response.usage.input_tokens + response.usage.output_tokens
                    self.total_tokens_used += message_tokens
                    
                    # Display token usage
                    self._display_token_usage(response.usage)
                    
                    # Check if we've exceeded the token limit
                    if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS:
                        self.console.print("\n[bold red]Token limit reached! Please reset the conversation.[/bold red]")
                        return "Token limit reached! Please type 'reset' to start a new conversation."

                if response.stop_reason == "tool_use":
                    # Check if tool is being created
                    is_creation = any(
                        content.type == "tool_use" and
                        "create" in content.name.lower()
                        for content in response.content
                    )

                    if is_creation:
                        self.console.print("\n[bold yellow]🛠  Creating Tool...[/bold yellow]\n")
                    else:
                        self.console.print("\n[bold yellow]🛠  Using Tool...[/bold yellow]\n")

                    # Process each tool use in the response
                    tool_results = []
                    for content in response.content:
                        if content.type == "tool_use":
                            result = self._execute_tool(content)
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": content.id,
                                "content": result
                            })

                    # Add the tool results as a user message
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content  # This includes the tool_use blocks
                    })
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_results  # This includes the tool_result blocks
                    })

                    # Continue the loop to allow for chained tool usage
                    continue

                else:
                    # No more tools needed, append the final response and break
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": response.content
                    })
                    # Escape any Rich markup in the response
                    text_response = response.content[0].text
                    return text_response.replace('[', '\\[').replace(']', '\\]')

        except Exception as e:
            return f"Error: {str(e)}"

    def reset(self):
        """Reset the assistant's conversation history and token count"""
        self.conversation_history = []
        self.total_tokens_used = 0
        self.console.print("\n[bold green]🔄 Assistant memory has been reset![/bold green]")
        
        # Display welcome message again
        welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
        self.console.print(Markdown(welcome_text))
        self.display_available_tools()

def main():
    console = Console()

    # Define prompt style
    style = Style.from_dict({
        'prompt': 'orange',
    })

    try:
        assistant = Assistant()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("Please make sure you have set the ANTHROPIC_API_KEY environment variable")
        return

    # Display welcome message
    welcome_text = """
# Claude Engineer v3. A self-improving assistant framework with tool creation

Type 'refresh' to reload available tools
Type 'reset' to clear conversation history
Type 'quit' to exit

Available tools:
"""
    console.print(Markdown(welcome_text))
    assistant.display_available_tools()

    while True:
        try:
            user_input = prompt(
                "You: ",
                style=style
            ).strip()

            if user_input.lower() == 'quit':
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break
            elif user_input.lower() == 'reset':
                assistant.reset()
                continue

            response = assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer:[/bold purple]", style="bold")
            # Handle the response safely
            if isinstance(response, str):
                # Escape any Rich markup in the response
                safe_response = response.replace('[', '\\[').replace(']', '\\]')
                console.print(safe_response)
            else:
                console.print(str(response))

        except KeyboardInterrupt:
            continue
        except EOFError:
            break

if __name__ == "__main__":
    main()
