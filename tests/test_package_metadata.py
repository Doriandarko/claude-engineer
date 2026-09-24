from pathlib import Path

from tools.e2bcodetool import E2bCodeTool


ROOT = Path(__file__).resolve().parents[1]


def test_readme_filename_matches_metadata():
    names = {path.name for path in ROOT.iterdir()}
    assert "README.md" in names
    assert "readme.md" not in names
    assert 'readme = "README.md"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_e2b_tool_imports():
    assert E2bCodeTool.name == "e2bcodetool"
