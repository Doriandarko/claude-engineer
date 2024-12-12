from tools.base import BaseTool
import subprocess
from typing import List
import json

class LintingTool(BaseTool):
    name = "lintingtool"
    description = '''
    Runs the Ruff linter on the given Python files or directories to detect and fix coding style or syntax issues.
    Supports configurable rule selection, automatic fixes, unsafe fixes, adding noqa directives, and watch mode.
    Returns the linter output as a string.
    '''

    input_schema = {
        "type": "object",
        "properties": {
            "paths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file or directory paths to lint. Defaults to current directory if none provided."
            },
            "fix": {
                "type": "boolean",
                "default": False,
                "description": "Whether to automatically fix fixable issues."
            },
            "unsafe_fixes": {
                "type": "boolean",
                "default": False,
                "description": "Enable unsafe fixes."
            },
            "add_noqa": {
                "type": "boolean",
                "default": False,
                "description": "Add noqa directives to all lines with violations."
            },
            "select": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of rule codes to exclusively enforce."
            },
            "extend_select": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of additional rule codes to enforce alongside the default selection."
            },
            "watch": {
                "type": "boolean",
                "default": False,
                "description": "Watch for file changes and re-run linting on change."
            },
            "exit_zero": {
                "type": "boolean",
                "default": False,
                "description": "Exit with code 0 even if violations are found."
            },
            "exit_non_zero_on_fix": {
                "type": "boolean",
                "default": False,
                "description": "Exit with non-zero even if all violations were fixed automatically."
            }
        },
        "required": []
    }

    def execute(self, **kwargs) -> str:
        paths = kwargs.get("paths", [])
        fix = kwargs.get("fix", False)
        unsafe_fixes = kwargs.get("unsafe_fixes", False)
        add_noqa = kwargs.get("add_noqa", False)
        select = kwargs.get("select", [])
        extend_select = kwargs.get("extend_select", [])
        watch = kwargs.get("watch", False)
        exit_zero = kwargs.get("exit_zero", False)
        exit_non_zero_on_fix = kwargs.get("exit_non_zero_on_fix", False)

        cmd = ["uv", "run", "ruff", "check"]

        if fix:
            cmd.append("--fix")
        if unsafe_fixes:
            cmd.append("--unsafe-fixes")
        if add_noqa:
            cmd.append("--add-noqa")
        if watch:
            cmd.append("--watch")
        if exit_zero:
            cmd.append("--exit-zero")
        if exit_non_zero_on_fix:
            cmd.append("--exit-non-zero-on-fix")

        for rule in select:
            cmd.extend(["--select", rule])
        for rule in extend_select:
            cmd.extend(["--extend-select", rule])

        if not paths:
            paths = ["."]
        cmd.extend(paths)

        try:
            result = subprocess.run(
                cmd,
                text=True,
                capture_output=True,
                check=False
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error running ruff check: {str(e)}"
