"""World Vision — Layer 4. Periodic synthesis of who the user is.

See 03_ARCHITECTURE/VISION_DU_MONDE_SCHEMA.md for the full JSON schema.
See ARCHITECTURE_HARNESS.md section 3.5.

This document is NEVER shown to the user. It feeds S1 and S2 as context.
"""

import json
import logging
from datetime import datetime
from uuid import uuid4

from src.config import get_vision_prompt, MINIMAX_MODEL
from src.llm_client import LLMClient

logger = logging.getLogger("delirium.memory.world_vision")

# Re-synthesis triggers [NC: à calibrer]
RESYNTH_INTERVAL_SESSIONS = 10


class WorldVision:
    """Layer 4 — periodic synthesis of the user's world model."""

    def __init__(self, conn, llm: LLMClient):
        self.conn = conn
        self.llm = llm
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS world_vision (
                id TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                vision_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def _table_exists(self, table_name: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        return row is not None

    def should_resynthesize(self, s2_result: dict | None, sessions_since: int) -> bool:
        """Check if a re-synthesis is needed."""
        if sessions_since >= RESYNTH_INTERVAL_SESSIONS:
            return True
        if s2_result:
            if s2_result.get("danger_level", 0) >= 2:
                return True
            if s2_result.get("loop_detected", False):
                return True
            if s2_result.get("axis_crossing", False):
                return True
        return False

    def resynthesize(self, themes: list[dict], correlations: list[dict],
                     loops: list[dict], danger_history: dict | None = None,
                     fragment_count: int = 0) -> dict:
        """Run full re-synthesis via LLM. Returns the vision JSON."""
        vision_prompt = get_vision_prompt()

        # Build input data for the LLM
        input_data = {
            "themes": themes,
            "correlations": correlations,
            "loops": loops,
            "danger_history": danger_history or {},
            "fragment_count": fragment_count,
            "current_date": datetime.now().isoformat(),
        }

        try:
            raw = self.llm.chat(
                system=vision_prompt,
                messages=[{"role": "user", "content": json.dumps(input_data, ensure_ascii=False)}],
                model=MINIMAX_MODEL,
            )
            vision = self._parse_vision(raw)
        except Exception as e:
            logger.error("Vision re-synthesis failed: %s", e)
            vision = self._default_vision()

        # Store (versioned, never overwritten)
        current_version = self._get_current_version()
        new_version = current_version + 1
        vision["version"] = new_version

        self.conn.execute(
            "INSERT INTO world_vision (id, version, vision_json, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), new_version, json.dumps(vision, ensure_ascii=False),
             datetime.now().isoformat())
        )
        self.conn.commit()

        logger.info("Vision du monde v%d synthesized", new_version)
        return vision

    def get_sessions_since_last_vision(self) -> int:
        """Count sessions started since the latest stored world vision."""
        if not self._table_exists("sessions"):
            return 0

        latest = self.conn.execute(
            "SELECT created_at FROM world_vision ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if not latest:
            row = self.conn.execute("SELECT COUNT(*) as cnt FROM sessions").fetchone()
            return row["cnt"] if row else 0

        row = self.conn.execute(
            "SELECT COUNT(*) as cnt FROM sessions WHERE started_at > ?",
            (latest["created_at"],)
        ).fetchone()
        return row["cnt"] if row else 0

    def get_danger_history(self, limit: int = 20) -> dict:
        """Summarize recent S2 danger signals for the next synthesis."""
        if not self._table_exists("execution_logs"):
            return {
                "sample_size": 0,
                "max_danger_level": 0,
                "high_danger_count": 0,
                "recent_levels": [],
                "recent_triggers": [],
            }

        rows = self.conn.execute(
            "SELECT content FROM execution_logs "
            "WHERE log_type = 's2_analysis' ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()

        levels: list[int] = []
        triggers: list[str] = []
        for row in rows:
            try:
                payload = json.loads(row["content"])
            except (TypeError, json.JSONDecodeError):
                continue

            levels.append(int(payload.get("danger_level", 0)))
            trigger = payload.get("trigger_description")
            if trigger:
                triggers.append(str(trigger))

        return {
            "sample_size": len(levels),
            "max_danger_level": max(levels, default=0),
            "high_danger_count": sum(level >= 2 for level in levels),
            "recent_levels": levels,
            "recent_triggers": triggers[:5],
        }

    def get_current(self) -> dict | None:
        """Get the latest vision."""
        row = self.conn.execute(
            "SELECT vision_json FROM world_vision ORDER BY version DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                return json.loads(row["vision_json"])
            except (TypeError, json.JSONDecodeError):
                logger.warning("Stored world vision is invalid JSON, ignoring latest row")
                return None
        return None

    def get_summary_for_s1(self) -> str | None:
        """Get a short summary suitable for injection into S1 prompt.

        Only: who_they_are.summary + blind_spots + next_priorities.
        """
        vision = self.get_current()
        if not vision:
            return None

        parts = []

        who = vision.get("who_they_are", {})
        if who.get("summary"):
            parts.append(f"Cet humain : {who['summary']}")

        blind_spots = vision.get("blind_spots", [])
        if blind_spots:
            spots = [
                bs.get("description")
                for bs in blind_spots[:3]
                if isinstance(bs, dict) and bs.get("description")
            ]
            if spots:
                parts.append("Angles morts : " + " | ".join(spots))

        priorities = vision.get("next_priorities", [])
        if priorities:
            prios = [
                f"{p.get('type')}: {p.get('target')}"
                for p in priorities[:3]
                if isinstance(p, dict) and p.get("type") and p.get("target")
            ]
            if prios:
                parts.append("Priorités : " + ", ".join(prios))

        return "\n".join(parts) if parts else None

    def _get_current_version(self) -> int:
        row = self.conn.execute(
            "SELECT MAX(version) as v FROM world_vision"
        ).fetchone()
        return row["v"] or 0 if row else 0

    def _parse_vision(self, raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Vision output is not valid JSON, using defaults")
            return self._default_vision()
        return self._normalize_vision(parsed)

    def _normalize_vision(self, vision: object) -> dict:
        default = self._default_vision()
        if not isinstance(vision, dict):
            logger.warning("Vision output is not a JSON object, using defaults")
            return default

        normalized = dict(vision)
        normalized["synthesized_at"] = str(
            normalized.get("synthesized_at") or default["synthesized_at"]
        )

        who = vision.get("who_they_are")
        if isinstance(who, dict):
            normalized["who_they_are"] = {
                **default["who_they_are"],
                **who,
            }
        else:
            normalized["who_they_are"] = dict(default["who_they_are"])

        blind_spots = vision.get("blind_spots")
        normalized["blind_spots"] = blind_spots if isinstance(blind_spots, list) else []

        priorities = vision.get("next_priorities")
        normalized["next_priorities"] = priorities if isinstance(priorities, list) else []
        return normalized

    def _default_vision(self) -> dict:
        return {
            "version": 0,
            "synthesized_at": datetime.now().isoformat(),
            "who_they_are": {"summary": "Pas encore assez de données.", "confidence": 0.0},
            "blind_spots": [],
            "next_priorities": [],
        }
