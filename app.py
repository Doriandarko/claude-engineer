from flask import Flask, render_template, request, jsonify, url_for, make_response
from ce3 import Assistant
import os
from werkzeug.utils import secure_filename
import base64
from config import Config

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the assistant
assistant = Assistant()

# Define theme configuration
THEME_CONFIG = {
    'dark': {
        'bg': 'bg-dark-bg',
        'text': 'text-dark-text',
        'border': 'border-dark-surface',
        'surface': 'bg-dark-surface',
        'input': 'bg-dark-surface border-gray-600/50',
        'button': 'bg-dark-surface hover:bg-gray-700 text-dark-text',
        'shadow': 'shadow-lg shadow-black/20'
    },
    'light': {
        'bg': 'bg-white',
        'text': 'text-gray-900',
        'border': 'border-gray-200',
        'surface': 'bg-white',
        'input': 'bg-white border-gray-300',
        'button': 'bg-white hover:bg-gray-100 text-gray-900',
        'shadow': 'shadow-md'
    }
}

@app.route('/')
def home():
    # Get the current theme preference from cookie
    theme = request.cookies.get('theme', 'light')
    return render_template('index.html', theme=theme, theme_classes=THEME_CONFIG[theme])

@app.route('/toggle-theme', methods=['POST'])
def toggle_theme():
    # Get the current theme from the request
    new_theme = request.json.get('theme', 'light')

    # Create response with the new theme and theme classes
    response = make_response(jsonify({
        'theme': new_theme,
        'theme_classes': THEME_CONFIG[new_theme]
    }))

    # Set cookie to remember the theme preference
    response.set_cookie('theme', new_theme, max_age=31536000)  # Cookie expires in 1 year

    return response

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message', '')
    image_data = data.get('image')  # Get the base64 image data

    # Prepare the message content
    if image_data:
        # Create a message with both text and image in correct order
        message_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",  # We should detect this from the image
                    "data": image_data.split(',')[1] if ',' in image_data else image_data  # Remove data URL prefix if present
                }
            }
        ]

        # Only add text message if there is actual text
        if message.strip():
            message_content.append({
                "type": "text",
                "text": message
            })
    else:
        # Text-only message
        message_content = message

    try:
        # Handle the chat message with the appropriate content
        response = assistant.chat(message_content)

        # Get token usage from assistant
        token_usage = {
            'total_tokens': assistant.total_tokens_used,
            'max_tokens': Config.MAX_CONVERSATION_TOKENS
        }

        # Get the last used tool from the conversation history
        tool_name = None
        if assistant.conversation_history:
            for msg in reversed(assistant.conversation_history):
                if msg.get('role') == 'assistant' and msg.get('content'):
                    content = msg['content']
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'tool_use':
                                tool_name = block.get('name')
                                break
                    if tool_name:
                        break

        return jsonify({
            'response': response,
            'thinking': False,
            'tool_name': tool_name,
            'token_usage': token_usage
        })

    except Exception as e:
        return jsonify({
            'response': f"Error: {str(e)}",
            'thinking': False,
            'tool_name': None,
            'token_usage': None
        }), 200  # Return 200 even for errors to handle them gracefully in frontend

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Get the actual media type
        media_type = file.content_type or 'image/jpeg'  # Default to jpeg if not detected

        # Convert image to base64
        with open(filepath, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        # Clean up the file
        os.remove(filepath)

        return jsonify({
            'success': True,
            'image_data': encoded_string,
            'media_type': media_type
        })

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/reset', methods=['POST'])
def reset():
    # Reset the assistant's conversation history
    assistant.reset()
    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='127.0.0.1',reload=True)
