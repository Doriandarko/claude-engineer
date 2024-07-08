TOOLS = [
    {
        "type": "function",
        "name": "read_folder_tree",
        "description": "Read the contents of a folder at the specified path. Use this when you need to see the structure of a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "delete_file",
        "description": "Delete a file at the specified path. Use this when you need to remove a file from the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to delete"
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "rename_file",
        "description": "Rename a file at the specified path. Use this when you need to rename a file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to rename"
                },
                "new_name": {
                    "type": "string",
                    "description": "The new name of the file"
                }
            },
            "required": ["path", "new_name"]
        }
    },
     # Move file
    {
        "type": "function",
        "name": "move_file",
        "description": "Move a file from one path to another. Use this when you need to relocate a file within the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_path": {
                    "type": "string",
                    "description": "The current path of the file"
                },
                "destination_path": {
                    "type": "string",
                    "description": "The new path of the file"
                }
            },
            "required": ["source_path", "destination_path"]
        }
    },
    {
        "type": "function",
        "name": "create_folder",
        "description": "Create a new folder at the specified path. Use this when you need to create a new directory in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the folder should be created"
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "create_file",
        "description": "Create a new file at the specified path with optional content. Use this when you need to create a new file in the project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path where the file should be created"
                },
                "content": {
                    "type": "string",
                    "description": "The initial content of the file (optional)"
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "apply_patch",
        "description": "Apply a patch to a file or directory. Use this when you need to make changes to an existing file or directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pwd": {
                    "type": "string",
                    "description": "The working directory where the patch should be applied"
                },
                "patch": {
                    "type": "string",
                    "description": "The patch to apply"
                }
            },
            "required": ["pwd", "patch"]
        }
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read the contents of a file at the specified path and prepend line numbers on each line. Use this when you need to examine the contents of an existing file. Use the line numbers when writing a patch, ignore them otherwise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the file to read"
                }
            },
            "required": ["path"]
        }
    },
    {
        "type": "function",
        "name": "list_files",
        "description": "List all files and directories in the root folder where the script is running. Use this when you need to see the contents of the current directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path of the folder to list (default: current directory)"
                }
            }
        }
    },
    {
        "type": "function",
        "name": "tavily_search",
        "description": "Perform a web search using Tavily API to get up-to-date information or additional context. Use this when you need current information or feel a search could provide a better answer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "type": "function",
        "name": "run_build_command",
        "description": "Run a build command in the current directory. Use this when you need to build a project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pwd": {
                    "type": "string",
                    "description": "The working directory where the build command should be run"
                },
                "command": {
                    "type": "string",
                    "description": "The build command to run"
                }
            },
            "required": ["pwd", "command"]
        }
    },
    {
        "type": "function",
        "name": "end_automode",
        "description": "End the automode and return to manual mode. Use this when you know your goals are completed and the build passes (if the user provided a build command).",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]