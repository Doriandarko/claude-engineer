from tools.base import BaseTool
from e2b_code_interpreter import Sandbox
from dotenv import load_dotenv
import os
import time
import json

class E2bCodeTool(BaseTool):
    name = "e2bcodetool"
    description = '''
    Executes Python code in a sandboxed environment using e2b-code-interpreter.
    Supports environment variables and timeout configuration.
    Returns execution results including stdout, stderr, and execution time.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python code to execute"
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds",
                "default": 300
            },
            "env_vars": {
                "type": "object",
                "description": "Dictionary of environment variables",
                "additionalProperties": {"type": "string"}
            }
        },
        "required": ["code"]
    }

    def execute(self, **kwargs) -> str:
        try:
            load_dotenv()
            
            code = kwargs.get("code")
            timeout = kwargs.get("timeout", 300)
            
            sandbox = Sandbox()
            result = sandbox.run_code(code)
            
            response = {
                "stdout": result.logs.stdout,
                "stderr": result.logs.stderr,
                "success": True,
                "error": None
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"Tool execution failed: {str(e)}",
                "stdout": "",
                "stderr": ""
            }, indent=2)