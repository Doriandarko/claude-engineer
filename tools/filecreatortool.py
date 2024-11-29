from tools.base import BaseTool
import os
import json
from typing import Union, List, Dict
from pathlib import Path

class FileCreatorTool(BaseTool):
    name = "filecreatortool"
    description = '''
    Creates new files with specified content.
    Accepts single file specification or list of files.
    Each file spec must include path and content.
    Creates parent directories as needed.
    Supports both text and binary content.
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
        files = kwargs.get('files', [])
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