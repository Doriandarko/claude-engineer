from tools.base_tool import base_tool

class create_file(base_tool):
    def __init__(self):
        super().__init__()
        self.definition = {
        "name": "create_file",
        "description": "Create a new file at the specified path with content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "The content of the file"
                }
            },
            "required": ["path", "content"]
        }
    }
        self.name = self.definition["name"]
    
    def execute(tool_input):
        try:
            path = tool_input["path"]
            content = tool_input["content"]
            with open(path, 'w') as f:
                f.write(content)
            return f"File created: {path}"
        except Exception as e:
            return f"Error creating file: {str(e)}"