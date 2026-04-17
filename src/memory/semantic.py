"""Semantic Memory — Layer 3 (simplified). Theme tracking and correlations.

See ARCHITECTURE_HARNESS.md section 3.4.
Prototype: SQLite-backed instead of full graph DB.
"""

import json
import sqlite3
from datetime import datetime
from uuid import uuid4


class SemanticMemory:
    """Tracks themes, correlations, and loops detected by S2."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS themes (
                id TEXT PRIMARY KEY,
                label TEXT UNIQUE NOT NULL,
                weight REAL DEFAULT 0.1,
                activation_count INTEGER DEFAULT 0,
                last_activated TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS correlations (
                id TEXT PRIMARY KEY,
                hypothesis TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                state TEXT DEFAULT 'H',
                evidence_json TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loops (
                id TEXT PRIMARY KEY,
                theme TEXT NOT NULL,
                occurrences INTEGER DEFAULT 1,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );
        """)
        self.conn.commit()

    @staticmethod
    def _clamp_weight(weight: float) -> float:
        return min(max(weight, 0.0), 1.0)

    def update_from_s2(self, fragment_id: str, s2_result: dict):
        now = datetime.now().isoformat()

        # Update themes
        for theme_label in s2_result.get("themes_latents", []):
            existing = self.conn.execute(
                "SELECT id, weight, activation_count FROM themes WHERE label = ?",
                (theme_label,)
            ).fetchone()

            if existing:
                new_weight = self._clamp_weight(existing["weight"] + 0.1)
                self.conn.execute(
                    "UPDATE themes SET weight = ?, activation_count = activation_count + 1, "
                    "last_activated = ? WHERE id = ?",
                    (new_weight, now, existing["id"])
                )
            else:
                self.conn.execute(
                    "INSERT INTO themes (id, label, weight, activation_count, last_activated, created_at) "
                    "VALUES (?, ?, 0.1, 1, ?, ?)",
                    (str(uuid4()), theme_label, now, now)
                )

        # Update correlations
        correlation = s2_result.get("correlation")
        if correlation and isinstance(correlation, dict) and correlation.get("confidence", 0) > 0.3:
            self.conn.execute(
                "INSERT INTO correlations (id, hypothesis, confidence, state, created_at, updated_at) "
                "VALUES (?, ?, ?, 'H', ?, ?)",
                (str(uuid4()), correlation.get("hypothesis", ""),
                 correlation["confidence"], now, now)
            )

        # Track loops
        if s2_result.get("loop_detected"):
            loop_theme = s2_result.get("loop_theme", "unknown")
            existing = self.conn.execute(
                "SELECT id, occurrences FROM loops WHERE theme = ?", (loop_theme,)
            ).fetchone()
            if existing:
                self.conn.execute(
                    "UPDATE loops SET occurrences = occurrences + 1, last_seen = ? WHERE id = ?",
                    (now, existing["id"])
                )
            else:
                self.conn.execute(
                    "INSERT INTO loops (id, theme, occurrences, first_seen, last_seen) "
                    "VALUES (?, ?, 1, ?, ?)",
                    (str(uuid4()), loop_theme, now, now)
                )

        self.conn.commit()

    def add_or_reinforce_theme(self, label: str, weight: float):
        """Add a theme or increase its weight if it exists."""
        now = datetime.now().isoformat()
        existing = self.conn.execute(
            "SELECT id, weight FROM themes WHERE label = ?", (label,)
        ).fetchone()
        if existing:
            new_weight = self._clamp_weight(existing["weight"] + weight)
            self.conn.execute(
                "UPDATE themes SET weight = ?, activation_count = activation_count + 1, "
                "last_activated = ? WHERE id = ?",
                (new_weight, now, existing["id"])
            )
        else:
            self.conn.execute(
                "INSERT INTO themes (id, label, weight, activation_count, last_activated, created_at) "
                "VALUES (?, ?, ?, 1, ?, ?)",
                (str(uuid4()), label, self._clamp_weight(weight), now, now)
            )
        self.conn.commit()

    def get_active_themes(self, threshold: float = 0.3) -> list[dict]:
        rows = self.conn.execute(
            "SELECT label, weight FROM themes WHERE weight >= ? ORDER BY weight DESC",
            (threshold,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_loops(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT theme, occurrences, first_seen, last_seen FROM loops ORDER BY occurrences DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_correlations(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT hypothesis, confidence, state, evidence_json, created_at, updated_at "
            "FROM correlations ORDER BY confidence DESC, updated_at DESC"
        ).fetchall()
        correlations = []
        for row in rows:
            correlation = dict(row)
            try:
                raw_evidence = correlation.pop("evidence_json", "[]")
                evidence = json.loads(raw_evidence) if raw_evidence is not None else []
                correlation["evidence"] = evidence if isinstance(evidence, list) else []
            except (TypeError, json.JSONDecodeError):
                correlation["evidence"] = []
            correlations.append(correlation)
        return correlations
