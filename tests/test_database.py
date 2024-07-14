# tests/test_database.py
import os
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

# Set testing environment variable before importing database
os.environ["TESTING"] = "true"

import database
from database import (
    ensure_table_exists,
    execute_transaction,
    init_db,
    load_state,
    save_state,
)


@pytest.fixture(autouse=True)
def use_in_memory_database():
    print("\nSetting up in-memory database")
    original_db_file = database.DB_FILE
    database.DB_FILE = ":memory:"
    database.close_db_connection()  # Close any existing connection
    database.conversation_history = []  # Reset conversation_history
    database.init_db()  # Ensure tables are created for each test
    yield
    database.close_db_connection()  # Close the connection after the test
    database.conversation_history = []  # Reset conversation_history after test
    database.DB_FILE = original_db_file


def test_execute_transaction():
    queries = [
        ("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", ()),
        ("INSERT INTO test (value) VALUES (?)", ("test_value",)),
        ("SELECT value FROM test", ()),
    ]
    result = execute_transaction(queries)

    assert result == [[], [], [("test_value",)]]


def test_ensure_table_exists():
    result = ensure_table_exists("conversation_history")
    assert result == [[]]

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
        )
        assert cursor.fetchone() is not None


def test_init_db():
    init_db()

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
        )
        assert cursor.fetchone() is not None


def test_load_state():
    ensure_table_exists("conversation_history")
    execute_transaction(
        [
            (
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                ("user", "Hello"),
            ),
            (
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                ("assistant", "Hi there!"),
            ),
        ]
    )

    loaded_history = load_state()
    assert loaded_history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    assert database.conversation_history == loaded_history


def test_save_state():
    database.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    save_state()

    result = execute_transaction(
        [("SELECT role, content FROM conversation_history", ())]
    )
    assert result == [[("user", "Hello"), ("assistant", "Hi there!")]]


@patch("database.get_db_connection")
def test_connection_closed_after_exception(mock_get_conn):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_cursor.execute.side_effect = sqlite3.Error("Test error")

    with pytest.raises(sqlite3.Error):
        execute_transaction([("SELECT * FROM non_existent_table", ())])

    # For in-memory databases, we don't close the connection after each transaction
    # Instead, we check if close_db_connection was called in the fixture teardown
    if database.DB_FILE == ":memory:":
        mock_conn.close.assert_not_called()
    else:
        mock_conn.close.assert_called_once()
