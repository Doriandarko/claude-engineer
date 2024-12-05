# assistant.py
import anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.panel import Panel
from typing import List, Dict, Any
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
        if not getattr(Config, 'ANTHROPIC_API_KEY', None):
            raise ValueError("No ANTHROPIC_API_KEY found in environment variables")

        # Initialize Anthropics client
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)

        self.conversation_history: List[Dict[str, Any]] = []
        self.console = Console()
        self.tools = self._load_tools()

        # Safe defaults for configuration
        self.thinking_enabled = getattr(Config, 'ENABLE_THINKING', False)
        self.temperature = getattr(Config, 'DEFAULT_TEMPERATURE', 0.7)
        self.total_tokens_used = 0

    def _load_tools(self) -> List[Dict[str, Any]]:
        """
        Dynamically load all tool classes from the tools directory.
        Tools must subclass BaseTool. Skips tools that cannot be loaded
        due to missing dependencies or other errors.
        """
        tools = []
        tools_path = getattr(Config, 'TOOLS_DIR', None)

        if tools_path is None:
            self.console.print("[red]TOOLS_DIR not set in Config[/red]")
            return tools

        # Clear cached modules for a fresh import of the tools directory
        for module_name in list(sys.modules.keys()):
            if module_name.startswith('tools.') and module_name != 'tools.base':
                del sys.modules[module_name]

        # Iterate through modules in the tools directory
        try:
            for module_info in pkgutil.iter_modules([str(tools_path)]):
                if module_info.name == 'base':
                    continue
                try:
                    module = importlib.import_module(f'tools.{module_info.name}')
                    # Find tool classes in the module
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and
                            issubclass(obj, BaseTool) and
                            obj != BaseTool):
                            try:
                                tool_instance = obj()
                                tools.append({
                                    "name": tool_instance.name,
                                    "description": tool_instance.description,
                                    "input_schema": tool_instance.input_schema
                                })
                                self.console.print(f"[green]Loaded tool:[/green] {tool_instance.name}")
                            except Exception as tool_init_err:
                                self.console.print(f"[red]Error initializing tool {name}:[/red] {str(tool_init_err)}")
                except ImportError as e:
                    # Attempt to parse missing module name from ImportError
                    err_str = str(e)
                    if "No module named" in err_str:
                        parts = err_str.split("No module named")
                        missing_module = parts[-1].strip(" '\"")
                    else:
                        missing_module = str(e)

                    self.console.print(f"\n[yellow]Missing dependency:[/yellow] {missing_module} for tool {module_info.name}")
                    user_response = input(f"Would you like to install {missing_module}? (y/n): ").lower()
                    
                    if user_response == 'y':
                        installation_message = f"Please install the package '{missing_module}' using UV package manager"
                        try:
                            # Attempt to handle installation via chat method
                            self.chat(installation_message)
                            # Retry loading the module
                            try:
                                module = importlib.import_module(f'tools.{module_info.name}')
                                for name, obj in inspect.getmembers(module):
                                    if (inspect.isclass(obj) and
                                        issubclass(obj, BaseTool) and
                                        obj != BaseTool):
                                        tool_instance = obj()
                                        tools.append({
                                            "name": tool_instance.name,
                                            "description": tool_instance.description,
                                            "input_schema": tool_instance.input_schema
                                        })
                                        self.console.print(f"[green]Loaded tool:[/green] {tool_instance.name}")
                            except Exception as retry_err:
                                self.console.print(f"[red]Failed to load tool after installation: {str(retry_err)}[/red]")
                        except Exception as install_err:
                            self.console.print(f"[red]Error during installation process: {str(install_err)}[/red]")
                    else:
                        self.console.print(f"[yellow]Skipping tool {module_info.name} due to missing dependency[/yellow]")
                except Exception as mod_err:
                    self.console.print(f"[red]Error loading module {module_info.name}:[/red] {str(mod_err)}")
        except Exception as overall_err:
            self.console.print(f"[red]Error in tool loading process:[/red] {str(overall_err)}")

        return tools

    def refresh_tools(self):
        """Refresh the available tools and display newly added tools, if any."""
        current_tool_names = {tool['name'] for tool in self.tools}
        self.tools = self._load_tools()
        new_tool_names = {tool['name'] for tool in self.tools}
        new_tools = new_tool_names - current_tool_names

        if new_tools:
            self.console.print("\n")
            for tool_name in new_tools:
                tool_info = next((t for t in self.tools if t['name'] == tool_name), None)
                if tool_info:
                    description_lines = tool_info['description'].strip().split('\n')
                    formatted_description = '\n    '.join(line.strip() for line in description_lines)
                    self.console.print(f"[bold green]NEW[/bold green] 🔧 [cyan]{tool_name}[/cyan]:\n    {formatted_description}")
        else:
            self.console.print("\n[yellow]No new tools found[/yellow]")

    def display_available_tools(self):
        """Display the list of currently available tools."""
        self.console.print("\n[bold cyan]Available tools:[/bold cyan]")
        tool_names = [tool['name'] for tool in self.tools]
        formatted_tools = ", ".join([f"🔧 [cyan]{name}[/cyan]" for name in tool_names]) if tool_names else "No tools available."
        self.console.print(formatted_tools)
        self.console.print("\n---")

    def _display_tool_usage(self, tool_name: str, input_data: Dict, result: str):
        """Display tool execution details if SHOW_TOOL_USAGE is enabled."""
        if not getattr(Config, 'SHOW_TOOL_USAGE', False):
            return
        
        tool_info = f"""[cyan]📥 Input:[/cyan] {json.dumps(input_data, indent=2)}
[cyan]📤 Result:[/cyan] {result}"""
        panel = Panel(
            tool_info,
            title=f"Tool used: {tool_name}",
            title_align="left",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)

    def _execute_tool(self, tool_use):
        """Execute a tool and return its result. Handles errors gracefully."""
        tool_name = tool_use.name
        tool_input = tool_use.input or {}
        tool_result = None

        try:
            module = importlib.import_module(f'tools.{tool_name}')
            tool_instance = None

            # Find the correct tool class
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseTool) and
                    obj != BaseTool):
                    candidate_tool = obj()
                    if candidate_tool.name == tool_name:
                        tool_instance = candidate_tool
                        break

            if not tool_instance:
                tool_result = f"Tool not found: {tool_name}"
            else:
                # Execute the tool method
                try:
                    result = tool_instance.execute(**tool_input)
                    tool_result = result.replace('[', '\\[').replace(']', '\\]')
                except Exception as exec_err:
                    tool_result = f"Error executing tool '{tool_name}': {str(exec_err)}"

        except ImportError:
            tool_result = f"Failed to import tool: {tool_name}"
        except Exception as e:
            tool_result = f"Error executing tool: {str(e)}"

        self._display_tool_usage(tool_name, tool_input, tool_result)
        return tool_result

    def _display_token_usage(self, usage):
        """Display token usage in a progress bar style, if usage data is available."""
        used_percentage = (self.total_tokens_used / Config.MAX_CONVERSATION_TOKENS) * 100
        remaining_tokens = max(0, Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used)

        self.console.print(f"\nTotal used: {self.total_tokens_used:,} / {Config.MAX_CONVERSATION_TOKENS:,}")

        bar_width = 40
        filled = int(used_percentage / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        color = "green"
        if used_percentage > 75:
            color = "yellow"
        if used_percentage > 90:
            color = "red"

        self.console.print(f"[{color}][{bar}] {used_percentage:.1f}%[/{color}]")

        if remaining_tokens < 20000:
            self.console.print(f"[bold red]Warning: Only {remaining_tokens:,} tokens remaining![/bold red]")

        self.console.print("---")

    def _count_tokens(self, messages, system_prompt=None):
        """
        Count tokens using Anthropic's token counting API.
        Fallback to rough estimation if the API call fails.
        """
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
            self.console.print(f"[yellow]Warning: Token counting API failed, using estimation.[/yellow]")
            # Rough estimation: half the character count of all messages combined
            total_chars = sum(len(str(m.get('content', ''))) for m in messages)
            return int(total_chars * 0.5)

    def chat(self, user_input: str):
        """Process user input and return assistant's response or handle special commands."""
        if user_input.lower() == 'refresh':
            self.refresh_tools()
            return "Tools refreshed successfully!"

        new_message = {"role": "user", "content": user_input}
        messages_to_check = self.conversation_history + [new_message]
        estimated_tokens = self._count_tokens(
            messages=messages_to_check,
            system_prompt=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
        )

        # Check token budget
        if (self.total_tokens_used + estimated_tokens) >= Config.MAX_CONVERSATION_TOKENS:
            self.console.print("\n[bold red]Token limit approaching! Please reset the conversation.[/bold red]")
            return "Token limit approaching! Please type 'reset' to start a new conversation."

        self.conversation_history.append(new_message)

        try:
            spinner_text = 'Thinking...' if self.thinking_enabled else ''
            spinner = Spinner('dots', text=spinner_text, style="cyan")

            while True:
                # Warn if close to token limit
                if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS * 0.9:
                    self.console.print("\n[bold yellow]Warning: Approaching token limit![/bold yellow]")

                with Live(spinner, refresh_per_second=10, transient=True):
                    # Attempt to create a message-based completion
                    response = self.client.messages.create(
                        model=Config.MODEL,
                        max_tokens=min(
                            Config.MAX_TOKENS,
                            Config.MAX_CONVERSATION_TOKENS - self.total_tokens_used
                        ),
                        temperature=self.temperature,
                        tools=self.tools,
                        messages=self.conversation_history,
                        system=f"{SystemPrompts.DEFAULT}\n\n{SystemPrompts.TOOL_USAGE}"
                    )

                    # Update token usage if available
                    if hasattr(response, 'usage') and response.usage:
                        message_tokens = response.usage.input_tokens + response.usage.output_tokens
                    else:
                        # If usage is not provided, fallback to estimation
                        message_tokens = estimated_tokens

                    self.total_tokens_used += message_tokens
                    self._display_token_usage(response.usage if hasattr(response, 'usage') else None)

                    # Check token limit again
                    if self.total_tokens_used >= Config.MAX_CONVERSATION_TOKENS:
                        self.console.print("\n[bold red]Token limit reached! Please reset the conversation.[/bold red]")
                        return "Token limit reached! Please type 'reset' to start a new conversation."

                # Handle tool usage or finalize response
                if response.stop_reason == "tool_use":
                    self.console.print("\n[bold yellow]🛠  Handling Tool Use...[/bold yellow]\n")

                    tool_results = []
                    # response.content should be a structured set of messages indicating which tool to use
                    if getattr(response, 'content', None) and isinstance(response.content, list):
                        for content_block in response.content:
                            if content_block.type == "tool_use":
                                result = self._execute_tool(content_block)
                                tool_results.append({
                                    "type": "tool_result",
                                    "tool_use_id": content_block.id,
                                    "content": result
                                })

                        # Add the intermediate tool usage messages to the conversation history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        self.conversation_history.append({
                            "role": "user",
                            "content": tool_results
                        })
                        # Continue loop to process the next step after tool results
                        continue
                    else:
                        # If no content to process, break to avoid infinite loop
                        self.console.print("[red]No tool content received despite 'tool_use' stop reason.[/red]")
                        break
                else:
                    # Final response
                    if getattr(response, 'content', None) and isinstance(response.content, list) and response.content:
                        final_content = response.content[0].text
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": response.content
                        })
                        # Escape Rich markup
                        return final_content.replace('[', '\\[').replace(']', '\\]')
                    else:
                        self.console.print("[red]No content in final response.[/red]")
                        return "No response content available."

        except Exception as e:
            return f"Error: {str(e)}"

    def reset(self):
        """Reset the assistant's conversation history and token count."""
        self.conversation_history = []
        self.total_tokens_used = 0
        self.console.print("\n[bold green]🔄 Assistant memory has been reset![/bold green]")

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
    style = Style.from_dict({'prompt': 'orange'})

    try:
        assistant = Assistant()
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print("Please ensure ANTHROPIC_API_KEY is set correctly.")
        return

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
            user_input = prompt("You: ", style=style).strip()

            if user_input.lower() == 'quit':
                console.print("\n[bold blue]👋 Goodbye![/bold blue]")
                break
            elif user_input.lower() == 'reset':
                assistant.reset()
                continue

            response = assistant.chat(user_input)
            console.print("\n[bold purple]Claude Engineer:[/bold purple]")
            if isinstance(response, str):
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
