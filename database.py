# database.py
import datetime as dt
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
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
                    """
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT
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


def load_state(session_id: str = None):
    global conversation_history
    ensure_table_exists("conversation_history")
    where_clause = ""
    if session_id is not None:
        where_clause = "WHERE session_id = ?"
    results = execute_transaction(
        [
            (
                f"SELECT role, content FROM conversation_history {where_clause} ORDER BY id",
                (session_id,) if session_id is not None else (),
            )
        ]
    )
    conversation_history = [
        {"role": role, "content": content} for role, content in results[0]
    ]
    return conversation_history


def save_state(session_id: str):
    global conversation_history
    ensure_table_exists("conversation_history")

    queries = [("DELETE FROM conversation_history WHERE session_id = ?", (session_id,))]
    queries.extend(
        [
            (
                "INSERT INTO conversation_history (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    dt.datetime.now(dt.UTC).isoformat(),
                    entry["role"],
                    entry["content"],
                    json.dumps(entry.get("metadata", {})),
                ),
            )
            for entry in conversation_history
        ]
    )

    execute_transaction(queries)


def save_message(
    session_id: str, role: str, content: str, metadata: Dict[str, Any] = None
):
    ensure_table_exists("conversation_history")

    timestamp = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(metadata) if metadata else None

    execute_transaction(
        [
            (
                "INSERT INTO conversation_history (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, timestamp, role, content, metadata_json),
            )
        ]
    )


# Initialize the database
init_db()

# Load the state at the start of the session
load_state()
