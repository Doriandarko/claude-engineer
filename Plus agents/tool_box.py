import os
import sys
import json
import importlib
import inspect

class ToolBox:
    def __init__(self):
        self.tools = []
        self.tool_definitions = []
        tools_folder = os.path.join(os.path.dirname(__file__), "tools")
        self.tools = self.import_tools(tools_folder)

    def import_tools(self, subfolder_path):
        sys.path.append(os.path.dirname(subfolder_path))
        
        for filename in os.listdir(subfolder_path):
            if filename.endswith('.py') and not filename.startswith('__') and filename != 'base_tool.py':
                file_path = os.path.join(subfolder_path, filename)
                module_name = f"tools.{os.path.splitext(filename)[0]}"
                
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Import base_tool here to ensure it's in the module's namespace
                    from tools.base_tool import base_tool
                    
                    for name, obj in inspect.getmembers(module):
                        if inspect.isclass(obj):
                            try:
                                if issubclass(obj, base_tool) and obj is not base_tool:
                                    tool_instance = obj()
                                    self.tools.append(tool_instance)
                                    self.tool_definitions.append(tool_instance.definition)
                            except TypeError as e:
                                print(f"TypeError when checking {name}: {e}")
                                print(f"obj: {obj}, base_tool: {base_tool}")
                                print(f"obj type: {type(obj)}, base_tool type: {type(base_tool)}")
                except Exception as e:
                    print(f"Error importing {filename}: {e}")
        
        sys.path.remove(os.path.dirname(subfolder_path))
    
    def execute_tool(self, tool_name, tool_input):
        for tool in self.tools:
            if tool_name == tool.name:
                return tool.execute(tool_input)
        return f"Unknown tool: {tool_name}"