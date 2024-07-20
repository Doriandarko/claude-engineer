import difflib
from utils import highlight_diff, print_panel
from tools.base_tool import base_tool


class edit_and_apply(base_tool):
    def __init__(self):
        super().__init__()
        self.definition = {
        "name": "edit_and_apply",
        "description": "Apply changes to a file. Use this when you need to edit an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to edit"
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content to apply to the file"
                }
            },
            "required": ["path", "new_content"]
        }
    }
        self.name = self.definition["name"]
    
    def execute(tool_input):
        try:
            path = tool_input["path"]
            new_content = tool_input["new_content"]
            with open(path, 'r') as file:
                original_content = file.read()
            
            if new_content != original_content:
                diff = list(difflib.unified_diff(
                    original_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3
                ))

                with open(path, 'w') as f:
                    f.write(new_content)

                diff_text = ''.join(diff)
                highlighted_diff = highlight_diff(diff_text)

                print_panel(highlighted_diff, f"Changes in {path}")

                added_lines = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
                removed_lines = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))

                return f"Changes applied to {path}. Lines added: {added_lines}, Lines removed: {removed_lines}"
            else:
                return f"No changes needed for {path}"
        except Exception as e:
            return f"Error editing/applying to file: {str(e)}"
    