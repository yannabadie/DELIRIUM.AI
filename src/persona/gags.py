"""Running Gags Tracker — Birth, evolution, death of recurring jokes.

See 03_ARCHITECTURE/ARCHITECTURE_RUNNING_GAGS.md.
Gags emerge from conversation, never programmed. They're co-constructed markers
of relationship depth.
"""

import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from src.persona.gag_contract import (
    canonical_seed_key,
    extract_recurring_minor_elements,
    normalize_gag_type,
    normalize_recurring_minor_element,
    normalize_text_value,
    reaction_priority,
)

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
                canonical_seed TEXT,
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
        self._ensure_column("running_gags", "canonical_seed", "TEXT")
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_gags_status_seed_content
            ON running_gags (status, seed_content COLLATE NOCASE)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_gags_status_canonical_seed
            ON running_gags (status, canonical_seed)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_gags_active_seed_lookup
            ON running_gags (
                status,
                canonical_seed,
                last_activated DESC,
                seed_content COLLATE NOCASE,
                id
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_gags_active_ordering
            ON running_gags (
                status,
                last_activated DESC,
                user_callback_count DESC,
                occurrence_count DESC,
                seed_content COLLATE NOCASE,
                id
            )
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_running_gags_active_decay
            ON running_gags (
                status,
                last_activated,
                id
            )
        """)
        self.conn.commit()

    def _ensure_column(self, table_name: str, column_name: str, column_type: str) -> None:
        existing_columns = {
            row["name"]
            for row in self.conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in existing_columns:
            return
        self.conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )

    def detect_seed(self, s2_result: dict) -> dict | None:
        """Detect a potential running gag seed from S2 analysis.

        A gag seed is a minor element mentioned 2+ times with positive reaction.
        """
        recurring = extract_recurring_minor_elements(s2_result)

        best_seed = None
        best_score = None
        best_tiebreaker = None
        for element in recurring:
            normalized = normalize_recurring_minor_element(element)
            if normalized is None:
                continue

            content = normalized["content"]
            reaction = normalized["user_reaction"]
            gag_type = normalized["type"]
            importance = normalized["importance"]
            count = normalized["count"]

            if (reaction in ("amused", "engaged", "callback")
                    and importance < 0.3
                    and count >= 2):
                seed = {
                    "seed": content,
                    "type": gag_type,
                    "user_callback": reaction == "callback",
                }
                score = (count, -importance, reaction_priority(reaction))
                tiebreaker = (gag_type.casefold(), content.casefold())
                if (
                    best_score is None
                    or score > best_score
                    or (score == best_score and (
                        best_tiebreaker is None or tiebreaker < best_tiebreaker
                    ))
                ):
                    best_seed = seed
                    best_score = score
                    best_tiebreaker = tiebreaker
        return best_seed

    @staticmethod
    def _normalize_seed_content(value) -> str:
        return normalize_text_value(value, collapse_internal_whitespace=True)

    @staticmethod
    def _normalize_gag_type(value) -> str:
        return normalize_gag_type(value, "in_joke")

    @classmethod
    def _canonical_seed_key(cls, value) -> str:
        return canonical_seed_key(value)

    @staticmethod
    def _require_seed_content(seed_content: str) -> str:
        if not seed_content:
            raise ValueError("seed_content must contain non-whitespace text")
        return seed_content

    @classmethod
    def _prepare_seed_lookup(cls, seed_content: str) -> tuple[str, str]:
        normalized_seed = cls._require_seed_content(cls._normalize_seed_content(seed_content))
        return normalized_seed, cls._canonical_seed_key(normalized_seed)

    def _insert_gag(
        self,
        seed_content: str,
        canonical_seed: str,
        gag_type: str,
        *,
        user_callback: bool = False,
    ) -> str:
        gag_id = str(uuid4())
        now = datetime.now().isoformat()
        self.conn.execute(
            "INSERT INTO running_gags "
            "(id, seed_content, canonical_seed, type, first_seen, last_activated, "
            "user_callback_count) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                gag_id,
                seed_content,
                canonical_seed,
                gag_type,
                now,
                now,
                int(user_callback),
            )
        )
        self.conn.commit()
        logger.info("New running gag registered: %s (%s)", seed_content[:50], gag_type)
        return gag_id

    def _find_active_gag_id(self, canonical_seed: str) -> str | None:
        if not canonical_seed:
            return None

        fast_match = self.conn.execute(
            "SELECT id FROM running_gags "
            "WHERE status = 'active' AND canonical_seed = ? "
            "ORDER BY last_activated DESC, seed_content COLLATE NOCASE ASC, id ASC LIMIT 1",
            (canonical_seed,),
        ).fetchone()
        if fast_match:
            return fast_match["id"]

        # Preserve older rows that predate canonical_seed storage and backfill lazily.
        rows = self.conn.execute(
            "SELECT id, seed_content FROM running_gags "
            "WHERE status = 'active' AND (canonical_seed IS NULL OR canonical_seed = '') "
            "ORDER BY last_activated DESC, seed_content COLLATE NOCASE ASC, id ASC"
        ).fetchall()
        return self._backfill_legacy_rows(rows, canonical_seed)

    def _backfill_legacy_rows(self, rows, canonical_seed: str) -> str | None:
        matched_id = None
        updates = []
        for row in rows:
            row_canonical_seed = self._canonical_seed_key(row["seed_content"])
            if not row_canonical_seed:
                continue
            updates.append((row_canonical_seed, row["id"]))
            if matched_id is None and row_canonical_seed == canonical_seed:
                matched_id = row["id"]
        if updates:
            self.conn.executemany(
                "UPDATE running_gags SET canonical_seed = ? WHERE id = ?",
                updates,
            )
            self.conn.commit()
        return matched_id

    def register_gag(
        self,
        seed_content: str,
        gag_type: str = "in_joke",
        *,
        user_callback: bool = False,
    ) -> str:
        """Register a new running gag."""
        seed_content, canonical_seed = self._prepare_seed_lookup(seed_content)
        gag_type = self._normalize_gag_type(gag_type)
        existing_id = self._find_active_gag_id(canonical_seed)
        if existing_id:
            return existing_id

        return self._insert_gag(
            seed_content,
            canonical_seed,
            gag_type,
            user_callback=user_callback,
        )

    def register_or_refresh_gag(
        self,
        seed_content: str,
        gag_type: str = "in_joke",
        *,
        user_callback: bool = False,
    ) -> tuple[str, bool]:
        """Register a new gag or refresh an existing active one.

        Returns `(gag_id, created)` where `created` is `True` only for brand-new gags.
        """
        seed_content, canonical_seed = self._prepare_seed_lookup(seed_content)
        gag_type = self._normalize_gag_type(gag_type)
        existing_id = self._find_active_gag_id(canonical_seed)
        if existing_id:
            self.activate(existing_id, user_callback=user_callback)
            return existing_id, False

        return self._insert_gag(
            seed_content,
            canonical_seed,
            gag_type,
            user_callback=user_callback,
        ), True

    def activate(self, gag_id: str, variation: str | None = None,
                 user_callback: bool = False):
        """Record an activation of a running gag."""
        now = datetime.now().isoformat()
        self.conn.execute(
            "UPDATE running_gags "
            "SET last_activated = ?, "
            "occurrence_count = occurrence_count + 1, "
            "user_callback_count = user_callback_count + ? "
                "WHERE id = ?",
            (now, int(user_callback), gag_id)
        )
        variation = self._normalize_seed_content(variation)
        if variation:
            variation_key = self._canonical_seed_key(variation)
            row = self.conn.execute(
                "SELECT variations FROM running_gags WHERE id = ?", (gag_id,)
            ).fetchone()
            if row:
                try:
                    variations = json.loads(row["variations"])
                except (TypeError, ValueError, json.JSONDecodeError):
                    variations = []
                if not isinstance(variations, list):
                    variations = []
                existing_variations = {
                    existing_key
                    for existing in variations
                    if (existing_key := self._canonical_seed_key(existing))
                }
                if variation_key not in existing_variations:
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
        # Compare normalized ISO timestamps directly so SQLite can use the
        # `(status, last_activated, id)` index instead of wrapping the column
        # in `julianday(...)` for every active row.
        cutoff_iso = (datetime.now() - timedelta(days=180)).isoformat()
        rows = self.conn.execute(
            "SELECT id FROM running_gags "
            "WHERE status = 'active' "
            "AND last_activated <= ? "
            "ORDER BY last_activated ASC, id ASC",
            (cutoff_iso,),
        ).fetchall()
        stale_ids = [row["id"] for row in rows]
        if stale_ids:
            self.conn.executemany(
                "UPDATE running_gags SET status = 'dead', death_reason = ? WHERE id = ?",
                [("forgotten", gag_id) for gag_id in stale_ids]
            )
            self.conn.commit()
        killed = len(stale_ids)
        if killed:
            logger.info("Killed %d stale running gags", killed)
        return killed

    def get_active_gags(self, limit: int | None = None) -> list[dict]:
        """Get all active running gags."""
        if limit is not None and limit <= 0:
            return []

        query = (
            "SELECT id, seed_content, type, occurrence_count, user_callback_count "
            "FROM running_gags WHERE status = 'active' "
            "ORDER BY last_activated DESC, user_callback_count DESC, "
            "occurrence_count DESC, seed_content COLLATE NOCASE ASC, id ASC"
        )
        params: tuple[int, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def get_gag_context_for_s1(self) -> str | None:
        """Build gag context for S1 prompt injection."""
        gags = self.get_active_gags(limit=3)
        if not gags:
            return None

        lines = []
        for g in gags:
            callbacks = g["user_callback_count"]
            strength = "fort" if callbacks >= 2 else "naissant"
            lines.append(f"- {g['seed_content']} ({g['type']}, {g['occurrence_count']}x, {strength})")

        return "═══ RUNNING GAGS ACTIFS ═══\n" + "\n".join(lines)
