from tools.base import BaseTool
import os
import json

class FileContentReaderTool(BaseTool):
    name = "filecontentreadertool"
    description = '''
    Reads content from multiple files and returns their contents.
    Accepts a list of file paths and returns a dictionary with file paths as keys
    and their content as values.
    Handles file reading errors gracefully with built-in Python exceptions.
    '''
    
    input_schema = {
        "type": "object",
        "properties": {
            "file_paths": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of file paths to read"
            }
        },
        "required": ["file_paths"]
    }

    def _read_file(self, file_path: str) -> str:
        """Safely read a file and handle errors."""
        try:
            if not os.path.exists(file_path):
                return "Error: File not found"

            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()

        except PermissionError:
            return "Error: Permission denied"
        except IsADirectoryError:
            return "Error: Path is a directory"
        except UnicodeDecodeError:
            return "Error: Unable to decode file"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, **kwargs) -> str:
        file_paths = kwargs.get('file_paths', [])
        results = {}

        try:
            # Read each file
            for file_path in file_paths:
                content = self._read_file(file_path)
                results[file_path] = content

            # Format the output as JSON with proper escaping
            formatted_results = json.dumps(results, indent=2)
            return formatted_results

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)