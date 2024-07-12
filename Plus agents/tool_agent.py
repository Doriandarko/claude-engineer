from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, TOOL_MODEL

class ToolAgent:
    def __init__(self, tool_name, tool_description, tool_schema):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.tool_name = tool_name
        self.tool_description = tool_description
        self.tool_schema = tool_schema
        self.conversation_history = []
        self.system_prompt = f"""You are a specialized Claude agent responsible for the {tool_name} tool. 
Your role is to:
1. Understand the task delegated by the coordinator
2. Execute the {tool_name} tool accurately
3. Provide clear and concise results back to the coordinator

Tool description: {tool_description}

Always focus on your specific task and tool. If you need additional information or clarification, request it from the coordinator."""

    def execute(self, task):
        messages = self.conversation_history + [{"role": "user", "content": task}]
        
        try:
            response = self.client.messages.create(
                model=TOOL_MODEL,
                max_tokens=4000,
                system=self.system_prompt,
                messages=messages
            )
            tool_response = response.content[0].text
            self.conversation_history.append({"role": "assistant", "content": tool_response})
            return tool_response
        except Exception as e:
            return f"Error executing {self.tool_name}: {str(e)}"

    def reset_memory(self):
        self.conversation_history = []