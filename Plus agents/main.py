import os
from coordinator import Coordinator
from utils import print_panel, encode_image_to_base64, print_markdown
from config import MAX_CONTINUATION_ITERATIONS, CONTINUATION_EXIT_PHRASE

def main():
    coordinator = Coordinator()
    print_panel("Welcome to the Claude-3-Sonnet Engineer Chat with Multi-Agent Support!", "Welcome", style="bold green")
    print("Type 'exit' to end the conversation.")
    print("Type 'image' to include an image in your message.")
    print("Type 'automode [number]' to enter Autonomous mode with a specific number of iterations.")
    print("Type 'reset' to clear the conversation history.")

    while True:
        user_input = input("\nYou: ").strip()

        if user_input.lower() == 'exit':
            print_panel("Thank you for chatting. Goodbye!", "Goodbye", style="bold green")
            break

        elif user_input.lower() == 'reset':
            coordinator.reset_memory()
            print_panel("Conversation history has been cleared.", "Reset", style="bold yellow")
            continue

        elif user_input.lower() == 'image':
            image_path = input("Drag and drop your image here, then press enter: ").strip().replace("'", "")
            if os.path.isfile(image_path):
                image_base64 = encode_image_to_base64(image_path)
                if image_base64.startswith("Error"):
                    print_panel(f"Error processing image: {image_base64}", "Error", style="bold red")
                    continue
                user_input = input("You (prompt for image): ")
                response = coordinator.chat_with_image(user_input, image_base64)
            else:
                print_panel("Invalid image path. Please try again.", "Error", style="bold red")
                continue

        elif user_input.lower().startswith('automode'):
            parts = user_input.split()
            if len(parts) > 1 and parts[1].isdigit():
                max_iterations = int(parts[1])
            else:
                max_iterations = MAX_CONTINUATION_ITERATIONS

            coordinator.set_automode(True)
            print_panel(f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.", "Automode", style="bold yellow")
            user_input = input("You: ")
            
            try:
                for i in range(max_iterations):
                    response = coordinator.chat(user_input)
                    print_markdown(f"Claude: {response}")
                    
                    if CONTINUATION_EXIT_PHRASE in response:
                        print_panel("Automode goal achieved. Exiting automode.", "Automode Complete", style="bold green")
                        coordinator.set_automode(False)
                        break
                    
                    if not coordinator.automode:
                        break
                    
                    if i < max_iterations - 1:
                        user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                
                if coordinator.automode:
                    print_panel("Max iterations reached. Exiting automode.", "Automode", style="bold red")
                    coordinator.set_automode(False)

                print_panel("Exited automode. Returning to regular chat.", "Automode Exit", style="green")
            
            except KeyboardInterrupt:
                print_panel("\nAutomode interrupted by user. Exiting automode.", "Automode", style="bold red")
                coordinator.set_automode(False)

            continue

        else:
            response = coordinator.chat(user_input)

        print_markdown(f"Claude: {response}")

if __name__ == "__main__":
    main()