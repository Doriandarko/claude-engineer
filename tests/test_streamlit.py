import streamlit as st
import pytest
from streamlit.testing import TestClient

# Define the Streamlit app
def app():
    st.title("Claude Engineer Streamlit App")
    st.header("Chat with Claude")
    user_input = st.text_input("You: ", "")
    if user_input:
        st.write("Claude: ", user_input)

# Test functions
def test_app_loads():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "Claude Engineer Streamlit App" in response.text

def test_user_input():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    response = client.post("/", data={"You: ": "Hello, Claude!"})
    assert response.status_code == 200
    assert "Claude: Hello, Claude!" in response.text

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
