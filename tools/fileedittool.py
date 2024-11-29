from tools.base import BaseTool
import os
import re

class FileEditTool(BaseTool):
    name = "fileedittool"
    description = '''
    A tool for editing file contents with support for:
    - Full file content replacement
    - Partial content editing by line numbers
    - Pattern-based text search and replace
    - Multiple file type support
    - Error handling for file operations
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to the file to edit"},
            "edit_type": {"type": "string", "enum": ["full", "partial"], "description": "Type of edit operation"},
            "new_content": {"type": "string", "description": "New content to write"},
            "start_line": {"type": "integer", "description": "Starting line number for partial edits"},
            "end_line": {"type": "integer", "description": "Ending line number for partial edits"},
            "search_pattern": {"type": "string", "description": "Pattern to search for in partial edits"},
            "replacement_text": {"type": "string", "description": "Text to replace matched patterns"}
        },
        "required": ["file_path", "edit_type", "new_content"]
    }

    def execute(self, **kwargs) -> str:
        file_path = kwargs.get('file_path')
        edit_type = kwargs.get('edit_type')
        new_content = kwargs.get('new_content')
        
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

            with open(file_path, 'r', encoding='utf-8') as file:
                original_content = file.read()
                lines = original_content.splitlines()

            if edit_type == "full":
                updated_content = new_content
            else:
                start_line = kwargs.get('start_line')
                end_line = kwargs.get('end_line')
                search_pattern = kwargs.get('search_pattern')
                replacement_text = kwargs.get('replacement_text')

                if start_line is not None and end_line is not None:
                    updated_content = self._edit_by_lines(lines, start_line, end_line, new_content)
                elif search_pattern and replacement_text:
                    updated_content = self._find_and_replace(original_content, search_pattern, replacement_text)
                else:
                    raise ValueError("Invalid partial edit parameters")

            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(updated_content)

            return f"File successfully updated: {file_path}\n{updated_content}"

        except Exception as e:
            return f"Error editing file: {str(e)}"

    def _edit_by_lines(self, lines: list, start_line: int, end_line: int, new_content: str) -> str:
        if start_line < 1 or end_line > len(lines) or start_line > end_line:
            raise ValueError("Invalid line numbers")

        lines[start_line-1:end_line] = new_content.splitlines()
        return '\n'.join(lines)

    def _find_and_replace(self, content: str, pattern: str, replacement: str) -> str:
        try:
            return re.sub(pattern, replacement, content)
        except re.error as e:
            raise ValueError(f"Invalid regular expression pattern: {str(e)}")