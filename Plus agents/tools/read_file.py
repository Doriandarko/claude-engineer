from tools.base_tool import base_tool

class read_file(base_tool):
    def __init__(self):
        super().__init__()
        self.definition = {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read"
                }
            },
            "required": ["path"]
        }
    }
        self.name = self.definition["name"]
    
    def execute(tool_input):
        try:
            path = tool_input["path"]
            with open(path, 'r') as f:
                content = f.read()
            return content
        except Exception as e:
            return f"Error reading file: {str(e)}"