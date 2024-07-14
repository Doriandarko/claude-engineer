import difflib
import os

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from tavily import TavilyClient

from config import TAVILY_API_KEY

console = Console()
tavily = TavilyClient(api_key=TAVILY_API_KEY)


def create_folder(path):
    try:
        os.makedirs(path, exist_ok=True)
        return f"Folder created: {path}"
    except Exception as e:
        return f"Error creating folder: {str(e)}"


def create_file(path, content=""):
    try:
        with open(path, "w") as f:
            f.write(content)
        return f"File created: {path}"
    except Exception as e:
        return f"Error creating file: {str(e)}"


def highlight_diff(diff_text):
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)


def generate_and_apply_diff(original_content, new_content, path):
    diff = list(
        difflib.unified_diff(
            original_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )

    if not diff:
        return "No changes detected."

    try:
        with open(path, "w") as f:
            f.writelines(new_content)

        diff_text = "".join(diff)
        highlighted_diff = highlight_diff(diff_text)

        diff_panel = Panel(
            highlighted_diff,
            title=f"Changes in {path}",
            expand=False,
            border_style="cyan",
        )

        console.print(diff_panel)

        added_lines = sum(
            1 for line in diff if line.startswith("+") and not line.startswith("+++")
        )
        removed_lines = sum(
            1 for line in diff if line.startswith("-") and not line.startswith("---")
        )

        summary = f"Changes applied to {path}:\n"
        summary += f"  Lines added: {added_lines}\n"
        summary += f"  Lines removed: {removed_lines}\n"

        return summary

    except Exception as e:
        error_panel = Panel(
            f"Error: {str(e)}", title="Error Applying Changes", style="bold red"
        )
        console.print(error_panel)
        return f"Error applying changes: {str(e)}"


def edit_and_apply(path, new_content):
    try:
        with open(path, "r") as file:
            original_content = file.read()

        if new_content != original_content:
            diff_result = generate_and_apply_diff(original_content, new_content, path)
            return f"Changes applied to {path}:\n{diff_result}"
        else:
            return f"No changes needed for {path}"
    except Exception as e:
        return f"Error editing/applying to file: {str(e)}"


def read_file(path):
    try:
        with open(path, "r") as f:
            content = f.read()
        return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


def list_files(path="."):
    try:
        files = os.listdir(path)
        return "\n".join(files)
    except Exception as e:
        return f"Error listing files: {str(e)}"


def tavily_search(query):
    try:
        response = tavily.qna_search(query=query, search_depth="advanced")
        return response
    except Exception as e:
        return f"Error performing search: {str(e)}"


tools = [
    {
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "create_file",
        "description": "Create a new file at the specified path with content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created",
                },
                "content": {"type": "string", "description": "The content of the file"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "search_file",
        "description": "Search for a specific pattern in a file and return the line numbers where the pattern is found. Use this to locate specific code or text within a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to search",
                },
                "search_pattern": {
                    "type": "string",
                    "description": "The pattern to search for in the file",
                },
            },
            "required": ["path", "search_pattern"],
        },
    },
    {
        "name": "edit_and_apply",
        "description": "Apply changes to a file. Use this when you need to edit an existing file. YOU ALWAYS PROVIDE THE FULL FILE CONTENT WHEN EDITING. NO PARTIAL CONTENT OR COMMENTS. YOU MUST PROVIDE THE FULL FILE CONTENT.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to edit",
                },
                "new_content": {
                    "type": "string",
                    "description": "The new content to apply to the file",
                },
            },
            "required": ["path", "new_content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_files",
        "description": "List all files and directories in the specified folder. Use this when you need to see the contents of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)",
                }
            },
        },
    },
    {
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
]


def execute_tool(tool_name, tool_input):
    try:
        if tool_name == "create_folder":
            return create_folder(tool_input["path"])
        elif tool_name == "create_file":
            return create_file(tool_input["path"], tool_input.get("content", ""))
        elif tool_name == "edit_and_apply":
            return edit_and_apply(tool_input["path"], tool_input.get("new_content"))
        elif tool_name == "read_file":
            return read_file(tool_input["path"])
        elif tool_name == "list_files":
            return list_files(tool_input.get("path", "."))
        elif tool_name == "tavily_search":
            return tavily_search(tool_input["query"])
        else:
            return f"Unknown tool: {tool_name}"
    except KeyError as e:
        return f"Error: Missing required parameter {str(e)} for tool {tool_name}"
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"
