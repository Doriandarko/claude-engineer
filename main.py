import os
from dotenv import load_dotenv
import json
from tavily import TavilyClient
import base64
from PIL import Image
import io
import re
from anthropic import Anthropic, APIStatusError, APIError
import difflib
import time
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
import asyncio
import aiohttp
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
import datetime
import venv
import subprocess
import sys
import signal

def setup_virtual_environment():
    venv_name = "code_execution_env"
    venv_path = os.path.join(os.getcwd(), venv_name)
    if not os.path.exists(venv_path):
        venv.create(venv_path, with_pip=True)
    
    # Activate the virtual environment
    if sys.platform == "win32":
        activate_script = os.path.join(venv_path, "Scripts", "activate.bat")
    else:
        activate_script = os.path.join(venv_path, "bin", "activate")
    
    return venv_path, activate_script


# Load environment variables from .env file
load_dotenv()

# Initialize the Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
client = Anthropic(api_key=anthropic_api_key)

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    raise ValueError("TAVILY_API_KEY not found in environment variables")
tavily = TavilyClient(api_key=tavily_api_key)

console = Console()

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Available Claude models:
# Claude 3 Opus     claude-3-opus-20240229
# Claude 3 Sonnet   claude-3-sonnet-20240229
# Claude 3 Haiku    claude-3-haiku-20240307
# Claude 3.5 Sonnet claude-3-5-sonnet-20240620

# Models to use
MAINMODEL = "claude-3-5-sonnet-20240620"
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"
CODEEDITORMODEL = "claude-3-5-sonnet-20240620"
CODEEXECUTIONMODEL = "claude-3-5-sonnet-20240620"

# Token tracking variables
main_model_tokens = {'input': 0, 'output': 0}
tool_checker_tokens = {'input': 0, 'output': 0}
code_editor_tokens = {'input': 0, 'output': 0}
code_execution_tokens = {'input': 0, 'output': 0}


# You can set this to whatever you want, so you can see the progress towards a certain amount of tokens
# I set to 1M tokens, so you can see the progress towards 1M tokens
MAX_CONTEXT_TOKENS = 1000000  # 1M tokens for context window



# Set up the conversation memory
conversation_history = []

# Code editor memory
code_editor_memory = []

# automode flag
automode = False

# Global dictionary to store running processes
running_processes = {}

# base prompt
# base prompt
base_system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model, specialized in software development with access to a variety of tools and the ability to instruct and direct a coding agent and a code execution one. Your capabilities include:

1. Creating and managing project structures
2. Writing, debugging, and improving code across multiple languages
3. Providing architectural insights and applying design patterns
4. Staying current with the latest technologies and best practices
5. Analyzing and manipulating files within the project directory
6. Performing web searches for up-to-date information
7. Executing code and analyzing its output within an isolated 'code_execution_env' virtual environment
8. Managing and stopping running processes started within the 'code_execution_env', DO NOT STOP ANYTHING UNLESS THE USER ASKS YOU TO!!!

Available tools and their optimal use cases:

1. create_folder: Create new directories in the project structure.
2. create_file: Generate new files with specified content. With as much content as possible and needed. Do your best to make the file complete and useful.
3. edit_and_apply: Examine and modify existing files by instructing a separate AI coding agent. You are responsible for providing clear, detailed instructions to this agent. When using this tool:
   - Provide comprehensive context about the project, including recent changes, new variables or functions, and how files are interconnected.
   - Clearly state the specific changes or improvements needed, explaining the reasoning behind each modification.
   - Include ALL the snippets of code to change, along with the desired modifications.
   - Specify coding standards, naming conventions, or architectural patterns to be followed.
   - Anticipate potential issues or conflicts that might arise from the changes and provide guidance on how to handle them.
4. execute_code: Run Python code exclusively in the 'code_execution_env' virtual environment and analyze its output. Use this when you need to test code functionality or diagnose issues. Remember that all code execution happens in this isolated environment. This tool now returns a process ID for long-running processes.
5. stop_process: Stop a running process by its ID. Use this when you need to terminate a long-running process started by the execute_code tool.

Tool Usage Guidelines:
- Always use the most appropriate tool for the task at hand.
- For file modifications, use edit_and_apply. Remember, you are instructing another AI, so be clear and specific in your directions.
- After making changes, always review the diff output to ensure accuracy and alignment with your intentions.
- Use execute_code to run and test code within the 'code_execution_env' virtual environment, then analyze the results to provide insights or suggest improvements.
- For long-running processes (like servers), use the process ID returned by execute_code to stop them later if needed.
- Proactively use tavily_search when you need up-to-date information or context to provide better instructions to the coding agent.

Error Handling and Recovery:
- If a tool operation fails, analyze the error message and attempt to resolve the issue.
- For file-related errors, check file paths and permissions before retrying.
- If a search fails, try rephrasing the query or breaking it into smaller, more specific searches.
- If code execution fails within the 'code_execution_env', analyze the error output and suggest potential fixes, considering the isolated nature of the environment.
- If a process fails to stop, consider potential reasons and suggest alternative approaches.

Project Creation and Management:
1. Start by creating a root folder for new projects.
2. Create necessary subdirectories and files within the root folder.
3. Organize the project structure logically, following best practices for the specific project type.

Always strive for accuracy, clarity, and efficiency in your responses and actions. Remember, you are guiding another AI through the coding process, so your instructions must be precise and comprehensive. If uncertain, use the tavily_search tool or admit your limitations. When executing code, always keep in mind that it runs in the isolated 'code_execution_env' virtual environment. Be aware of any long-running processes you start and manage them appropriately, including stopping them when they are no longer needed.
"""

# Auto mode-specific system prompt
automode_system_prompt = """
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

def update_system_prompt(current_iteration=None, max_iterations=None):
    global base_system_prompt, automode_system_prompt
    chain_of_thought_prompt = """
    Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

    Do not reflect on the quality of the returned search results in your response.
    """
    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return base_system_prompt + "\n\n" + automode_system_prompt.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt
    else:
        return base_system_prompt + "\n\n" + chain_of_thought_prompt

def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"

def create_file(path, content=""):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"File created: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"

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


async def send_to_ai_for_editing(file_content, batch_content, instructions, project_context):
    global code_editor_tokens, code_editor_memory
    try:
        
        # Log the raw batch content
        console.print(Panel("Batch content sent to AI:", title="Batch", style="bold yellow"))
        console.print(batch_content)

        # Prepare memory context
        memory_context = "\n".join([f"Memory {i+1}:\n{mem}" for i, mem in enumerate(code_editor_memory)])

        system_prompt = f"""
        You are an incredible AI coding agent that edits code files. Your task is to carefully review, analyze, and improve the provided code based on the given instructions and project context. Follow these steps:

        1. Review the entire file content to understand the context:
        {file_content}

        2. Carefully analyze the specific instructions:
        {instructions}

        3. Take into account the overall project context:
        {project_context}

        4. Consider the memory of previous edits:
        {memory_context}

        5. Examine the batch of code provided in the user message.

        6. Before making any changes, consider:
           - How the instructions apply to this specific batch
           - The batch in the context of the entire file and all previously edited batches
           - The overall structure and purpose of the code
           - Potential impacts on other parts of the file and other files in the project
           - Best practices and coding standards for the language
           - Potential issues and improvements not mentioned in the instructions

        7. Make improvements to the code, ensuring you:
           - Address all relevant aspects of the instructions
           - Maintain or enhance code readability and efficiency
           - Use the correct indentation and formatting of each line
           - Add, remove, or modify lines as necessary, matching surrounding indentation
           - Consider the file type when formatting the edited lines
           - Ensure consistency with all previously edited batches and the project context

        8. If no improvements are needed or if the instructions don't apply to this batch, return the lines unchanged.

        CRITICAL: 
        - USE THE RIGHT indentation and formatting.
        - Focus only on code improvements based on the instructions and your analysis of the file and project context.
        - Ensure consistency with all previously edited batches and other files in the project.

        IMPORTANT: RETURN ONLY THE EDITED BATCH, WITH THE RIGHT INDENTATION. NO EXPLANATIONS OR COMMENTS.
        DO NOT FOR ANY REASON RETURN THE LINE NUMBERS. WE ONLY NEED THE CODE LIKE YOU WERE WRITING IT IN A FILE.
        """

        # Make the API call
        response = client.messages.create(
            model=CODEEDITORMODEL,
            max_tokens=8000,
            system=system_prompt,
            extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
            messages=[
                {"role": "user", "content": f"Edit this batch RETURN ONLY THE EDITED CODE, WITH THE RIGHT INDENTATION. NO EXPLANATIONS OR COMMENTS LEAVE CODE UNTOUCHED IF NO IMPROVEMENTS ARE NEEDED:\n{batch_content}"}
            ]
        )
        # Update token usage for code editor
        code_editor_tokens['input'] += response.usage.input_tokens
        code_editor_tokens['output'] += response.usage.output_tokens

        # Log the AI's response
        # console.print(Panel("Raw AI response:", title="Debug", style="bold yellow"))
        # console.print(response.content[0].text)

        edited_content = response.content[0].text

        # Update code editor memory
        code_editor_memory.append(f"Batch:\n{batch_content}\n\nEdited:\n{edited_content}")

        return edited_content

    except Exception as e:
        console.print(f"Error in AI editing: {str(e)}", style="bold red")
        return batch_content  # Return original batch content if any exception occurs



async def edit_and_apply(path, instructions, project_context, batch_size=None, is_automode=False):
    try:
        with open(path, 'r') as file:
            original_content = file.read()

        # If batch_size is None, let process_code_file determine the appropriate size
        edited_content = await process_code_file(path, instructions, project_context, batch_size, is_automode)

        if edited_content != original_content:
            # Print the raw AI output for debugging
            # console.print(Panel("Raw AI Output:", title="Debug", style="bold yellow"))
            # console.print(edited_content)

            diff_result = generate_and_apply_diff(original_content, edited_content, path)

            console.print(Panel("The following changes have been suggested:", title="File Changes", style="cyan"))
            console.print(diff_result)

            if not is_automode:
                confirm = console.input("[bold yellow]Do you want to apply these changes? (yes/no): [/bold yellow]")
                if confirm.lower() != 'yes':
                    # Revert changes
                    with open(path, 'w') as file:
                        file.write(original_content)
                    return "Changes were not applied and file reverted to original content."

            # In automode, changes are already applied, so we don't need to write again
            if not is_automode:
                with open(path, 'w') as file:
                    file.write(edited_content)
            return f"Changes applied to {path}:\n{diff_result}"
        else:
            return f"No changes needed for {path}"
    except Exception as e:
        return f"Error editing/applying to file: {str(e)}"


async def process_code_file(file_path, instructions, project_context, batch_size=None, is_automode=False):
    with open(file_path, 'r') as f:
        original_content = f.read()

    lines = original_content.splitlines(keepends=True)
    total_lines = len(lines)

    if batch_size is None:
        # Determine appropriate batch size based on file size
        if total_lines < 200:
            batch_size = total_lines  # Process entire file as one batch
        elif total_lines < 1000:
            batch_size = 250  # Use middle value of 200-300 for medium files
        else:
            batch_size = 350  # Use middle value of 300-400 for large files

    edited_content = []
    previous_batches = []  # New: Keep track of previous batches

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Editing file...", total=total_lines)

        for i in range(0, total_lines, batch_size):
            batch = lines[i:i+batch_size]
            batch_content = ''.join(batch)
            edited_batch = await send_to_ai_for_editing(original_content, batch_content, instructions, project_context)
            
            edited_content.extend(edited_batch.splitlines(keepends=True))
            previous_batches.append(edited_batch)  # New: Add edited batch to previous_batches

            # Write the changes to the file after each batch
            if is_automode:
                with open(file_path, 'w') as f:
                    f.writelines(edited_content + lines[i+batch_size:])

            progress.update(task, advance=len(batch))
            await asyncio.sleep(0.01)

    progress.update(task, completed=total_lines)

    # Display token usage after all batches have been processed
    display_token_usage()

    return ''.join(edited_content)

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
    try:
        with open(path, 'r') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"

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


tools = [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with content. Use this when you need to create a new file in the project structure. WIth as much content as possible and needed. Do your best to make the file complete and useful.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "search_file",
        "description": "Search for a specific pattern in a file and return the line numbers where the pattern is found. Use this to locate specific code or text within a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to search"
                },
                "search_pattern": {
                    "type": "string",
                    "description": "The pattern to search for in the file"
                }
            },
            "required": ["path", "search_pattern"]
        }
    },
    {
    "name": "edit_and_apply",
    "description": "Apply AI-powered improvements to a file based on specific instructions and detailed project context. This function reads the file, processes it in batches using AI with conversation history and comprehensive code-related project context. It generates a diff and allows the user to confirm changes before applying them. The goal is to maintain consistency and prevent breaking connections between files.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to edit"
            },
            "instructions": {
                "type": "string",
                "description": "Specific instructions for code changes, including:\n1. Functionality to add, modify, or remove\n2. Performance optimizations to implement\n3. Code style or formatting changes to apply\n4. Refactoring suggestions to improve code structure\n5. Error handling or input validation to enhance\n6. Documentation or comments to update or add\n7. Integration of new libraries or APIs\n8. Implementation of specific algorithms or design patterns\n9. Addressing of known bugs or issues\n10. Any other specific code modifications or improvements to be made"
            },
            "batch_size": {
                "type": "integer",
                "description": "Number of lines to process in each batch. Suggest an appropriate size based on file content (e.g., entire file as a batch for small files < 200 lines, 200-300 lines for medium files 200-1000 lines, 300-400 lines for large files > 1000 lines). Consider function/class boundaries when suggesting a batch size.",
                "default": 250
            },
            "project_context": {
                "type": "string",
                "description": "Detailed code-specific context about the project, including:\n1. New variables, functions, or classes added in other files\n2. Changes to existing functions or method signatures\n3. Modifications to shared data structures or APIs\n4. Updates to import statements or module dependencies\n5. Alterations to configuration files or environment variables\n6. Changes in project structure or file organization\n7. Updates to third-party library versions or dependencies\n8. Modifications to database schemas or data models\n9. Changes in naming conventions or coding standards\n10. Any other code-related changes that might affect the interconnections between files"
            }
        },
        "required": ["path", "instructions", "project_context"]
    }
},
{
    "name": "execute_code",
    "description": "Execute Python code in the 'code_execution_env' virtual environment and return the output. Use this when you need to run code and see its output or check for errors. All code execution happens exclusively in this isolated environment.",
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute in the 'code_execution_env' virtual environment"
            }
        },
        "required": ["code"]
    }
},
{
    "name": "stop_process",
    "description": "Stop a running process by its ID.",
    "input_schema": {
        "type": "object",
        "properties": {
            "process_id": {
                "type": "string",
                "description": "The ID of the process to stop"
            }
        },
        "required": ["process_id"]
    }
},
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. Use this when you need to see the contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)"
                }
            }
        }
    },
    {
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
]

# Update the execute_tool function
async def execute_tool(tool_name, tool_input):
    try:
        if tool_name == "create_folder":
            return create_folder(tool_input["path"])
        elif tool_name == "create_file":
            return create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "edit_and_apply":
            return await edit_and_apply(
                tool_input["path"],
                tool_input["instructions"],
                tool_input["project_context"],
                batch_size=tool_input.get("batch_size", 250),
                is_automode=automode
            )
        elif tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "list_files":
            return list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            return tavily_search(tool_input["query"])
        elif tool_name == "stop_process":
            return stop_process(tool_input["process_id"])
        elif tool_name == "execute_code":
            process_id, execution_result = await execute_code(tool_input["code"])
            analysis = await send_to_ai_for_executing(tool_input["code"], execution_result)
            result = f"{execution_result}\n\nAnalysis:\n{analysis}"
            return result
            if return_code == "Running":
                result += "\n\nNote: The process is still running in the background."
            return result
        else:
            return f"Unknown tool: {tool_name}"
    except KeyError as e:
        return f"Error: Missing required parameter {str(e)} for tool {tool_name}"
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

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



async def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode, main_model_tokens



    current_conversation = []

    if image_path:
        console.print(Panel(f"Processing image at path: {image_path}", title_align="left", title="Image Processing", expand=False, style="yellow"))
        image_base64 = encode_image_to_base64(image_path)

        if image_base64.startswith("Error"):
            console.print(Panel(f"Error encoding image: {image_base64}", title="Error", style="bold red"))
            return "I'm sorry, there was an error processing the image. Please try again.", False

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
        current_conversation.append(image_message)
        console.print(Panel("Image message added to conversation history", title_align="left", title="Image Added", style="green"))
    else:
        current_conversation.append({"role": "user", "content": user_input})

    messages = conversation_history + current_conversation

    try:
        response = client.messages.create(
            model=MAINMODEL,
            max_tokens=8000,
            system=update_system_prompt(current_iteration, max_iterations),
            extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
        # Update token usage
        main_model_tokens['input'] += response.usage.input_tokens
        main_model_tokens['output'] += response.usage.output_tokens
        
        # Display token usage after each main model call
        display_token_usage()
    except APIStatusError as e:
        if e.status_code == 429:
            console.print(Panel("Rate limit exceeded. Retrying after a short delay...", title="API Error", style="bold yellow"))
            time.sleep(5)
            return await chat_with_claude(user_input, image_path, current_iteration, max_iterations)
        else:
            console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
            return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    except APIError as e:
        console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False

    assistant_response = ""
    exit_continuation = False
    tool_uses = []

    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_uses.append(content_block)

    console.print(Panel(Markdown(assistant_response), title="Claude's Response", title_align="left", border_style="blue", expand=False))

    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="green"))
        console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="green"))

        try:
            result = await execute_tool(tool_name, tool_input)
            console.print(Panel(result, title_align="left", title="Tool Result", style="green"))
        except Exception as e:
            result = f"Error executing tool: {str(e)}"
            console.print(Panel(result, title="Tool Execution Error", style="bold red"))

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

        current_conversation.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": result
                }
            ]
        })

        messages = conversation_history + current_conversation

        try:
            # Reset tool checker tokens before each call
            
            # print("Debug: About to call tool checker")

            tool_response = client.messages.create(
                model=TOOLCHECKERMODEL,
                max_tokens=8000,
                system=update_system_prompt(current_iteration, max_iterations),
                extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )
            # print(f"Debug: Tool checker response received. Usage: {tool_response.usage}")
            # Update token usage for tool checker
            tool_checker_tokens['input'] += tool_response.usage.input_tokens
            tool_checker_tokens['output'] += tool_response.usage.output_tokens

            # Display token usage after each tool checker call
            display_token_usage()

            tool_checker_response = ""
            for tool_content_block in tool_response.content:
                if tool_content_block.type == "text":
                    tool_checker_response += tool_content_block.text
            console.print(Panel(Markdown(tool_checker_response), title="Claude's Response to Tool Result",  title_align="left", border_style="blue", expand=False))
            assistant_response += "\n\n" + tool_checker_response
        except APIError as e:
            error_message = f"Error in tool response: {str(e)}"
            console.print(Panel(error_message, title="Error", style="bold red"))
            assistant_response += f"\n\n{error_message}"

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    conversation_history = messages + [{"role": "assistant", "content": assistant_response}]

    return assistant_response, exit_continuation

def reset_code_editor_memory():
    global code_editor_memory
    code_editor_memory = []
    console.print(Panel("Code editor memory has been reset.", title="Reset", style="bold green"))


def reset_conversation():
    global conversation_history, main_model_tokens, tool_checker_tokens, code_editor_tokens, code_execution_tokens
    conversation_history = []
    main_model_tokens = {'input': 0, 'output': 0}
    tool_checker_tokens = {'input': 0, 'output': 0}
    code_editor_tokens = {'input': 0, 'output': 0}
    code_execution_tokens = {'input': 0, 'output': 0}
    reset_code_editor_memory()
    console.print(Panel("Conversation history, token counts, and code editor memory have been reset.", title="Reset", style="bold green"))
    display_token_usage()

def display_token_usage():
    console.print("\n Token Usage:")
    total_input = 0
    total_output = 0
    
    for model, tokens in [("Main Model", main_model_tokens), 
                          ("Tool Checker", tool_checker_tokens),
                          ("Code Editor", code_editor_tokens),
                          ("Code Execution", code_execution_tokens)]:
        total = tokens['input'] + tokens['output']
        percentage = (total / MAX_CONTEXT_TOKENS) * 100
        
        total_input += tokens['input']
        total_output += tokens['output']

        console.print(f"{model}:")
        console.print(f"  Input: {tokens['input']}, Output: {tokens['output']}, Total: {total}")
        console.print(f"  Percentage of context window used: {percentage:.2f}%")
        
        with Progress(TextColumn("[progress.description]{task.description}"),
                      BarColumn(bar_width=50),
                      TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                      console=console) as progress:
            progress.add_task(f"Context window usage", total=100, completed=percentage)

    grand_total = total_input + total_output
    total_percentage = (grand_total / MAX_CONTEXT_TOKENS) * 100

    # Calculate the cost
    input_cost = (total_input / 1_000_000) * 3.00
    output_cost = (total_output / 1_000_000) * 15.00
    total_cost = input_cost + output_cost

    console.print(f"\nTotal Token Usage: Input: {total_input}, Output: {total_output}, Grand Total: {grand_total}, Cost: ${total_cost:.3f}")

    console.print("\n")


    

async def main():
    global automode, conversation_history
    console.print(Panel("Welcome to the Claude-3-Sonnet Engineer Chat with Multi-Agent and Image Support!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("Type 'reset' to clear the conversation history.")
    console.print("Type 'save chat' to save the conversation to a Markdown file.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")

    while True:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
            break

        if user_input.lower() == 'reset':
            reset_conversation()
            continue

        if user_input.lower() == 'save chat':
            filename = save_chat()
            console.print(Panel(f"Chat saved to {filename}", title="Chat Saved", style="bold green"))
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
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS

                automode = True
                console.print(Panel(f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.", title_align="left", title="Automode", style="bold yellow"))
                console.print(Panel("Press Ctrl+C at any time to exit the automode loop.", style="bold yellow"))
                user_input = console.input("[bold cyan]You:[/bold cyan] ")

                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = await chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(Panel("Automode completed.", title_align="left", title="Automode", style="green"))
                            automode = False
                        else:
                            console.print(Panel(f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode. ", title_align="left", title="Automode", style="yellow"))
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(Panel("Max iterations reached. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                            automode = False
                except KeyboardInterrupt:
                    console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                    automode = False
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                automode = False
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})

            console.print(Panel("Exited automode. Returning to regular chat.", style="green"))
        else:
            response, _ = await chat_with_claude(user_input)

if __name__ == "__main__":
    asyncio.run(main())
