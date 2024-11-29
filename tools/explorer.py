import os
import shutil
from datetime import datetime
from tools.base import BaseTool

class FileTool(BaseTool):
    name = "explorer"
    description = '''
    Enhanced file and directory management tool for handling all file system operations.
    Can create, list, delete, move, and search both files and directories.
    Provides detailed information about files and directories.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["list", "create_file", "create_dir", "delete", "move", "search", "info"],
                "description": "File system operation to perform"
            },
            "path": {
                "type": "string",
                "description": "File or directory path"
            },
            "destination": {
                "type": "string",
                "description": "Destination path for move operation"
            },
            "content": {
                "type": "string",
                "description": "Content for file creation"
            },
            "search_term": {
                "type": "string",
                "description": "Term to search for in files/directories"
            }
        },
        "required": ["operation", "path"]
    }

    def execute(self, **kwargs) -> str:
        operation = kwargs.get("operation")
        path = kwargs.get("path")
        
        try:
            if operation == "list":
                return self._list_directory(path)
            elif operation == "create_file":
                content = kwargs.get("content", "")
                return self._create_file(path, content)
            elif operation == "create_dir":
                return self._create_directory(path)
            elif operation == "delete":
                return self._delete_item(path)
            elif operation == "move":
                destination = kwargs.get("destination")
                return self._move_item(path, destination)
            elif operation == "search":
                search_term = kwargs.get("search_term", "")
                return self._search_items(path, search_term)
            elif operation == "info":
                return self._get_item_info(path)
            else:
                return f"Invalid operation: {operation}"
        except Exception as e:
            return f"Error: {str(e)}"

    def _list_directory(self, path: str) -> str:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        items = os.listdir(path)
        formatted_items = []
        for item in items:
            full_path = os.path.join(path, item)
            item_type = "[DIR]" if os.path.isdir(full_path) else "[FILE]"
            formatted_items.append(f"{item_type} {item}")
        return "\n".join(formatted_items)

    def _create_file(self, path: str, content: str) -> str:
        try:
            with open(path, 'w') as f:
                f.write(content)
            return f"File created successfully: {path}"
        except Exception as e:
            return f"Failed to create file: {str(e)}"

    def _create_directory(self, path: str) -> str:
        try:
            os.makedirs(path, exist_ok=True)
            return f"Directory created successfully: {path}"
        except Exception as e:
            return f"Failed to create directory: {str(e)}"

    def _delete_item(self, path: str) -> str:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        try:
            if os.path.isfile(path):
                os.remove(path)
                return f"Successfully deleted file: {path}"
            else:
                shutil.rmtree(path)
                return f"Successfully deleted directory: {path}"
        except Exception as e:
            return f"Failed to delete: {str(e)}"

    def _move_item(self, source: str, destination: str) -> str:
        if not os.path.exists(source):
            return f"Source path does not exist: {source}"
        
        try:
            shutil.move(source, destination)
            item_type = "directory" if os.path.isdir(destination) else "file"
            return f"Successfully moved {item_type} from {source} to {destination}"
        except Exception as e:
            return f"Failed to move: {str(e)}"

    def _search_items(self, path: str, search_term: str) -> str:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        results = []
        for root, dirs, files in os.walk(path):
            for dir_name in dirs:
                if search_term.lower() in dir_name.lower():
                    full_path = os.path.join(root, dir_name)
                    results.append(f"[DIR] {full_path}")
            for file_name in files:
                if search_term.lower() in file_name.lower():
                    full_path = os.path.join(root, file_name)
                    results.append(f"[FILE] {full_path}")
        
        return "\n".join(results) if results else "No matches found"

    def _get_item_info(self, path: str) -> str:
        if not os.path.exists(path):
            return f"Path does not exist: {path}"
        
        stats = os.stat(path)
        item_type = "Directory" if os.path.isdir(path) else "File"
        size = stats.st_size
        modified = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        info = [
            f"Type: {item_type}",
            f"Size: {size} bytes",
            f"Last Modified: {modified}",
            f"Permissions: {oct(stats.st_mode)[-3:]}"
        ]
        
        return "\n".join(info)