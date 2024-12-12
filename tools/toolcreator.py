from tools.base import BaseTool
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
import os
from dotenv import load_dotenv
import re
import anthropic

load_dotenv()

class ToolCreatorTool(BaseTool):
    name = "toolcreator"
    description = '''
    Creates a new tool based on a natural language description.
    Use this when you need a new capability that isn't available in current tools.
    The tool will be automatically generated and saved to the tools directory.
    Returns the generated tool code and creation status.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Natural language description of what the tool should do"
            }
        },
        "required": ["description"]
    }

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        self.console = Console()
        self.tools_dir = Path(__file__).parent.parent / "tools"  # Fixed path

    def _sanitize_filename(self, name: str) -> str:
        """Convert tool name to valid Python filename"""
        return name + '.py'  # Keep exact name, just add .py

    def _validate_tool_name(self, name: str) -> bool:
        """Validate tool name matches required pattern"""
        return bool(re.match(r'^[a-zA-Z0-9_-]{1,64}$', name))

    def execute(self, **kwargs) -> str:
        description = kwargs.get("description")

        # Create exact same prompt as the original
        prompt = f"""Create a Python tool class that follows our BaseTool interface. The tool should:

1. {description}

Important:
- The filename MUST EXACTLY match the tool name used in the class
- The name property MUST EXACTLY match the class name in lowercase
- For example, if the class is `WeatherTool`, then:
  - name property must be "weathertool"
  - file must be weathertool.py

Here's the required structure (including imports and format):

```python
from tools.base import BaseTool  # This import must be present
import requests  # Add any other required imports

class ToolName(BaseTool):  # Class name must match name property in uppercase first letter
    name = "toolname"  # Must match class name in lowercase
    description = '''
    Detailed description here.
    Multiple lines for clarity.
    '''
    input_schema = {{
        "type": "object",
        "properties": {{
            # Required input parameters
        }},
        "required": []  # List required parameters
    }}

    def execute(self, **kwargs) -> str:
        # Implementation here
        pass
```

Generate the complete tool implementation following this exact structure.
Return ONLY the Python code without any explanation or markdown formatting.
"""

        try:
            # Get tool implementation from Claude with animation
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            tool_code = response.content[0].text.strip()

            # Extract tool name from the generated code
            name_match = re.search(r'name\s*=\s*["\']([a-zA-Z0-9_-]+)["\']', tool_code)
            if not name_match:
                return "Error: Could not extract tool name from generated code"

            tool_name = name_match.group(1)
            filename = self._sanitize_filename(tool_name)

            # Ensure the tools directory exists
            self.tools_dir.mkdir(exist_ok=True)

            # Save tool to file
            file_path = self.tools_dir / filename
            with open(file_path, 'w') as f:
                f.write(tool_code)

            # Format the response using Panel like the original
            result = f"""[bold green]✅ Tool created successfully![/bold green]
Tool name: [cyan]{tool_name}[/cyan]
File created: [cyan]{filename}[/cyan]

[bold]Generated Tool Code:[/bold]
{Panel(tool_code, border_style="green")}

[bold green]✨ Tool is ready to use![/bold green]
Type 'refresh' to load your new tool."""

            return result

        except Exception as e:
            return f"[bold red]Error creating tool:[/bold red] {str(e)}"
