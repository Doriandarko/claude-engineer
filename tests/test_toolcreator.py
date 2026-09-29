import pytest

from tools.toolcreator import ToolCreatorTool


def make_tool():
    return ToolCreatorTool.__new__(ToolCreatorTool)


def test_clean_generated_code_strips_outer_python_fence():
    code = make_tool()._clean_generated_code(
        "```python\nfrom tools.base import BaseTool\n\nclass DemoTool(BaseTool):\n    name = \"demotool\"\n```"
    )

    assert code.startswith("from tools.base import BaseTool")
    assert "```" not in code


def test_clean_generated_code_rejects_invalid_python():
    with pytest.raises(SyntaxError):
        make_tool()._clean_generated_code("```python\nclass Broken(:\n```")
