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
                openai_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
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

        response = requests.post(
            url,
            headers=self.client.headers,
            json=payload,
            stream=stream
        )
        response.raise_for_status()

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
                    yield {
                        'type': 'message',
                        'content': message.get('content', ''),
                        'tool_calls': message.get('tool_calls', [])
                    } 