from tools.base import BaseTool
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv
import os
import time
import json
import base64

class E2bCodeTool(BaseTool):
    name = "e2bcodetool"
    description = '''
    Executes Python code in a sandboxed environment using e2b-code-interpreter.
    Features:
    - Execute Python code safely in isolation
    - Upload files to sandbox
    - Download files from sandbox
    - Support for environment variables
    Returns execution results including stdout, stderr, and file contents.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "env_vars": {
                "type": "object",
                "description": "Dictionary of environment variables",
                "additionalProperties": {"type": "string"}
            },
            "upload_files": {
                "type": "array",
                "description": "List of files to upload to sandbox",
                "items": {
                    "type": "object",
                    "properties": {
                        "local_path": {"type": "string"},
                        "sandbox_path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["sandbox_path", "content"]
                }
            },
            "download_paths": {
                "type": "array",
                "description": "List of file paths to download from sandbox",
                "items": {"type": "string"}
            }
        },
        "required": ["code"]
    }

    def execute(self, **kwargs) -> str:
        try:
            load_dotenv()
            
            code = kwargs.get("code")
            upload_files = kwargs.get("upload_files", [])
            download_paths = kwargs.get("download_paths", [])
            
            # Create sandbox instance
            sandbox = Sandbox()
            
            # Upload files if specified
            uploaded_files = []
            for file_spec in upload_files:
                try:
                    sandbox_path = file_spec["sandbox_path"]
                    content = file_spec["content"]
                    
                    # Handle both text and base64 content
                    if ";base64," in content:
                        # Extract base64 data
                        content = content.split(";base64,")[1]
                        file_content = base64.b64decode(content)
                    else:
                        file_content = content.encode('utf-8')
                        
                    sandbox.files.write(sandbox_path, file_content)
                    uploaded_files.append(sandbox_path)
                except Exception as e:
                    return json.dumps({
                        "success": False,
                        "error": f"Failed to upload file {sandbox_path}: {str(e)}",
                        "stdout": "",
                        "stderr": ""
                    }, indent=2)

            # Execute code
            result = sandbox.run_code(code)
            
            # Download requested files
            downloaded_files = {}
            for file_path in download_paths:
                try:
                    content = sandbox.files.read(file_path)
                    # Convert binary content to base64
                    if isinstance(content, bytes):
                        content = base64.b64encode(content).decode('utf-8')
                        content = f"data:application/octet-stream;base64,{content}"
                    downloaded_files[file_path] = content
                except Exception as e:
                    downloaded_files[file_path] = f"Error downloading: {str(e)}"
            
            response = {
                "stdout": result.logs.stdout,
                "stderr": result.logs.stderr,
                "success": True,
                "error": None,
                "uploaded_files": uploaded_files,
                "downloaded_files": downloaded_files
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "stdout": "",
                "stderr": "",
                "uploaded_files": [],
                "downloaded_files": {}
            }, indent=2)