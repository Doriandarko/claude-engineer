import asyncio
import base64    
from typing import List, Dict, Union
import json 
import queue
import difflib
import io
import json
import os
import re
import tempfile
import threading
import time
import wave
import subprocess
import itertools

import aiohttp
import numpy as np
import simpleaudio as sa
import sounddevice as sd
from anthropic import Anthropic, APIError, APIStatusError
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image
from pydub import AudioSegment
from pydub.playback import play
from pynput import keyboard
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import (BarColumn, Progress, SpinnerColumn,
                           TaskProgressColumn, TextColumn)
from rich.syntax import Syntax
from rich.live import Live
from rich.spinner import Spinner

ctrl_pressed = False
esc_pressed = False


def on_press(key):
    global ctrl_pressed
    global esc_pressed
    if key == keyboard.Key.ctrl:
        ctrl_pressed = True
    elif key == keyboard.Key.esc:
        esc_pressed = True

def on_release(key):
    global ctrl_pressed
    global esc_pressed
    if key == keyboard.Key.ctrl:
        ctrl_pressed = False
    elif key == keyboard.Key.esc:
        esc_pressed = False

# Load environment variables from .env file
load_dotenv(override=True)

console = Console()
voice_input = ""

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

# Initialize the Anthropic client
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Tavily API configuration
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_API_URL = "https://api.tavily.com/search"

# Add error checking for required environment variables
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY is not set in the environment variables")

if not os.getenv("TAVILY_API_KEY"):
    raise ValueError("TAVILY_API_KEY is not set in the environment variables")

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False

# base prompt
base_system_prompt = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model, specializied in software development with access to a variety of tool and the ability to instruct and direct a coding agent. Your capabilities include:

1. Creating and managing project structures
2. Writing, debugging, and improving code across multiple languages
3. Providing architectural insights and applying design patterns
4. Staying current with the latest technologies and best practices
5. Analyzing and manipulating files within the project directory
6. Performing web searches for up-to-date information

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
- For file modifications, use edit_and_apply. This now processes files in batches.
- After making changes, always review the diff output to ensure accuracy.
- Proactively use tavily_search when you need up-to-date information or context.

Code Editing Best Practices:
1. When using edit_and_apply, each batch will be processed for potential improvements.
2. Analyze the code and determine necessary modifications within each batch.
3. Pay close attention to maintaining the overall structure, logic, and indentation of the code.
4. Ensure that your edits do not break the existing code structure or formatting.
5. If a batch contains the start of a function but not its end, include the entire function in that batch.
6. Review changes thoroughly after each modification to ensure formatting consistency.


Error Handling and Recovery:
- If a tool operation fails, analyze the error message and attempt to resolve the issue.
- For file-related errors, check file paths and permissions before retrying.
- If a search fails, try rephrasing the query or breaking it into smaller, more specific searches.

Project Creation and Management:
1. Start by creating a root folder for new projects.
2. Create necessary subdirectories and files within the root folder.
3. Organize the project structure logically, following best practices for the specific project type.


Always strive for accuracy, clarity, and efficiency in your responses and actions. If uncertain, use the tavily_search tool or admit your limitations.

If you want a specific part of your response to be spoken aloud to the user,                                                                                                                                                             │
  enclose that part in double asterisks (**) on each side.                                                                                                                                                                                          │
                                                                                                                                                                                                                                           │
  Example:                                                                                                                                                                                                                                 │
  Hello! **How can I assist you today?**                                                                                                                                                                                                        │
                                                                                                                                                                                                                                           │
  Only the text between the double asterisks will be converted to speech.        

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

def speech_to_text(filename="recorded_audio.wav", debug=False):
    is_recording = False
    recorded_audio = []
    samplerate = 44100  # Sample rate

    def transcribe_audio_openai(file_path):
        client = OpenAI()
        with open(file_path, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                file=audio, model="whisper-1", language="en"
            )
        if debug:
            print("Transcribed Text (OpenAI):", transcript)
        return transcript

    def on_press(key):
        nonlocal is_recording
        if key == keyboard.Key.ctrl:
            if not is_recording:
                is_recording = True
                recorded_audio.clear()

    def on_release(key):
        nonlocal is_recording
        if key == keyboard.Key.ctrl:
            if is_recording:
                is_recording = False
                return False  # Stop listener

    def callback(indata, frames, time, status):
        if is_recording:
            recorded_audio.append(indata.copy())

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        with sd.InputStream(samplerate=samplerate, channels=1, callback=callback):
            listener.join()

    if not recorded_audio:
        return None

    recording = np.concatenate(recorded_audio, axis=0)
    recording_int = np.int16(recording * 32767)
    
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(recording_int.tobytes())

    return transcribe_audio_openai(filename)

def text_to_speech(message, service="openai"):
    def convert_opus_to_wav(opus_file_path):
        wav_file_path = opus_file_path.replace(".opus", ".wav")
        command = f"ffmpeg -i {opus_file_path} {wav_file_path} > /dev/null 2>&1"
        os.system(command)
        return wav_file_path

    def audio_player(playback_queue):
        while True:
            wav_path = playback_queue.get()
            try:
                audio = AudioSegment.from_file(wav_path, format="wav")
                play_obj = sa.play_buffer(
                    audio.raw_data,
                    num_channels=audio.channels,
                    bytes_per_sample=audio.sample_width,
                    sample_rate=audio.frame_rate,
                )
                play_obj.wait_done()
                print(f"Audio played: {wav_path}")
            except subprocess.CalledProcessError as e:
                print(f"Subprocess error: {e}")
            except Exception as e:
                print(f"Unexpected error: {e}")
            finally:
                os.remove(wav_path)
                playback_queue.task_done()

    def create_temp_file(suffix=".wav"):
        temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
        os.close(temp_fd)
        return temp_path

    def generate_with_openai(message):
        temp_path = create_temp_file(suffix=".opus")
        client = OpenAI()
        
        # Extract the text from the Transcription object if necessary
        if hasattr(message, 'text'):
            message = message.text
        
        response = client.audio.speech.create(
            model="tts-1", response_format="opus", voice="alloy", input=message, speed="1.0"
        )
        with open(temp_path, "wb") as f:
            f.write(response.content)
            print(f"Audio generated: {temp_path}")
            return temp_path

    message_queue = queue.Queue()
    playback_queue = queue.Queue()

    def audio_generator():
        while True:
            service, message = message_queue.get()
            if service == "openai":
                try:
                    temp_path = generate_with_openai(message)
                    playback_queue.put(convert_opus_to_wav(temp_path))
                except Exception as e:
                    print(f"Error generating audio: {e}")
            else:
                print(f"Unknown service: {service}")
            message_queue.task_done()

    message_queue.put((service, message))

    threading.Thread(target=audio_generator, daemon=True).start()
    threading.Thread(target=audio_player, args=(playback_queue,), daemon=True).start()

    # Wait for the queues to be empty
    message_queue.join()
    playback_queue.join()


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



async def send_to_ai_for_editing(file_content, batch_content, start_line_number, instructions, conversation):
    try:
        lines_to_edit = batch_content.splitlines(keepends=True)
        lines_with_numbers = [f"Line {i}: {line}" for i, line in enumerate(lines_to_edit, start=start_line_number)]
        lines_to_edit_str = ''.join(lines_with_numbers)

        # Ensure the conversation ends with an assistant message
        if not conversation or conversation[-1]["role"] == "user":
            conversation.append({"role": "assistant", "content": "I'm ready to edit the next batch of lines. Please provide them."})

        # Add the new user message with the lines to edit
        conversation.append({"role": "user", "content": f"Edit these lines:\n{lines_to_edit_str}"})

        # Make the API call
        response = client.messages.create(
            model=CODEEDITORMODEL,
            max_tokens=4000,
            messages=conversation,
            system=(
                "You are an AI assistant that edits code files. Improve the following lines of code based on the provided instructions and file context. "
                "Consider the entire file context when making changes to these specific lines. "
                "CRITICAL: Preserve the exact indentation and formatting of each line. "
                "You can add or remove lines as necessary to improve the code. "
                "If adding lines, match the indentation of surrounding lines. "
                "If moving lines, maintain their original indentation in the new position. "
                "If no improvements are needed or if the instructions don't apply, return the lines unchanged. "
                "Consider the file type when formatting the edited lines. "
                "IMPORTANT: RETURN ONLY THE EDITED LINES, WITH EXACT INDENTATION AND ORIGINAL LINE ENDINGS. NO EXPLANATIONS OR COMMENTS. "
                "To ensure a successful edit, prefix each line with its line number and a colon, followed by a single space, then the line content with its original indentation and line ending, e.g., '1: def example():\n', '2:     print(\"Hello, World!\")\n'"
            )
        )

        # Return the raw response from the AI
        return response.content[0].text

    except Exception as e:
        console.print(f"Error in AI editing: {str(e)}", style="bold red")
        return batch_content  # Return original batch content if any exception occurs



async def edit_and_apply(path, instructions, batch_size=50, is_automode=False):
    try:
        with open(path, 'r') as file:
            original_content = file.read()

        edited_content = await process_code_file(path, instructions, batch_size)

        if edited_content != original_content:
            # Print the raw AI output for debugging
            console.print(Panel("Raw AI Output:", title="Debug", style="bold yellow"))
            console.print(edited_content)

            diff_result = generate_and_apply_diff(original_content, edited_content, path)

            console.print(Panel("The following changes have been suggested:", title="File Changes", style="cyan"))
            console.print(diff_result)

            if not is_automode:
                confirm = console.input("[bold yellow]Do you want to apply these changes? (yes/no): [/bold yellow]")
                if confirm.lower() != 'yes':
                    return "Changes were not applied."

            with open(path, 'w') as file:
                file.write(edited_content)
            return f"Changes applied to {path}:\n{diff_result}"
        else:
            return f"No changes needed for {path}"
    except Exception as e:
        return f"Error editing/applying to file: {str(e)}"


async def process_code_file(file_path, instructions, batch_size=50):
    with open(file_path, 'r') as f:
        file_content = f.read()

    lines = file_content.splitlines(keepends=True)
    edited_content = []
    total_lines = len(lines)
    conversation = [
        {"role": "user", "content": f"File content:\n{file_content}\n\nInstructions: {instructions}"},
        {"role": "assistant", "content": "Understood. I'm ready to edit the file based on your instructions. Please provide the first batch of lines to edit."}
    ]

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
            edited_batch = await send_to_ai_for_editing(file_content, batch_content, i+1, instructions, conversation)
            
            edited_content.append(edited_batch)

            progress.update(task, advance=len(batch))
            await asyncio.sleep(0.01)

    progress.update(task, completed=total_lines)

    return ''.join(edited_content)

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

async def tavily_search(query):
    try:
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": TAVILY_API_KEY
        }
        payload = {
            "query": query,
            "search_depth": "advanced"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(TAVILY_API_URL, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result
                else:
                    return f"Error performing search: HTTP {response.status}, {await response.text()}"
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
        "name": "edit_and_apply",
        "description": "Apply AI-powered improvements to a file based on specific instructions. This function reads the file, processes it in batches using AI with conversation history, generates a diff, and allows the user to confirm changes before applying them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to edit"
                },
                "instructions": {
                    "type": "string",
                    "description": "Specific instructions for code changes"
                },
                "batch_size": {
                    "type": "integer",
                    "description": "Number of lines to process in each batch (default is 50)",
                    "default": 50
                }
            },
            "required": ["path", "instructions"]
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
                        batch_size=tool_input.get("batch_size", 10),
                        is_automode=automode
                    )
                elif tool_name == "read_file":
                    return read_file(tool_input["path"])
                elif tool_name == "list_files":
                    return list_files(tool_input.get("path", "."))
                elif tool_name == "tavily_search":
                    return await tavily_search(tool_input["query"])
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

async def chat_with_claude(user_input, image_path=None, current_iteration=None, max_iterations=None):
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
        console.print(Panel("Image message added to conversation history", title_align="left", title="Image Added", expand=False, style="green"))
    else:
        current_conversation.append({"role": "user", "content": user_input})

    messages = conversation_history + current_conversation

    try:
        response = client.messages.create(
            model=MAINMODEL,
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            stream=True  # Enable streaming
        )
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

    # Handle streaming response
    for chunk in response:
        if chunk.type == "content_block_start":
            if chunk.content_block.type == "text":
                console.print("[bold green]Claude:[/bold green] ", end="")
            elif chunk.content_block.type == "tool_use":
                tool_uses.append(chunk.content_block)
        elif chunk.type == "content_block_delta":
            if chunk.delta.type == "text_delta":
                console.print(chunk.delta.text, end="")
                assistant_response += chunk.delta.text
                if CONTINUATION_EXIT_PHRASE in chunk.delta.text:
                    exit_continuation = True
        elif chunk.type == "content_block_stop":
            console.print()  # Add a newline at the end of the response

    console.print("\n")

    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="green"))
        console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="green"))

        try:
            result = await execute_tool(tool_name, tool_input)
            console.print(Panel(str(result), title_align="left", title="Tool Result", style="green"))
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
            tool_response = client.messages.create(
                model=TOOLCHECKERMODEL,
                max_tokens=4000,
                system=update_system_prompt(current_iteration, max_iterations),
                messages=messages,
                stream=True  # Enable streaming for tool response
            )

            tool_checker_response = ""
            console.print("[bold green]Claude (Tool Response):[/bold green] ", end="")
            for chunk in tool_response:
                if chunk.type == "content_block_delta" and chunk.delta.type == "text_delta":
                    console.print(chunk.delta.text, end="")
                    tool_checker_response += chunk.delta.text
            console.print()  # Add a newline at the end of the tool response
            assistant_response += "\n\n" + tool_checker_response
        except APIError as e:
            error_message = f"Error in tool response: {str(e)}"
            console.print(Panel(error_message, title="Error", style="bold red"))
            assistant_response += f"\n\n{error_message}"

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    conversation_history = messages + [{"role": "assistant", "content": assistant_response}]

    return assistant_response, exit_continuation




async def main():
    global automode, conversation_history, voice_input, esc_pressed, ctrl_pressed
    
    ctrl_pressed = False
    esc_pressed = False
    
    console.print(Panel("Welcome to the Claude-3-Sonnet Engineer Chat with Image Support!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("Type 'voice' to enter voice input mode.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")
    
    def speech_to_text_thread(voice_input_queue, stop_event):
        while not stop_event.is_set():
            voice_input = speech_to_text()
            if voice_input and hasattr(voice_input, 'text'):
                voice_input_queue.put(voice_input.text)
            time.sleep(0.1)

    voice_mode = False
    voice_input_queue = queue.Queue()
    stop_event = threading.Event()

    keyboard_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    keyboard_listener.start()

    while True:
        if not voice_mode:
            console.print("[bold cyan]You:[/bold cyan] ", end="")
            user_input = input()
        
        if user_input.lower() == 'voicemode':
            voice_mode = True
            console.print(Panel("Entering voice mode. Hold Ctrl to speak, release when done. Say 'exit voicemode' or press Esc to exit voice mode.", title="Voice Mode", style="bold blue"))
            
            stop_event.clear()
            speech_thread = threading.Thread(target=speech_to_text_thread, args=(voice_input_queue, stop_event), daemon=True)
            speech_thread.start()
            
            spinner = Spinner("dots")
            
            with Live(spinner, refresh_per_second=10) as live:
                live.update("Hold Ctrl to speak...")
                
                while voice_mode:
                    try:
                        if ctrl_pressed:
                            live.update("Listening...")
                            
                            while ctrl_pressed:
                                await asyncio.sleep(0.1)
                            
                            live.update("Processing...")
                            
                            user_input = await asyncio.wait_for(wait_for_voice_input(voice_input_queue), timeout=5.0)
                            
                            if user_input:
                                live.update(f"[bold cyan]You (voice):[/bold cyan] {user_input}")
                            
                                if user_input.lower() == 'exit voicemode':
                                    voice_mode = False
                                    live.update("Exiting voice mode. Returning to text input.")
                                    break
                            
                                response, _ = await chat_with_claude(user_input)
                                
                                # Extract and process ** tags
                                speak_content = re.findall(r'\*\*(.*?)\*\*', response, re.DOTALL)
                                for content in speak_content:
                                    text_to_speech(content)
                                
                                # Remove ** tags from the response
                                response = re.sub(r'\*\*', '', response)
                                
                                live.update(Panel(Markdown(response), title="Claude's Response", title_align="left", expand=False))
                            else:
                                live.update("No speech detected. Please try again.")
                        
                        elif esc_pressed:
                            voice_mode = False
                            esc_pressed = False
                            live.update("Exiting voice mode. Returning to text input.")
                            break
                        
                        await asyncio.sleep(0.1)
                        
                    except asyncio.TimeoutError:
                        live.update("Voice input timed out. Please try again.")
                    
                    live.update("Hold Ctrl to speak...")
            
            # Clean up voice mode resources
            stop_event.set()
            speech_thread.join(timeout=1)
            voice_input_queue = queue.Queue()
            continue

        if user_input.lower() == 'exit':
            if voice_mode:
                console.print(Panel("OK, you're back to typing.", title="Exiting Voice", style="bold blue"))
                voice_mode = False
                speech_thread.join()
                continue
            else:
                console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
                break

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

    keyboard_listener.stop()

async def wait_for_voice_input(queue):
    while queue.empty():
        await asyncio.sleep(0.1)
    return queue.get()

if __name__ == "__main__":
    asyncio.run(main())