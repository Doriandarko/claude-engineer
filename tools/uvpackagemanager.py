import logging
import subprocess
from typing import List, Optional

from tools.base import BaseTool


class UVPackageManager(BaseTool):
    name = "uvpackagemanager"
    description = '''
    Comprehensive interface to the uv package manager providing package management,
    project management, Python version management, tool management, and script support.
    Supports all major platforms with pip compatibility.
    '''
    input_schema = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Primary command (install, remove, update, init, venv, etc.)"
            },
            "packages": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of packages to operate on"
            },
            "python_version": {
                "type": "string",
                "description": "Python version for operations that require it"
            },
            "project_path": {
                "type": "string",
                "description": "Path to project directory"
            },
            "requirements_file": {
                "type": "string",
                "description": "Path to requirements file"
            },
            "global_install": {
                "type": "boolean",
                "description": "Whether to install packages globally"
            }
        },
        "required": ["command"]
    }

    def execute(self, **kwargs) -> str:
        command = kwargs.get("command")
        packages = kwargs.get("packages", [])
        python_version = kwargs.get("python_version")
        project_path = kwargs.get("project_path", ".")
        requirements_file = kwargs.get("requirements_file")
        global_install = kwargs.get("global_install", False)

        try:
            if command == "install":
                return self._install_packages(packages, requirements_file, global_install)
            elif command == "remove":
                return self._remove_packages(packages)
            elif command == "update":
                return self._update_packages(packages)
            elif command == "list":
                return self._list_packages()
            elif command == "init":
                return self._init_project(project_path)
            elif command == "venv":
                return self._create_venv(project_path, python_version)
            elif command == "python":
                return self._manage_python(python_version)
            elif command == "compile":
                return self._compile_requirements()
            elif command == "run":
                return self._run_script(kwargs.get("script"), packages)
            else:
                return f"Unknown command: {command}"
        except Exception as e:
            logging.error(f"Error executing UV command: {e!s}")
            return f"Error: {e!s}"

    def _run_uv_command(self, args: List[str]) -> str:
        try:
            result = subprocess.run(
                ["uv"] + args,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"UV command failed: {e.stderr}")

    def _install_packages(self, packages: List[str], requirements_file: Optional[str], global_install: bool) -> str:
        args = ["pip", "install"]
        if global_install:
            args.append("--global")
        if requirements_file:
            args.extend(["-r", requirements_file])
        if packages:
            args.extend(packages)
        return self._run_uv_command(args)

    def _remove_packages(self, packages: List[str]) -> str:
        return self._run_uv_command(["pip", "uninstall", "-y"] + packages)

    def _update_packages(self, packages: List[str]) -> str:
        args = ["pip", "install", "--upgrade"]
        if packages:
            args.extend(packages)
        return self._run_uv_command(args)

    def _list_packages(self) -> str:
        return self._run_uv_command(["pip", "list"])

    def _init_project(self, project_path: str) -> str:
        return self._run_uv_command(["init", project_path])

    def _create_venv(self, path: str, python_version: Optional[str]) -> str:
        args = ["venv"]
        if python_version:
            args.extend(["--python", python_version])
        args.append(path)
        return self._run_uv_command(args)

    def _manage_python(self, version: Optional[str]) -> str:
        if not version:
            return self._run_uv_command(["python", "list"])
        return self._run_uv_command(["python", "install", version])

    def _compile_requirements(self) -> str:
        return self._run_uv_command(["pip", "compile", "requirements.in"])

    def _run_script(self, script: str, packages: List[str]) -> str:
        args = ["run"]
        if packages:
            args.extend(["--with"] + packages)
        args.extend(["--", "python", script])
        return self._run_uv_command(args)