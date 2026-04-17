"""Episodic Memory — Layer 2. SQLite storage for conversation fragments.

See ARCHITECTURE_HARNESS.md section 3.3.
Phase 2: adds embedding storage, source tracking, collision support.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import numpy as np

from src.embeddings import embedding_to_bytes, bytes_to_embedding, cosine_similarity
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
                source TEXT DEFAULT 'delirium',
                h_value REAL DEFAULT 0.0,
                phase TEXT DEFAULT 'probing',
                embedding BLOB,
                sycophancy_score REAL
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

            CREATE TABLE IF NOT EXISTS collisions (
                id TEXT PRIMARY KEY,
                fragment_a_id TEXT NOT NULL,
                fragment_b_id TEXT NOT NULL,
                collision_score REAL NOT NULL,
                connection TEXT,
                delivered INTEGER DEFAULT 0,
                delivered_session TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (fragment_a_id) REFERENCES conversations(id),
                FOREIGN KEY (fragment_b_id) REFERENCES conversations(id)
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts
                USING fts5(user_input, s1_response, content=conversations, content_rowid=rowid);
        """)
        # Migrate: add columns if they don't exist (for DBs created in Phase 1)
        for col, typedef in [("source", "TEXT DEFAULT 'delirium'"),
                             ("embedding", "BLOB"),
                             ("sycophancy_score", "REAL"),
                             ("retrieval_weight", "REAL DEFAULT 1.0"),
                             ("last_decay_at", "TEXT")]:
            try:
                self.conn.execute(f"ALTER TABLE conversations ADD COLUMN {col} {typedef}")
            except sqlite3.OperationalError:
                pass  # column already exists
        self.conn.commit()

    def store(self, user_message: str, response: str, session_id: str,
              persona_state: PersonaState, source: str = "delirium",
              embedding: np.ndarray | None = None,
              sycophancy_score: float | None = None) -> str:
        fragment_id = str(uuid4())
        now = datetime.now().isoformat()

        emb_bytes = embedding_to_bytes(embedding) if embedding is not None else None

        self.conn.execute(
            "INSERT INTO conversations "
            "(id, session_id, timestamp, user_input, s1_response, source, h_value, phase, "
            "embedding, sycophancy_score, last_decay_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (fragment_id, session_id, now, user_message, response,
             source, persona_state.H, persona_state.phase, emb_bytes, sycophancy_score, now)
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

    def update_embedding(self, fragment_id: str, embedding: np.ndarray):
        self.conn.execute(
            "UPDATE conversations SET embedding = ? WHERE id = ?",
            (embedding_to_bytes(embedding), fragment_id)
        )
        self.conn.commit()

    def update_sycophancy_score(self, fragment_id: str, score: float):
        self.conn.execute(
            "UPDATE conversations SET sycophancy_score = ? WHERE id = ?",
            (score, fragment_id)
        )
        self.conn.commit()

    def search(self, query: str, n_results: int = 5,
               min_retrieval_weight: float = 0.1) -> list[dict]:
        """Search past conversations by text similarity (FTS5).

        Filters by retrieval_weight (Bjork RS) — forgotten fragments are excluded.
        """
        # FTS5 treats quotes and apostrophes as syntax — escape by quoting each token
        safe_query = " ".join(
            '"' + word.replace('"', '""') + '"'
            for word in query.split() if word.strip()
        )
        if not safe_query:
            return []
        try:
            rows = self.conn.execute(
                "SELECT c.id, c.timestamp, c.user_input, c.s1_response, c.h_value, c.phase, "
                "c.source, COALESCE(c.retrieval_weight, 1.0) as retrieval_weight "
                "FROM conversations_fts f "
                "JOIN conversations c ON c.rowid = f.rowid "
                "WHERE conversations_fts MATCH ? "
                "AND COALESCE(c.retrieval_weight, 1.0) >= ? "
                "ORDER BY rank, retrieval_weight DESC, c.timestamp DESC LIMIT ?",
                (safe_query, min_retrieval_weight, n_results)
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            return []

    def purge_collisions(self) -> int:
        """Delete all collisions. Returns count deleted."""
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM collisions").fetchone()
        count = row["cnt"]
        self.conn.execute("DELETE FROM collisions")
        self.conn.commit()
        return count

    def get_all_with_embeddings(self) -> list[dict]:
        """Get all fragments that have embeddings (for Cold Weaver)."""
        rows = self.conn.execute(
            "SELECT id, user_input, s1_response, source, session_id, timestamp, embedding "
            "FROM conversations WHERE embedding IS NOT NULL"
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["embedding"] = bytes_to_embedding(d["embedding"])
            results.append(d)
        return results

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

    def get_fragment_count(self, source: str | None = None) -> int:
        if source:
            row = self.conn.execute(
                "SELECT COUNT(*) as cnt FROM conversations WHERE source = ?", (source,)
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()
        return row["cnt"]

    # --- Collisions ---

    def store_collision(self, fragment_a_id: str, fragment_b_id: str,
                        score: float, connection: str) -> str:
        collision_id = str(uuid4())
        self.conn.execute(
            "INSERT INTO collisions (id, fragment_a_id, fragment_b_id, collision_score, connection, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (collision_id, fragment_a_id, fragment_b_id, score, connection,
             datetime.now().isoformat())
        )
        self.conn.commit()
        return collision_id

    def get_pending_collision(self) -> dict | None:
        """Get the best undelivered collision."""
        row = self.conn.execute(
            "SELECT co.id, co.fragment_a_id, co.fragment_b_id, co.collision_score, co.connection, "
            "ca.user_input as a_input, cb.user_input as b_input "
            "FROM collisions co "
            "JOIN conversations ca ON ca.id = co.fragment_a_id "
            "JOIN conversations cb ON cb.id = co.fragment_b_id "
            "WHERE co.delivered = 0 "
            "ORDER BY co.collision_score DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    def mark_collision_delivered(self, collision_id: str, session_id: str):
        self.conn.execute(
            "UPDATE collisions SET delivered = 1, delivered_session = ? WHERE id = ?",
            (session_id, collision_id)
        )
        self.conn.commit()

    def collision_already_exists(self, frag_a: str, frag_b: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM collisions WHERE "
            "(fragment_a_id = ? AND fragment_b_id = ?) OR "
            "(fragment_a_id = ? AND fragment_b_id = ?)",
            (frag_a, frag_b, frag_b, frag_a)
        ).fetchone()
        return row is not None

    def collision_delivered_this_session(self, session_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM collisions WHERE delivered_session = ?", (session_id,)
        ).fetchone()
        return row is not None

    def get_collision_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as cnt FROM collisions").fetchone()
        return row["cnt"]

    # --- Logging ---

    def log_execution(self, fragment_id: str | None, log_type: str, content: dict):
        self.conn.execute(
            "INSERT INTO execution_logs (id, fragment_id, log_type, content, timestamp) "
            "VALUES (?, ?, ?, ?, ?)",
            (str(uuid4()), fragment_id, log_type, json.dumps(content, ensure_ascii=False),
             datetime.now().isoformat())
        )
        self.conn.commit()

    # --- Persona persistence ---

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
