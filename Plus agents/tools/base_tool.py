from abc import ABC, abstractmethod
from typing import Dict, Any

class base_tool(ABC):
    def __init__(self):
        self.name = None
        pass

    @abstractmethod
    def execute(self, tool_input: Dict[str, Any]) -> Any:
        pass