"""S2 Analyzer — Async metacognition module.

Runs after each S1 response. Produces structured JSON analysis.
See ARCHITECTURE_IA.md section 2.
"""

import asyncio
import json
import logging
from datetime import datetime

from src.config import get_s2_prompt, MINIMAX_MODEL_FAST
from src.llm_client import AsyncLLMClient
from src.persona.engine import PersonaEngine
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory

logger = logging.getLogger("delirium.s2")

# Default S2 result when parsing fails or API is unavailable
DEFAULT_S2_RESULT = {
    "intention": {"label": "unknown", "confidence": 0.0},
    "defensiveness_score": 0.0,
    "defensiveness_markers": [],
    "danger_level": 0,
    "danger_signals": [],
    "themes_latents": [],
    "loop_detected": False,
    "loop_theme": None,
    "loop_count": 0,
    "correlation": None,
    "ipc_position": {"agency": 0.0, "communion": 0.0},
    "axis_crossing": False,
    "sycophancy_risk": 0.0,
    "fanfaronade_score": 0.0,
    "cold_weaver_topics": [],
    "trigger_description": "routine",
    "recommended_H_delta": 0.0,
    "recommended_phase": None,
}


class S2Analyzer:
    """Runs S2 metacognition asynchronously after each S1 response."""

    def __init__(self, async_client: AsyncLLMClient, episodic: EpisodicMemory,
                 semantic: SemanticMemory, persona_engine: PersonaEngine):
        self.client = async_client
        self.episodic = episodic
        self.semantic = semantic
        self.persona_engine = persona_engine

    async def analyze(self, fragment_id: str, user_message: str,
                      s1_response: str, session_messages: list[dict],
                      session_id: str):
        """Run S2 analysis in background. Updates persona and semantic memory."""
        try:
            s2_prompt = get_s2_prompt()

            # Build conversation context for S2
            context = {
                "last_user_message": user_message,
                "last_s1_response": s1_response,
                "session_history": session_messages[-10:],  # last 10 exchanges
            }

            raw = await self.client.chat(
                system=s2_prompt,
                messages=[{"role": "user", "content": json.dumps(context, ensure_ascii=False)}],
                model=MINIMAX_MODEL_FAST,
            )

            s2_result = self._parse_s2_output(raw)

            # Update semantic memory
            self.semantic.update_from_s2(fragment_id, s2_result)

            # Update persona state
            time_ctx = {
                "messages_this_session": self.episodic.get_session_message_count(session_id),
                "total_sessions": self.episodic.get_total_sessions(),
                "ignored_injections": 0,
            }
            new_state = self.persona_engine.transition(s2_result, time_ctx)
            self.episodic.save_persona_state(new_state)

            # Log execution (mandatory)
            self.episodic.log_execution(fragment_id, "s2_analysis", s2_result)

            logger.info(
                "S2 done: danger=%d, H_delta=%.2f, themes=%s",
                s2_result.get("danger_level", 0),
                s2_result.get("recommended_H_delta", 0),
                s2_result.get("themes_latents", []),
            )

        except Exception as e:
            logger.error("S2 analysis failed: %s", e)
            self.episodic.log_execution(
                fragment_id, "s2_error", {"error": str(e)}
            )

    def _parse_s2_output(self, raw: str) -> dict:
        """Parse S2 JSON output, with fallback to defaults."""
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines)

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("S2 output is not valid JSON, using defaults")
            return dict(DEFAULT_S2_RESULT)

        # Merge with defaults for missing keys
        merged = dict(DEFAULT_S2_RESULT)
        merged.update(result)
        return merged
