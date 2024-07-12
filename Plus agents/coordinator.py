import logging
import time
from anthropic import Anthropic
from config import ANTHROPIC_API_KEY, COORDINATOR_MODEL, COORDINATOR_BASE_PROMPT, CONTINUATION_EXIT_PHRASE
from tool_agent import ToolAgent
from tools import tool_definitions, execute_tool
from utils import parse_goals, print_panel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Coordinator:
    def __init__(self):
        self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.conversation_history = []
        self.tool_agents = {tool["name"]: ToolAgent(tool["name"], tool["description"], tool["input_schema"]) for tool in tool_definitions}
        self.current_goals = []
        self.automode = False

    def chat(self, user_input, image_base64=None, max_retries=3):
        if image_base64:
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_base64
                    }
                },
                {
                    "type": "text",
                    "text": user_input
                }
            ]
        else:
            message_content = user_input

        messages = self.conversation_history + [{"role": "user", "content": message_content}]
        
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=COORDINATOR_MODEL,
                    max_tokens=4000,
                    system=COORDINATOR_BASE_PROMPT,
                    messages=messages,
                    tools=tool_definitions
                )
                
                self.conversation_history.append({"role": "user", "content": message_content})
                
                logger.info(f"Received response with stop_reason: {response.stop_reason}")
                
                if response.stop_reason == "tool_use":
                    tool_use = response.content[-1]  # Get the last content item, which should be the tool_use
                    tool_name = tool_use.name
                    tool_input = tool_use.input
                    
                    logger.info(f"Tool use requested: {tool_name}")
                    logger.info(f"Tool input: {tool_input}")
                    
                    # Execute the actual tool function
                    actual_result = execute_tool(tool_name, tool_input)
                    
                    logger.info(f"Tool result: {actual_result}")
                    
                    # Format the tool result correctly
                    tool_result = {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": tool_use.id,
                                "content": actual_result
                            }
                        ]
                    }
                    
                    # Add the tool use and tool result to the conversation history
                    self.conversation_history.append({"role": "assistant", "content": [tool_use]})
                    self.conversation_history.append(tool_result)
                    
                    # Continue the conversation with the tool result
                    continuation_response = self.client.messages.create(
                        model=COORDINATOR_MODEL,
                        max_tokens=2000,
                        system=COORDINATOR_BASE_PROMPT,
                        messages=self.conversation_history,
                        tools=tool_definitions
                    )
                    
                    # Process the continuation response
                    assistant_response = continuation_response.content[0].text
                    self.conversation_history.append({"role": "assistant", "content": assistant_response})
                else:
                    logger.info("No tool use requested")
                    assistant_response = response.content[0].text
                    self.conversation_history.append({"role": "assistant", "content": assistant_response})
                
                logger.info(f"Assistant response: {assistant_response[:100]}...")  # Log first 100 chars of response
                
                if self.automode:
                    self.current_goals = parse_goals(assistant_response)
                    self.execute_goals()
                
                return assistant_response

            except Exception as e:
                logger.error(f"Error in coordinator chat (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Wait for 1 second before retrying
                else:
                    return f"Error in coordinator chat after {max_retries} attempts: {str(e)}"

        return "Max retries reached without success"

    def execute_goals(self):
        for goal in self.current_goals:
            print_panel(f"Executing goal: {goal}", "Goal Execution", style="yellow")
            response = self.chat(f"Continue working on goal: {goal}")
            if CONTINUATION_EXIT_PHRASE in response:
                self.automode = False
                print_panel("Exiting automode.", "Automode", style="green")
                break

    def set_automode(self, enabled):
        self.automode = enabled

    def reset_memory(self):
        self.conversation_history = []
        for agent in self.tool_agents.values():
            agent.reset_memory()

    def chat_with_image(self, user_input, image_base64):
        return self.chat(user_input, image_base64)