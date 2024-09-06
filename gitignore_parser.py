import os
import io
import re
import mimetypes
import fnmatch

class GitignoreParser:
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.exclusion_rules = []

    def _parse_gitignore(self, file_path, relative_path):
        """Parses a .gitignore file and adds its patterns to the exclusion rules."""
        patterns = []
        with open(file_path, 'r') as f:
            for line in f:
                # Strip whitespace
                line = line.strip()
                # Ignore empty lines and comments
                if not line or line.startswith('#'):
                    continue
                # Escape rules starting with literal '#'
                if line.startswith('\\#'):
                    line = line[1:]
                # Handle negation
                negate = line.startswith('!')
                if negate:
                    line = line[1:]
                # Handle trailing spaces with backslash escape
                if line.endswith('\\ '):
                    line = line[:-1] + ' '
                
                # If pattern starts with /, it's relative to the directory containing the .gitignore 
                if line.startswith('/'):
                    pattern = os.path.join(relative_path, line[1:])
                else:
                    # No leading /, means it applies to all levels under the root
                    pattern = os.path.join('**', line)
                
                patterns.append((negate, pattern))
        return patterns

    def _scan_directory(self, dir_path):
        """Recursively scans directories, collecting patterns from .gitignore files."""
        for root, dirs, files in os.walk(dir_path):
            relative_path = os.path.relpath(root, self.root_dir)
            gitignore_path = os.path.join(root, '.gitignore')
            if os.path.isfile(gitignore_path):
                patterns = self._parse_gitignore(gitignore_path, relative_path)
                self.exclusion_rules.extend(patterns)

    def add_exclusions(self, manual_exclusions):
        self.exclusion_rules.extend(manual_exclusions)

    def build_exclusion_list(self):
        """Scans the project directory and builds a list of exclusion rules."""
        self._scan_directory(self.root_dir)

    def _match_pattern(self, pattern, path):
        """Checks if a path matches a given pattern."""
        # Special handling for '**' wildcards
        if '**' in pattern:
            # '**' can match zero or more directories
            pattern = pattern.replace('**', '*')
            return fnmatch.fnmatch(path, pattern)
        # Regular pattern matching
        return fnmatch.fnmatch(path, pattern)

    def is_excluded(self, path):
        """Determines if a given path is excluded by the .gitignore rules."""
        # Paths must be relative to the root directory
        relative_path = os.path.relpath(path, self.root_dir)
        # Apply rules in order, as later rules can negate earlier ones
        excluded = False
        for negate, pattern in self.exclusion_rules:
            if self._match_pattern(pattern, relative_path):
                excluded = not negate
        return excluded
