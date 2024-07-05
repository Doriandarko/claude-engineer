import base64
import io
import os
import pygments.util
from anthropic import Anthropic
from colorama import Style
from jinja2 import Environment, FileSystemLoader
from PIL import Image
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import TerminalFormatter

from config import (
    ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_TOKENS, MAX_CONTINUATION_ITERATIONS,
    CONTINUATION_EXIT_PHRASE, USER_COLOR, CLAUDE_COLOR, TOOL_COLOR, RESULT_COLOR,
    PROMPTS_DIR, SYSTEM_PROMPT_TEMPLATE, MAX_IMAGE_SIZE
)
from tools import tools, execute_tool

def print_colored(text, color):
    print(f"{color}{text}{Style.RESET_ALL}")

def print_code(code, language):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
        formatted_code = highlight(code, lexer, TerminalFormatter())
        print(formatted_code)
    except pygments.util.ClassNotFound:
        print_colored(f"Code (language: {language}):\n{code}", CLAUDE_COLOR)

def encode_image_to_base64(image_path):
    try:
        with Image.open(image_path) as img:
            img.thumbnail(MAX_IMAGE_SIZE, Image.DEFAULT_STRATEGY)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG')
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
    except Exception as e:
        return f"Error encoding image: {str(e)}"

def process_and_display_response(response: str):
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

class ClaudeAgent:
    def __init__(self):
        environment = Environment(loader=FileSystemLoader(PROMPTS_DIR))
        self.template = environment.get_template(SYSTEM_PROMPT_TEMPLATE)

        # Initialize the Anthropic client
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Initialize the automode status
        self.automode = False

        # Set up the conversation memory
        self.conversation_history = []

    def update_system_prompt(self, current_iteration=None, max_iterations=None):
        iterations_left = 1
        automode_status = "You are currently in automode." if self.automode else "You are not in automode."
        if current_iteration is not None and max_iterations is not None:
            automode_status += f"You are currently on iteration {current_iteration} out of {max_iterations} in automode."
            iterations_left = max_iterations - current_iteration

        return self.template.render(
            automode_status=automode_status,
            iterations_left=iterations_left
        )

    def chat_with_claude(self, user_input, image_path=None, current_iteration=None, max_iterations=None):
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
            self.conversation_history.append(image_message)
            print_colored("Image message added to conversation history", TOOL_COLOR)
        else:
            self.conversation_history.append({"role": "user", "content": user_input})
        
        messages = [msg for msg in self.conversation_history if msg.get('content')]
        
        try:
            response = self.client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=MAX_TOKENS,
                system=self.update_system_prompt(current_iteration, max_iterations),
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
                
                self.conversation_history.append({"role": "assistant", "content": [content_block]})
                self.conversation_history.append({
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
                    tool_response = self.client.messages.create(
                        model=CLAUDE_MODEL,
                        max_tokens=MAX_TOKENS,
                        system=self.update_system_prompt(current_iteration, max_iterations),
                        messages=[msg for msg in self.conversation_history if msg.get('content')],
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
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
        
        return assistant_response, exit_continuation

    def conversation(self):
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
                    response, _ = self.chat_with_claude(user_input, image_path)
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
                            response, exit_continuation = self.chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=max_iterations)
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
                        if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                            self.conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
                except KeyboardInterrupt:
                    print_colored("\nAutomode interrupted by user. Exiting automode.", TOOL_COLOR)
                    automode = False
                    # Ensure the conversation history ends with an assistant message
                    if self.conversation_history and self.conversation_history[-1]["role"] == "user":
                        self.conversation_history.append({"role": "assistant", "content": "Automode interrupted. How can I assist you further?"})
                
                print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
            else:
                response, _ = self.chat_with_claude(user_input)
                process_and_display_response(response)