import streamlit as st
import anthropic
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the Anthropic client
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
if not anthropic_api_key:
    st.error("ANTHROPIC_API_KEY not found in environment variables")
    st.stop()
client = anthropic.Anthropic(api_key=anthropic_api_key)

# Initialize the Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    st.error("TAVILY_API_KEY not found in environment variables")
    st.stop()
tavily = TavilyClient(api_key=tavily_api_key)

# Initialize the base URL
base_url = os.getenv("BASE_URL")
if not base_url:
    st.error("BASE_URL not found in environment variables")
    st.stop()

# Streamlit app title
st.title("Claude Engineer Streamlit App")

# Chat interface
st.header("Chat with Claude")

# User input
user_input = st.text_input("You: ", "")

# Function to handle user input and display responses
def handle_user_input(user_input):
    if user_input:
        # Add user input to conversation history
        conversation_history.append({"role": "user", "content": user_input})

        # Call the Claude API
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=8000,
            system=[
                {
                    "type": "text",
                    "text": update_system_prompt(),
                    "cache_control": {"type": "ephemeral"}
                },
                {
                    "type": "text",
                    "text": json.dumps(tools),
                    "cache_control": {"type": "ephemeral"}
                }
            ],
            messages=conversation_history,
            tools=tools,
            tool_choice={"type": "auto"},
            extra_headers={"anthropic-beta": "prompt-caching-2024-07-31"}
        )

        # Extract and display the response
        assistant_response = ""
        for content_block in response.content:
            if content_block.type == "text":
                assistant_response += content_block.text

        # Add assistant response to conversation history
        conversation_history.append({"role": "assistant", "content": assistant_response})

        # Display the response
        st.write("Claude: ", assistant_response)

# Handle user input
if user_input:
    handle_user_input(user_input)

# Display conversation history
st.header("Conversation History")
for message in conversation_history:
    if message["role"] == "user":
        st.write("You: ", message["content"])
    elif message["role"] == "assistant":
        st.write("Claude: ", message["content"])

# Settings page for API keys and base URL
def settings_page():
    st.header("Settings")
    anthropic_api_key = st.text_input("Anthropic API Key", value=os.getenv("ANTHROPIC_API_KEY", ""))
    tavily_api_key = st.text_input("Tavily API Key", value=os.getenv("TAVILY_API_KEY", ""))
    base_url = st.text_input("Base URL", value=os.getenv("BASE_URL", ""))

    if st.button("Save"):
        with open('.env', 'w') as f:
            f.write(f"ANTHROPIC_API_KEY={anthropic_api_key}\n")
            f.write(f"TAVILY_API_KEY={tavily_api_key}\n")
            f.write(f"BASE_URL={base_url}\n")
        st.success("Settings saved. Please restart the app to apply changes.")

if __name__ == "__main__":
    settings_page()
