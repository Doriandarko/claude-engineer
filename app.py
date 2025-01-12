from flask import Flask, render_template, request, jsonify, url_for
from ce3 import Assistant
import os
from werkzeug.utils import secure_filename
import base64
from config import Config
import logging
import json

app = Flask(__name__, static_folder='static')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize the assistant
assistant = Assistant()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        message = data.get('message', '')
        image_data = data.get('image')
        
        def generate_response():
            try:
                # Prepare the message content
                if image_data:
                    message_content = [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data.split(',')[1] if ',' in image_data else image_data
                            }
                        }
                    ]
                    if message.strip():
                        message_content.append({
                            "type": "text",
                            "text": message
                        })
                else:
                    message_content = message
                
                # Get the response generator
                response_generator = assistant.chat(message_content)
                
                # Process each chunk
                response_content = []
                tool_name = None
                
                for chunk in response_generator:
                    if isinstance(chunk, dict):
                        if chunk.get('type') == 'error':
                            error_msg = chunk.get('error', 'Unknown error occurred')
                            logging.error(f"OpenRouter API Error: {error_msg}")
                            yield json.dumps({
                                'response': f"Error: {error_msg}",
                                'thinking': False,
                                'tool_name': None,
                                'token_usage': None
                            }) + '\n'
                            return
                            
                        elif chunk.get('type') == 'message':
                            response_content = chunk.get('content', [])
                            if chunk.get('tool_calls'):
                                tool_name = chunk['tool_calls'][0].get('function', {}).get('name')
                                
                            # Get token usage
                            token_usage = {
                                'total_tokens': assistant.total_tokens_used,
                                'max_tokens': Config.MAX_CONVERSATION_TOKENS
                            }
                            
                            # Send the complete message
                            yield json.dumps({
                                'response': response_content,
                                'thinking': False,
                                'tool_name': tool_name,
                                'token_usage': token_usage
                            }) + '\n'
                            
                        elif chunk.get('type') == 'message_delta':
                            if 'tool_calls' in chunk.get('delta', {}):
                                tool_name = chunk['delta']['tool_calls'][0].get('function', {}).get('name')
                            elif 'text' in chunk.get('delta', {}):
                                response_content.append({
                                    'type': 'text',
                                    'text': chunk['delta']['text']
                                })
                                
                                # Send the delta
                                yield json.dumps({
                                    'response': response_content,
                                    'thinking': False,
                                    'tool_name': tool_name,
                                    'token_usage': None
                                }) + '\n'
                
            except Exception as e:
                logging.error(f"Error in chat endpoint - assistant.chat(): {str(e)}", exc_info=True)
                yield json.dumps({
                    'response': f"Error: {str(e)}",
                    'thinking': False,
                    'tool_name': None,
                    'token_usage': None
                }) + '\n'
        
        return app.response_class(generate_response(), mimetype='text/plain')
        
    except Exception as e:
        logging.error(f"Error in chat endpoint - request processing: {str(e)}", exc_info=True)
        return jsonify({
            'response': "Error: Failed to process request",
            'thinking': False,
            'tool_name': None,
            'token_usage': None
        })

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
    app.run(debug=False) 