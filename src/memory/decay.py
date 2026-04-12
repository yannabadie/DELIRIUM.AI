"""Decay Engine — Selective forgetting based on Bjork & Bjork (1992).

Two independent memory strengths:
- Storage Strength (SS): embedding persists forever
- Retrieval Strength (RS): decays exponentially, restored on reactivation

See 03_ARCHITECTURE/ARCHITECTURE_OUBLI_SELECTIF.md
"""

import logging
import math
from datetime import datetime

logger = logging.getLogger("delirium.memory.decay")

# Decay parameters [NC: à calibrer]
HALF_LIFE_NORMAL = 90      # days — mode normal
HALF_LIFE_MINIMAL = 30     # days — mode minimaliste
RETRIEVAL_THRESHOLD = 0.1  # below this, fragment not retrieved in prompt
FORGET_THRESHOLD = 0.01    # below this, fragment is "forgotten" (but SS intact)
REACTIVATION_BOOST = 0.3   # RS boost when topic is re-mentioned


class DecayEngine:
    """Implements selective forgetting (Bjork & Bjork 1992 New Theory of Disuse)."""

    def __init__(self, conn, mode: str = "normal"):
        """
        Args:
            conn: SQLite connection (shared with EpisodicMemory).
            mode: "sponge" (no decay), "normal" (90d half-life), "minimal" (30d half-life).
        """
        self.conn = conn
        self.mode = mode
        self._ensure_column()

    def _ensure_column(self):
        """Add retrieval_weight column if missing (migration)."""
        try:
            self.conn.execute("ALTER TABLE conversations ADD COLUMN retrieval_weight REAL DEFAULT 1.0")
            self.conn.commit()
        except Exception:
            pass  # column already exists

    def apply_decay(self):
        """Reduce RS of all fragments based on time since last activation.

        Called at session start or daily.
        Does NOT delete data — only reduces retrieval_weight (RS).
        Storage Strength (embedding) remains intact.
        """
        if self.mode == "sponge":
            logger.info("Decay mode=sponge, skipping")
            return 0

        half_life = HALF_LIFE_NORMAL if self.mode == "normal" else HALF_LIFE_MINIMAL
        now = datetime.now()

        rows = self.conn.execute(
            "SELECT id, timestamp, retrieval_weight FROM conversations "
            "WHERE retrieval_weight > ? AND source != 'arxiv'",
            (FORGET_THRESHOLD,)
        ).fetchall()

        updated = 0
        for row in rows:
            try:
                ts = datetime.fromisoformat(row["timestamp"])
            except (ValueError, TypeError):
                continue

            days_since = (now - ts).days
            if days_since <= 0:
                continue

            # Exponential decay: RS = RS_0 * 0.5^(days / half_life)
            new_weight = row["retrieval_weight"] * (0.5 ** (days_since / half_life))
            new_weight = max(new_weight, 0.0)

            if abs(new_weight - row["retrieval_weight"]) > 0.001:
                self.conn.execute(
                    "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
                    (new_weight, row["id"])
                )
                updated += 1

        self.conn.commit()
        logger.info("Decay applied to %d fragments (mode=%s, half_life=%dd)",
                    updated, self.mode, half_life)
        return updated

    def reactivate(self, fragment_id: str):
        """When a topic is re-mentioned, RS goes back up (re-learning effect).

        Bjork: re-learning is fast when SS is high but RS is low.
        """
        row = self.conn.execute(
            "SELECT retrieval_weight FROM conversations WHERE id = ?",
            (fragment_id,)
        ).fetchone()

        if row:
            new_weight = min(row["retrieval_weight"] + REACTIVATION_BOOST, 1.0)
            self.conn.execute(
                "UPDATE conversations SET retrieval_weight = ?, timestamp = ? WHERE id = ?",
                (new_weight, datetime.now().isoformat(), fragment_id)
            )
            self.conn.commit()

    def reactivate_related(self, user_message: str, episodic):
        """Reactivate fragments related to the current message (FTS search)."""
        try:
            related = episodic.search(user_message, n_results=3)
            for frag in related:
                self.reactivate(frag["id"])
        except Exception:
            pass  # FTS can fail on certain queries

    def get_forgotten_topics(self) -> list[dict]:
        """Get themes with RS below threshold — for return messages."""
        rows = self.conn.execute(
            "SELECT id, user_input, retrieval_weight, timestamp FROM conversations "
            "WHERE retrieval_weight < ? AND retrieval_weight > 0 "
            "AND source = 'delirium' "
            "ORDER BY retrieval_weight ASC LIMIT 10",
            (RETRIEVAL_THRESHOLD,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Get decay statistics for /status command."""
        total = self.conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()["cnt"]
        accessible = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE retrieval_weight > ?",
            (RETRIEVAL_THRESHOLD,)
        ).fetchone()["cnt"]
        forgotten = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE retrieval_weight <= ?",
            (FORGET_THRESHOLD,)
        ).fetchone()["cnt"]

        return {
            "total": total,
            "accessible": accessible,
            "forgotten": forgotten,
            "fading": total - accessible - forgotten,
            "mode": self.mode,
        }
