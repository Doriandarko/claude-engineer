import os
import json
from tavily import TavilyClient
import base64
from PIL import Image
import io
import re
from anthropic import Anthropic
import difflib
import time
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

console = Console()

from dotenv import load_dotenv

# try to load the .env file. If it doesn't exist, the code will continue without it
load_dotenv()

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = "AUTOMODE_COMPLETE"
MAX_CONTINUATION_ITERATIONS = 25

# Models to use
MAINMODEL = "claude-3-5-sonnet-20240620"
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"
CODECHECKERMODEL = "claude-3-5-sonnet-20240620"

# Initialize the Anthropic client
if "ANTHROPIC_API_KEY" in os.environ:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = Anthropic(api_key=api_key)
else:
    client = Anthropic(api_key="YOUR KEY")

# Initialize the Tavily client
if "TAVILY_API_KEY" in os.environ:
    api_key = os.environ["TAVILY_API_KEY"]
    tavily = TavilyClient(api_key=api_key)
else:
    tavily = TavilyClient(api_key="YOUR KEY")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# Base system prompt
base_system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model. You are an exceptional software developer with vast knowledge across multiple programming languages, frameworks, and best practices. Your capabilities include:

1. Creating project structures, including folders and files
2. Writing clean, efficient, and well-documented code
3. Debugging complex issues and providing detailed explanations
4. Offering architectural insights and design patterns
5. Staying up-to-date with the latest technologies and industry trends
6. Reading and analyzing existing files in the project directory
7. Listing files in the root directory of the project
8. Performing web searches to get up-to-date information or additional context
9. When you use search, make sure you use the best query to get the most accurate and up-to-date information
10. Analyzing images provided by the user

Available tools and when to use them:

1. create_folder: Use this tool to create a new folder at a specified path.
   Example: When setting up a new project structure.

2. create_file: Use this tool to create a new file at a specified path with content.
   Example: When creating new source code files or configuration files.

3. search_file: Use this tool to search for specific patterns in a file and get the line numbers where the pattern is found. This is especially useful for large files.
   Example: When you need to locate specific functions or variables in a large codebase.

4. edit_file: Use this tool to edit a specific range of lines in a file. You should use this after using search_file to identify the lines you want to edit.
   Example: When you need to modify a specific function or block of code.

5. read_file: Use this tool to read the contents of a file at a specified path.
   Example: When you need to examine the current content of a file before making changes.

6. list_files: Use this tool to list all files and directories in a specified folder (default is the current directory).
   Example: When you need to understand the current project structure or find specific files.

7. tavily_search: Use this tool to perform a web search and get up-to-date information or additional context.
   Example: When you need current information about a technology, library, or best practice.

IMPORTANT: For file modifications, always use the search_file tool first to identify the lines you want to edit, then use the edit_file tool to make the changes. This two-step process ensures more accurate and targeted edits.

Follow these steps when editing files:
1. Use the read_file tool to examine the current contents of the file you want to edit.
2. For longer files, use the search_file tool to find the specific lines you want to edit.
3. Use the edit_file tool with the line numbers returned by search_file to make the changes.

This approach will help you make precise edits to files of any size or complexity.

When asked to create a project:
- Always start by creating a root folder for the project using the create_folder tool.
- Then, create the necessary subdirectories and files within that root folder using the create_folder and create_file tools.
- Organize the project structure logically and follow best practices for the specific type of project being created.

When asked to make edits or improvements:
- ALWAYS START by using the read_file tool to examine the contents of existing files.
- Use the search_file tool to locate the specific lines you want to edit.
- Use the edit_file tool to make the necessary changes.
- Analyze the code and suggest improvements or make necessary edits.
- Pay close attention to the existing code structure.
- Ensure that you're replacing old code with new code, not just adding new code alongside the old.
- After making changes, always re-read the entire file to check for any unintended duplications.
- If you notice any duplicated code after your edits, immediately remove the duplication and explain the correction.

Be sure to consider the type of project (e.g., Python, JavaScript, web application) when determining the appropriate structure and files to include.

Always strive to provide the most accurate, helpful, and detailed responses possible. If you're unsure about something, admit it and consider using the tavily_search tool to find the most current information.
"""

# Auto mode-specific system prompt
automode_system_prompt = """
You are currently in automode!!!

When in automode:
1. Set clear, achievable goals for yourself based on the user's request
2. Work through these goals one by one, using the available tools as needed
3. REMEMBER!! You can read files, write code, search for specific lines of code to make edits and list the files, search the web. Use these tools as necessary to accomplish each goal
4. ALWAYS READ A FILE BEFORE EDITING IT IF YOU ARE MISSING CONTENT. Provide regular updates on your progress
5. IMPORTANT RULE!! When you know your goals are completed, DO NOT CONTINUE IN POINTLESS BACK AND FORTH CONVERSATIONS with yourself. If you think you've achieved the results established in the original request, say "AUTOMODE_COMPLETE" in your response to exit the loop!
6. ULTRA IMPORTANT! You have access to this {iteration_info} amount of iterations you have left to complete the request. Use this information to make decisions and to provide updates on your progress, knowing the number of responses you have left to complete the request.

Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

YOU NEVER ASK "Is there anything else you'd like to add or modify in the project or code?" or "Is there anything else you'd like to add or modify in the project?" or anything like that once you feel the request is complete. just say "AUTOMODE_COMPLETE" in your response to exit the loop!
"""

# Base system prompt and automode_system_prompt remain unchanged

def update_system_prompt(current_iteration=None, max_iterations=None):
    global base_system_prompt, automode_system_prompt
    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return base_system_prompt + "\n\n" + automode_system_prompt.format(iteration_info=iteration_info)
    else:
        return base_system_prompt

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

        # Create a panel with the highlighted diff
        diff_panel = Panel(
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="cyan"
        )

        # Print the panel
        console.print(diff_panel)

        # Count the number of added and removed lines
        added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
        removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

        # Create a summary message
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

def search_file(path, search_pattern):
    try:
        with open(path, 'r') as file:
            content = file.readlines()

        matches = []
        for i, line in enumerate(content, 1):
            if re.search(search_pattern, line):
                matches.append(i)

        return f"Matches found at lines: {matches}"
    except Exception as e:
        return f"Error searching file: {str(e)}"

def edit_file(path, start_line, end_line, new_content):
    try:
        with open(path, 'r') as file:
            content = file.readlines()

        original_content = ''.join(content)

        # Convert to 0-based index
        start_index = start_line - 1
        end_index = end_line

        # Replace the specified lines with new content
        content[start_index:end_index] = new_content.splitlines(True)

        new_content = ''.join(content)

        diff_result = generate_and_apply_diff(original_content, new_content, path)

        return f"Successfully edited lines {start_line} to {end_line} in {path}\n{diff_result}"
    except Exception as e:
        return f"Error editing file: {str(e)}"

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
        "description": "Create a new file at the specified path with content. Use this when you need to create a new file in the project structure.",
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
        "description": "Search for a specific pattern in a file and return the line numbers where the pattern is found.",
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
        "name": "edit_file",
        "description": "Edit a specific range of lines in a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to edit"
                },
                "start_line": {
                    "type": "integer",
                    "description": "The starting line number of the edit"
                },
                "end_line": {
                    "type": "integer",
                    "description": "The ending line number of the edit"
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content to replace the specified lines"
                }
            },
            "required": ["path", "start_line", "end_line", "new_content"]
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
    try:
        if tool_name == "create_folder":
            return create_folder(tool_input["path"])
        elif tool_name == "create_file":
            return create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "search_file":
            return search_file(tool_input["path"], tool_input["search_pattern"])
        elif tool_name == "edit_file":
            return edit_file(tool_input["path"], tool_input["start_line"], tool_input["end_line"], tool_input["new_content"])
        elif tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "list_files":
            return list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            return tavily_search(tool_input["query"])
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

def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
    global conversation_history, automode

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
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"}
        )
    except Exception as e:
        console.print(Panel(f"Error calling Claude API: {str(e)}", title="API Error", style="bold red"))
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

    # Display main model response
    console.print(Panel(Markdown(assistant_response), title="Claude's Response", title_align="left", expand=False))

    # Process tool uses
    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="yellow"))
        console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="yellow"))

        result = execute_tool(tool_name, tool_input)
        console.print(Panel(result, title_align="left", title="Tool Result", style="green"))

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
            tool_response = client.messages.create(
                model=TOOLCHECKERMODEL,
                max_tokens=4000,
                system=update_system_prompt(current_iteration, max_iterations),
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )

            tool_checker_response = ""
            for tool_content_block in tool_response.content:
                if tool_content_block.type == "text":
                    tool_checker_response += tool_content_block.text
            #tookchecker response
            console.print(Panel(Markdown(tool_checker_response), title_align="left", title="Claude's Response"))
            assistant_response += "\n\n" + tool_checker_response
        except Exception as e:
            error_message = f"Error in tool response: {str(e)}"
            console.print(Panel(error_message, title="Error", style="bold red"))
            assistant_response += f"\n\n{error_message}"

    # Check if edit_file was used and perform a review
    if "edit_file" in assistant_response:
        file_path_match = re.search(r"Successfully edited lines \d+ to \d+ in (.+)\n", assistant_response)
        if file_path_match:
            file_path = file_path_match.group(1)
            file_content = read_file(file_path)
            review_prompt = f"""I've made edits to the file {file_path}. Please perform a thorough review of the entire file content:

{file_content}

1. Check for any unintended duplications:
   - If you find duplications, remove them and explain the changes.
   - Ensure that the removal of duplications doesn't affect the code's functionality.

2. Verify that no essential code is missing:
   - Look for any incomplete functions, classes, or logic flows.
   - Identify any missing imports, variable declarations, or closing brackets.

3. Assess the overall structure and coherence of the code:
   - Ensure that the edits maintain the logical flow of the code.
   - Check that all necessary components are present and properly connected.

If you find any issues (duplications, missing code, or structural problems), please provide:
1. A clear explanation of the issue
2. The corrected code snippet
3. A brief justification for the changes

If no issues are found, confirm that the file is clean, complete, and structurally sound.

Please present your review findings and any necessary corrections."""

            try:
                review_response = client.messages.create(
                    model=CODECHECKERMODEL,
                    max_tokens=4000,
                    system=update_system_prompt(current_iteration, max_iterations),
                    messages=messages + [{"role": "user", "content": review_prompt}],
                    tools=tools,
                    tool_choice={"type": "auto"}
                )

                review_text = ""
                for review_content_block in review_response.content:
                    if review_content_block.type == "text":
                        review_text += review_content_block.text

                console.print(Panel(Markdown(review_text), title_align="left", title="Code Review", style="bold blue"))
                assistant_response += "\n\nCode Review:\n" + review_text

                # If the review found and fixed duplications, update the file
                if "removed" in review_text.lower() or "fixed" in review_text.lower():
                    updated_content = re.search(r"Updated file content:\n```(?:python)?\n(.*?)```", review_text, re.DOTALL)
                    if updated_content:
                        with open(file_path, 'w') as file:
                            file.write(updated_content.group(1))
                        console.print(Panel("File updated to remove duplications.", title_align="left", title="File Update", style="bold green"))

            except Exception as e:
                error_message = f"Error in review response: {str(e)}"
                console.print(Panel(error_message, title="Error", style="bold red"))
                assistant_response += f"\n\n{error_message}"

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    # Update the global conversation history
    conversation_history = messages + [{"role": "assistant", "content": assistant_response}]

    return assistant_response, exit_continuation

def main():
    global automode, conversation_history
    console.print(Panel("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")

    while True:
        user_input = console.input("[bold cyan]You:[/bold cyan] ")

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
            break

        if user_input.lower() == 'image':
            image_path = console.input("[bold cyan]Drag and drop your image here, then press enter:[/bold cyan] ").strip().replace("'", "")

            if os.path.isfile(image_path):
                user_input = console.input("[bold cyan]You (prompt for image):[/bold cyan] ")
                response, _ = chat_with_claude(user_input, image_path)
                # process_and_display_response(response) # Remove this call
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
                        response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
                        # process_and_display_response(response) # Remove this call

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(Panel("Automode completed.", title_align="left", title="Automode", style="green"))
                            automode = False
                        else:
                            console.print(Panel(f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode. ", title_align="left", title="Automode", style="yellow"))
                            # console.print(Panel("Press Ctrl+C to exit automode.", style="bold yellow"))
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(Panel("Max iterations reached. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                            automode = False
                except KeyboardInterrupt:
                    console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                    automode = False
                    # Ensure the conversation history ends with an assistant message
                    if conversation_history and conversation_history[-1]["role"] == "user":
                        conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
            except KeyboardInterrupt:
                console.print(Panel("\nAutomode interrupted by user. Exiting automode.", title_align="left", title="Automode", style="bold red"))
                automode = False
                # Ensure the conversation history ends with an assistant message
                if conversation_history and conversation_history[-1]["role"] == "user":
                    conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})

            console.print(Panel("Exited automode. Returning to regular chat.", style="green"))
        else:
            response, _ = chat_with_claude(user_input)
            # process_and_display_response(response) # Remove this call

if __name__ == "__main__":
    main()
