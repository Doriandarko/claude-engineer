import gradio as gr
import os
from dotenv import load_dotenv
from anthropic import Anthropic, APIStatusError, APIError

# Load environment variables from .env file
load_dotenv()

# Initialize the Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
client = Anthropic(api_key=anthropic_api_key)

def chat_with_claude(user_input):
    try:
        response = client.completions.create(
            model="claude-3",
            prompt=f"User: {user_input}\nClaude:",
            max_tokens_to_sample=300
        )
        return response.completion
    except (APIStatusError, APIError) as e:
        return f"Error: {str(e)}"

def gradio_interface(user_input):
    response = chat_with_claude(user_input)
    return response

with gr.Blocks() as demo:
    gr.Markdown("# Claude Engineer Gradio App")
    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(label="User Input")
            submit_button = gr.Button("Submit")
        with gr.Column():
            output = gr.Textbox(label="Claude's Response")

    submit_button.click(gradio_interface, inputs=user_input, outputs=output)

if __name__ == "__main__":
    demo.launch()
