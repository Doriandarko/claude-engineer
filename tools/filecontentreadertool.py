from tools.base import BaseTool
import os
import json
import mimetypes

class FileContentReaderTool(BaseTool):
    name = "filecontentreadertool"
    description = '''
    Reads content from multiple files and returns their contents.
    Accepts a list of file paths and returns a dictionary with file paths as keys
    and their content as values.
    Handles file reading errors gracefully with built-in Python exceptions.
    When given a directory, recursively reads all text files while skipping binaries and common ignore patterns.
    '''
    
    # Files and directories to ignore
    IGNORE_PATTERNS = {
        # Hidden files and directories
        '.git', '.svn', '.hg', '.DS_Store', '.env', '.idea', '.vscode', '.settings',
        # Build directories
        'node_modules', '__pycache__', 'build', 'dist', 'venv', 'env', 'bin', 'obj',
        'target', 'out', 'Debug', 'Release', 'x64', 'x86', 'builds', 'coverage',
        # Binary file extensions
        '.pyc', '.pyo', '.so', '.dll', '.dylib', '.pdb', '.ilk', '.exp', '.map',
        '.exe', '.bin', '.dat', '.db', '.sqlite', '.sqlite3', '.o', '.cache',
        '.lib', '.a', '.sys', '.ko', '.obj', '.iso', '.msi', '.msp', '.msm',
        '.img', '.dmg', '.class', '.jar', '.war', '.ear', '.aar', '.apk',
        # Media files
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.psd', '.ai', '.eps',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.aac', '.m4a', '.wma', '.midi',
        '.flv', '.mkv', '.wmv', '.m4v', '.webm', '.3gp', '.mpg', '.mpeg', '.m2v',
        '.ogg', '.ogv', '.webp', '.heic', '.raw', '.svg', '.ico', '.icns',
        # Archive files
        '.zip', '.tar', '.gz', '.rar', '.7z', '.pkg', '.deb', '.rpm', '.snap',
        '.bz2', '.xz', '.cab', '.iso', '.tgz', '.tbz2', '.lz', '.lzma', '.tlz',
        # IDE and editor files
        '.sln', '.suo', '.user', '.workspace', '.project', '.classpath', '.iml',
        # Log and temp files
        '.log', '.tmp', '.temp', '.swp', '.bak', '.old', '.orig', '.pid'
    }

    input_schema = {
        "type": "object",
        "properties": {
            "file_paths": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "List of file paths to read"
            }
        },
        "required": ["file_paths"]
    }

    def _should_skip(self, path: str) -> bool:
        """Determine if a file or directory should be skipped."""
        name = os.path.basename(path)
        ext = os.path.splitext(name)[1].lower()

        # Skip if name or extension matches ignore patterns
        if name in self.IGNORE_PATTERNS or ext in self.IGNORE_PATTERNS:
            return True

        # Skip hidden files/directories (starting with .)
        if name.startswith('.'):
            return True

        # If it's a file, check if it's binary using mimetype
        if os.path.isfile(path):
            mime_type, _ = mimetypes.guess_type(path)
            if mime_type and not mime_type.startswith('text/'):
                return True

        return False

    def _read_file(self, file_path: str) -> str:
        """Safely read a file and handle errors."""
        try:
            if not os.path.exists(file_path):
                return "Error: File not found"

            if self._should_skip(file_path):
                return "Skipped: Binary or ignored file type"

            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()

        except PermissionError:
            return "Error: Permission denied"
        except IsADirectoryError:
            return "Error: Path is a directory"
        except UnicodeDecodeError:
            return "Error: Unable to decode file (likely binary)"
        except Exception as e:
            return f"Error: {str(e)}"

    def _read_directory(self, dir_path: str) -> dict:
        """Recursively read all files in a directory."""
        results = {}

        try:
            for root, dirs, files in os.walk(dir_path):
                # Filter out directories to skip
                dirs[:] = [d for d in dirs if not self._should_skip(os.path.join(root, d))]

                # Process files
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self._should_skip(file_path):
                        content = self._read_file(file_path)
                        results[file_path] = content

        except Exception as e:
            results[dir_path] = f"Error reading directory: {str(e)}"

        return results

    def execute(self, **kwargs) -> str:
        file_paths = kwargs.get('file_paths', [])
        results = {}

        try:
            for path in file_paths:
                if os.path.isdir(path):
                    # If it's a directory, read it recursively
                    dir_results = self._read_directory(path)
                    results.update(dir_results)
                else:
                    # If it's a file, read it directly
                    content = self._read_file(path)
                    results[path] = content

            return json.dumps(results, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e)}, indent=2)