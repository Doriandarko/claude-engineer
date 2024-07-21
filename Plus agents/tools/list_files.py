import os
from tools.base_tool import base_tool

class list_files(base_tool):
    def __init__(self):
        super().__init__()
        self.definition = {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. Use this when you need to see the contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)"
                }
            }
        }
    }
        self.name = self.definition["name"]
    
    def execute(self, tool_input):
        try:
            path = tool_input["path"]
            files = os.listdir(path)
            return "\n".join(files)
        except Exception as e:
            return f"Error listing files: {str(e)}"