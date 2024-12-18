from tools.base import BaseTool
import os
import fnmatch
from typing import List, Optional

class DirectoryListingTool(BaseTool):
    name = "directorylistingtool"
    description = '''
    Creates a recursive directory listing showing the structure of files and folders.
    Generates a tree-like representation of the directory hierarchy.
    Supports filtering, depth limits, and hidden file handling.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Root directory path to scan"
            },
            "max_depth": {
                "type": "integer",
                "description": "Maximum recursion depth (optional)",
                "minimum": 1
            },
            "exclude_patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Patterns to exclude (e.g. .git, __pycache__)"
            },
            "show_hidden": {
                "type": "boolean",
                "description": "Whether to show hidden files and folders"
            }
        },
        "required": ["path"]
    }

    def _should_exclude(self, name: str, exclude_patterns: List[str]) -> bool:
        if not exclude_patterns:
            return False
        return any(fnmatch.fnmatch(name, pattern) for pattern in exclude_patterns)

    def _is_hidden(self, name: str) -> bool:
        return name.startswith('.')

    def _list_directory(self, path: str, prefix: str = "", current_depth: int = 0,
                       max_depth: Optional[int] = None, exclude_patterns: List[str] = None,
                       show_hidden: bool = False) -> str:
        if not os.path.exists(path):
            return "Error: Directory does not exist"

        if max_depth is not None and current_depth > max_depth:
            return ""

        try:
            items = os.listdir(path)
        except PermissionError:
            return f"{prefix}[Permission Denied]\n"
        except Exception as e:
            return f"{prefix}[Error: {str(e)}]\n"

        result = []
        for item in sorted(items):
            if not show_hidden and self._is_hidden(item):
                continue
            
            if exclude_patterns and self._should_exclude(item, exclude_patterns):
                continue

            full_path = os.path.join(path, item)
            is_dir = os.path.isdir(full_path)
            
            if is_dir:
                result.append(f"{prefix}├── {item}/")
                subdir_content = self._list_directory(
                    full_path,
                    prefix + "│   ",
                    current_depth + 1,
                    max_depth,
                    exclude_patterns,
                    show_hidden
                )
                if subdir_content:
                    result.append(subdir_content)
            else:
                result.append(f"{prefix}├── {item}")

        return "\n".join(result)

    def execute(self, **kwargs) -> str:
        path = kwargs.get("path")
        max_depth = kwargs.get("max_depth")
        exclude_patterns = kwargs.get("exclude_patterns", [])
        show_hidden = kwargs.get("show_hidden", False)

        if not os.path.isdir(path):
            return f"Error: '{path}' is not a valid directory"

        result = f"Directory listing for: {path}\n"
        listing = self._list_directory(
            path,
            max_depth=max_depth,
            exclude_patterns=exclude_patterns,
            show_hidden=show_hidden
        )
        
        return result + listing