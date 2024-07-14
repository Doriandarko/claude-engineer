import importlib
import os
import sys
from unittest.mock import mock_open, patch

import pytest


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    original_environ = dict(os.environ)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    yield
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture
def load_config():
    def _load_config():
        if "config" in sys.modules:
            del sys.modules["config"]
        import config

        return importlib.reload(config)

    return _load_config


@pytest.fixture(autouse=True)
def mock_dotenv_load(monkeypatch):
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)


def test_env_variables_loaded(monkeypatch, load_config):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")
    config = load_config()
    assert config.ANTHROPIC_API_KEY == "test_anthropic_key"
    assert config.TAVILY_API_KEY == "test_tavily_key"


def test_tavily_api_key_missing(monkeypatch, load_config):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    with pytest.raises(
        ValueError, match="TAVILY_API_KEY is not set in the environment variables"
    ):
        load_config()


def test_anthropic_api_key_missing(monkeypatch, load_config):
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")
    with pytest.raises(
        ValueError, match="ANTHROPIC_API_KEY is not set in the environment variables"
    ):
        load_config()


def test_both_api_keys_missing(load_config):
    with pytest.raises(
        ValueError, match="ANTHROPIC_API_KEY is not set in the environment variables"
    ):
        load_config()


def test_load_dotenv_file(monkeypatch, load_config):
    mock_env_content = (
        "ANTHROPIC_API_KEY=test_anthropic_key\nTAVILY_API_KEY=test_tavily_key"
    )
    monkeypatch.setattr("builtins.open", mock_open(read_data=mock_env_content))
    monkeypatch.setattr("os.path.exists", lambda x: True)
    monkeypatch.setattr("dotenv.load_dotenv", lambda: None)

    def mock_getenv(key, default=None):
        if key == "ANTHROPIC_API_KEY":
            return "test_anthropic_key"
        elif key == "TAVILY_API_KEY":
            return "test_tavily_key"
        return default

    monkeypatch.setattr("os.getenv", mock_getenv)

    config = load_config()
    assert config.ANTHROPIC_API_KEY == "test_anthropic_key"
    assert config.TAVILY_API_KEY == "test_tavily_key"


def test_constants(monkeypatch, load_config):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setenv("TAVILY_API_KEY", "test_tavily_key")
    config = load_config()
    assert config.CONTINUATION_EXIT_PHRASE == "AUTOMODE_COMPLETE"
    assert config.MAX_CONTINUATION_ITERATIONS == 25
    assert config.MAX_TOKENS == 10000
    assert config.DB_FILE == "conversation_state.db"
    assert config.MAINMODEL == "claude-3-5-sonnet-20240620"
    assert config.TOOLCHECKERMODEL == "claude-3-5-sonnet-20240620"


@pytest.fixture(autouse=True)
def debug_env():
    print("Environment at start:", dict(os.environ))
    yield
    print("Environment at end:", dict(os.environ))
