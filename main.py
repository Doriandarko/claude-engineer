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
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
import glob
import speech_recognition as sr
import websockets
from pydub import AudioSegment
from pydub.playback import play
import datetime
import venv
import sys
import signal
import logging
from typing import Tuple, Optional, Dict, Any
import mimetypes
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import subprocess

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables from .env file
load_dotenv()

# Create a recognizer object
recognizer = sr.Recognizer()

# Define a list of voice commands
VOICE_COMMANDS = {
    "exit voice mode": "exit_voice_mode",
    "save chat": "save_chat",
    "reset conversation": "reset_conversation"
}


# Global variables
recognizer = None
microphone = None

# 11 Labs TTS
tts_enabled = True
use_tts = False
ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')
VOICE_ID = 'YOUR ID'
MODEL_ID = 'eleven_turbo_v2_5'


async def text_to_speech(text):
    if not ELEVEN_LABS_API_KEY:
        console.print("ElevenLabs API key not found. Text-to-speech is disabled.", style="bold yellow")
        console.print("Fallback: Printing the text instead.", style="bold yellow")
        console.print(text)
        return

    uri = f"wss://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream-input?model_id={MODEL_ID}"
    
    async def chunk_text(text):
        sentences = re.split('(?<=[.,?!;:—\-()[\]{}]) +', text)
        for sentence in sentences:
            yield sentence + " "

    try:
        logging.info("Connecting to ElevenLabs API")
        async with websockets.connect(uri, extra_headers={'xi-api-key': ELEVEN_LABS_API_KEY}) as websocket:
            logging.info("Connected to ElevenLabs API")
            await websocket.send(json.dumps({
                "text": " ",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                "xi_api_key": ELEVEN_LABS_API_KEY,
            }))

            audio_stream = AudioSegment.empty()
            async for chunk in chunk_text(text):
                logging.debug(f"Sending chunk: {chunk}")
                await websocket.send(json.dumps({"text": chunk, "try_trigger_generation": True}))

            await websocket.send(json.dumps({"text": ""}))  # Closing message
            logging.info("Sent all text chunks")

            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    if data.get('audio'):
                        audio_data = base64.b64decode(data['audio'])
                        audio_chunk = AudioSegment.from_mp3(io.BytesIO(audio_data))
                        audio_stream += audio_chunk
                        play(audio_chunk)  # Play each chunk as it's received
                        logging.debug("Played audio chunk")
                    elif data.get('isFinal'):
                        logging.info("Received final message")
                        break
                except websockets.exceptions.ConnectionClosed:
                    logging.error("WebSocket connection closed unexpectedly")
                    console.print("WebSocket connection closed unexpectedly", style="bold red")
                    break

    except websockets.exceptions.InvalidStatusCode as e:
        logging.error(f"Failed to connect to ElevenLabs API: {e}")
        console.print(f"Failed to connect to ElevenLabs API: {e}", style="bold red")
        console.print("Fallback: Printing the text instead.", style="bold yellow")
        console.print(text)
    except Exception as e:
        logging.error(f"Error in text-to-speech: {str(e)}")
        console.print(f"Error in text-to-speech: {str(e)}", style="bold red")
        console.print("Fallback: Printing the text instead.", style="bold yellow")
        console.print(text)

def initialize_speech_recognition():
    global recognizer, microphone
    recognizer = sr.Recognizer()
    microphone = sr.Microphone()
    
    # Adjust for ambient noise
    with microphone as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
    
    logging.info("Speech recognition initialized")

async def voice_input(max_retries=3):
    global recognizer, microphone

    for attempt in range(max_retries):
        # Reinitialize speech recognition objects before each attempt
        initialize_speech_recognition()

        try:
            with microphone as source:
                console.print("Listening... Speak now.", style="bold green")
                audio = recognizer.listen(source, timeout=5)
                
            console.print("Processing speech...", style="bold yellow")
            text = recognizer.recognize_google(audio)
            console.print(f"You said: {text}", style="cyan")
            return text.lower()
        except sr.WaitTimeoutError:
            console.print(f"No speech detected. Attempt {attempt + 1} of {max_retries}.", style="bold red")
            logging.warning(f"No speech detected. Attempt {attempt + 1} of {max_retries}")
        except sr.UnknownValueError:
            console.print(f"Speech was unintelligible. Attempt {attempt + 1} of {max_retries}.", style="bold red")
            logging.warning(f"Speech was unintelligible. Attempt {attempt + 1} of {max_retries}")
        except sr.RequestError as e:
            console.print(f"Could not request results from speech recognition service; {e}", style="bold red")
            logging.error(f"Could not request results from speech recognition service; {e}")
            return None
        except Exception as e:
            console.print(f"Unexpected error in voice input: {str(e)}", style="bold red")
            logging.error(f"Unexpected error in voice input: {str(e)}")
            return None
        
        # Add a short delay between attempts
        await asyncio.sleep(1)
    
    console.print("Max retries reached. Returning to text input mode.", style="bold red")
    logging.info("Max retries reached in voice input. Returning to text input mode.")
    return None

def cleanup_speech_recognition():
    global recognizer, microphone
    recognizer = None
    microphone = None
    logging.info('Speech recognition objects cleaned up')

def process_voice_command(command):
    if command in VOICE_COMMANDS:
        action = VOICE_COMMANDS[command]
        if action == "exit_voice_mode":
            return False, "Exiting voice mode."
        elif action == "save_chat":
            filename = save_chat()
            return True, f"Chat saved to {filename}"
        elif action == "reset_conversation":
            reset_conversation()
            return True, "Conversation has been reset."
    return True, None

async def get_user_input(prompt="You: "):
    style = Style.from_dict({
        'prompt': 'cyan bold',
    })
    session = PromptSession(style=style)
    return await session.prompt_async(prompt, multiline=False)




def setup_virtual_environment() -> Tuple[str, str]:
    venv_name = "code_execution_env"
    venv_path = os.path.join(os.getcwd(), venv_name)
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



# Token tracking variables
main_model_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
tool_checker_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
code_editor_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
code_execution_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}

USE_FUZZY_SEARCH = True

# Set up the conversation memory (maintains context for MAINMODEL)
conversation_history = []

# Store file contents (part of the context for MAINMODEL)
file_contents = {}

# Code editor memory (maintains some context for CODEEDITORMODEL between calls)
code_editor_memory = []

# Files already present in code editor's context
code_editor_files = set()

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

MAINMODEL = "claude-3-5-sonnet-20240620"
TOOLCHECKERMODEL = "claude-3-5-sonnet-20240620"
CODEEDITORMODEL = "claude-3-5-sonnet-20240620"
CODEEXECUTIONMODEL = "claude-3-5-sonnet-20240620"

# System prompts
BASE_SYSTEM_PROMPT = """
You are Claude, an AI assistant powered by Anthropic's Claude-3.5-Sonnet model, specialized in software development with access to a variety of tools and the ability to instruct and direct a coding agent and a code execution one. Your capabilities include:

<capabilities>
1. Creating and managing project structures
2. Writing, debugging, and improving code across multiple languages
3. Providing architectural insights and applying design patterns
4. Staying current with the latest technologies and best practices
5. Analyzing and manipulating files within the project directory
6. Performing web searches for up-to-date information
7. Executing code and analyzing its output within an isolated 'code_execution_env' virtual environment
8. Managing and stopping running processes started within the 'code_execution_env'
</capabilities>

Available tools and their optimal use cases:

<tools>
1. create_folders: Create new folders at the specified paths, including nested directories. Use this to create one or more directories in the project structure, even complex nested structures in a single operation.
2. create_files: Generate one or more new files with specified content. Strive to make the files as complete and useful as possible.
3. edit_and_apply_multiple: Examine and modify one or more existing files by instructing a separate AI coding agent. You are responsible for providing clear, detailed instructions for each file. When using this tool:
   - Provide comprehensive context about the project, including recent changes, new variables or functions, and how files are interconnected.
   - Clearly state the specific changes or improvements needed for each file, explaining the reasoning behind each modification.
   - Include ALL the snippets of code to change, along with the desired modifications.
   - Specify coding standards, naming conventions, or architectural patterns to be followed.
   - Anticipate potential issues or conflicts that might arise from the changes and provide guidance on how to handle them.
4. execute_code: Run Python code exclusively in the 'code_execution_env' virtual environment and analyze its output. Use this when you need to test code functionality or diagnose issues. Remember that all code execution happens in this isolated environment. This tool returns a process ID for long-running processes.
5. stop_process: Stop a running process by its ID. Use this when you need to terminate a long-running process started by the execute_code tool.
6. read_multiple_files: Read the contents of one or more existing files, supporting wildcards (e.g., '*.py') and recursive directory reading. This tool can handle single or multiple file paths, directory paths, and wildcard patterns. Use this when you need to examine or work with file contents, especially for multiple files or entire directories.
 IMPORTANT: Before using the read_multiple_files tool, always check if the files you need are already in your context (system prompt).
    If the file contents are already available to you, use that information directly instead of calling the read_multiple_files tool.
    Only use the read_multiple_files tool for files that are not already in your context.
7. list_files: List all files and directories in a specified folder.
8. tavily_search: Perform a web search using the Tavily API for up-to-date information.
9. scan_folder: Scan a specified folder and create a Markdown file with the contents of all coding text files, excluding binary files and common ignored folders. Use this tool to generate comprehensive documentation of project structures.
10. run_shell_command: Execute a shell command and return its output. Use this tool when you need to run system commands or interact with the operating system. Ensure the command is safe and appropriate for the current operating system.
IMPORTANT: Use this tool to install dependencies in the code_execution_env when using the execute_code tool.
</tools>

<tool_usage_guidelines>
Tool Usage Guidelines:
- Always use the most appropriate tool for the task at hand.
- Provide detailed and clear instructions when using tools, especially for edit_and_apply_multiple.
- After making changes, always review the output to ensure accuracy and alignment with intentions.
- Use execute_code to run and test code within the 'code_execution_env' virtual environment, then analyze the results.
- For long-running processes, use the process ID returned by execute_code to stop them later if needed.
- Proactively use tavily_search when you need up-to-date information or additional context.
- When working with files, use read_multiple_files for both single and multiple file read making sure that the files are not already in your context.
</tool_usage_guidelines>

<error_handling>
Error Handling and Recovery:
- If a tool operation fails, carefully analyze the error message and attempt to resolve the issue.
- For file-related errors, double-check file paths and permissions before retrying.
- If a search fails, try rephrasing the query or breaking it into smaller, more specific searches.
- If code execution fails, analyze the error output and suggest potential fixes, considering the isolated nature of the environment.
- If a process fails to stop, consider potential reasons and suggest alternative approaches.
</error_handling>

<project_management>
Project Creation and Management:
1. Start by creating a root folder for new projects.
2. Create necessary subdirectories and files within the root folder.
3. Organize the project structure logically, following best practices for the specific project type.
</project_management>

Always strive for accuracy, clarity, and efficiency in your responses and actions. Your instructions must be precise and comprehensive. If uncertain, use the tavily_search tool or admit your limitations. When executing code, always remember that it runs in the isolated 'code_execution_env' virtual environment. Be aware of any long-running processes you start and manage them appropriately, including stopping them when they are no longer needed.

<tool_usage_best_practices>
When using tools:
1. Carefully consider if a tool is necessary before using it.
2. Ensure all required parameters are provided and valid.
3. Handle both successful results and errors gracefully.
4. Provide clear explanations of tool usage and results to the user.
</tool_usage_best_practices>

Remember, you are an AI assistant, and your primary goal is to help the user accomplish their tasks effectively and efficiently while maintaining the integrity and security of their development environment.
"""

AUTOMODE_SYSTEM_PROMPT = """
You are currently in automode. Follow these guidelines:

<goal_setting>
1. Goal Setting:
   - Set clear, achievable goals based on the user's request.
   - Break down complex tasks into smaller, manageable goals.
</goal_setting>

<goal_execution>
2. Goal Execution:
   - Work through goals systematically, using appropriate tools for each task.
   - Utilize file operations, code writing, and web searches as needed.
   - Always read a file before editing and review changes after editing.
</goal_execution>

<progress_tracking>
3. Progress Tracking:
   - Provide regular updates on goal completion and overall progress.
   - Use the iteration information to pace your work effectively.
</progress_tracking>

<task_breakdown>
Break Down Complex Tasks:
When faced with a complex task or project, break it down into smaller, manageable steps. Provide a clear outline of the steps involved, potential challenges, and how to approach each part of the task.
</task_breakdown>

<explanation_preference>
Prefer Answering Without Code:
When explaining concepts or providing solutions, prioritize clear explanations and pseudocode over full code implementations. Only provide full code snippets when explicitly requested or when it's essential for understanding.
</explanation_preference>

<code_review_process>
Code Review Process:
When reviewing code, follow these steps:
1. Understand the context and purpose of the code
2. Check for clarity and readability
3. Identify potential bugs or errors
4. Suggest optimizations or improvements
5. Ensure adherence to best practices and coding standards
6. Consider security implications
7. Provide constructive feedback with explanations
</code_review_process>

<project_planning>
Project Planning:
When planning a project, consider the following:
1. Define clear project goals and objectives
2. Break down the project into manageable tasks and subtasks
3. Estimate time and resources required for each task
4. Identify potential risks and mitigation strategies
5. Suggest appropriate tools and technologies
6. Outline a testing and quality assurance strategy
7. Consider scalability and future maintenance
</project_planning>

<security_review>
Security Review:
When conducting a security review, focus on:
1. Identifying potential vulnerabilities in the code
2. Checking for proper input validation and sanitization
3. Ensuring secure handling of sensitive data
4. Reviewing authentication and authorization mechanisms
5. Checking for secure communication protocols
6. Identifying any use of deprecated or insecure functions
7. Suggesting security best practices and improvements
</security_review>

Remember to apply these additional skills and processes when assisting users with their software development tasks and projects.

<tool_usage>
4. Tool Usage:
   - Leverage all available tools to accomplish your goals efficiently.
   - Prefer edit_and_apply_multiple for file modifications, applying changes in chunks for large edits.
   - Use tavily_search proactively for up-to-date information.
</tool_usage>

<error_handling>
5. Error Handling:
   - If a tool operation fails, analyze the error and attempt to resolve the issue.
   - For persistent errors, consider alternative approaches to achieve the goal.
</error_handling>

<automode_completion>
6. Automode Completion:
   - When all goals are completed, respond with "AUTOMODE_COMPLETE" to exit automode.
   - Do not ask for additional tasks or modifications once goals are achieved.
</automode_completion>

<iteration_awareness>
7. Iteration Awareness:
   - You have access to this {iteration_info}.
   - Use this information to prioritize tasks and manage time effectively.
</iteration_awareness>

Remember: Focus on completing the established goals efficiently and effectively. Avoid unnecessary conversations or requests for additional tasks.
"""


def update_system_prompt(current_iteration: Optional[int] = None, max_iterations: Optional[int] = None) -> str:
    global file_contents
    chain_of_thought_prompt = """
    Answer the user's request using relevant tools (if they are available). Before calling a tool, do some analysis within <thinking></thinking> tags. First, think about which of the provided tools is the relevant tool to answer the user's request. Second, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool call. BUT, if one of the values for a required parameter is missing, DO NOT invoke the function (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters. DO NOT ask for more information on optional parameters if it is not provided.

    Do not reflect on the quality of the returned search results in your response.
    """

    files_in_context = "\n".join(file_contents.keys())
    file_contents_prompt = f"\n\nFiles already in your context:\n{files_in_context}\n\nFile Contents:\n"
    for path, content in file_contents.items():
        file_contents_prompt += f"\n--- {path} ---\n{content}\n"

    if automode:
        iteration_info = ""
        if current_iteration is not None and max_iterations is not None:
            iteration_info = f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + AUTOMODE_SYSTEM_PROMPT.format(iteration_info=iteration_info) + "\n\n" + chain_of_thought_prompt
    else:
        return BASE_SYSTEM_PROMPT + file_contents_prompt + "\n\n" + chain_of_thought_prompt

def create_folders(paths):
    results = []
    for path in paths:
        try:
            # Use os.makedirs with exist_ok=True to create nested directories
            os.makedirs(path, exist_ok=True)
            results.append(f"Folder(s) created: {path}")
        except Exception as e:
            results.append(f"Error creating folder(s) {path}: {str(e)}")
    return "\n".join(results)

def create_files(files):
    global file_contents
    results = []
    
    # Handle different input types
    if isinstance(files, str):
        # If a string is passed, assume it's a single file path
        files = [{"path": files, "content": ""}]
    elif isinstance(files, dict):
        # If a single dictionary is passed, wrap it in a list
        files = [files]
    elif not isinstance(files, list):
        return "Error: Invalid input type for create_files. Expected string, dict, or list."
    
    for file in files:
        try:
            if not isinstance(file, dict):
                results.append(f"Error: Invalid file specification: {file}")
                continue
            
            path = file.get('path')
            content = file.get('content', '')
            
            if path is None:
                results.append(f"Error: Missing 'path' for file")
                continue
            
            dir_name = os.path.dirname(path)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            
            file_contents[path] = content
            results.append(f"File created and added to system prompt: {path}")
        except Exception as e:
            results.append(f"Error creating file: {str(e)}")
    
    return "\n".join(results)


async def generate_edit_instructions(file_path, file_content, instructions, project_context, full_file_contents):
    global code_editor_tokens, code_editor_memory, code_editor_files
    try:
        # Prepare memory context (this is the only part that maintains some context between calls)
        memory_context = "\n".join([f"Memory {i+1}:\n{mem}" for i, mem in enumerate(code_editor_memory)])

        # Prepare full file contents context, excluding the file being edited if it's already in code_editor_files
        full_file_contents_context = "\n\n".join([
            f"--- {path} ---\n{content}" for path, content in full_file_contents.items()
            if path != file_path or path not in code_editor_files
        ])

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

        IMPORTANT: RETURN ONLY THE SEARCH/REPLACE BLOCKS. NO EXPLANATIONS OR COMMENTS.
        USE THE FOLLOWING FORMAT FOR EACH BLOCK:

        <SEARCH>
        Code to be replaced
        </SEARCH>
        <REPLACE>
        New code to insert
        </REPLACE>

        If no changes are needed, return an empty list.
        """

        response = client.beta.prompt_caching.messages.create(
            model=CODEEDITORMODEL,
            max_tokens=8000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[
                {"role": "user", "content": "Generate SEARCH/REPLACE blocks for the necessary changes."}
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )
        # Update token usage for code editor
        code_editor_tokens['input'] += response.usage.input_tokens
        code_editor_tokens['output'] += response.usage.output_tokens
        code_editor_tokens['cache_creation'] = response.usage.cache_creation_input_tokens
        code_editor_tokens['cache_read'] = response.usage.cache_read_input_tokens

        # Parse the response to extract SEARCH/REPLACE blocks
        edit_instructions = parse_search_replace_blocks(response.content[0].text)

        # Update code editor memory (this is the only part that maintains some context between calls)
        code_editor_memory.append(f"Edit Instructions for {file_path}:\n{response.content[0].text}")

        # Add the file to code_editor_files set
        code_editor_files.add(file_path)

        return edit_instructions

    except Exception as e:
        console.print(f"Error in generating edit instructions: {str(e)}", style="bold red")
        return []  # Return empty list if any exception occurs



def parse_search_replace_blocks(response_text, use_fuzzy=USE_FUZZY_SEARCH):
    """
    Parse the response text for SEARCH/REPLACE blocks.

    Args:
    response_text (str): The text containing SEARCH/REPLACE blocks.
    use_fuzzy (bool): Whether to use fuzzy matching for search blocks.

    Returns:
    list: A list of dictionaries, each containing 'search', 'replace', and 'similarity' keys.
    """
    blocks = []
    pattern = r'<SEARCH>\s*(.*?)\s*</SEARCH>\s*<REPLACE>\s*(.*?)\s*</REPLACE>'
    matches = re.findall(pattern, response_text, re.DOTALL)

    for search, replace in matches:
        search = search.strip()
        replace = replace.strip()
        similarity = 1.0  # Default to exact match

        if use_fuzzy and search not in response_text:
            # Implement fuzzy matching logic here
            best_match = difflib.get_close_matches(search, [response_text], n=1, cutoff=0.6)
            if best_match:
                similarity = difflib.SequenceMatcher(None, search, best_match[0]).ratio()
            else:
                similarity = 0.0

        blocks.append({
            'search': search,
            'replace': replace,
            'similarity': similarity
        })

    return blocks


async def edit_and_apply_multiple(files, project_context, is_automode=False):
    global file_contents
    results = []
    console_outputs = []

    # Ensure files is always a list
    if isinstance(files, dict):
        files = [files]

    logging.info(f"Starting edit_and_apply_multiple with {len(files)} file(s)")

    for file in files:
        path = file['path']
        instructions = file['instructions']
        logging.info(f"Processing file: {path}")
        try:
            original_content = file_contents.get(path, "")
            if not original_content:
                logging.info(f"Reading content for file: {path}")
                with open(path, 'r') as f:
                    original_content = f.read()
                file_contents[path] = original_content

            logging.info(f"Generating edit instructions for file: {path}")
            edit_instructions = await generate_edit_instructions(path, original_content, instructions, project_context, file_contents)

            if edit_instructions:
                console.print(Panel(f"File: {path}\nThe following SEARCH/REPLACE blocks have been generated:", title="Edit Instructions", style="cyan"))
                for i, block in enumerate(edit_instructions, 1):
                    console.print(f"Block {i}:")
                    console.print(Panel(f"SEARCH:\n{block['search']}\n\nREPLACE:\n{block['replace']}\nSimilarity: {block['similarity']:.2f}", expand=False))

                logging.info(f"Applying edits to file: {path}")
                edited_content, changes_made, failed_edits, console_output = await apply_edits(path, edit_instructions, original_content)
                console_outputs.append(console_output)

                if changes_made:
                    file_contents[path] = edited_content
                    console.print(Panel(f"File contents updated in system prompt: {path}", style="green"))
                    logging.info(f"Changes applied to file: {path}")

                    if failed_edits:
                        logging.warning(f"Some edits failed for file: {path}")
                        results.append({
                            "path": path,
                            "status": "partial_success",
                            "message": f"Some changes applied to {path}, but some edits failed.",
                            "failed_edits": failed_edits,
                            "edited_content": edited_content
                        })
                    else:
                        results.append({
                            "path": path,
                            "status": "success",
                            "message": f"All changes successfully applied to {path}",
                            "edited_content": edited_content
                        })
                else:
                    logging.warning(f"No changes applied to file: {path}")
                    results.append({
                        "path": path,
                        "status": "no_changes",
                        "message": f"No changes could be applied to {path}. Please review the edit instructions and try again."
                    })
            else:
                logging.warning(f"No edit instructions generated for file: {path}")
                results.append({
                    "path": path,
                    "status": "no_instructions",
                    "message": f"No edit instructions generated for {path}"
                })
        except Exception as e:
            logging.error(f"Error editing/applying to file {path}: {str(e)}")
            error_message = f"Error editing/applying to file {path}: {str(e)}"
            results.append({
                "path": path,
                "status": "error",
                "message": error_message
            })
            console_outputs.append(error_message)

    logging.info("Completed edit_and_apply_multiple")
    return results, "\n".join(console_outputs)



async def apply_edits(file_path, edit_instructions, original_content):
    changes_made = False
    edited_content = original_content
    total_edits = len(edit_instructions)
    failed_edits = []
    console_output = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        edit_task = progress.add_task("[cyan]Applying edits...", total=total_edits)

        for i, edit in enumerate(edit_instructions, 1):
            search_content = edit['search'].strip()
            replace_content = edit['replace'].strip()
            similarity = edit['similarity']

            # Use regex to find the content, ignoring leading/trailing whitespace
            pattern = re.compile(re.escape(search_content), re.DOTALL)
            match = pattern.search(edited_content)

            if match or (USE_FUZZY_SEARCH and similarity >= 0.8):
                if not match:
                    # If using fuzzy search and no exact match, find the best match
                    best_match = difflib.get_close_matches(search_content, [edited_content], n=1, cutoff=0.6)
                    if best_match:
                        match = re.search(re.escape(best_match[0]), edited_content)

                if match:
                    # Replace the content, preserving the original whitespace
                    start, end = match.span()
                    # Strip <SEARCH> and <REPLACE> tags from replace_content
                    replace_content_cleaned = re.sub(r'</?SEARCH>|</?REPLACE>', '', replace_content)
                    edited_content = edited_content[:start] + replace_content_cleaned + edited_content[end:]
                    changes_made = True

                    # Display the diff for this edit
                    diff_result = generate_diff(search_content, replace_content, file_path)
                    console.print(Panel(diff_result, title=f"Changes in {file_path} ({i}/{total_edits}) - Similarity: {similarity:.2f}", style="cyan"))
                    console_output.append(f"Edit {i}/{total_edits} applied successfully")
                else:
                    message = f"Edit {i}/{total_edits} not applied: content not found (Similarity: {similarity:.2f})"
                    console_output.append(message)
                    console.print(Panel(message, style="yellow"))
                    failed_edits.append(f"Edit {i}: {search_content}")
            else:
                message = f"Edit {i}/{total_edits} not applied: content not found (Similarity: {similarity:.2f})"
                console_output.append(message)
                console.print(Panel(message, style="yellow"))
                failed_edits.append(f"Edit {i}: {search_content}")

            progress.update(edit_task, advance=1)

    if not changes_made:
        message = "No changes were applied. The file content already matches the desired state."
        console_output.append(message)
        console.print(Panel(message, style="green"))
    else:
        # Write the changes to the file
        with open(file_path, 'w') as file:
            file.write(edited_content)
        message = f"Changes have been written to {file_path}"
        console_output.append(message)
        console.print(Panel(message, style="green"))

    return edited_content, changes_made, "\n".join(failed_edits), "\n".join(console_output)


def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)


def generate_diff(original, new, path):
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        n=3
    ))

    diff_text = ''.join(diff)
    highlighted_diff = highlight_diff(diff_text)

    return highlighted_diff


async def execute_code(code, timeout=10):
    global running_processes
    venv_path, activate_script = setup_virtual_environment()

    # Input validation
    if not isinstance(code, str):
        raise ValueError("code must be a string")
    if not isinstance(timeout, (int, float)):
        raise ValueError("timeout must be a number")

    # Generate a unique identifier for this process
    process_id = f"process_{len(running_processes)}"

    # Write the code to a temporary file
    try:
        with open(f"{process_id}.py", "w") as f:
            f.write(code)
    except IOError as e:
        return process_id, f"Error writing code to file: {str(e)}"

    # Prepare the command to run the code
    if sys.platform == "win32":
        command = f'"{activate_script}" && python3 {process_id}.py'
    else:
        command = f'source "{activate_script}" && python3 {process_id}.py'

    try:
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
    except Exception as e:
        return process_id, f"Error executing code: {str(e)}"
    finally:
        # Cleanup: remove the temporary file
        try:
            os.remove(f"{process_id}.py")
        except OSError:
            pass  # Ignore errors in removing the file

# Update the read_multiple_files function to handle both single and multiple files
def read_multiple_files(paths, recursive=False):
    global file_contents
    results = []

    if isinstance(paths, str):
        paths = [paths]

    for path in paths:
        try:
            if os.path.isdir(path):
                if recursive:
                    file_paths = glob.glob(os.path.join(path, '**', '*'), recursive=True)
                else:
                    file_paths = glob.glob(os.path.join(path, '*'))
                file_paths = [f for f in file_paths if os.path.isfile(f)]
            else:
                file_paths = glob.glob(path, recursive=recursive)

            for file_path in file_paths:
                if os.path.isfile(file_path):
                    if file_path not in file_contents:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        file_contents[file_path] = content
                        results.append(f"File '{file_path}' has been read and stored in the system prompt.")
                    else:
                        results.append(f"File '{file_path}' is already in the system prompt. No need to read again.")
                else:
                    results.append(f"Skipped '{file_path}': Not a file.")
        except Exception as e:
            results.append(f"Error reading path '{path}': {str(e)}")

    return "\n".join(results)

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

def run_shell_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.CalledProcessError as e:
        return {
            "stdout": e.stdout,
            "stderr": e.stderr,
            "return_code": e.returncode,
            "error": str(e)
        }
    except Exception as e:
        return {
            "error": f"An error occurred while executing the command: {str(e)}"
        }


tools = [
    {
        "name": "create_folders",
        "description": "Create new folders at the specified paths, including nested directories. This tool should be used when you need to create one or more directories (including nested ones) in the project structure. It will create all necessary parent directories if they don't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "An array of absolute or relative paths where the folders should be created. Use forward slashes (/) for path separation, even on Windows systems. For nested directories, simply include the full path (e.g., 'parent/child/grandchild')."
                }
            },
            "required": ["paths"]
        }
    },
    {
        "name": "scan_folder",
        "description": "Scan a specified folder and create a Markdown file with the contents of all coding text files, excluding binary files and common ignored folders.",
        "input_schema": {
            "type": "object",
            "properties": {
                "folder_path": {
                    "type": "string",
                    "description": "The absolute or relative path of the folder to scan. Use forward slashes (/) for path separation, even on Windows systems."
                },
                "output_file": {
                    "type": "string",
                    "description": "The name of the output Markdown file to create with the scanned contents."
                }
            },
            "required": ["folder_path", "output_file"]
        }
    },
    {
        "name": "create_files",
        "description": "Create one or more new files with the given contents. This tool should be used when you need to create files in the project structure. It will create all necessary parent directories if they don't exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "oneOf": [
                        {
                            "type": "string",
                            "description": "A single file path to create an empty file."
                        },
                        {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"type": "string"}
                            },
                            "required": ["path"]
                        },
                        {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {"type": "string"},
                                    "content": {"type": "string"}
                                },
                                "required": ["path"]
                            }
                        }
                    ]
                }
            },
            "required": ["files"]
        }
    },
    {
        "name": "edit_and_apply_multiple",
        "description": "Apply AI-powered improvements to multiple files based on specific instructions and detailed project context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "The absolute or relative path of the file to edit."
                            },
                            "instructions": {
                                "type": "string",
                                "description": "Specific instructions for editing this file."
                            }
                        },
                        "required": ["path", "instructions"]
                    }
                },
                "project_context": {
                    "type": "string",
                    "description": "Comprehensive context about the project, including recent changes, new variables or functions, interconnections between files, coding standards, and any other relevant information that might affect the edits."
                }
            },
            "required": ["files", "project_context"]
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
        "name": "read_multiple_files",
        "description": "Read the contents of one or more existing files, supporting wildcards and recursive directory reading.",
        "input_schema": {
            "type": "object",
            "properties": {
                "paths": {
                    "oneOf": [
                        {
                            "type": "string",
                            "description": "A single file path, directory path, or wildcard pattern."
                        },
                        {
                            "type": "array",
                            "items": {
                                "type": "string"
                            },
                            "description": "An array of file paths, directory paths, or wildcard patterns."
                        }
                    ],
                    "description": "The path(s) of the file(s) to read. Use forward slashes (/) for path separation, even on Windows systems. Supports wildcards (e.g., '*.py') and directory paths."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, read files recursively from directories. Default is false.",
                    "default": False
                }
            },
            "required": ["paths"]
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
    },
    {
        "name": "run_shell_command",
        "description": "Execute a shell command and return its output. This tool should be used when you need to run system commands or interact with the operating system. It will return the standard output, standard error, and return code of the executed command.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute. Ensure the command is safe and appropriate for the current operating system."
                }
            },
            "required": ["command"]
        }
    }
]



async def decide_retry(tool_checker_response, edit_results):
    try:
        response = client.messages.create(
            model=TOOLCHECKERMODEL,
            max_tokens=1000,
            system="""You are an AI assistant tasked with deciding whether to retry editing files based on the previous edit results and the AI's response. Respond with a JSON object containing 'retry' (boolean) and 'files_to_retry' (list of file paths).

Example of the expected JSON response:
{
    "retry": true,
    "files_to_retry": ["/path/to/file1.py", "/path/to/file2.py"]
}

Only return the JSON object, nothing else. Ensure that the JSON is properly formatted with double quotes around property names and string values.""",
            messages=[
                {"role": "user", "content": f"Previous edit results: {json.dumps(edit_results)}\n\nAI's response: {tool_checker_response}\n\nDecide whether to retry editing any files."}
            ]
        )
        
        # Extract the text content from the response
        response_text = response.content[0].text.strip()
        
        # Try to find a valid JSON object within the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            decision = json.loads(json_str)
        else:
            # If no valid JSON found, make a decision based on the presence of "retry" in the response
            decision = {
                "retry": "retry" in response_text.lower(),
                "files_to_retry": []
            }
        
        return {
            "retry": decision.get("retry", False),
            "files_to_retry": decision.get("files_to_retry", [])
        }
    except json.JSONDecodeError as e:
        console.print(Panel(f"Error parsing JSON in decide_retry: {str(e)}", title="Error", style="bold red"))
        return {"retry": False, "files_to_retry": []}
    except Exception as e:
        console.print(Panel(f"Error in decide_retry: {str(e)}", title="Error", style="bold red"))
        return {"retry": False, "files_to_retry": []}

async def execute_tool(tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = None
        is_error = False
        console_output = None

        if tool_name == "create_files":
            if isinstance(tool_input, dict) and 'files' in tool_input:
                files = tool_input['files']
            else:
                files = tool_input
            result = create_files(files)
        elif tool_name == "edit_and_apply_multiple":
            files = tool_input.get("files", [tool_input])
            result, console_output = await edit_and_apply_multiple(files, tool_input["project_context"], is_automode=automode)
        elif tool_name == "create_folders":
            result = create_folders(tool_input["paths"])
        elif tool_name == "read_multiple_files":
            paths = tool_input.get("paths")
            recursive = tool_input.get("recursive", False)
            if paths is None:
                result = "Error: No file paths provided"
                is_error = True
            else:
                files_to_read = [p for p in (paths if isinstance(paths, list) else [paths]) if p not in file_contents]
                if not files_to_read:
                    result = "All requested files are already in the system prompt. No need to read from disk."
                else:
                    result = read_multiple_files(files_to_read, recursive)
            if paths is None:
                result = "Error: No file paths provided"
                is_error = True
            else:
                result = read_multiple_files(paths)
        elif tool_name == "list_files":
            result = list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            result = tavily_search(tool_input["query"])
        elif tool_name == "stop_process":
            result = stop_process(tool_input["process_id"])
        elif tool_name == "execute_code":
            process_id, execution_result = await execute_code(tool_input["code"])
            analysis_task = asyncio.create_task(send_to_ai_for_executing(tool_input["code"], execution_result))
            analysis = await analysis_task
            result = f"{execution_result}\n\nAnalysis:\n{analysis}"
            if process_id in running_processes:
                result += "\n\nNote: The process is still running in the background."
        elif tool_name == "scan_folder":
            result = scan_folder(tool_input["folder_path"], tool_input["output_file"])
        elif tool_name == "run_shell_command":
            result = run_shell_command(tool_input["command"])
        else:
            is_error = True
            result = f"Unknown tool: {tool_name}"

        return {
            "content": result,
            "is_error": is_error,
            "console_output": console_output
        }
    except KeyError as e:
        logging.error(f"Missing required parameter {str(e)} for tool {tool_name}")
        return {
            "content": f"Error: Missing required parameter {str(e)} for tool {tool_name}",
            "is_error": True,
            "console_output": None
        }
    except Exception as e:
        logging.error(f"Error executing tool {tool_name}: {str(e)}")
        return {
            "content": f"Error executing tool {tool_name}: {str(e)}",
            "is_error": True,
            "console_output": None
        }

def scan_folder(folder_path: str, output_file: str) -> str:
    ignored_folders = {'.git', '__pycache__', 'node_modules', 'venv', 'env'}
    markdown_content = f"# Folder Scan: {folder_path}\n\n"
    total_chars = len(markdown_content)
    max_chars = 600000  # Approximating 150,000 tokens

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in ignored_folders]

        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, folder_path)

            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('text'):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    file_content = f"## {relative_path}\n\n```\n{content}\n```\n\n"
                    if total_chars + len(file_content) > max_chars:
                        remaining_chars = max_chars - total_chars
                        if remaining_chars > 0:
                            truncated_content = file_content[:remaining_chars]
                            markdown_content += truncated_content
                            markdown_content += "\n\n... Content truncated due to size limitations ...\n"
                        else:
                            markdown_content += "\n\n... Additional files omitted due to size limitations ...\n"
                        break
                    else:
                        markdown_content += file_content
                        total_chars += len(file_content)
                except Exception as e:
                    error_msg = f"## {relative_path}\n\nError reading file: {str(e)}\n\n"
                    if total_chars + len(error_msg) <= max_chars:
                        markdown_content += error_msg
                        total_chars += len(error_msg)

        if total_chars >= max_chars:
            break

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)

    return f"Folder scan complete. Markdown file created at: {output_file}. Total characters: {total_chars}"

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

        response = client.beta.prompt_caching.messages.create(
            model=CODEEXECUTIONMODEL,
            max_tokens=2000,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=[
                {"role": "user", "content": f"Analyze this code execution from the 'code_execution_env' virtual environment:\n\nCode:\n{code}\n\nExecution Result:\n{execution_result}"}
            ],
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )

        # Update token usage for code execution
        code_execution_tokens['input'] += response.usage.input_tokens
        code_execution_tokens['output'] += response.usage.output_tokens
        code_execution_tokens['cache_creation'] = response.usage.cache_creation_input_tokens
        code_execution_tokens['cache_read'] = response.usage.cache_read_input_tokens

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
    global conversation_history, automode, main_model_tokens, use_tts, tts_enabled

    # Input validation
    if not isinstance(user_input, str):
        raise ValueError("user_input must be a string")
    if image_path is not None and not isinstance(image_path, str):
        raise ValueError("image_path must be a string or None")
    if current_iteration is not None and not isinstance(current_iteration, int):
        raise ValueError("current_iteration must be an integer or None")
    if max_iterations is not None and not isinstance(max_iterations, int):
        raise ValueError("max_iterations must be an integer or None")

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

    # Filter conversation history to maintain context
    filtered_conversation_history = []
    for message in conversation_history:
        if isinstance(message['content'], list):
            filtered_content = [
                content for content in message['content']
                if content.get('type') != 'tool_result' or (
                    content.get('type') == 'tool_result' and
                    not any(keyword in content.get('output', '') for keyword in [
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

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            # MAINMODEL call with prompt caching
            response = client.beta.prompt_caching.messages.create(
                model=MAINMODEL,
                max_tokens=8000,
                system=[
                    {
                        "type": "text",
                        "text": update_system_prompt(current_iteration, max_iterations),
                        "cache_control": {"type": "ephemeral"}
                    },
                    {
                        "type": "text",
                        "text": json.dumps(tools),
                        "cache_control": {"type": "ephemeral"}
                    }
                ],
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"},
                extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
            )
            # Update token usage for MAINMODEL
            main_model_tokens['input'] += response.usage.input_tokens
            main_model_tokens['output'] += response.usage.output_tokens
            main_model_tokens['cache_write'] = response.usage.cache_creation_input_tokens
            main_model_tokens['cache_read'] = response.usage.cache_read_input_tokens
            break  # If successful, break out of the retry loop
        except APIStatusError as e:
            if e.status_code == 429 and attempt < max_retries - 1:
                console.print(Panel(f"Rate limit exceeded. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})", title="API Error", style="bold yellow"))
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
                return "I'm sorry, there was an error communicating with the AI. Please try again.", False
        except APIError as e:
            console.print(Panel(f"API Error: {str(e)}", title="API Error", style="bold red"))
            return "I'm sorry, there was an error communicating with the AI. Please try again.", False
    else:
        console.print(Panel("Max retries reached. Unable to communicate with the AI.", title="Error", style="bold red"))
        return "I'm sorry, there was a persistent error communicating with the AI. Please try again later.", False

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
    
    if tts_enabled and use_tts:
        await text_to_speech(assistant_response)

    # Display files in context
    if file_contents:
        files_in_context = "\n".join(file_contents.keys())
    else:
        files_in_context = "No files in context. Read, create, or edit files to add."
    console.print(Panel(files_in_context, title="Files in Context", title_align="left", border_style="white", expand=False))

    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="green"))
        console.print(Panel(f"Tool Input: {json.dumps(tool_input, indent=2)}", style="green"))

        if tool_name == 'create_files':
            tool_result = create_files(tool_input.get('files', [tool_input]))
        else:
            tool_result = await execute_tool(tool_name, tool_input)

        if isinstance(tool_result, dict) and tool_result.get("is_error"):
            console.print(Panel(tool_result["content"], title="Tool Execution Error", style="bold red"))
        else:
            # Format the tool result content for proper rendering
            formatted_result = json.dumps(tool_result, indent=2) if isinstance(tool_result, (dict, list)) else str(tool_result)
            # console.print(Panel(formatted_result, title_align="left", title="Tool Result", style="green"))

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

        # Modify this part to ensure correct structure
        tool_result_content = {
            "type": "text",
            "text": json.dumps(tool_result) if isinstance(tool_result, (dict, list)) else str(tool_result)
        }

        current_conversation.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": [tool_result_content],  # Wrap the content in a list
                    "is_error": tool_result.get("is_error", False) if isinstance(tool_result, dict) else False
                }
            ]
        })

        # Update the file_contents dictionary if applicable
        if tool_name in ['create_files', 'edit_and_apply_multiple', 'read_multiple_files'] and not (isinstance(tool_result, dict) and tool_result.get("is_error")):
            if tool_name == 'create_files':
                for file in tool_input['files']:
                    if "File created and added to system prompt" in str(tool_result):
                        file_contents[file['path']] = file['content']
            elif tool_name == 'edit_and_apply_multiple':
                edit_results = tool_result if isinstance(tool_result, list) else [tool_result]
                for result in edit_results:
                    if isinstance(result, dict) and result.get("status") in ["success", "partial_success"]:
                        file_contents[result["path"]] = result.get("edited_content", file_contents.get(result["path"], ""))
            elif tool_name == 'read_multiple_files':
                # The file_contents dictionary is already updated in the read_multiple_files function
                pass

        messages = filtered_conversation_history + current_conversation

        try:
            tool_response = client.messages.create(
                model=TOOLCHECKERMODEL,
                max_tokens=8000,
                system=update_system_prompt(current_iteration, max_iterations),
                extra_headers={"anthropic-beta": "max-tokens-3-5-sonnet-2024-07-15"},
                messages=messages,
                tools=tools,
                tool_choice={"type": "auto"}
            )
            # Update token usage for tool checker
            tool_checker_tokens['input'] += tool_response.usage.input_tokens
            tool_checker_tokens['output'] += tool_response.usage.output_tokens

            tool_checker_response = ""
            for tool_content_block in tool_response.content:
                if tool_content_block.type == "text":
                    tool_checker_response += tool_content_block.text
            console.print(Panel(Markdown(tool_checker_response), title="Claude's Response to Tool Result",  title_align="left", border_style="blue", expand=False))
            if use_tts:
                await text_to_speech(tool_checker_response)
            assistant_response += "\n\n" + tool_checker_response

            # If the tool was edit_and_apply_multiple, let the AI decide whether to retry
            if tool_name == 'edit_and_apply_multiple':
                retry_decision = await decide_retry(tool_checker_response, edit_results)
                if retry_decision["retry"]:
                    console.print(Panel(f"AI has decided to retry editing for files: {', '.join(retry_decision['files_to_retry'])}", style="yellow"))
                    retry_files = [file for file in tool_input['files'] if file['path'] in retry_decision['files_to_retry']]
                    retry_result, retry_console_output = await edit_and_apply_multiple(retry_files, tool_input['project_context'])
                    console.print(Panel(retry_console_output, title="Retry Result", style="cyan"))
                    assistant_response += f"\n\nRetry result: {json.dumps(retry_result, indent=2)}"
                else:
                    console.print(Panel("Claude has decided not to retry editing", style="green"))

        except APIError as e:
            error_message = f"Error in tool response: {str(e)}"
            console.print(Panel(error_message, title="Error", style="bold red"))
            assistant_response += f"\n\n{error_message}"

    if assistant_response:
        current_conversation.append({"role": "assistant", "content": assistant_response})

    conversation_history = messages + [{"role": "assistant", "content": assistant_response}]

    # Display token usage at the end
    display_token_usage()

    return assistant_response, exit_continuation

def reset_code_editor_memory():
    global code_editor_memory
    code_editor_memory = []
    console.print(Panel("Code editor memory has been reset.", title="Reset", style="bold green"))


def reset_conversation():
    global conversation_history, main_model_tokens, tool_checker_tokens, code_editor_tokens, code_execution_tokens, file_contents, code_editor_files
    conversation_history = []
    main_model_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
    tool_checker_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
    code_editor_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
    code_execution_tokens = {'input': 0, 'output': 0, 'cache_write': 0, 'cache_read': 0}
    file_contents = {}
    code_editor_files = set()
    reset_code_editor_memory()
    console.print(Panel("Conversation history, token counts, file contents, code editor memory, and code editor files have been reset.", title="Reset", style="bold green"))
    display_token_usage()

def display_token_usage():
    from rich.table import Table
    from rich.panel import Panel
    from rich.box import ROUNDED

    table = Table(box=ROUNDED)
    table.add_column("Model", style="cyan")
    table.add_column("Input", style="magenta")
    table.add_column("Output", style="magenta")
    table.add_column("Cache Write", style="blue")
    table.add_column("Cache Read", style="blue")
    table.add_column("Total", style="green")
    table.add_column(f"% of Context ({MAX_CONTEXT_TOKENS:,})", style="yellow")
    table.add_column("Cost ($)", style="red")

    model_costs = {
        "Main Model": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30, "has_context": True},
        "Tool Checker": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30, "has_context": False},
        "Code Editor": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30, "has_context": True},
        "Code Execution": {"input": 3.00, "output": 15.00, "cache_write": 3.75, "cache_read": 0.30, "has_context": False}
    }

    total_input = 0
    total_output = 0
    total_cache_write = 0
    total_cache_read = 0
    total_cost = 0
    total_context_tokens = 0

    for model, tokens in [("Main Model", main_model_tokens),
                          ("Tool Checker", tool_checker_tokens),
                          ("Code Editor", code_editor_tokens),
                          ("Code Execution", code_execution_tokens)]:
        input_tokens = tokens.get('input', 0)
        output_tokens = tokens.get('output', 0)
        cache_write_tokens = tokens.get('cache_write', 0)
        cache_read_tokens = tokens.get('cache_read', 0)
        total_tokens = input_tokens + output_tokens + cache_write_tokens + cache_read_tokens

        total_input += input_tokens
        total_output += output_tokens
        total_cache_write += cache_write_tokens
        total_cache_read += cache_read_tokens

        input_cost = (input_tokens / 1_000_000) * model_costs[model]["input"]
        output_cost = (output_tokens / 1_000_000) * model_costs[model]["output"]
        cache_write_cost = (cache_write_tokens / 1_000_000) * model_costs[model]["cache_write"]
        cache_read_cost = (cache_read_tokens / 1_000_000) * model_costs[model]["cache_read"]
        model_cost = input_cost + output_cost + cache_write_cost + cache_read_cost
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
            f"{cache_write_tokens:,}",
            f"{cache_read_tokens:,}",
            f"{total_tokens:,}",
            f"{percentage:.2f}%" if model_costs[model]["has_context"] else "Doesn't save context",
            f"${model_cost:.3f}"
        )

    grand_total = total_input + total_output + total_cache_write + total_cache_read
    total_percentage = (total_context_tokens / MAX_CONTEXT_TOKENS) * 100

    table.add_row(
        "Total",
        f"{total_input:,}",
        f"{total_output:,}",
        f"{total_cache_write:,}",
        f"{total_cache_read:,}",
        f"{grand_total:,}",
        f"{total_percentage:.2f}%",
        f"${total_cost:.3f}",
        style="bold"
    )

    console.print(table)



async def test_voice_mode():
    global voice_mode
    voice_mode = True
    initialize_speech_recognition()
    console.print(Panel("Entering voice input test mode. Say a few phrases, then say 'exit voice mode' to end the test.", style="bold green"))
    
    while voice_mode:
        user_input = await voice_input()
        if user_input is None:
            voice_mode = False
            cleanup_speech_recognition()
            console.print(Panel("Exited voice input test mode due to error.", style="bold yellow"))
            break
        
        stay_in_voice_mode, command_result = process_voice_command(user_input)
        if not stay_in_voice_mode:
            voice_mode = False
            cleanup_speech_recognition()
            console.print(Panel("Exited voice input test mode.", style="bold green"))
            break
        elif command_result:
            console.print(Panel(command_result, style="cyan"))
    
    console.print(Panel("Voice input test completed.", style="bold green"))

async def main():
    global automode, conversation_history, use_tts, tts_enabled
    console.print(Panel("Welcome to the Claude-3-Sonnet Engineer Chat with Multi-Agent, Image, Voice, and Text-to-Speech Support!", title="Welcome", style="bold green"))
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print("Type 'voice' to enter voice input mode.")
    console.print("Type 'test voice' to run a voice input test.")
    console.print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    console.print("Type 'reset' to clear the conversation history.")
    console.print("Type 'save chat' to save the conversation to a Markdown file.")
    console.print("Type '11labs on' to enable text-to-speech.")
    console.print("Type '11labs off' to disable text-to-speech.")
    console.print("While in automode, press Ctrl+C at any time to exit the automode to return to regular chat.")

    voice_mode = False

    while True:
        if voice_mode:
            user_input = await voice_input()
            if user_input is None:
                voice_mode = False
                cleanup_speech_recognition()
                console.print(Panel("Exited voice input mode due to error. Returning to text input.", style="bold yellow"))
                continue
            
            stay_in_voice_mode, command_result = process_voice_command(user_input)
            if not stay_in_voice_mode:
                voice_mode = False
                cleanup_speech_recognition()
                console.print(Panel("Exited voice input mode. Returning to text input.", style="bold green"))
                if command_result:
                    console.print(Panel(command_result, style="cyan"))
                continue
            elif command_result:
                console.print(Panel(command_result, style="cyan"))
                continue
        else:
            user_input = await get_user_input()

        if user_input.lower() == 'exit':
            console.print(Panel("Thank you for chatting. Goodbye!", title_align="left", title="Goodbye", style="bold green"))
            break

        if user_input.lower() == 'test voice':
            await test_voice_mode()
            continue

        if user_input.lower() == '11labs on':
            use_tts = True
            tts_enabled = True
            console.print(Panel("Text-to-speech enabled.", style="bold green"))
            continue

        if user_input.lower() == '11labs off':
            use_tts = False
            tts_enabled = False
            console.print(Panel("Text-to-speech disabled.", style="bold yellow"))
            continue



        if user_input.lower() == 'reset':
            reset_conversation()
            continue

        if user_input.lower() == 'save chat':
            filename = save_chat()
            console.print(Panel(f"Chat saved to {filename}", title="Chat Saved", style="bold green"))
            continue

        if user_input.lower() == 'voice':
            voice_mode = True
            initialize_speech_recognition()
            console.print(Panel("Entering voice input mode. Say 'exit voice mode' to return to text input.", style="bold green"))
            continue

        if user_input.lower() == 'image':
            image_path = (await get_user_input("Drag and drop your image here, then press enter: ")).strip().replace("'", "")

            if os.path.isfile(image_path):
                user_input = await get_user_input("You (prompt for image): ")
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
                user_input = await get_user_input()

                iteration_count = 0
                error_count = 0
                max_errors = 3  # Maximum number of consecutive errors before exiting automode
                try:
                    while automode and iteration_count < max_iterations:
                        try:
                            response, exit_continuation = await chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
                            error_count = 0  # Reset error count on successful iteration
                        except Exception as e:
                            console.print(Panel(f"Error in automode iteration: {str(e)}", style="bold red"))
                            error_count += 1
                            if error_count >= max_errors:
                                console.print(Panel(f"Exiting automode due to {max_errors} consecutive errors.", style="bold red"))
                                automode = False
                                break
                            continue

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

def validate_files_structure(files):
    if not isinstance(files, (dict, list)):
        raise ValueError("Invalid 'files' structure. Expected a dictionary or a list of dictionaries.")
    
    if isinstance(files, dict):
        files = [files]
    
    for file in files:
        if not isinstance(file, dict):
            raise ValueError("Each file must be a dictionary.")
        if 'path' not in file or 'instructions' not in file:
            raise ValueError("Each file dictionary must contain 'path' and 'instructions' keys.")
        if not isinstance(file['path'], str) or not isinstance(file['instructions'], str):
            raise ValueError("'path' and 'instructions' must be strings.")

    return files

def validate_files_structure(files):
    if not isinstance(files, (dict, list)):
        raise ValueError("Invalid 'files' structure. Expected a dictionary or a list of dictionaries.")
    
    if isinstance(files, dict):
        files = [files]
    
    for file in files:
        if not isinstance(file, dict):
            raise ValueError("Each file must be a dictionary.")
        if 'path' not in file or 'instructions' not in file:
            raise ValueError("Each file dictionary must contain 'path' and 'instructions' keys.")
        if not isinstance(file['path'], str) or not isinstance(file['instructions'], str):
            raise ValueError("'path' and 'instructions' must be strings.")

    return files



    # Add more tests for other functions as needed

if __name__ == "__main__":


    # Run the main program
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\nProgram interrupted by user. Exiting...", style="bold red")
    except Exception as e:
        console.print(f"An unexpected error occurred: {str(e)}", style="bold red")
        logging.error(f"Unexpected error: {str(e)}", exc_info=True)
    finally:
        console.print("Program finished. Goodbye!", style="bold green")
