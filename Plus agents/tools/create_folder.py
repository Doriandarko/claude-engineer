import os
from tools.base_tool import base_tool

class create_folder(base_tool):
    def __init__(self):
        super().__init__()
        self.definition = {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created"
                }
            },
            "required": ["path"]
        }
    }
        self.name = self.definition["name"]
    
    def execute(self, tool_input):
        try:
            path = tool_input["path"]
            os.makedirs(path, exist_ok=True)
            return f"Folder created: {path}"
        except Exception as e:
            return f"Error creating folder: {str(e)}"