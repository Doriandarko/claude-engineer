from tools.base import BaseTool
import anthropic
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "claude-3-sonnet-20240229"
MAX_TOKENS = 4000
BACKUP_SUFFIX = ".bak"

load_dotenv()

class FileOperationError(Exception):
    """Custom exception for file operations"""
    pass

class SmartFileEditorTool(BaseTool):
    """A tool for making smart edits to files using Claude's assistance."""
    
    name = "smartfileeditortool"
    description = "Makes precise edits to files based on specific instructions."
    
    input_schema = {
        "type": "object",
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Path to the file to edit"
            },
            "instructions": {
                "type": "string",
                "description": "Instructions for how to modify the code"
            }
        },
        "required": ["file_path", "instructions"]
    }

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _read_file_content(self, file_path: str) -> str:
        """Safely read file content."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise FileOperationError(f"Could not read file: {str(e)}")

    def _write_file_safely(self, file_path: str, content: str) -> None:
        """Safely write content to file with error handling."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Write to temporary file first
            temp_path = f"{file_path}.tmp"
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            # Rename temporary file to target file
            os.replace(temp_path, file_path)
        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {str(e)}")
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise FileOperationError(f"Could not write file: {str(e)}")

    def _create_edit_prompt(self, code: str, instructions: str) -> str:
        """Create the prompt for code editing."""
        return "\n".join([
            "You are a code editor. Generate an updated version of this code based on the instructions.",
            "Return ONLY the modified code without any explanations.",
            "",
            "Original code:",
            code,
            "",
            "Instructions:",
            instructions
        ])

    def _create_verify_prompt(self, original_code: str, new_code: str, instructions: str) -> str:
        """Create the prompt for code verification."""
        return "\n".join([
            "You are a code reviewer. Review these changes and ensure they match the instructions.",
            "If the changes are correct, return ONLY the new code.",
            "If there are issues, return ERROR: followed by the issue.",
            "",
            "Original code:",
            original_code,
            "",
            "New code:",
            new_code,
            "",
            "Instructions:",
            instructions
        ])

    def _create_backup(self, file_path: str, content: str) -> str:
        """Create a backup of the file with proper error handling."""
        try:
            backup_path = f"{file_path}{BACKUP_SUFFIX}"
            counter = 1
            while os.path.exists(backup_path):
                backup_path = f"{file_path}{BACKUP_SUFFIX}.{counter}"
                counter += 1
            
            self._write_file_safely(backup_path, content)
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            raise FileOperationError(f"Could not create backup: {str(e)}")

    def _generate_improved_code(self, current_code: str, instructions: str) -> str:
        """Generate improved code using Claude."""
        try:
            # First pass - generate changes
            prompt = self._create_edit_prompt(current_code, instructions)
            response = self.client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            new_code = response.content[0].text.strip()

            # Second pass - verify changes
            verify_prompt = self._create_verify_prompt(current_code, new_code, instructions)
            verify_response = self.client.messages.create(
                model=MODEL_NAME,
                max_tokens=MAX_TOKENS,
                temperature=0,
                messages=[{"role": "user", "content": verify_prompt}]
            )
            verified_code = verify_response.content[0].text.strip()
            
            if verified_code.startswith("ERROR:"):
                raise ValueError(verified_code.replace("ERROR:", "").strip())
                
            return verified_code
            
        except Exception as e:
            logger.error(f"Error generating improved code: {str(e)}")
            raise

    def execute(self, **kwargs) -> str:
        file_path: str = kwargs.get("file_path", "")
        instructions: str = kwargs.get("instructions", "")

        try:
            # Validate inputs
            if not file_path or not os.path.exists(file_path):
                return "Error: File not found"
            if not instructions:
                return "Error: Instructions are required"

            # Read current content
            logger.info(f"Reading file: {file_path}")
            current_content = self._read_file_content(file_path)

            # Generate improved code
            logger.info("Generating improved code")
            improved_code = self._generate_improved_code(current_content, instructions)

            # Create backup
            logger.info("Creating backup")
            backup_path = self._create_backup(file_path, current_content)

            # Write new content
            logger.info("Writing improved code")
            self._write_file_safely(file_path, improved_code)

            return f"Successfully updated file {file_path} and created backup {backup_path}"

        except FileOperationError as e:
            return f"File operation error: {str(e)}"
        except ValueError as e:
            return f"Validation error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"Error: {str(e)}"