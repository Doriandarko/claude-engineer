import requests
from typing import List, Dict, Any, Generator, Optional
import json

class OpenRouterClient:
    """
    OpenRouter client implementation that mimics the Anthropic client interface
    """
    
    def __init__(self, api_key: str, base_url: str, app_name: str, app_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'HTTP-Referer': app_url,
            'X-Title': app_name,
            'Content-Type': 'application/json'
        }

    def messages(self) -> 'Messages':
        return Messages(self)

class Messages:
    def __init__(self, client: OpenRouterClient):
        self.client = client

    def create(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        stream: bool = True,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Create a chat completion request to OpenRouter
        """
        url = f"{self.client.base_url}/chat/completions"
        
        # Convert Anthropic message format to OpenAI format
        openai_messages = []
        for msg in messages:
            if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                # Handle tool calls
                openai_messages.append({
                    'role': 'assistant',
                    'content': None,
                    'tool_calls': msg['tool_calls']
                })
            elif msg.get('role') == 'tool':
                # Handle tool responses
                openai_messages.append({
                    'role': 'tool',
                    'content': msg['content'],
                    'tool_call_id': msg.get('tool_call_id')
                })
            else:
                # Handle regular messages
                content = msg.get('content', '')
                if isinstance(content, list):
                    # Handle structured content (text + images)
                    formatted_content = []
                    for item in content:
                        if item.get('type') == 'text':
                            formatted_content.append(item.get('text', ''))
                        elif item.get('type') == 'image':
                            formatted_content.append({
                                'type': 'image_url',
                                'image_url': {
                                    'url': f"data:{item['source']['media_type']};base64,{item['source']['data']}"
                                }
                            })
                    content = formatted_content
                openai_messages.append({
                    'role': msg['role'],
                    'content': content
                })

        payload = {
            'model': model,
            'messages': openai_messages,
            'temperature': temperature,
            'stream': stream,
            'max_tokens': max_tokens
        }

        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'

        try:
            response = requests.post(
                url,
                headers=self.client.headers,
                json=payload,
                stream=stream
            )
            
            # Check for error status codes
            if not response.ok:
                error_msg = "OpenRouter API Error"
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = f"OpenRouter API Error: {error_data['error'].get('message', str(response.status_code))}"
                except:
                    error_msg = f"OpenRouter API Error: HTTP {response.status_code}"
                
                yield {
                    'type': 'error',
                    'error': error_msg
                }
                return

            if stream:
                for line in response.iter_lines():
                    if line:
                        if line.startswith(b'data: '):
                            json_str = line[6:].decode('utf-8')
                            if json_str.strip() == '[DONE]':
                                break
                            try:
                                chunk = json.loads(json_str)
                                # Convert OpenAI format to Anthropic format
                                if 'choices' in chunk and chunk['choices']:
                                    choice = chunk['choices'][0]
                                    if 'delta' in choice:
                                        delta = choice['delta']
                                        if 'tool_calls' in delta:
                                            yield {
                                                'type': 'message_delta',
                                                'delta': {
                                                    'tool_calls': delta['tool_calls']
                                                }
                                            }
                                        elif 'content' in delta and delta['content']:
                                            yield {
                                                'type': 'message_delta',
                                                'delta': {
                                                    'text': delta['content']
                                                }
                                            }
                            except json.JSONDecodeError:
                                continue
            else:
                response_json = response.json()
                # Convert OpenAI format to Anthropic format for non-streaming response
                if 'choices' in response_json and response_json['choices']:
                    choice = response_json['choices'][0]
                    if 'message' in choice:
                        message = choice['message']
                        content = message.get('content', '')
                        tool_calls = message.get('tool_calls', [])
                        
                        # Format response like Anthropic's API
                        yield {
                            'type': 'message',
                            'content': [{
                                'type': 'text',
                                'text': content
                            }] if content else [],
                            'tool_calls': tool_calls,
                            'model': model,
                            'role': 'assistant'
                        }

        except requests.exceptions.RequestException as e:
            error_msg = f"OpenRouter API Error: {str(e)}"
            if hasattr(e.response, 'json'):
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_msg = f"OpenRouter API Error: {error_data['error'].get('message', str(e))}"
                except:
                    pass
            yield {
                'type': 'error',
                'error': error_msg
            } 