from tools.base import BaseTool
import os
import re
import json
from typing import List, Dict, Any

class InProjectCodeSearchTool(BaseTool):
    name = "inprojectcodesearchtool"
    description = '''
    Indexes all local files in the project directory and performs fast in-memory searches.
    Supports searching by:
    - filename substring
    - function name (e.g., Python "def " patterns or language-specific patterns)
    - keyword occurrence in file contents
    
    This is language-agnostic and attempts to read all files as text. Files that cannot be read as text are skipped.
    '''

    input_schema = {
        "type": "object",
        "properties": {
            "root_directory": {
                "type": "string",
                "description": "The root directory of the project to index. Defaults to current directory."
            },
            "search_type": {
                "type": "string",
                "enum": ["filename", "function", "keyword"],
                "description": "Type of search to perform: 'filename', 'function', or 'keyword'"
            },
            "query": {
                "type": "string",
                "description": "The search query: substring for filename search, function name pattern, or keyword."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return.",
                "default": 50
            }
        },
        "required": ["search_type", "query"]
    }

    def __init__(self):
        # We’ll build a simple cache in memory for indexing.
        self.indexed_files: Dict[str, List[str]] = {}
        self.indexed_root: str = ""

    def _index_files(self, root_directory: str):
        """
        Walk through the project directory, read all files as text,
        and store their contents in memory. Non-text or unreadable files are skipped.
        """
        self.indexed_files.clear()
        for dirpath, _, filenames in os.walk(root_directory):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        # Heuristic check: skip binary files by searching for null byte
                        if '\0' in content:
                            continue
                        lines = content.splitlines()
                        self.indexed_files[file_path] = lines
                except Exception:
                    # If file can't be read for any reason, skip it
                    continue
        self.indexed_root = root_directory

    def _search_by_filename(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Return files whose name includes the query as a substring.
        """
        results = []
        for file_path in self.indexed_files.keys():
            filename = os.path.basename(file_path)
            if query.lower() in filename.lower():
                results.append({"file_path": file_path})
                if len(results) >= max_results:
                    break
        return results

    def _search_by_function(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search for lines that look like function definitions and contain the query.
        
        A generic pattern is used to detect function-like definitions across various languages:
        - Python: def function_name(
        - JS/TS: function functionName( or arrow functions
        - Java/C-like: <type> functionName(...){
        We look for common keywords and patterns.
        """
        fn_patterns = [
            r"^\s*def\s+\w+",               # Python function definition
            r"^\s*(async\s+)?function\s+\w+", # JS function keyword
            r"^\s*\w+\s+\w+\(.*\)\s*\{",   # Java/C-like function signature
            r"^\s*(const|let|var)\s+\w+\s*=\s*\(.*\)\s*=>" # JS/TS arrow functions
        ]
        combined_pattern = re.compile("|".join(fn_patterns), re.IGNORECASE)
        
        results = []
        for file_path, lines in self.indexed_files.items():
            for i, line in enumerate(lines):
                if combined_pattern.search(line) and query.lower() in line.lower():
                    snippet_start = max(0, i-2)
                    snippet_end = min(len(lines), i+3)
                    snippet = lines[snippet_start:snippet_end]
                    results.append({
                        "file_path": file_path,
                        "line_number": i+1,
                        "match_line": line.strip(),
                        "context": snippet
                    })
                    if len(results) >= max_results:
                        return results
        return results

    def _search_by_keyword(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search all lines in all indexed files for a substring match of the keyword.
        """
        results = []
        lower_query = query.lower()
        for file_path, lines in self.indexed_files.items():
            for i, line in enumerate(lines):
                if lower_query in line.lower():
                    snippet_start = max(0, i-2)
                    snippet_end = min(len(lines), i+3)
                    snippet = lines[snippet_start:snippet_end]
                    results.append({
                        "file_path": file_path,
                        "line_number": i+1,
                        "match_line": line.strip(),
                        "context": snippet
                    })
                    if len(results) >= max_results:
                        return results
        return results

    def execute(self, **kwargs) -> str:
        root_directory = kwargs.get("root_directory", ".")
        search_type = kwargs["search_type"]
        query = kwargs["query"]
        max_results = kwargs.get("max_results", 50)

        # Re-index if root_directory changed or if this is the first run
        if not self.indexed_files or self.indexed_root != root_directory:
            self._index_files(root_directory)

        if search_type == "filename":
            results = self._search_by_filename(query, max_results)
        elif search_type == "function":
            results = self._search_by_function(query, max_results)
        elif search_type == "keyword":
            results = self._search_by_keyword(query, max_results)
        else:
            return json.dumps({"error": "Invalid search type."}, indent=2)

        return json.dumps({"results": results}, indent=2)
