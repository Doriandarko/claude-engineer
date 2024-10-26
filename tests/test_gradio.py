import gradio as gr
import pytest
from gradio.testing import TestClient

# Define the Gradio app
def app():
    def chat_with_claude(user_input):
        return f"Claude: {user_input}"

    with gr.Blocks() as demo:
        gr.Markdown("# Claude Engineer Gradio App")
        with gr.Row():
            with gr.Column():
                user_input = gr.Textbox(label="User Input")
                submit_button = gr.Button("Submit")
            with gr.Column():
                output = gr.Textbox(label="Claude's Response")

        submit_button.click(chat_with_claude, inputs=user_input, outputs=output)

    return demo

# Test functions
def test_app_loads():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Claude Engineer Gradio App" in response.text

def test_user_input():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    response = client.post("/", data={"User Input": "Hello, Claude!"})
    assert response.status_code == 200
    assert "Claude: Hello, Claude!" in response.text

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
