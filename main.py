import os
import json
from datetime import datetime
from colorama import init, Fore, Style
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter
from tavily import TavilyClient
import pygments.util
import base64
from PIL import Image
import io
import re
from anthropic import Anthropic
import difflib
import httpx

# Initialize colorama
init()

# Color constants
USER_COLOR = Fore.WHITE
CLAUDE_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

# Constants
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25
MODEL = os.environ.get("CLAUDE_MODEL", "claude-3-5-sonnet-20240620")
TOOL_CHOICE = {"type": os.environ.get("TOOL_CHOICE", "auto")}

# Initialize the Anthropic client
client = Anthropic(api_key="YOUR KEY")

# Initialize the Tavily client
tavily = TavilyClient(api_key="YOUR KEY")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# System prompt
system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model. You are a versatile software developer and problem-solver with access to various tools and capabilities. Your primary function is to assist users with coding tasks, answer questions, and provide up-to-date information.

Your available tools and their functions are:

1. create_folder(path): Create a new folder at the specified path.
2. create_file(path, content=""): Create a new file at the specified path with optional content.
3. write_to_file(path, content): Write or update content in a file at the specified path.
4. read_file(path): Read and return the contents of a file at the specified path.
5. list_files(path="."): List all files and directories in the specified folder (default is current directory).
6. tavily_search(query): Perform a web search using the Tavily API to get up-to-date information.
7. format_json(data): Format the given data as a JSON string.

When using these tools:
- Always provide full paths for file and folder operations.
- Use the read_file tool before attempting to modify existing files.
- Utilize the tavily_search tool when you need current information or additional context.
- Use the list_files tool to understand the project structure when necessary.

Your capabilities include:

1. Creating and managing project structures, including folders and files.
2. Writing, reading, and modifying code in various programming languages.
3. Debugging issues and providing detailed explanations.
4. Offering architectural insights and suggesting design patterns.
5. Staying informed about the latest technologies and industry trends.
6. Analyzing and describing images provided by the user.

When working on projects or answering questions:
- Start by creating a root folder for new projects, then add necessary subdirectories and files.
- Organize project structures logically, following best practices for the specific type of project.
- Provide clean, efficient, and well-documented code.
- Use the tavily_search tool to gather up-to-date information when needed.
- When editing files, always provide the full content, even for small changes.

Before using any tool, analyze the request within <thinking></thinking> tags:
1. Determine which tool is most appropriate for the task.
2. Consider if all required parameters are provided or can be reasonably inferred.
3. If a required parameter is missing, ask the user for the necessary information instead of using the tool.
4. Do not ask for optional parameters if they are not provided.

Special modes:
- Automode: When activated, work autonomously to complete tasks, providing regular updates on your progress.
- Image analysis: When an image is provided, carefully analyze its contents and incorporate your observations into your responses.

Automode Operation:
When in automode, follow these steps:
1. Set clear, achievable goals based on the user's request.
2. Work through these goals one by one, using the available tools as needed.
3. Provide regular updates on your progress.
4. ULTRA MEGA IMPORTANT: When you believe all goals have been completed or the original request has been fully addressed, include the phrase "AUTOMODE_COMPLETE" in your response. This will signal the system to exit the automode loop.
5. Do not engage in unnecessary back-and-forth conversations with yourself once the goals are achieved.
6. Be mindful of the number of iterations left (provided in {iteration_info}) and use this information to pace your work and provide appropriate updates.

Always strive to provide accurate, helpful, and detailed responses. If you're unsure about something, admit it and consider using the tavily_search tool to find the most current information.

Remember, you are here to assist and guide the user. Be proactive in suggesting solutions and offering advice, but also be receptive to the user's preferences and instructions.

{automode_status}
{iteration_info}
"""

def update_system_prompt(current_iteration=None, max_iterations=None):
    global system_prompt
    automode_status = "You are currently in automode." if automode else "You are not in automode."
    iteration_info = ""
    if current_iteration is not None and max_iterations is not None:
        iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
    return system_prompt.format(automode_status=automode_status, iteration_info=iteration_info)

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def print_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
        formatted_code = highlight(code, lexer, TerminalFormatter())
        print(formatted_code)
    except pygments.util.ClassNotFound:
        print_colored(f"Code (language: {language}):\n{code}", CLAUDE_COLOR)

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
        return f"Changes applied to {path}:\n" + ''.join(diff)
    except Exception as e:
        return f"Error applying changes: {str(e)}"

def write_to_file(path, content):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                original_content = f.read()
            result = generate_and_apply_diff(original_content, content, path)
        else:
            with open(path, 'w') as f:
                f.write(content)
            result = f"New file created and content written to: {path}"
        return result
    except Exception as e:
        return f"Error writing to file: {str(e)}"

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

def format_json(data):
    return json.dumps(data, indent=2)

tools = [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure. This tool is useful for organizing files and setting up the initial project layout. It will not create parent directories if they don't exist. Use with caution in existing projects to avoid overwriting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The full path where the folder should be created, e.g., '/project/src/components'"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with optional content. Use this when you need to create a new file in the project structure. This tool is ideal for initializing new source code files, configuration files, or documentation. Be careful not to overwrite existing files unintentionally.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The full path where the file should be created, including the filename and extension"
                },
                "content": {
                    "type": "string",
                    "description": "The initial content of the file (optional)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_to_file",
        "description": "Write content to a file at the specified path. If the file exists, only the necessary changes will be applied. If the file doesn't exist, it will be created. Always provide the full intended content of the file. This tool is useful for updating existing files or creating new ones with specific content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The full path of the file to write to, including the filename and extension"
                },
                "content": {
                    "type": "string",
                    "description": "The full content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file. This tool is helpful for understanding the current state of a file before making changes or for retrieving information from configuration files, source code, or documentation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The full path of the file to read, including the filename and extension"
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. Use this when you need to see the contents of a directory. This tool is useful for understanding the structure of a project, finding specific files, or verifying the presence of expected files and folders.",
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
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer. This tool is particularly useful for finding recent developments, verifying facts, or gathering supplementary information on a topic.",
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
    },
    {
        "name": "format_json",
        "description": "Format the given data as a JSON string. Use this when you need to return structured data in JSON format. This tool is helpful for creating configuration files, API responses, or any situation where data needs to be represented in a standardized, machine-readable format.",
        "input_schema": {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "description": "The data to be formatted as JSON"
                }
            },
            "required": ["data"]
        }
    }
]

def execute_tool(tool_name, tool_input):
    try:
        if tool_name == "create_folder":
            return create_folder(tool_input["path"])
        elif tool_name == "create_file":
            return create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "write_to_file":
            return write_to_file(tool_input["path"], tool_input["content"])
        elif tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "list_files":
            return list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            return tavily_search(tool_input["query"])
        elif tool_name == "format_json":
            return format_json(tool_input["data"])
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    except Exception as e:
        return {
            "content": f"Error executing {tool_name}: {str(e)}",
            "is_error": True
        }

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
        print_colored(f"\nExecuting Goal {i}: {goal}", TOOL_COLOR)
        response, _ = chat_with_claude(f"Continue working on goal: {goal}")
        if CONTINUATION_EXIT_PHRASE in response:
            automode = False
            print_colored("Exiting automode.", TOOL_COLOR)
            break

def manage_tool_dependencies(tool_results):
    # This function can be expanded to handle complex dependencies between tools
    return tool_results

def estimate_token_usage(messages, tools):
    # This is a very rough estimate and should be refined based on actual usage
    message_tokens = sum(len(str(m.get("content", ""))) for m in messages)
    tool_tokens = sum(len(str(t)) for t in tools)
    system_prompt_tokens = 294  # For Claude 3.5 Sonnet with auto tool choice
    return message_tokens + tool_tokens + system_prompt_tokens

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None, max_tokens=4000):
    global conversation_history, automode
    
    if image_path:
        print_colored(f"Processing image at path: {image_path}", TOOL_COLOR)
        image_base64 = encode_image_to_base64(image_path)
        
        if image_base64.startswith("Error"):
            print_colored(f"Error encoding image: {image_base64}", TOOL_COLOR)
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
        conversation_history.append(image_message)
        print_colored("Image message added to conversation history", TOOL_COLOR)
    else:
        conversation_history.append({"role": "user", "content": user_input})
    
    messages = [msg for msg in conversation_history if msg.get('content')]
    
    estimated_tokens = estimate_token_usage(messages, tools)
    print_colored(f"Estimated token usage: {estimated_tokens}", TOOL_COLOR)
    
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice=TOOL_CHOICE
        )
    except Exception as e:
        print_colored(f"Error calling Claude API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    assistant_response = ""
    exit_continuation = False
    tool_use_blocks = []
    
    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_name = content_block.name
            tool_input = content_block.input
            tool_use_id = content_block.id
            
            print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
            print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
            
            result = execute_tool(tool_name, tool_input)
            if isinstance(result, dict) and result.get("is_error"):
                print_colored(f"Tool Error: {result['content']}", TOOL_COLOR)
            else:
                print_colored(f"Tool Result: {result}", RESULT_COLOR)
            
            tool_use_blocks.append(content_block)
            tool_result = {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": result if isinstance(result, str) else result["content"],
                "is_error": result.get("is_error", False) if isinstance(result, dict) else False
            }
            
            # Immediately add tool use and tool result to conversation history
            conversation_history.append({"role": "assistant", "content": [content_block]})
            conversation_history.append({"role": "user", "content": [tool_result]})
    
    # Add the final assistant response to the conversation history
    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})
    
    actual_input_tokens = response.usage.input_tokens
    actual_output_tokens = response.usage.output_tokens
    print_colored(f"Actual token usage - Input: {actual_input_tokens}, Output: {actual_output_tokens}", TOOL_COLOR)
    
    return assistant_response, exit_continuation

def process_and_display_response(response):
    if response.startswith("Error") or response.startswith("I'm sorry"):
        print_colored(response, TOOL_COLOR)
    else:
        if "```" in response:
            parts = response.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 0:
                    print_colored(part, CLAUDE_COLOR)
                else:
                    lines = part.split('\n')
                    language = lines[0].strip() if lines else ""
                    code = '\n'.join(lines[1:]) if len(lines) > 1 else ""
                    
                    if language and code:
                        print_code(code, language)
                    elif code:
                        print_colored(f"Code:\n{code}", CLAUDE_COLOR)
                    else:
                        print_colored(part, CLAUDE_COLOR)
        else:
            print_colored(response, CLAUDE_COLOR)

def main():
    global automode, conversation_history
    print_colored("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", CLAUDE_COLOR)
    print_colored("Type 'exit' to end the conversation.", CLAUDE_COLOR)
    print_colored("Type 'image' to include an image in your message.", CLAUDE_COLOR)
    print_colored("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.", CLAUDE_COLOR)
    print_colored("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.", CLAUDE_COLOR)
    
    while True:
        user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
        
        if user_input.lower() == 'exit':
            print_colored("Thank you for chatting. Goodbye!", CLAUDE_COLOR)
            break
        
        if user_input.lower() == 'image':
            image_path = input(f"{USER_COLOR}Drag and drop your image here: {Style.RESET_ALL}").strip().replace("'", "")
            
            if os.path.isfile(image_path):
                user_input = input(f"{USER_COLOR}You (prompt for image): {Style.RESET_ALL}")
                response, _ = chat_with_claude(user_input, image_path)
                process_and_display_response(response)
            else:
                print_colored("Invalid image path. Please try again.", CLAUDE_COLOR)
                continue
        elif user_input.lower().startswith('automode'):
            try:
                parts = user_input.split()
                if len(parts) > 1 and parts[1].isdigit():
                    max_iterations = int(parts[1])
                else:
                    max_iterations = MAX_CONTINUATION_ITERATIONS
                
                automode = True
                print_colored(f"Entering automode with {max_iterations} iterations. Press Ctrl+C to exit automode at any time.", TOOL_COLOR)
                print_colored("Press Ctrl+C at any time to exit the automode loop.", TOOL_COLOR)
                user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
                
                iteration_count = 0
                try:
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
                        process_and_display_response(response)
                        
                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            print_colored("Automode completed.", TOOL_COLOR)
                            automode = False
                        else:
                            print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                            print_colored("Press Ctrl+C to exit automode.", TOOL_COLOR)
                            user_input = "Continue with the next step."
                        
                        iteration_count += 1
                        
                        if iteration_count >= max_iterations:
                            print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                            automode = False
                except KeyboardInterrupt:
                    print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                    automode = False
                    # Ensure the conversation history ends with an assistant message
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                automode = False
                # Ensure the conversation history ends with an assistant message
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            
            print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
        else:
            response, _ = chat_with_claude(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()
