import os
from datetime import datetime
import json
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

# Initialize colorama
init()

# Color constants
USER_COLOR = Fore.WHITE
CLAUDE_COLOR = Fore.BLUE
TOOL_COLOR = Fore.YELLOW
RESULT_COLOR = Fore.GREEN

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Initialize the Anthropic client
client = Anthropic(api_key="YOUR API KEY")

# Initialize the Tavily client
tavily = TavilyClient(api_key="YOUR API KEY")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# System prompt
system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

1. Creating project structures, including folders and files
2. Writing clean, efficient, and well-documented code
3. Debugging complex issues and providing detailed explanations
4. Offering architectural insights and design patterns
5. Staying up-to-date with the latest technologies and industry trends
6. Reading and analyzing existing files in the project directory
7. Listing files in the root directory of the project
8. Performing web searches to get up-to-date information or additional context
9. When you use search make sure you use the best query to get the most accurate and up-to-date information
10. IMPORTANT!! You NEVER remove existing code if it doesn't require to be changed or removed, never use comments like # ... (keep existing code) ... or # ... (rest of the code) ... etc, you only add new code or remove it or EDIT IT.
11. Analyzing images provided by the user
12. Analyzing and displaying file and directory structures using the tree_directory function
13. Concatenating and displaying contents of multiple files simultaneously using the cat_multiple_files function, with conservative file size management to maintain conversation history and prevent exceeding token limits

When asked to create a project:
- Always start by creating a root folder for the project.
- Then, create the necessary subdirectories and files within that root folder.
- Organize the project structure logically and follow best practices for the specific type of project being created.
- Use the provided tools to create folders and files as needed.

When asked to make edits or improvements:
- Use the read_file tool to examine the contents of individual existing files, especially for larger files or when focusing on specific sections.
- Use the cat_multiple_files tool when you need to examine and compare multiple related files simultaneously, such as:
  * Reviewing a set of related components or modules
  * Comparing configuration files across different environments
  * Analyzing implementation files alongside their corresponding test files
- Remember the file size limits for cat_multiple_files (50 KB per file, 200 KB total) and use read_file for larger files or when you need to focus on specific parts of a file.
- Analyze the code and suggest improvements or make necessary edits.
- Use the write_to_file tool to implement changes.

Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

When analyzing project structures and codebases:

1. Maintain conversation history:
   - Always prioritize maintaining the context of the conversation over loading large amounts of code.
   - Be mindful that your responses and the code you analyze contribute to your token usage.

2. Start with a broad overview:
   - Use tree_directory with a shallow depth (max_depth=2 or 3) to get an overview of top-level directories.
   - This provides a general sense of the project's structure without getting lost in details.

3. Explore strategically:
   - If the project structure isn't clear from the initial overview, explore specific directories in more detail.
   - Use tree_directory on subdirectories or increase the max_depth parameter as needed.

4. Handle large directories efficiently:
   - Use the exclude_folders parameter to omit directories that often contain numerous files but aren't central to understanding the project structure (e.g., dependency directories, build outputs).
   - Example: tree_directory(path='.', max_depth=3, exclude_folders=['node_modules', 'build', 'dist'])

5. Use cat_multiple_files conservatively:
   - The cat_multiple_files function has conservative file size limits:
     * Default total limit across all files: 200 KB
     * Default limit for any single file: 50 KB
   - You can adjust these limits if absolutely necessary, but be very cautious about increasing them.
   - Example usage: cat_multiple_files(file_paths=['file1.py', 'file2.py'], max_total_size_kb=300, max_single_file_size_kb=75)
   - The function will skip files that exceed the single file limit and stop adding files if the total limit would be exceeded.
   - Always check the summary at the end of the output to see how many files were actually displayed.
   - Prefer cat_multiple_files when you need to analyze or compare multiple related files simultaneously.
   - Good use cases include:
     * Comparing multiple configuration files (e.g., for different environments)
     * Analyzing a set of related components or modules
     * Reviewing test files alongside their corresponding implementation files

6. Handle large files and codebases efficiently:
   - For files larger than 50 KB, use the read_file function to examine specific portions of the file.
   - For large codebases, use tree_directory to get an overview, then strategically select small, critical files for analysis with cat_multiple_files.
   - If cat_multiple_files skips files due to size limits, examine those files individually using read_file, focusing on the most relevant parts.

7. Balance analysis with token conservation:
   - Start with analyzing small, critical files that provide the most insight into the project structure or specific issues.
   - Use read_file for targeted examination of larger files, focusing on specific functions or sections rather than entire files.
   - Summarize your findings frequently, and only keep the most relevant code snippets in the conversation.

8. Provide context-aware analysis:
   - When discussing code, always reference the specific files and sections you've examined.
   - If some files were skipped due to size limits, mention this in your analysis and explain how it might affect your conclusions.
   - Be transparent about any limitations in your analysis due to file size constraints.

9. Optimize token usage:
   - After analyzing code, summarize key findings and remove large code blocks from the conversation if they're no longer needed for immediate context.
   - If the conversation is getting long, consider summarizing earlier parts to free up tokens for new information.

10. Verify and cross-reference:
    - Always check the directory summary for total counts and truncated directories.
    - Use list_files on the root or specific directories to see all items if tree_directory output is truncated.

11. Avoid assumptions:
    - Never assume a directory or file is missing based solely on its absence in a truncated view.
    - Always verify using multiple tools and approaches before drawing conclusions about the project structure.

12. Adapt to project type:
    - Be flexible in your analysis, as project structures can vary widely depending on the type of project, programming language, or framework used.
    - Look for common patterns in structure, but be open to unique or non-standard organizations.

Remember: Your primary goal is to provide helpful, insightful analysis while maintaining the overall context of the conversation. Use the file size information provided by cat_multiple_files to guide your analysis strategy, and always err on the side of conserving tokens when in doubt. The goal is to understand the project structure accurately, regardless of its complexity or organization. Use the available tools wisely to build a comprehensive picture of the codebase.

When you need current information or feel that a search could provide a better answer, use the tavily_search tool. This tool performs a web search and returns a concise answer along with relevant sources.

Always strive to provide the most accurate, helpful, and detailed responses possible. If you're unsure about something, admit it and consider using the search tool to find the most current information.

{automode_status}

When in automode:
1. Set clear, achievable goals for yourself based on the user's request
2. Work through these goals one by one, using the available tools as needed
3. REMEMBER!! You can Read files, write code, LIST the files, analyze file structures, view multiple file contents, and even SEARCH and make edits, use these tools as necessary to accomplish each goal
4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
5. IMPORTANT RULE!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself, if you think we achieved the results established to the original request say "AUTOMODE_COMPLETE" in your response to exit the loop!
6. ULTRA IMPORTANT! You have access to this {iteration_info} amount of iterations you have left to complete the request, you can use this information to make decisions and to provide updates on your progress knowing the amount of responses you have left to complete the request.

Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.
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

def write_to_file(path, content):
    try:
        with open(path, 'w') as f:
            f.write(content)
        return f"Content written to file: {path}"
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

def tree_directory(path=".", max_lines=1000, max_depth=3, exclude_folders=None):
    if exclude_folders is None:
        exclude_folders = []

    def count_items(path, level=0):
        nonlocal total_dirs, total_files
        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_dir():
                        total_dirs += 1
                        if entry.name not in exclude_folders and level < max_depth:
                            count_items(entry.path, level + 1)
                    else:
                        total_files += 1
        except PermissionError:
            pass

    def _tree(path, level=0):
        nonlocal line_count, displayed_dirs, displayed_files, truncated_dirs
        result = []
        if level >= max_depth or line_count >= max_lines:
            return result
        try:
            entries = sorted(os.scandir(path), key=lambda e: e.name)
        except PermissionError:
            return [f"{' ' * (level * 4)}[Permission Denied]"]
        for entry in entries:
            if line_count >= max_lines:
                if level == 0:
                    truncated_dirs.append(entry.name)
                return result
            prefix = "│   " * level + "├── "
            result.append(f"{prefix}{entry.name}")
            line_count += 1
            if entry.is_dir():
                displayed_dirs += 1
                if entry.name not in exclude_folders:
                    result.extend(_tree(entry.path, level + 1))
                else:
                    result.append(f"{prefix}│   [Contents excluded]")
            else:
                displayed_files += 1
        return result

    total_dirs = 0
    total_files = 0
    count_items(path)

    line_count = 0
    displayed_dirs = 0
    displayed_files = 0
    truncated_dirs = []
    tree_output = _tree(path)
    
    summary = [
        f"\nDirectory summary:",
        f"Total directories: {total_dirs}",
        f"Total files: {total_files}",
        f"Displayed directories: {displayed_dirs}",
        f"Displayed files: {displayed_files}",
        f"Displayed items: {line_count}",
    ]
    
    if truncated_dirs:
        summary.append(f"Truncated directories: {', '.join(truncated_dirs)}")
        summary.append("Use tree_directory or list_files on these directories for more details.")
    
    if exclude_folders:
        summary.append(f"Folders with excluded contents: {', '.join(exclude_folders)}")
    
    return "\n".join(tree_output + summary)

def cat_multiple_files(file_paths, max_total_size_kb=200, max_single_file_size_kb=50):
    output = []
    total_size = 0
    files_to_display = []

    # Check file sizes
    for file_path in file_paths:
        try:
            file_size = os.path.getsize(file_path) / 1024  # Convert to KB
            if file_size > max_single_file_size_kb:
                output.append(f"Skipped {file_path}: File size ({file_size:.2f} KB) exceeds the maximum single file size limit ({max_single_file_size_kb} KB)")
                continue
            if total_size + file_size > max_total_size_kb:
                output.append(f"Skipped remaining files: Total size would exceed the maximum limit ({max_total_size_kb} KB)")
                break
            total_size += file_size
            files_to_display.append(file_path)
        except Exception as e:
            output.append(f"Error checking size of {file_path}: {str(e)}")

    # Display file contents
    for file_path in files_to_display:
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                output.append(f"--- {file_path} ---\n{content}\n")
        except Exception as e:
            output.append(f"Error reading {file_path}: {str(e)}")

    summary = f"\nFiles displayed: {len(files_to_display)} out of {len(file_paths)} requested"
    summary += f"\nTotal size of displayed files: {total_size:.2f} KB"
    
    return "\n".join(output) + summary

def tavily_search(query):
    try:
        response = tavily.qna_search(query=query, search_depth="advanced")
        return response
    except Exception as e:
        return f"Error performing search: {str(e)}"

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
        "description": "Create a new file at the specified path with optional content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
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
        "description": "Write content to an existing file at the specified path. Use this when you need to add or update content in an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
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
        "description": "List all files and directories in the root folder where the script is running. Use this when you need to see the contents of the current directory.",
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
        "name": "tree_directory",
        "description": "Display the file and directory structure. Useful for getting an overview of the file structure. Limited to a maximum number of lines and depth to prevent excessive output. Can exclude specified folders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the directory to display (default: current directory)"
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to output (default: 1000)"
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth of directories to display (default: 3)"
                },
                "exclude_folders": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "List of folder names to exclude from the tree (e.g., ['node_modules', '.git'])"
                }
            }
        }
    },
    {
        "name": "cat_multiple_files",
        "description": "Concatenate and display the contents of multiple files. Useful for reviewing the content of several files at once.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "An array of file paths to concatenate and display"
                }
            },
            "required": ["file_paths"]
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

def execute_tool(tool_name, tool_input):
    if tool_name == "create_folder":
        return create_folder(tool_input["path"])
    elif tool_name == "create_file":
        return create_file(tool_input["path"], tool_input.get("content", ""))
    elif tool_name == "write_to_file":
        return write_to_file(tool_input["path"], tool_input.get("content", ""))
    elif tool_name == "read_file":
        return read_file(tool_input["path"])
    elif tool_name == "list_files":
        return list_files(tool_input.get("path", "."))
    elif tool_name == "tree_directory":
        return tree_directory(
            tool_input.get("path", "."),
            tool_input.get("max_lines", 1000),
            tool_input.get("max_depth", 3),
            tool_input.get("exclude_folders")
        )
    elif tool_name == "cat_multiple_files":
        return cat_multiple_files(
            tool_input["file_paths"],
            tool_input.get("max_total_size_kb", 200),
            tool_input.get("max_single_file_size_kb", 50)
        )
    elif tool_name == "tavily_search":
        return tavily_search(tool_input["query"])
    else:
        return f"Unknown tool: {tool_name}"

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

def chat_with_claude(user_input, image_path=None):
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
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            system=update_system_prompt(),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
    except Exception as e:
        print_colored(f"Error calling Claude API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    assistant_response = ""
    exit_continuation = False
    
    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            print_colored(f"\nClaude: {content_block.text}", CLAUDE_COLOR)
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_name = content_block.name
            tool_input = content_block.input
            tool_use_id = content_block.id
            
            print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
            print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
            
            result = execute_tool(tool_name, tool_input)
            print_colored(f"Tool Result: {result}", RESULT_COLOR)
            
            conversation_history.append({"role": "assistant", "content": [content_block]})
            conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result
                    }
                ]
            })
            
            try:
                tool_response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system=update_system_prompt(),
                    messages=[msg for msg in conversation_history if msg.get('content')],
                    tools=tools,
                    tool_choice={"type": "auto"}
                )
                
                for tool_content_block in tool_response.content:
                    if tool_content_block.type == "text":
                        assistant_response += tool_content_block.text
                        print_colored(f"\nClaude: {tool_content_block.text}", CLAUDE_COLOR)
            except Exception as e:
                print_colored(f"Error in tool response: {str(e)}", TOOL_COLOR)
                assistant_response += "\nI encountered an error while processing the tool result. Please try again."
    
    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})
    
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

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
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
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
    except Exception as e:
        print_colored(f"Error calling Claude API: {str(e)}", TOOL_COLOR)
        return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    
    assistant_response = ""
    exit_continuation = False
    
    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
            print_colored(f"\nClaude: {content_block.text}", CLAUDE_COLOR)
            if CONTINUATION_EXIT_PHRASE in content_block.text:
                exit_continuation = True
        elif content_block.type == "tool_use":
            tool_name = content_block.name
            tool_input = content_block.input
            tool_use_id = content_block.id
            
            print_colored(f"\nTool Used: {tool_name}", TOOL_COLOR)
            print_colored(f"Tool Input: {tool_input}", TOOL_COLOR)
            
            result = execute_tool(tool_name, tool_input)
            print_colored(f"Tool Result: {result}", RESULT_COLOR)
            
            conversation_history.append({"role": "assistant", "content": [content_block]})
            conversation_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result
                    }
                ]
            })
            
            try:
                tool_response = client.messages.create(
                    model="claude-3-5-sonnet-20240620",
                    max_tokens=4000,
                    system=update_system_prompt(current_iteration, max_iterations),
                    messages=[msg for msg in conversation_history if msg.get('content')],
                    tools=tools,
                    tool_choice={"type": "auto"}
                )
                
                for tool_content_block in tool_response.content:
                    if tool_content_block.type == "text":
                        assistant_response += tool_content_block.text
                        print_colored(f"\nClaude: {tool_content_block.text}", CLAUDE_COLOR)
            except Exception as e:
                print_colored(f"Error in tool response: {str(e)}", TOOL_COLOR)
                assistant_response += "\nI encountered an error while processing the tool result. Please try again."
    
    if assistant_response:
        conversation_history.append({"role": "assistant", "content": assistant_response})
    
    return assistant_response, exit_continuation

def main():
    global automode
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
            
            print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
        else:
            response, _ = chat_with_claude(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()
