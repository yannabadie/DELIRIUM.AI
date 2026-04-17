"""Decay Engine — Selective forgetting based on Bjork & Bjork (1992).

Two independent memory strengths:
- Storage Strength (SS): embedding persists forever
- Retrieval Strength (RS): decays exponentially, restored on reactivation

See 03_ARCHITECTURE/ARCHITECTURE_OUBLI_SELECTIF.md
"""

import logging
from datetime import datetime

logger = logging.getLogger("delirium.memory.decay")

# Decay parameters [NC: à calibrer]
HALF_LIFE_NORMAL = 90      # days — mode normal
HALF_LIFE_MINIMAL = 30     # days — mode minimaliste
RETRIEVAL_THRESHOLD = 0.1  # below this, fragment not retrieved in prompt
FORGET_THRESHOLD = 0.01    # below this, fragment is "forgotten" (but SS intact)
REACTIVATION_BOOST = 0.3   # RS boost when topic is re-mentioned
INTERFERENCE_PENALTY = 0.15
RETRIEVAL_INDUCED_COMPETITOR_PENALTY = 0.2
VALID_DECAY_MODES = {"sponge", "normal", "minimal"}
VALID_STRATEGIES = {"decay", "interference", "retrieval_induced"}


class DecayEngine:
    """Implements selective forgetting (Bjork & Bjork 1992 New Theory of Disuse)."""

    def __init__(self, conn, mode: str = "normal", strategy: str = "decay"):
        """
        Args:
            conn: SQLite connection (shared with EpisodicMemory).
            mode: "sponge" (no decay), "normal" (90d half-life), "minimal" (30d half-life).
            strategy: "decay", "interference", or "retrieval_induced".
        """
        self.conn = conn
        self.mode = self._normalize_mode(mode)
        self.strategy = self._normalize_strategy(strategy)
        self._ensure_column()
        self._repair_invalid_weights()

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        if mode in VALID_DECAY_MODES:
            return mode
        logger.warning("Unknown decay mode %r, defaulting to normal", mode)
        return "normal"

    @staticmethod
    def _normalize_strategy(strategy: str) -> str:
        if strategy in VALID_STRATEGIES:
            return strategy
        logger.warning("Unknown forgetting strategy %r, defaulting to decay", strategy)
        return "decay"

    @staticmethod
    def _sanitize_weight(weight) -> float:
        try:
            if weight is None:
                return 1.0
            weight = float(weight)
        except (TypeError, ValueError):
            return 1.0
        return min(max(weight, 0.0), 1.0)

    def _ensure_column(self):
        """Add forgetting-related columns if missing (migration)."""
        for statement in (
            "ALTER TABLE conversations ADD COLUMN retrieval_weight REAL DEFAULT 1.0",
            "ALTER TABLE conversations ADD COLUMN last_decay_at TEXT",
        ):
            try:
                self.conn.execute(statement)
                self.conn.commit()
            except Exception:
                pass  # column already exists

    def _repair_invalid_weights(self):
        """Clamp legacy retrieval weights into the [0, 1] interval."""
        self.conn.execute(
            "UPDATE conversations SET retrieval_weight = 1.0 "
            "WHERE retrieval_weight IS NULL"
        )
        self.conn.execute(
            "UPDATE conversations SET retrieval_weight = 0.0 "
            "WHERE retrieval_weight < 0.0"
        )
        self.conn.execute(
            "UPDATE conversations SET retrieval_weight = 1.0 "
            "WHERE retrieval_weight > 1.0"
        )
        self.conn.commit()

    @staticmethod
    def _compute_decayed_weight(weight: float, elapsed_days: float, half_life: int) -> float:
        if elapsed_days <= 0:
            return weight
        return max(weight * (0.5 ** (elapsed_days / half_life)), 0.0)

    @staticmethod
    def _resolve_decay_reference(last_decay_at, timestamp):
        for reference in (last_decay_at, timestamp):
            try:
                if reference:
                    return datetime.fromisoformat(reference)
            except (ValueError, TypeError):
                continue
        return None

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
            "SELECT id, timestamp, last_decay_at, COALESCE(retrieval_weight, 1.0) AS retrieval_weight "
            "FROM conversations "
            "WHERE COALESCE(retrieval_weight, 1.0) > ? AND source != 'arxiv'",
            (FORGET_THRESHOLD,)
        ).fetchall()

        updated = 0
        for row in rows:
            current_weight = self._sanitize_weight(row["retrieval_weight"])
            last_decay_at = self._resolve_decay_reference(
                row["last_decay_at"],
                row["timestamp"],
            )
            if last_decay_at is None:
                continue

            elapsed_days = (now - last_decay_at).total_seconds() / 86400
            if elapsed_days <= 0:
                continue

            new_weight = self._compute_decayed_weight(
                current_weight,
                elapsed_days,
                half_life,
            )

            if abs(new_weight - current_weight) > 0.001:
                self.conn.execute(
                    "UPDATE conversations SET retrieval_weight = ?, last_decay_at = ? WHERE id = ?",
                    (new_weight, now.isoformat(), row["id"])
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
            "SELECT COALESCE(retrieval_weight, 1.0) AS retrieval_weight, "
            "timestamp, last_decay_at FROM conversations WHERE id = ?",
            (fragment_id,)
        ).fetchone()

        if row:
            now = datetime.now()
            decayed_weight = self._sanitize_weight(row["retrieval_weight"])
            reference_time = self._resolve_decay_reference(
                row["last_decay_at"],
                row["timestamp"],
            )
            half_life = HALF_LIFE_NORMAL if self.mode == "normal" else HALF_LIFE_MINIMAL
            if self.mode != "sponge" and reference_time is not None:
                elapsed_days = (now - reference_time).total_seconds() / 86400
                decayed_weight = self._compute_decayed_weight(
                    decayed_weight,
                    elapsed_days,
                    half_life,
                )

            new_weight = min(decayed_weight + REACTIVATION_BOOST, 1.0)
            self.conn.execute(
                "UPDATE conversations SET retrieval_weight = ?, last_decay_at = ? WHERE id = ?",
                (new_weight, now.isoformat(), fragment_id)
            )
            self.conn.commit()

    def _penalize(self, fragment_id: str, amount: float):
        row = self.conn.execute(
            "SELECT retrieval_weight FROM conversations WHERE id = ?",
            (fragment_id,),
        ).fetchone()
        if not row:
            return

        current_weight = self._sanitize_weight(row["retrieval_weight"])
        new_weight = max(current_weight - amount, 0.0)
        if new_weight == current_weight:
            return

        self.conn.execute(
            "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
            (new_weight, fragment_id),
        )
        self.conn.commit()

    @staticmethod
    def _pick_primary(related: list[dict]) -> dict | None:
        if not related:
            return None
        return max(
            related,
            key=lambda frag: (
                DecayEngine._sanitize_weight(frag.get("retrieval_weight", 1.0)),
                frag.get("timestamp", ""),
                frag.get("id", ""),
            ),
        )

    def reactivate_related(self, user_message: str, episodic):
        """Reactivate fragments related to the current message (FTS search)."""
        try:
            related = episodic.search(user_message, n_results=3)
            if self.strategy == "decay":
                for frag in related:
                    self.reactivate(frag["id"])
                return

            primary = self._pick_primary(related)
            if not primary:
                return

            self.reactivate(primary["id"])
            for frag in related:
                if frag["id"] == primary["id"]:
                    continue
                penalty = (
                    RETRIEVAL_INDUCED_COMPETITOR_PENALTY
                    if self.strategy == "retrieval_induced"
                    else INTERFERENCE_PENALTY
                )
                self._penalize(frag["id"], penalty)
        except Exception as exc:
            logger.warning("Related-memory reactivation failed: %s", exc)

    def get_forgotten_topics(self) -> list[dict]:
        """Get themes with RS below threshold — for return messages."""
        rows = self.conn.execute(
            "SELECT id, user_input, COALESCE(retrieval_weight, 1.0) AS retrieval_weight, timestamp "
            "FROM conversations "
            "WHERE COALESCE(retrieval_weight, 1.0) < ? AND COALESCE(retrieval_weight, 1.0) > 0 "
            "AND source = 'delirium' "
            "ORDER BY retrieval_weight ASC LIMIT 10",
            (RETRIEVAL_THRESHOLD,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_stats(self) -> dict:
        """Get decay statistics for /status command."""
        total = self.conn.execute("SELECT COUNT(*) as cnt FROM conversations").fetchone()["cnt"]
        accessible = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE COALESCE(retrieval_weight, 1.0) >= ?",
            (RETRIEVAL_THRESHOLD,)
        ).fetchone()["cnt"]
        forgotten = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE COALESCE(retrieval_weight, 1.0) <= ?",
            (FORGET_THRESHOLD,)
        ).fetchone()["cnt"]

        return {
            "total": total,
            "accessible": accessible,
            "forgotten": forgotten,
            "fading": total - accessible - forgotten,
            "mode": self.mode,
        }
