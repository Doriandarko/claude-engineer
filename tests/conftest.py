# tests/conftest.py
import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env():
    os.environ["TESTING"] = "true"
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
    os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")
