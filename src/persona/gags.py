"""Running Gags Tracker — Birth, evolution, death of recurring jokes.

See 03_ARCHITECTURE/ARCHITECTURE_RUNNING_GAGS.md.
Gags emerge from conversation, never programmed. They're co-constructed markers
of relationship depth.
"""

import json
import logging
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger("delirium.persona.gags")


class GagTracker:
    """Tracks running gags: detection, storage, evolution, death."""

    def __init__(self, conn):
        self.conn = conn
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS running_gags (
                id TEXT PRIMARY KEY,
                seed_content TEXT NOT NULL,
                type TEXT,
                first_seen TEXT NOT NULL,
                last_activated TEXT NOT NULL,
                occurrence_count INTEGER DEFAULT 1,
                user_callback_count INTEGER DEFAULT 0,
                variations TEXT DEFAULT '[]',
                status TEXT DEFAULT 'active',
                death_reason TEXT
            )
        """)
        self.conn.commit()

    def detect_seed(self, s2_result: dict) -> dict | None:
        """Detect a potential running gag seed from S2 analysis.

        A gag seed is a minor element mentioned 2+ times with positive reaction.
        """
        recurring = s2_result.get("recurring_minor_elements", [])
        for element in recurring:
            if (element.get("user_reaction") in ("amused", "engaged", "callback")
                    and element.get("importance", 1.0) < 0.3
                    and element.get("count", 0) >= 2):
                return {
                    "seed": element["content"],
                    "type": element.get("type", "in_joke"),
                }
        return None

    def register_gag(self, seed_content: str, gag_type: str = "in_joke") -> str:
        """Register a new running gag."""
        existing = self.conn.execute(
            "SELECT id FROM running_gags WHERE seed_content = ? AND status = 'active'",
            (seed_content,)
        ).fetchone()
        if existing:
            return existing["id"]

        gag_id = str(uuid4())
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO running_gags (id, seed_content, type, first_seen, last_activated) "
            "VALUES (?, ?, ?, ?, ?)",
            (gag_id, seed_content, gag_type, now, now)
        )
        self.conn.commit()
        logger.info("New running gag registered: %s (%s)", seed_content[:50], gag_type)
        return gag_id

    def activate(self, gag_id: str, variation: str | None = None,
                 user_callback: bool = False):
        """Record an activation of a running gag."""
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE running_gags SET last_activated = ?, occurrence_count = occurrence_count + 1 "
            "WHERE id = ?",
            (now, gag_id)
        )
        if user_callback:
            self.conn.execute(
                "UPDATE running_gags SET user_callback_count = user_callback_count + 1 "
                "WHERE id = ?",
                (gag_id,)
            )
        if variation:
            row = self.conn.execute(
                "SELECT variations FROM running_gags WHERE id = ?", (gag_id,)
            ).fetchone()
            if row:
                variations = json.loads(row["variations"])
                variations.append(variation)
                self.conn.execute(
                    "UPDATE running_gags SET variations = ? WHERE id = ?",
                    (json.dumps(variations, ensure_ascii=False), gag_id)
                )
        self.conn.commit()

    def kill_gag(self, gag_id: str, reason: str = "exhaustion"):
        """Kill a running gag. Reasons: exhaustion, rejection, context_change, forgotten."""
        self.conn.execute(
            "UPDATE running_gags SET status = 'dead', death_reason = ? WHERE id = ?",
            (reason, gag_id)
        )
        self.conn.commit()

    def apply_decay(self):
        """Kill gags that haven't been activated in 6+ months."""
        cutoff = datetime.now().timestamp() - (180 * 86400)  # 180 days
        rows = self.conn.execute(
            "SELECT id, last_activated FROM running_gags WHERE status = 'active'"
        ).fetchall()
        killed = 0
        for row in rows:
            try:
                last = datetime.fromisoformat(row["last_activated"])
                if last.timestamp() < cutoff:
                    self.kill_gag(row["id"], "forgotten")
                    killed += 1
            except (ValueError, TypeError):
                continue
        if killed:
            logger.info("Killed %d stale running gags", killed)
        return killed

    def get_active_gags(self) -> list[dict]:
        """Get all active running gags."""
        rows = self.conn.execute(
            "SELECT id, seed_content, type, occurrence_count, user_callback_count "
            "FROM running_gags WHERE status = 'active' "
            "ORDER BY last_activated DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_gag_context_for_s1(self) -> str | None:
        """Build gag context for S1 prompt injection."""
        gags = self.get_active_gags()
        if not gags:
            return None

        lines = []
        for g in gags[:3]:  # max 3 active gags in context
            callbacks = g["user_callback_count"]
            strength = "fort" if callbacks >= 2 else "naissant"
            lines.append(f"- {g['seed_content']} ({g['type']}, {g['occurrence_count']}x, {strength})")

        return "═══ RUNNING GAGS ACTIFS ═══\n" + "\n".join(lines)
