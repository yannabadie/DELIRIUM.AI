"""Episodic Memory — Layer 2. SQLite storage for conversation fragments.

See ARCHITECTURE_HARNESS.md section 3.3.
Prototype: no vector DB, uses SQLite FTS5 for text search.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from src.persona.state import PersonaState


class EpisodicMemory:
    """Stores and retrieves conversation fragments in SQLite."""

    def __init__(self, db_path: str):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_input TEXT NOT NULL,
                s1_response TEXT NOT NULL,
                h_value REAL DEFAULT 0.0,
                phase TEXT DEFAULT 'probing'
            );

            CREATE TABLE IF NOT EXISTS execution_logs (
                id TEXT PRIMARY KEY,
                fragment_id TEXT,
                log_type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (fragment_id) REFERENCES conversations(id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                message_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS persona_history (
                id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
                USING fts5(user_input, s1_response, content=conversations, content_rowid=rowid);
        """)
        self.conn.commit()

    def store(self, user_message: str, response: str, session_id: str,
              persona_state: PersonaState) -> str:
        fragment_id = str(uuid4())
        now = datetime.now().isoformat()

        self.conn.execute(
            "INSERT INTO conversations (id, session_id, timestamp, user_input, s1_response, h_value, phase) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (fragment_id, session_id, now, user_message, response,
             persona_state.H, persona_state.phase)
        )
        # Update FTS index
        self.conn.execute(
            "INSERT INTO conversations_fts (rowid, user_input, s1_response) "
            "VALUES (last_insert_rowid(), ?, ?)",
            (user_message, response)
        )
        # Increment session message count
        self.conn.execute(
            "INSERT INTO sessions (id, started_at, message_count) VALUES (?, ?, 1) "
            "ON CONFLICT(id) DO UPDATE SET message_count = message_count + 1",
            (session_id, now)
        )
        self.conn.commit()
        return fragment_id

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        """Search past conversations by text similarity (FTS5)."""
        rows = self.conn.execute(
            "SELECT c.id, c.timestamp, c.user_input, c.s1_response, c.h_value, c.phase "
            "FROM conversations_fts f "
            "JOIN conversations c ON c.rowid = f.rowid "
            "WHERE conversations_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (query, n_results)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_recent(self, session_id: str, limit: int = 20) -> list[dict]:
        """Get recent messages from the current session as chat format."""
        rows = self.conn.execute(
            "SELECT user_input, s1_response FROM conversations "
            "WHERE session_id = ? ORDER BY timestamp ASC LIMIT ?",
            (session_id, limit)
        ).fetchall()
        messages = []
        for r in rows:
            messages.append({"role": "user", "content": r["user_input"]})
            messages.append({"role": "assistant", "content": r["s1_response"]})
        return messages

    def get_session_message_count(self, session_id: str) -> int:
        row = self.conn.execute(
            "SELECT message_count FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return row["message_count"] if row else 0

    def get_total_sessions(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()
        return row["cnt"]

    def log_execution(self, fragment_id: str | None, log_type: str, content: dict):
        self.conn.execute(
            "INSERT INTO execution_logs (id, fragment_id, log_type, content, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), fragment_id, log_type, json.dumps(content, ensure_ascii=False),
             datetime.now().isoformat())
        )
        self.conn.commit()

    def save_persona_state(self, state: PersonaState):
        self.conn.execute(
            "INSERT INTO persona_history (id, state_json, timestamp) VALUES (?, ?, ?)",
            (str(uuid4()), json.dumps(state.to_dict(), ensure_ascii=False),
             datetime.now().isoformat())
        )
        self.conn.commit()

    def load_latest_persona_state(self) -> PersonaState | None:
        row = self.conn.execute(
            "SELECT state_json FROM persona_history ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        if row:
            return PersonaState.from_dict(json.loads(row["state_json"]))
        return None

    def close(self):
        self.conn.close()
