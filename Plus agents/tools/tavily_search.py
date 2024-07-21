import json
import os
from tavily import tavily
from tavily import TavilyClient
from tools.base_tool import base_tool
from config import TAVILY_API_KEY

class tavily_search(base_tool):
    def __init__(self):
        super().__init__()
        api_key=TAVILY_API_KEY
        self.tavily = TavilyClient(api_key)
        self.definition = {
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    }
        self.name = self.definition["name"]
    
    def execute(self, tool_input):
        try:
            query = tool_input["query"]
            response = self.tavily.qna_search(query=query, search_depth="advanced")
            return json.dumps(response, indent=2)
        except Exception as e:
            return f"Error performing search: {str(e)}"