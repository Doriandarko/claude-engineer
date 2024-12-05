from tools.base import BaseTool
import os
from typing import Dict

class DiffEditorTool(BaseTool):
    name = "diffeditortool"
    description = '''
    Performs a precise replacement of a given text snippet in a specified file.
    It takes the following inputs:
    - path: The path to the target file.
    - old_text: The exact substring that should be replaced.
    - new_text: The new substring that replaces the old one.

    The tool will:
    1. Read the file contents.
    2. Search for `old_text` within the file.
    3. If found, replace the first occurrence of `old_text` with `new_text`.
    4. Write the modified content back to the file.
    5. Return a success message if successful, or indicate that the old_text was not found.
    '''

    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to be edited."
            },
            "old_text": {
                "type": "string",
                "description": "Exact substring in the file to replace."
            },
            "new_text": {
                "type": "string",
                "description": "New substring that will replace old_text."
            }
        },
        "required": ["path", "old_text", "new_text"]
    }

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        old_text = kwargs.get("old_text")
        new_text = kwargs.get("new_text")

        # Check if file exists
        if not os.path.isfile(path):
            return f"Error: File does not exist at path: {path}"

        # Read the file content
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return f"Error reading file {path}: {str(e)}"

        # Locate the old_text in the file
        index = content.find(old_text)
        if index == -1:
            return f"'{old_text}' not found in the file. No changes made."

        # Replace the first occurrence of old_text with new_text
        # Since find gave us the exact start, we can do a direct substring replacement:
        new_content = content[:index] + new_text + content[index+len(old_text):]

        # Write the updated content back to the file
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except Exception as e:
            return f"Error writing updated content to file {path}: {str(e)}"

        return f"Successfully replaced '{old_text}' with '{new_text}' in {path}."
