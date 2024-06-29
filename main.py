import os
from colorama import init, Style
from config import USER_COLOR, CLAUDE_COLOR, TOOL_COLOR, MAX_CONTINUATION_ITERATIONS
from utils import print_colored, process_and_display_response
from claude_chat import chat_with_claude, automode, execute_goals

# Initialize colorama
init()

def main():
    global automode
    print_colored("Welcome to the Claude-3.5-Sonnet Engineer Chat with Image Support!", CLAUDE_COLOR)
    print_colored("Type 'exit' to end the conversation.", CLAUDE_COLOR)
    print_colored("Type 'image' to include an image in your message.", CLAUDE_COLOR)
    print_colored("Type 'automode' to enter Autonomous mode.", CLAUDE_COLOR)
    
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
        elif user_input.lower() == 'automode':
            automode = True
            print_colored("Entering automode. Please provide your request.", TOOL_COLOR)
            user_input = input(f"\n{USER_COLOR}You: {Style.RESET_ALL}")
            
            iteration_count = 0
            while automode and iteration_count < MAX_CONTINUATION_ITERATIONS:
                response, exit_continuation = chat_with_claude(user_input, current_iteration=iteration_count+1, max_iterations=MAX_CONTINUATION_ITERATIONS)
                process_and_display_response(response)
                
                if exit_continuation:
                    print_colored("automode completed.", TOOL_COLOR)
                    automode = False
                else:
                    print_colored(f"Continuation iteration {iteration_count + 1} completed.", TOOL_COLOR)
                    user_input = "Continue with the next step."
                
                iteration_count += 1
                
                if iteration_count >= MAX_CONTINUATION_ITERATIONS:
                    print_colored("Max iterations reached. Exiting automode.", TOOL_COLOR)
                    automode = False
            
            print_colored("Exited automode. Returning to regular chat.", TOOL_COLOR)
        else:
            response, _ = chat_with_claude(user_input)
            process_and_display_response(response)

if __name__ == "__main__":
    main()