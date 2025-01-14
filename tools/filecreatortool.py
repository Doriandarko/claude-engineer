from tools.base import BaseTool
import os
import json
from typing import Union, List, Dict
from pathlib import Path

class FileCreatorTool(BaseTool):
    name = "filecreatortool"
    description = '''
    Creates new files with specified content.
    
    IMPORTANT: The input must follow this exact structure:
    1. For a single file:
       {
           "files": {
               "path": "path/to/file.txt",
               "content": "file content here"
           }
       }
    
    2. For multiple files:
       {
           "files": [
               {
                   "path": "path/to/file1.txt",
                   "content": "content for file 1"
               },
               {
                   "path": "path/to/file2.txt",
                   "content": "content for file 2"
               }
           ]
       }
    
    Features:
    - Creates parent directories automatically if they don't exist
    - Supports both text and binary content
    - Can create multiple files in one call
    - Handles JSON content automatically
    
    Optional parameters:
    - binary: boolean (default: false) - Set to true for binary files
    - encoding: string (default: "utf-8") - Specify file encoding
    
    Example usage:
    1. Create a Python file:
       {
           "files": {
               "path": "test.py",
               "content": "def hello():\\n    print('Hello, World!')"
           }
       }
    
    2. Create multiple files:
       {
           "files": [
               {
                   "path": "src/main.py",
                   "content": "# Main file content"
               },
               {
                   "path": "src/utils.py",
                   "content": "# Utils file content"
               }
           ]
       }
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "files": {
                "oneOf": [
                    {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"oneOf": [{"type": "string"}, {"type": "object"}]},
                            "binary": {"type": "boolean", "default": False},
                            "encoding": {"type": "string", "default": "utf-8"}
                        },
                        "required": ["path", "content"]
                    },
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "path": {"type": "string"},
                                "content": {"oneOf": [{"type": "string"}, {"type": "object"}]},
                                "binary": {"type": "boolean", "default": False},
                                "encoding": {"type": "string", "default": "utf-8"}
                            },
                            "required": ["path", "content"]
                        }
                    }
                ]
            }
        },
        "required": ["files"]
    }

    def execute(self, **kwargs) -> str:
        """
        Execute the file creation process.
        
        Args:
            **kwargs: Must contain 'files' key with either a dict or list of dicts
                     Each dict must have 'path' and 'content' keys
        
        Returns:
            str: JSON string containing results of file creation operations
        """
        files = kwargs.get('files', [])
        
        # Handle double nesting issue
        if isinstance(files, dict) and 'files' in files:
            files = files['files']
        
        if isinstance(files, dict):
            files = [files]

        results = []
        for file_spec in files:
            try:
                path = Path(file_spec['path'])
                content = file_spec['content']
                binary = file_spec.get('binary', False)
                encoding = file_spec.get('encoding', 'utf-8')

                # Create parent directories
                path.parent.mkdir(parents=True, exist_ok=True)

                # Handle content
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2)

                # Write file
                mode = 'wb' if binary else 'w'
                if binary:
                    if isinstance(content, str):
                        content = content.encode(encoding)
                    with open(path, mode) as f:
                        f.write(content)
                else:
                    with open(path, mode, encoding=encoding, newline='') as f:
                        f.write(content)

                results.append({
                    'path': str(path),
                    'success': True,
                    'size': path.stat().st_size
                })

            except Exception as e:
                results.append({
                    'path': str(path) if 'path' in locals() else None,
                    'success': False,
                    'error': str(e)
                })

        return json.dumps({
            'created_files': len([r for r in results if r['success']]),
            'failed_files': len([r for r in results if not r['success']]),
            'results': results
        }, indent=2)
