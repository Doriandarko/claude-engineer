# database.py
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Tuple

from config import DB_FILE

conversation_history: List[Dict[str, Any]] = []


_connection = None


@contextmanager
def get_db_connection():
    global _connection
    if DB_FILE == ":memory:":
        if _connection is None:
            _connection = sqlite3.connect(DB_FILE)
        conn = _connection
    else:
        conn = sqlite3.connect(DB_FILE)

    try:
        yield conn
    finally:
        if DB_FILE != ":memory:":
            conn.close()


def close_db_connection():
    global _connection
    if _connection:
        _connection.close()
        _connection = None


@contextmanager
def get_db_cursor(conn):
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def execute_transaction(queries: List[Tuple[str, tuple]]) -> List[List[Tuple]]:
    results = []
    with get_db_connection() as conn:
        with get_db_cursor(conn) as cursor:
            for query, params in queries:
                cursor.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    results.append(cursor.fetchall())
                else:
                    results.append([])
        conn.commit()
    return results


def ensure_table_exists(table_name: str) -> List[List[Tuple]]:
    if table_name == "conversation_history":
        return execute_transaction(
            [
                (
                    f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """,
                    (),
                )
            ]
        )
    else:
        raise ValueError(f"Unknown table name: {table_name}")


def init_db():
    ensure_table_exists("conversation_history")


def load_state():
    global conversation_history
    ensure_table_exists("conversation_history")
    results = execute_transaction(
        [("SELECT role, content FROM conversation_history ORDER BY id", ())]
    )
    conversation_history = [
        {"role": role, "content": content} for role, content in results[0]
    ]
    return conversation_history


def save_state():
    global conversation_history
    ensure_table_exists("conversation_history")

    queries = [("DELETE FROM conversation_history", ())]
    queries.extend(
        [
            (
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                (entry["role"], entry["content"]),
            )
            for entry in conversation_history
        ]
    )

    execute_transaction(queries)


# Initialize the database
init_db()

# Load the state at the start of the session
load_state()
