import os
from dotenv import load_dotenv
import json
from tavily import TavilyClient
import base64
from PIL import Image
import io
import re
from anthropic import Anthropic, APIStatusError, APIError
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageToolCall
import difflib
import time
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
import asyncio
import aiohttp
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import datetime
import venv
import sys
import signal
import logging
from typing import Tuple, Optional
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from aiohttp import ClientSession
from aiohttp_sse_client import client as sse_client

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.styles import Style

def select_ai_provider():
    console = Console()
    console.print(Panel("Seleccione el proveedor de IA:", title="Selección de Proveedor", expand=False))
    console.print("[1] Anthropic")
    console.print("[2] Open Router")
    
    while True:
        choice = console.input("Ingrese el número de su elección (1 o 2): ")
        if choice == "1":
            return "anthropic"
        elif choice == "2":
            return "open_router"
        else:
            console.print("Opción inválida. Por favor, ingrese 1 o 2.", style="bold red")

def select_model(ai_provider):
    if ai_provider == 'anthropic':
        anthropic_models = ['claude-3-5-sonnet-20240620', 'claude-3-opus-20240229']
        completer = WordCompleter(anthropic_models, ignore_case=True)
        while True:
            choice = prompt(
                "Select Anthropic model (or enter your own): ",
                completer=completer,
                complete_while_typing=True
            ).strip()
            if choice in anthropic_models or choice:
                return choice
            print("Please enter a valid model name.")
    else:
        openrouter_models = ['openai/gpt-4o-mini', 'anthropic/claude-3-sonnet', 'meta-llama/llama-2-70b-chat', 'openai/gpt-3.5-turbo']
        completer = WordCompleter(openrouter_models, ignore_case=True)
        while True:
            choice = prompt(
                "Select Open Router model (or enter your own): ",
                completer=completer,
                complete_while_typing=True
            ).strip()
            if choice in openrouter_models or choice:
                return choice
            print("Please enter a valid model name.")

AI_PROVIDER = select_ai_provider()
SELECTED_MODEL = select_model(AI_PROVIDER)


def setup_virtual_environment() -> Tuple[str, str]:
    venv_name = "code_execution_env"
    venv_path = os.path.join(os.getcwd(), venv_name)
    assistant_response = ""
    tool_uses = []
    
    try:
        if not os.path.exists(venv_path):
            venv.create(venv_path, with_pip=True)
        
        # Activate the virtual environment
        if sys.platform == "win32":
            activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
        else:
            activate_script = os.path.join(venv_path, "bin", "activate")
        
        return venv_path, activate_script
    except Exception as e:
        logging.error(f"Error setting up virtual environment: {str(e)}")
        raise


# Load environment variables from .env file
load_dotenv()

# Initialize the AI client
if AI_PROVIDER == 'anthropic':
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    client = Anthropic(api_key=anthropic_api_key)
else:
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY not found in environment variables")
    client = OpenAI(api_key=openrouter_api_key, base_url="https://openrouter.ai/api/v1")

# Function to get the appropriate model name
def get_model_name():
    if AI_PROVIDER == 'anthropic':
        return SELECTED_MODEL
    else:
        return f"{SELECTED_MODEL}"

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()


# Token tracking variables
main_model_tokens = {'input': 0, 'output': 0}
tool_checker_tokens = {'input': 0, 'output': 0}
code_editor_tokens = {'input': 0, 'output': 0}
code_execution_tokens = {'input': 0, 'output': 0}

# Set up the conversation memory (maintains context for MAINMODEL)
conversation_history = []

# Store file contents (part of the context for MAINMODEL)
file_contents = {}

# Code editor memory (maintains some context for CODEEDITORMODEL between calls)
code_editor_memory = []

# automode flag
automode = False

# Store file contents
file_contents = {}

# Global dictionary to store running processes
running_processes = {}

# Constants
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25
MAX_CONTEXT_TOKENS = 200000  # Reduced to 200k tokens for context window

# Models
# Models that maintain context memory across interactions
MAINMODEL = "claude-3-5-sonnet-20240620"  # Maintains conversation history and file contents
OPENROUTER_MAINMODEL = "anthropic/claude-3-sonnet"  # Maintains conversation history and file contents

# Models that don't maintain context (memory is reset after each call)
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"
CODEEDITORMODEL = "claude-3-5-sonnet-20240620"
CODEEXECUTIONMODEL = "claude-3-haiku-20240307"

# System prompts
BASE_SYSTEM_PROMPT = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model, specialized in software development with access to a variety of tools and the ability to instruct and direct a coding agent and a code execution one. Your capabilities include:

1. Creating and managing project structures
2. Writing, debugging, and improving code across multiple languages
3. Providing architectural insights and applying design patterns
4. Staying current with the latest technologies and best practices
5. Analyzing and manipulating files within the project directory
6. Performing web searches for up-to-date information
7. Executing code and analyzing its output within an isolated 'code_execution_env' virtual environment
8. Managing and stopping running processes started within the 'code_execution_env'

Available tools and their optimal use cases:

1. create_folder: Create new directories in the project structure.
2. create_file: Generate new files with specified content. Strive to make the file as complete and useful as possible.
3. edit_and_apply: Examine and modify existing files by instructing a separate AI coding agent. You are responsible for providing clear, detailed instructions to this agent. When using this tool:
   - Provide comprehensive context about the project, including recent changes, new variables or functions, and how files are interconnected.
   - Clearly state the specific changes or improvements needed, explaining the reasoning behind each modification.
   - Include ALL the snippets of code to change, along with the desired modifications.
   - Specify coding standards, naming conventions, or architectural patterns to be followed.
   - Anticipate potential issues or conflicts that might arise from the changes and provide guidance on how to handle them.
4. execute_code: Run Python code exclusively in the 'code_execution_env' virtual environment and analyze its output. Use this when you need to test code functionality or diagnose issues. Remember that all code execution happens in this isolated environment. This tool now returns a process ID for long-running processes.
5. stop_process: Stop a running process by its ID. Use this when you need to terminate a long-running process started by the execute_code tool.
6. execute_code: Run Python code exclusively in the 'code_execution_env' virtual environment and analyze its output.
7. stop_process: Stop a running process by its ID.
8. read_file: Read the contents of an existing file.
9. list_files: List all files and directories in a specified folder.
10. tavily_search: Perform a web search using the Tavily API for up-to-date information.

Tool Usage Guidelines:
- Always use the most appropriate tool for the task at hand.
- Provide detailed and clear instructions when using tools, especially for edit_and_apply.
- After making changes, always review the output to ensure accuracy and alignment with intentions.
- Use execute_code to run and test code within the 'code_execution_env' virtual environment, then analyze the results.
- For long-running processes, use the process ID returned by execute_code to stop them later if needed.
- Proactively use tavily_search when you need up-to-date information or additional context.

Error Handling and Recovery:
- If a tool operation fails, carefully analyze the error message and attempt to resolve the issue.
- For file-related errors, double-check file paths and permissions before retrying.
- If a search fails, try rephrasing the query or breaking it into smaller, more specific searches.
- If code execution fails, analyze the error output and suggest potential fixes, considering the isolated nature of the environment.
- If a process fails to stop, consider potential reasons and suggest alternative approaches.

Project Creation and Management:
1. Start by creating a root folder for new projects.
2. Create necessary subdirectories and files within the root folder.
3. Organize the project structure logically, following best practices for the specific project type.

Always strive for accuracy, clarity, and efficiency in your responses and actions. Your instructions must be precise and comprehensive. If uncertain, use the tavily_search tool or admit your limitations. When executing code, always remember that it runs in the isolated 'code_execution_env' virtual environment. Be aware of any long-running processes you start and manage them appropriately, including stopping them when they are no longer needed.

When using tools:
1. Carefully consider if a tool is necessary before using it.
2. Ensure all required parameters are provided and valid.
3. Handle both successful results and errors gracefully.
4. Provide clear explanations of tool usage and results to the user.

Remember, you are an AI assistant, and your primary goal is to help the user accomplish their tasks effectively and efficiently while maintaining the integrity and security of their development environment.
"""

AUTOMODE_SYSTEM_PROMPT = """
You are currently in automode. Follow these guidelines:

1. Goal Setting:
   - Set clear, achievable goals based on the user's request.
   - Break down complex tasks into smaller, manageable goals.

2. Goal Execution:
   - Work through goals systematically, using appropriate tools for each task.
   - Utilize file operations, code writing, and web searches as needed.
   - Always read a file before editing and review changes after editing.

3. Progress Tracking:
   - Provide regular updates on goal completion and overall progress.
   - Use the iteration information to pace your work effectively.

4. Tool Usage:
   - Leverage all available tools to accomplish your goals efficiently.
   - Prefer edit_and_apply for file modifications, applying changes in chunks for large edits.
   - Use tavily_search proactively for up-to-date information.

5. Error Handling:
   - If a tool operation fails, analyze the error and attempt to resolve the issue.
   - For persistent errors, consider alternative approaches to achieve the goal.

6. Automode Completion:
   - When all goals are completed, respond with "AUTOMODE_COMPLETE" to exit automode.
   - Do not ask for additional tasks or modifications once goals are achieved.

7. Iteration Awareness:
   - You have access to this {iteration_info}.
   - Use this information to prioritize tasks and manage time effectively.

Remember: Focus on completing the established goals efficiently and effectively. Avoid unnecessary conversations or requests for additional tasks.
"""


def update_system_prompt(current_iteration: Optional[int] = None, max_iterations: Optional[int] = None) -> str:
    global file_contents, console
    chain_of_thought_prompt = """
    Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

    Do not reflect on the quality of the returned search results in your response.
    """
    
    file_contents_prompt = "\n\nFile Contents:\n"
    for path, content in file_contents.items():
        file_contents_prompt += f"\n--- {path} ---\n{content}\n"
    
    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + AUTOMODE_SYSTEM_PROMPT.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt
    else:
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + chain_of_thought_prompt

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"

def create_file(path, content=""):
    global file_contents
    try:
        with open(path, 'w') as f:
            f.write(content)
        file_contents[path] = content
        console.print(Panel(f"File '{path}' created successfully.", title="File Created", style="green"))
        return f"File created and added to system prompt: {path}"
    except Exception as e:
        console.print(Panel(f"Error creating file '{path}': {str(e)}", title="Error", style="bold red"))
        return f"Error creating file '{path}': {str(e)}"

def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)

def generate_and_apply_diff(original_content, new_content, path):
    diff = list(difflib.unified_diff(
        original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    if not diff:
        return "No changes detected."

    try:
        with open(path, 'w') as f:
            f.writelines(new_content)

        diff_text = ''.join(diff)
        highlighted_diff = highlight_diff(diff_text)

        diff_panel = Panel(
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="cyan"
        )

        console.print(diff_panel)

        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        summary = f"Changes applied to {path}:\n"
        summary += f"  Lines added: {added_lines}\n"
        summary += f"  Lines removed: {removed_lines}\n"

        return summary

    except Exception as e:
        error_panel = Panel(
            f"Error: {str(e)}",
            title="Error Applying Changes",
            style="bold red"
        )
        console.print(error_panel)
        return f"Error applying changes: {str(e)}"


async def generate_edit_instructions(file_content, instructions, project_context, full_file_contents):
    global code_editor_tokens, code_editor_memory
    try:
        # Prepare memory context (this is the only part that maintains some context between calls)
        memory_context = "\n".join([f"Memory {i+1}:\n{mem}" for i, mem in enumerate(code_editor_memory)])

        # Prepare full file contents context
        full_file_contents_context = "\n\n".join([f"--- {path} ---\n{content}" for path, content in full_file_contents.items()])

        system_prompt = f"""
        You are an AI coding agent that generates edit instructions for code files. Your task is to analyze the provided code and generate SEARCH/REPLACE blocks for necessary changes. Follow these steps:

        1. Review the entire file content to understand the context:
        {file_content}

        2. Carefully analyze the specific instructions:
        {instructions}

        3. Take into account the overall project context:
        {project_context}

        4. Consider the memory of previous edits:
        {memory_context}

        5. Consider the full context of all files in the project:
        {full_file_contents_context}

        6. Generate SEARCH/REPLACE blocks for each necessary change. Each block should:
           - Include enough context to uniquely identify the code to be changed
           - Provide the exact replacement code, maintaining correct indentation and formatting
           - Focus on specific, targeted changes rather than large, sweeping modifications

        7. Ensure that your SEARCH/REPLACE blocks:
           - Address all relevant aspects of the instructions
           - Maintain or enhance code readability and efficiency
           - Consider the overall structure and purpose of the code
           - Follow best practices and coding standards for the language
           - Maintain consistency with the project context and previous edits
           - Take into account the full context of all files in the project

        8. For each SEARCH/REPLACE block, provide a brief explanation of the change and its purpose.

        IMPORTANT: USE THE FOLLOWING FORMAT FOR EACH BLOCK:

        <EXPLANATION>
        Brief explanation of the change and its purpose
        </EXPLANATION>
        <SEARCH>
        Code to be replaced
        </SEARCH>
        <REPLACE>
        New code to insert
        </REPLACE>

        If no changes are needed, return an empty list.
        """

        # Make the API call to CODEEDITORMODEL (context is not maintained except for code_editor_memory)
        response = client.chat.completions.create(
            model=CODEEDITORMODEL,
            max_tokens=8000,
            system=system_prompt,
            extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
            messages=[
                {"role": "user", "content": "Generate SEARCH/REPLACE blocks with explanations for the necessary changes."},
            ]
        )
        # Update token usage for code editor
        code_editor_tokens['input'] += response.usage.input_tokens
        code_editor_tokens['output'] += response.usage.output_tokens

        # Parse the response to extract SEARCH/REPLACE blocks with explanations
        edit_instructions = parse_search_replace_blocks_with_explanations(response.content[0].text)

        # Update code editor memory (this is the only part that maintains some context between calls)
        code_editor_memory.append(f"Edit Instructions:\n{response.content[0].text}")

        return edit_instructions

    except Exception as e:
        console.print(f"Error in generating edit instructions: {str(e)}", style="bold red")
        return []  # Return empty list if any exception occurs



def parse_search_replace_blocks_with_explanations(response_text):
    blocks = []
    lines = response_text.split('\n')
    current_block = {}
    current_section = None

    for line in lines:
        if line.strip() == '<EXPLANATION>':
            current_section = 'explanation'
            current_block['explanation'] = []
        elif line.strip() == '</EXPLANATION>':
            current_section = None
        elif line.strip() == '<SEARCH>':
            current_section = 'search'
            current_block['search'] = []
        elif line.strip() == '</SEARCH>':
            current_section = None
        elif line.strip() == '<REPLACE>':
            current_section = 'replace'
            current_block['replace'] = []
        elif line.strip() == '</REPLACE>':
            current_section = None
            if 'explanation' in current_block and 'search' in current_block and 'replace' in current_block:
                blocks.append({
                    'explanation': '\n'.join(current_block['explanation']),
                    'search': '\n'.join(current_block['search']),
                    'replace': '\n'.join(current_block['replace'])
                })
            current_block = {}
        elif current_section:
            current_block[current_section].append(line)

    return blocks





async def apply_edits(file_path, edit_instructions, original_content):
    changes_made = False
    edited_content = original_content
    total_edits = len(edit_instructions)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        edit_task = progress.add_task("[cyan]Applying edits...", total=total_edits)

        for i, edit in enumerate(edit_instructions, 1):
            search_content = edit['search']
            replace_content = edit['replace']
            
            if search_content in edited_content:
                edited_content = edited_content.replace(search_content, replace_content)
                changes_made = True
                
                # Display the diff for this edit
                diff_result = generate_and_apply_diff(search_content, replace_content, file_path)
                console.print(Panel(diff_result, title=f"Changes in {file_path} ({i}/{total_edits})", style="cyan"))

            progress.update(edit_task, advance=1)

    return edited_content, changes_made

async def execute_code(code, timeout=10):
    global running_processes
    venv_path, activate_script = setup_virtual_environment()
    
    # Generate a unique identifier for this process
    process_id = f"process_{len(running_processes)}"
    
    # Write the code to a temporary file
    with open(f"{process_id}.py", "w") as f:
        f.write(code)
    
    # Prepare the command to run the code
    if sys.platform == "win32":
        command = f'"{activate_script}" && python3 {process_id}.py'
    else:
        command = f'source "{activate_script}" && python3 {process_id}.py'
    
    # Create a process to run the command
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        shell=True,
        preexec_fn=None if sys.platform == "win32" else os.setsid
    )
    
    # Store the process in our global dictionary
    running_processes[process_id] = process
    
    try:
        # Wait for initial output or timeout
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        stdout = stdout.decode()
        stderr = stderr.decode()
        return_code = process.returncode
    except asyncio.TimeoutError:
        # If we timeout, it means the process is still running
        stdout = "Process started and running in the background."
        stderr = ""
        return_code = "Running"
    
    execution_result = f"Process ID: {process_id}\n\nStdout:\n{stdout}\n\nStderr:\n{stderr}\n\nReturn Code: {return_code}"
    return process_id, execution_result

def read_file(path):
    global file_contents
    try:
        with open(path, 'r') as f:
            content = f.read()
        file_contents[path] = content
        console.print(Panel(f"File '{path}' has been read successfully and stored in the system prompt.", title="File Read", style="green"))
        return content
    except FileNotFoundError:
        console.print(Panel(f"File '{path}' not found.", title="Error", style="bold red"))
        return f"File '{path}' not found."
    except Exception as e:
        console.print(Panel(f"Error reading file '{path}': {str(e)}", title="Error", style="bold red"))
        return f"Error reading file '{path}': {str(e)}"

def list_files(path="."):
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"

def tavily_search(query):
    try:
        response = tavily.qna_search(query=query, search_depth="advanced")
        return response
    except Exception as e:
        return f"Error performing search: {str(e)}"

def stop_process(process_id):
    global running_processes
    if process_id in running_processes:
        process = running_processes[process_id]
        if sys.platform == "win32":
            process.terminate()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        del running_processes[process_id]
        return f"Process {process_id} has been stopped."
    else:
        return f"No running process found with ID {process_id}."


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

tools = [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. This tool should be used when you need to create a new directory in the project structure. It will create all necessary parent directories if they don't exist. The tool will return a success message if the folder is created or already exists, and an error message if there's a problem creating the folder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path where the folder should be created. Use forward slashes (/) for path separation, even on Windows systems."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with the given content. This tool should be used when you need to create a new file in the project structure. It will create all necessary parent directories if they don't exist. The tool will return a success message if the file is created, and an error message if there's a problem creating the file or if the file already exists. The content should be as complete and useful as possible, including necessary imports, function definitions, and comments.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path where the file should be created. Use forward slashes (/) for path separation, even on Windows systems."
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file. This should include all necessary code, comments, and formatting."
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_and_apply",
        "description": "Apply AI-powered improvements to a file based on specific instructions and detailed project context. This function reads the file, processes it in batches using AI with conversation history and comprehensive code-related project context. It generates a diff and allows the user to confirm changes before applying them. The goal is to maintain consistency and prevent breaking connections between files. This tool should be used for complex code modifications that require understanding of the broader project context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path of the file to edit. Use forward slashes (/) for path separation, even on Windows systems."
                },
                "instructions": {
                    "type": "string",
                    "description": "After completing the code review, construct a plan for the change between <PLANNING> tags. Ask for additional source files or documentation that may be relevant. The plan should avoid duplication (DRY principle), and balance maintenance and flexibility. Present trade-offs and implementation choices at this step. Consider available Frameworks and Libraries and suggest their use when relevant. STOP at this step if we have not agreed a plan.\n\nOnce agreed, produce code between <OUTPUT> tags. Pay attention to Variable Names, Identifiers and String Literals, and check that they are reproduced accurately from the original source files unless otherwise directed. When naming by convention surround in double colons and in ::UPPERCASE::. Maintain existing code style, use language appropriate idioms. Produce Code Blocks with the language specified after the first backticks"
                },
                "project_context": {
                    "type": "string",
                    "description": "Comprehensive context about the project, including recent changes, new variables or functions, interconnections between files, coding standards, and any other relevant information that might affect the edit."
                }
            },
            "required": ["path", "instructions", "project_context"]
        }
    },
    {
        "name": "execute_code",
        "description": "Execute Python code in the 'code_execution_env' virtual environment and return the output. This tool should be used when you need to run code and see its output or check for errors. All code execution happens exclusively in this isolated environment. The tool will return the standard output, standard error, and return code of the executed code. Long-running processes will return a process ID for later management.",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Python code to execute in the 'code_execution_env' virtual environment. Include all necessary imports and ensure the code is complete and self-contained."
                }
            },
            "required": ["code"]
        }
    },
    {
        "name": "stop_process",
        "description": "Stop a running process by its ID. This tool should be used to terminate long-running processes that were started by the execute_code tool. It will attempt to stop the process gracefully, but may force termination if necessary. The tool will return a success message if the process is stopped, and an error message if the process doesn't exist or can't be stopped.",
        "input_schema": {
            "type": "object",
            "properties": {
                "process_id": {
                    "type": "string",
                    "description": "The ID of the process to stop, as returned by the execute_code tool for long-running processes."
                }
            },
            "required": ["process_id"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. This tool should be used when you need to examine the contents of an existing file. It will return the entire contents of the file as a string. If the file doesn't exist or can't be read, an appropriate error message will be returned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path of the file to read. Use forward slashes (/) for path separation, even on Windows systems."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. This tool should be used when you need to see the contents of a directory. It will return a list of all files and subdirectories in the specified path. If the directory doesn't exist or can't be read, an appropriate error message will be returned.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The absolute or relative path of the folder to list. Use forward slashes (/) for path separation, even on Windows systems. If not provided, the current working directory will be used."
                }
            }
        }
    },
    {
        "name": "tavily_search",
        "description": "Perform a web search using the Tavily API to get up-to-date information or additional context. This tool should be used when you need current information or feel a search could provide a better answer to the user's query. It will return a summary of the search results, including relevant snippets and source URLs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be as specific and detailed as possible to get the most relevant results."
                }
            },
            "required": ["query"]
        }
    }
]

from typing import Dict, Any

async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = None
        is_error = False

        if tool_name == "create_folder":
            result = create_folder(tool_input["path"])
        elif tool_name == "create_file":
            result = create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "edit_and_apply":
            result = await edit_and_apply(
                tool_input["path"],
                tool_input["instructions"],
                tool_input["project_context"],
                is_automode=automode,
                timeout=30
            )
        elif tool_name == "read_file":
            result = read_file(tool_input["path"])
        elif tool_name == "list_files":
            result = list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            result = tavily_search(tool_input["query"])
        elif tool_name == "stop_process":
            result = stop_process(tool_input["process_id"])
        elif tool_name == "execute_code":
            process_id, execution_result = await execute_code(tool_input["code"])
            analysis = await send_to_ai_for_executing(tool_input["code"], execution_result)
            result = f"{execution_result}\n\nAnalysis:\n{analysis}"
            if process_id in running_processes:
                result += "\n\nNote: The process is still running in the background."
        else:
            is_error = True
            result = f"Unknown tool: {tool_name}"

        # Ensure result is always a string
        if result is None:
            result = "Operation completed successfully, but no output was returned."

        if is_error:
            console.print(Panel(str(result), title=f"Error Executing Tool: {tool_name}", style="bold red"))
        else:
            console.print(Panel(str(result), title=f"Tool Execution Result: {tool_name}", style="green"))

        return {
            "content": str(result),
            "is_error": is_error
        }
    except KeyError as e:
        error_msg = f"Missing required parameter {str(e)} for tool {tool_name}"
        logging.error(error_msg)
        console.print(Panel(error_msg, title="Tool Execution Error", style="bold red"))
        return {
            "content": error_msg,
            "is_error": True
        }
    except Exception as e:
        error_msg = f"Error executing tool {tool_name}: {str(e)}"
        logging.error(error_msg)
        console.print(Panel(error_msg, title="Tool Execution Error", style="bold red"))
        return {
            "content": error_msg,
            "is_error": True
        }

    # Add a delay to prevent the system from getting stuck
    await asyncio.sleep(0.1)

    # Add a delay to prevent the system from getting stuck
    await asyncio.sleep(0.1)

    # Add a delay to prevent the system from getting stuck
    await asyncio.sleep(0.1)

    # Add a delay to prevent the system from getting stuck
    await asyncio.sleep(0.1)

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            max_size = (1024, 1024)
            img.thumbnail(max_size, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def parse_goals(response):
    goals = re.findall(r'Goal \d+: (.+)', response)
    return goals

def execute_goals(goals):
    global automode
    for i, goal in enumerate(goals, 1):
        console.print(Panel(f"Executing Goal {i}: {goal}", title="Goal Execution", style="bold yellow"))
        response, _ = chat_with_claude(f"Continue working on goal: {goal}")
        if CONTINUATION_EXIT_PHRASE in response:
            automode = False
            console.print(Panel("Exiting automode.", title="Automode", style="bold green"))
            break


async def send_to_ai_for_executing(code, execution_result):
    global code_execution_tokens

    try:
        system_prompt = f"""
        You are an AI code execution agent. Your task is to analyze the provided code and its execution result from the 'code_execution_env' virtual environment, then provide a concise summary of what worked, what didn't work, and any important observations. Follow these steps:

        1. Review the code that was executed in the 'code_execution_env' virtual environment:
        {code}

        2. Analyze the execution result from the 'code_execution_env' virtual environment:
        {execution_result}

        3. Provide a brief summary of:
           - What parts of the code executed successfully in the virtual environment
           - Any errors or unexpected behavior encountered in the virtual environment
           - Potential improvements or fixes for issues, considering the isolated nature of the environment
           - Any important observations about the code's performance or output within the virtual environment
           - If the execution timed out, explain what this might mean (e.g., long-running process, infinite loop)

        Be concise and focus on the most important aspects of the code execution within the 'code_execution_env' virtual environment.

        IMPORTANT: PROVIDE ONLY YOUR ANALYSIS AND OBSERVATIONS. DO NOT INCLUDE ANY PREFACING STATEMENTS OR EXPLANATIONS OF YOUR ROLE.
        """

        response = client.messages.create(
            model=CODEEXECUTIONMODEL,
            max_tokens=2000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Analyze this code execution from the 'code_execution_env' virtual environment:\n\nCode:\n{code}\n\nExecution Result:\n{execution_result}"}
            ]
        )

        # Update token usage for code execution
        code_execution_tokens['input'] += response.usage.input_tokens
        code_execution_tokens['output'] += response.usage.output_tokens

        analysis = response.content[0].text

        return analysis

    except Exception as e:
        console.print(f"Error in AI code execution analysis: {str(e)}", style="bold red")
        return f"Error analyzing code execution from 'code_execution_env': {str(e)}"


def save_chat():
    # Generate filename
    now = datetime.datetime.now()
    filename = f"Chat_{now.strftime('%H%M')}.md"
    
    # Format conversation history
    formatted_chat = "# Claude-3-Sonnet Engineer Chat Log\n\n"
    for message in conversation_history:
        if message['role'] == 'user':
            formatted_chat += f"## User\n\n{message['content']}\n\n"
        elif message['role'] == 'assistant':
            if isinstance(message['content'], str):
                formatted_chat += f"## Claude\n\n{message['content']}\n\n"
            elif isinstance(message['content'], list):
                for content in message['content']:
                    if content['type'] == 'tool_use':
                        formatted_chat += f"### Tool Use: {content['name']}\n\n```json\n{json.dumps(content['input'], indent=2)}\n```\n\n"
                    elif content['type'] == 'text':
                        formatted_chat += f"## Claude\n\n{content['text']}\n\n"
        elif message['role'] == 'user' and isinstance(message['content'], list):
            for content in message['content']:
                if content['type'] == 'tool_result':
                    formatted_chat += f"### Tool Result\n\n```\n{content['content']}\n```\n\n"
    
    # Save to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(formatted_chat)
    
    return filename



async def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None, retry=False):
    global conversation_history, automode, main_model_tokens

    # This function uses the selected model, which maintains context across calls
    current_conversation = []

    if image_path:
        console.print(Panel(f"Processing image at path: {image_path}", title_align="left", title="Image Processing", expand=False, style="yellow"))
        image_base64 = encode_image_to_base64(image_path)

        if image_base64.startswith("Error"):
            console.print(Panel(f"Error encoding image: {image_base64}", title="Error", style="bold red"))
            return "I'm sorry, there was an error processing the image. Please try again.", False

        if AI_PROVIDER == 'anthropic':
            image_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    },
                    {
                        "type": "text",
                        "text": f"User input for image: {user_input}"
                    }
                ]
            }
        else:
            image_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": f"User input for image: {user_input}"
                    }
                ]
            }
        current_conversation.append(image_message)
        console.print(Panel("Image message added to conversation history", title_align="left", title="Image Added", style="green"))
    else:
        current_conversation.append({"role": "user", "content": user_input})

    # Filter conversation history to maintain context
    filtered_conversation_history = []
    for message in conversation_history:
        if isinstance(message['content'], list):
            filtered_content = [
                content for content in message['content']
                if content.get('type') != 'tool_result' or (
                    content.get('type') == 'tool_result' and
                    not any(keyword in content.get('content', '') for keyword in [
                        "File contents updated in system prompt",
                        "File created and added to system prompt",
                        "has been read and stored in the system prompt"
                    ])
                )
            ]
            if filtered_content:
                filtered_conversation_history.append({**message, 'content': filtered_content})
        else:
            filtered_conversation_history.append(message)

    # Combine filtered history with current conversation to maintain context
    messages = filtered_conversation_history + current_conversation

    assistant_response = ""
    exit_continuation = False
    tool_uses = []

    try:
        model = get_model_name()
        if AI_PROVIDER == 'anthropic':
            # Anthropic API call
            response = client.chat.completions.create(
                model=model,
                max_tokens=8000,
                system=update_system_prompt(current_iteration, max_iterations),
                extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )
            # Update token usage for MAINMODEL (only for Anthropic)
            main_model_tokens['input'] += response.usage.input_tokens
            main_model_tokens['output'] += response.usage.output_tokens
            
            for content_block in response.content:
                if content_block.type == "text":
                    assistant_response += content_block.text
                    if CONTINUATION_EXIT_PHRASE in content_block.text:
                        exit_continuation = True
                elif content_block.type == "tool_use":
                    tool_uses.append(content_block)
        else:
            # OpenAI call for Open Router
            if retry:
                # Simplify the prompt for retry
                simplified_messages = [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": user_input}]
                response = client.chat.completions.create(
                    model=model,
                    messages=simplified_messages,
                    max_tokens=150  # Limit the response length
                )
            else:
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": update_system_prompt(current_iteration, max_iterations)}] + messages,
                        tools=get_openai_tools(tools),
                        tool_choice="auto"
                    )
                except Exception as e:
                    console.print(Panel(f"Error: {str(e)}", title="API Error", style="bold red"))
                    console.print(Panel("Retrying the request with a simplified prompt...", title="Retry", style="yellow"))
                    simplified_messages = [{"role": "system", "content": "You are a helpful AI assistant."}, {"role": "user", "content": user_input}]
                    response = client.chat.completions.create(
                        model=model,
                        messages=simplified_messages,
                        max_tokens=150  # Limit the response length
                    )
            
            console.print(Panel(f"Debug: Full Open Router response:\n{response}", title="Open Router Response", style="dim"))
            
            if hasattr(response, 'error'):
                error_msg = f"Open Router API Error: {response.error.get('message', 'Unknown error')}"
                console.print(Panel(error_msg, title="API Error", style="bold red"))
                if "The model produced invalid content" in error_msg:
                    console.print(Panel("Retrying the request with a simplified prompt...", title="Retry", style="yellow"))
                    return await chat_with_claude(user_input, image_path, current_iteration, max_iterations, retry=True)
                return f"Lo siento, hubo un error al procesar la respuesta de la API: {error_msg}. Por favor, intenta de nuevo.", False
            
            if response.choices:
                choice = response.choices[0]
                if hasattr(choice, 'message'):
                    assistant_response = choice.message.content or ""
                    if CONTINUATION_EXIT_PHRASE in assistant_response:
                        exit_continuation = True
                    
                    # Check if the response is a JSON string (DeepSeek Coder format)
                    if assistant_response.strip().startswith('```json'):
                        try:
                            json_content = json.loads(assistant_response.strip().split('```json')[1].strip().split('```')[0])
                            if 'function' in json_content:
                                tool_uses = [{
                                    'function': {
                                        'name': json_content['function'],
                                        'arguments': json.dumps(json_content.get('parameters', {}))
                                    }
                                }]
                                # Set assistant_response to an empty string as we've extracted the function call
                                assistant_response = ""
                            else:
                                tool_uses = []
                        except json.JSONDecodeError:
                            console.print(Panel("Error decoding JSON response from DeepSeek Coder", title="JSON Error", style="bold red"))
                            tool_uses = []
                    elif hasattr(choice.message, 'tool_calls') and choice.message.tool_calls:
                        tool_uses = []
                        for tool_call in choice.message.tool_calls:
                            if isinstance(tool_call, ChatCompletionMessageToolCall):
                                tool_uses.append({
                                    'function': {
                                        'name': tool_call.function.name,
                                        'arguments': tool_call.function.arguments
                                    }
                                })
                    else:
                        tool_uses = []  # Ensure tool_uses is always a list, even if empty
                else:
                    error_msg = f"Error: Response does not contain a message. Response structure: {choice}"
                    console.print(Panel(error_msg, title="API Error", style="bold red"))
                    return f"Lo siento, hubo un error al procesar la respuesta de la API: {error_msg}. Por favor, intenta de nuevo.", False
            else:
                error_msg = f"Error: Received an unexpected response format from Open Router. Response structure: {response}"
                console.print(Panel(error_msg, title="API Error", style="bold red"))
                return f"Lo siento, hubo un error al procesar la respuesta de la API: {error_msg}. Por favor, intenta de nuevo.", False
    except (APIStatusError, APIError) as e:
        if isinstance(e, APIStatusError) and e.status_code == 429:
            console.print(Panel("Rate limit exceeded. Retrying after a short delay...", title="API Error", style="bold yellow"))
            time.sleep(5)
            return await chat_with_claude(user_input, image_path, current_iteration, max_iterations)
        else:
            retry_count = 0
            while retry_count < 3:
                console.print(Panel(f"API Error: {str(e)}. Retrying after a short delay...", title="API Error", style="bold yellow"))
                time.sleep(5)
                try:
                    return await chat_with_claude(user_input, image_path, current_iteration, max_iterations)
                except (APIStatusError, APIError) as e:
                    retry_count += 1
            console.print(Panel(f"API Error: {str(e)}. Max retries reached. Please try again later.", title="API Error", style="bold red"))
            return "Lo siento, hubo un error al comunicarse con la IA. Por favor, intenta de nuevo.", False

    console.print(Panel(Markdown(assistant_response), title="AI's Response", title_align="left", border_style="blue", expand=False))

    # Display files in context
    if file_contents:
        files_in_context = "\n".join(file_contents.keys())
    else:
        files_in_context = "No files in context. Read, create, or edit files to add."
    console.print(Panel(files_in_context, title="Files in Context", title_align="left", border_style="white", expand=False))

    if tool_uses:
        for tool_use in tool_uses:
            if AI_PROVIDER == 'anthropic':
                tool_name = tool_use.name
                tool_input = tool_use.input
                tool_use_id = tool_use.id
            else:
                tool_name = tool_use['function']['name']
                tool_input = json.loads(tool_use['function']['arguments'])
                tool_use_id = 'tool_use_' + str(time.time())  # Generate a unique ID

            console.print(Panel(f"Tool Used: {tool_name}", style="green"))
            console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="green"))

            tool_result = await execute_tool(tool_name, tool_input)
            
            if tool_result["is_error"]:
                console.print(Panel(tool_result["content"], title="Tool Execution Error", style="bold red"))
            else:
                console.print(Panel(tool_result["content"], title_align="left", title="Tool Result", style="green"))
                if tool_name in ['create_file', 'edit_and_apply', 'read_file'] and 'path' in tool_input:
                    file_path = tool_input['path']
                    if any(phrase in tool_result["content"] for phrase in [
                        "File contents updated in system prompt",
                        "File created and added to system prompt",
                        "has been read and stored in the system prompt"
                    ]):
                        console.print(Panel(f"File '{file_path}' has been processed and its contents are now in the system context.", title="File Processed", style="cyan"))

            # Add tool use to the conversation
            current_conversation.append({
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input
                    }
                ]
            })

            # Add tool result to the conversation
            current_conversation.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result["content"],
                        "is_error": tool_result["is_error"]
                    }
                ]
            })

            # Process the tool result with the AI
            tool_response = await process_tool_result(tool_result, current_iteration, max_iterations)
            if tool_response:
                assistant_response += "\n\n" + tool_response

    else:
        console.print(Panel("No tool uses in this response.", title="Tool Usage", style="yellow"))

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    conversation_history = filtered_conversation_history + current_conversation

    # Display token usage at the end (only for Anthropic)
    if AI_PROVIDER == 'anthropic':
        display_token_usage()

    # Ensure user input is requested after tool execution if not in automode
    if not automode:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")
        return await chat_with_claude(user_input, current_iteration=current_iteration, max_iterations=max_iterations)
    else:
        return assistant_response, exit_continuation

async def process_tool_result(tool_result, current_iteration, max_iterations):
    try:
        model = get_model_name()
        tool_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": update_system_prompt(current_iteration, max_iterations)},
                {"role": "user", "content": f"Process this tool result and provide any necessary follow-up or analysis:\n\n{tool_result['content']}"}
            ],
            max_tokens=1000
        )
    
        if AI_PROVIDER == 'anthropic':
            # Update token usage for tool checker (only for Anthropic)
            if hasattr(tool_response, 'usage'):
                tool_checker_tokens['input'] += tool_response.usage.prompt_tokens
                tool_checker_tokens['output'] += tool_response.usage.completion_tokens

        tool_checker_response = tool_response.choices[0].message.content if tool_response.choices else ""
        
        if tool_checker_response:
            console.print(Panel(Markdown(tool_checker_response), title="AI's Response to Tool Result", title_align="left", border_style="blue", expand=False))
            return tool_checker_response
        else:
            console.print(Panel("No additional response from AI after tool use.", title="AI's Response to Tool Result", title_align="left", border_style="yellow", expand=False))
            return ""
    except Exception as e:
        error_message = f"Error in processing tool result: {str(e)}"
        console.print(Panel(error_message, title="Error", style="bold red"))
        return error_message

def reset_code_editor_memory():
    global code_editor_memory
    code_editor_memory = []
    console.print(Panel("Code editor memory has been reset.", title="Reset", style="bold green"))


def reset_conversation():
    global conversation_history, main_model_tokens, tool_checker_tokens, code_editor_tokens, code_execution_tokens, file_contents
    conversation_history = []
    main_model_tokens = {'input': 0, 'output': 0}
    tool_checker_tokens = {'input': 0, 'output': 0}
    code_editor_tokens = {'input': 0, 'output': 0}
    code_execution_tokens = {'input': 0, 'output': 0}
    file_contents = {}
    reset_code_editor_memory()
    console.print(Panel("Conversation history, token counts, file contents, and code editor memory have been reset.", title="Reset", style="bold green"))
    display_token_usage()

def display_token_usage():
    if AI_PROVIDER == 'anthropic':
        from rich.table import Table
        from rich.panel import Panel
        from rich.box import ROUNDED

        table = Table(box=ROUNDED)
        table.add_column("Model", style="cyan")
        table.add_column("Input", style="magenta")
        table.add_column("Output", style="magenta")
        table.add_column("Total", style="green")
        table.add_column(f"% of Context ({MAX_CONTEXT_TOKENS:,})", style="yellow")
        table.add_column("Cost ($)", style="red")

        model_costs = {
            "Main Model": {"input": 3.00, "output": 15.00, "has_context": True},
            "Tool Checker": {"input": 3.00, "output": 15.00, "has_context": False},
            "Code Editor": {"input": 3.00, "output": 15.00, "has_context": True},
            "Code Execution": {"input": 0.25, "output": 1.25, "has_context": False}
        }

        total_input = 0
        total_output = 0
        total_cost = 0
        total_context_tokens = 0

        for model, tokens in [("Main Model", main_model_tokens),
                              ("Tool Checker", tool_checker_tokens),
                              ("Code Editor", code_editor_tokens),
                              ("Code Execution", code_execution_tokens)]:
            input_tokens = tokens['input']
            output_tokens = tokens['output']
            total_tokens = input_tokens + output_tokens

            total_input += input_tokens
            total_output += output_tokens

            input_cost = (input_tokens / 1_000_000) * model_costs[model]["input"]
            output_cost = (output_tokens / 1_000_000) * model_costs[model]["output"]
            model_cost = input_cost + output_cost
            total_cost += model_cost

            if model_costs[model]["has_context"]:
                total_context_tokens += total_tokens
                percentage = (total_tokens / MAX_CONTEXT_TOKENS) * 100
            else:
                percentage = 0

            table.add_row(
                model,
                f"{input_tokens:,}",
                f"{output_tokens:,}",
                f"{total_tokens:,}",
                f"{percentage:.2f}%" if model_costs[model]["has_context"] else "Doesn't save context",
                f"${model_cost:.3f}"
            )

        grand_total = total_input + total_output
        total_percentage = (total_context_tokens / MAX_CONTEXT_TOKENS) * 100

        table.add_row(
            "Total",
            f"{total_input:,}",
            f"{total_output:,}",
            f"{grand_total:,}",
            "",  # Empty string for the "% of Context" column
            f"${total_cost:.3f}",
            style="bold"
        )

        console.print(table)
    else:
        console.print("Token usage display is not available for Open Router.")



async def main():
    global automode, conversation_history
    console.print(Panel("Welcome to the Claude-3-Sonnet Engineer Chat with Multi-Agent and Image Support!", title="Welcome", style="bold green"))
    console.print(Panel(
        "Commands:\n"
        "- 'exit': End the conversation\n"
        "- 'image': Include an image in your message\n"
        "- 'automode [number]': Enter Autonomous mode with a specific number of iterations\n"
        "- 'reset': Clear the conversation history\n"
        "- 'save chat': Save the conversation to a Markdown file\n"
        "- 'status': Display current status (automode, conversation length, etc.)\n"
        "While in automode, press Ctrl+C at any time to exit and return to regular chat.",
        title="Available Commands",
        expand=False,
        border_style="blue"
    ))

    while True:
        try:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if user_input.lower() == 'exit':
                console.print(Panel("Thank you for chatting. Goodbye!", title="Goodbye", style="bold green"))
                break

            if user_input.lower() == 'reset':
                reset_conversation()
                continue

            if user_input.lower() == 'save chat':
                filename = save_chat()
                console.print(Panel(f"Chat saved to {filename}", title="Chat Saved", style="bold green"))
                continue

            if user_input.lower() == 'status':
                display_status()
                continue

            if user_input.lower() == 'image':
                image_path = console.input("[bold cyan]Drag and drop your image here, then press enter:[/bold cyan] ").strip().replace("'", "")

                if os.path.isfile(image_path):
                    user_input = console.input("[bold cyan]You (prompt for image):[/bold cyan] ")
                    response, _ = await chat_with_claude(user_input, image_path)
                else:
                    console.print(Panel("Invalid image path. Please try again.", title="Error", style="bold red"))
                    continue
            elif user_input.lower().startswith('automode'):
                parts = user_input.split()
                max_iterations = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else MAX_CONTINUATION_ITERATIONS

                automode = True
                console.print(Panel(f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.", title="Automode", style="bold yellow"))
                console.print(Panel("Press Ctrl+C at any time to exit the automode loop.", style="bold yellow"))
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = await chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(Panel("Automode completed.", title="Automode", style="green"))
                            automode = False
                        else:
                            console.print(Panel(f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode.", title="Automode", style="yellow"))
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(Panel("Max iterations reached. Exiting automode.", title="Automode", style="bold red"))
                            automode = False
                except KeyboardInterrupt:
                    console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title="Automode", style="bold red"))
                    automode = False
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})

                console.print(Panel("Exited automode. Returning to regular chat.", style="green"))
            else:
                response, _ = await chat_with_claude(user_input)

        except KeyboardInterrupt:
            console.print(Panel("\nOperation interrupted by user. Returning to main menu.", style="bold yellow"))
            continue
        except Exception as e:
            console.print(Panel(f"An error occurred: {str(e)}\nReturning to main menu.", title="Error", style="bold red"))
            logging.error(f"Error in main loop: {str(e)}")
            continue

def display_status():
    global automode, conversation_history, file_contents
    status = f"Automode: {'On' if automode else 'Off'}\n"
    status += f"Conversation length: {len(conversation_history)} messages\n"
    status += f"Files in context: {len(file_contents)}\n"
    status += f"Current AI Provider: {AI_PROVIDER}\n"
    status += f"Current Model: {SELECTED_MODEL}\n"
    console.print(Panel(status, title="Current Status", expand=False, border_style="cyan"))

if __name__ == "__main__":
    asyncio.run(main())
async def edit_and_apply(path, instructions, project_context, is_automode=False, timeout=30):
    global file_contents
    try:
        original_content = read_file(path)
        file_contents[path] = original_content

        edit_instructions = await asyncio.wait_for(
            generate_edit_instructions(original_content, instructions, project_context, file_contents),
            timeout=timeout
        )

        if not edit_instructions:
            return "No se necesitaron cambios basados en las instrucciones proporcionadas."

        new_content = original_content
        changes_made = False
        for edit in edit_instructions:
            if edit['search'] in new_content:
                new_content = new_content.replace(edit['search'], edit['replace'])
                changes_made = True
            else:
                console.print(Panel(f"Advertencia: No se pudo encontrar el siguiente contenido para reemplazar en {path}:\n{edit['search']}", title="Advertencia de Edición", style="yellow"))

        if not changes_made:
            return f"No se aplicaron cambios a {path}. No se encontró el contenido especificado para reemplazar."

        # Aplicar los cambios al archivo
        with open(path, 'w') as file:
            file.write(new_content)

        diff_result = generate_and_apply_diff(original_content, new_content, path)

        file_contents[path] = new_content

        return f"Cambios aplicados exitosamente a {path}.\n\n{diff_result}"
    except asyncio.TimeoutError:
        return f"Error: La operación se agotó mientras se intentaba editar {path}. Por favor, intente de nuevo o simplifique sus instrucciones."
    except Exception as e:
        return f"Error en edit_and_apply: {str(e)}"
