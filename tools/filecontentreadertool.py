from tools.base import BaseTool
import os

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

    def execute(self, **kwargs) -> str:
        file_paths = kwargs.get('file_paths', [])
        results = {}

        for file_path in file_paths:
            try:
                if not os.path.exists(file_path):
                    results[file_path] = f"Error: File not found: {file_path}"
                    continue

                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read()
                    results[file_path] = content

            except PermissionError:
                results[file_path] = f"Error: Permission denied for file: {file_path}"
            except IsADirectoryError:
                results[file_path] = f"Error: Path is a directory: {file_path}"
            except UnicodeDecodeError:
                results[file_path] = f"Error: Unable to decode file: {file_path}"
            except Exception as e:
                results[file_path] = f"Error: Unexpected error reading file {file_path}: {str(e)}"

        return str(results)