import anthropic
from config import Config
import asyncio
import json
from typing import Dict, Any, List
import tempfile
import os

class ConversationSummarizer:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
        self.temp_dir = tempfile.mkdtemp(prefix="claude_context_")
    
    async def summarize_async(self, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Asynchronously summarizes the conversation history using Claude 3.5.
        """
        # Convert conversation history to a format Claude can understand
        formatted_messages = []
        for msg in conversation_history:
            if msg["role"] in ["user", "assistant"]:
                content = self._format_content(msg["content"])
                formatted_messages.append({
                    "role": msg["role"],
                    "content": content
                })
        
        prompt = """Summarize the following conversation between a user and an AI assistant. 
        Focus on these key aspects:

        1. Key topics discussed
        2. Important decisions or conclusions
        3. Tools used and their outcomes
        4. Context needed for future interactions
        5. Any pending tasks or follow-ups

        Keep technical details and code snippets that might be relevant for future context.
        """
        
        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model=Config.MODEL,
                max_tokens=2000,
                temperature=0.5,
                messages=[
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nConversation to summarize:\n{self._format_conversation(formatted_messages)}"
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"Error in summarization: {str(e)}")
            return "Error generating summary"

    def _format_content(self, content: Any) -> str:
        """
        Formats message content into a string representation.
        Handles both text and structured content (like tool usage).
        """
        if isinstance(content, str):
            return content
            
        if isinstance(content, list):
            formatted_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        formatted_parts.append(item.get("text", ""))
                    elif item.get("type") == "tool_use":
                        formatted_parts.append(
                            f"[Tool Use - {item.get('name', '')}: {json.dumps(item.get('input', {}), default=str)}]"
                        )
                    elif item.get("type") == "tool_result":
                        formatted_parts.append(
                            f"[Tool Result: {json.dumps(item.get('content', ''), default=str)}]"
                        )
            return " ".join(formatted_parts)
            
        return str(content)

    def _format_conversation(self, messages: List[Dict[str, Any]]) -> str:
        """
        Formats the conversation into a readable string.
        """
        formatted = []
        for msg in messages:
            formatted.append(f"{msg['role'].upper()}: {msg['content']}")
        return "\n\n".join(formatted)

    def save_context_to_temp(self, conversation_history: List[Dict[str, Any]]) -> str:
        """
        Saves the conversation context to a temporary file.
        Returns the file path.
        """
        temp_file = os.path.join(self.temp_dir, "context.json")
        with open(temp_file, "w") as f:
            json.dump(conversation_history, f, default=str)
        return temp_file

    def load_context_from_temp(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Loads the conversation context from a temporary file.
        """
        with open(file_path, "r") as f:
            return json.load(f)

    def cleanup_temp_files(self):
        """
        Cleans up temporary files when the chat session ends.
        """
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")