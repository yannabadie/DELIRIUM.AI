"""PersonaEngine — computes persona transitions between T and T+1.

Based on ARCHITECTURE_HARNESS.md section 2.2.
"""

from datetime import datetime
import math
from src.persona.state import PersonaState, clamp


class PersonaEngine:
    """Calculates persona state transitions after each message exchange."""

    def __init__(self):
        self._state = PersonaState()

    def get_current_state(self) -> PersonaState:
        return self._state

    def transition(self, s2_analysis: dict, time_context: dict) -> PersonaState:
        """Compute new persona state from S2 analysis and time context.

        Args:
            s2_analysis: Output from S2 module (intention, danger, defensiveness...).
            time_context: {messages_this_session, total_sessions, ignored_injections}.
        """
        current = self._state
        new = PersonaState()

        # === H (tonality) ===
        h_delta = self._finite_float(s2_analysis.get("recommended_H_delta", 0.0))
        danger_level = self._finite_int(s2_analysis.get("danger_level", 0))
        defensiveness_score = self._bounded_float(
            s2_analysis.get("defensiveness_score", 0.0)
        )
        session_length = self._finite_int(time_context.get("messages_this_session", 0))
        total_sessions = self._finite_int(time_context.get("total_sessions", 0))
        ignored_injections = self._finite_int(time_context.get("ignored_injections", 0))

        phase_factors = {
            "probing": -0.5,
            "silent": -0.3,
            "reflection": 0.0,
            "sparring": 0.3,
        }

        new.H = clamp(
            current.H * 0.7          # 70% inertia
            + h_delta * 0.15         # S2 recommendation
            + phase_factors.get(current.phase, 0.0) * 0.1
            + self._time_to_h_delta(time_context) * 0.05,
            -1.0, 1.0
        )

        # === Empathy / confrontation / creativity (defaults from current) ===
        new.empathy = current.empathy
        new.confrontation = current.confrontation
        new.creativity = current.creativity
        new.listen_ratio = current.listen_ratio

        # === DANGER OVERRIDE ===
        if danger_level >= 2:
            new.H = min(new.H, -0.5)
            new.empathy = max(current.empathy, 0.8)
            new.confrontation = 0.0
            new.creativity = 0.0
        if danger_level >= 3:
            new.H = -1.0  # exit role

        # === DEFENSIVENESS ===
        new.defensiveness_detected = defensiveness_score
        if defensiveness_score > 0.6:
            new.confrontation = min(current.confrontation, 0.1)
            new.listen_ratio = max(current.listen_ratio, 0.8)

        # === FATIGUE ===
        new.fatigue = clamp(
            current.fatigue + session_length * 0.02 + ignored_injections * 0.1 - 0.3,
            0.0, 1.0
        )

        # === PHASE ===
        new.phase = self._compute_phase({"total_sessions": total_sessions})

        new.timestamp = datetime.now()
        new.trigger = s2_analysis.get("trigger_description", "routine")

        self._state = new
        return new

    def set_state(self, state: PersonaState):
        self._state = state

    def _compute_phase(self, ctx: dict) -> str:
        total_sessions = ctx.get("total_sessions", 0)
        if total_sessions == 0:
            return "probing"
        elif total_sessions < 10:
            return "silent"
        elif total_sessions < 20:
            return "reflection"
        else:
            return "sparring"

    def _time_to_h_delta(self, ctx: dict) -> float:
        """Time-based H adjustment. Late night = slightly lower H."""
        hour = datetime.now().hour
        if 0 <= hour < 6:
            return -0.2  # late night, calmer
        elif 6 <= hour < 12:
            return 0.1   # morning energy
        return 0.0

    def _finite_float(self, value, default: float = 0.0) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        return value if math.isfinite(value) else default

    def _finite_int(self, value, default: int = 0) -> int:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return default
        if not math.isfinite(value):
            return default
        return int(value)

    def _bounded_float(
        self, value, default: float = 0.0, lo: float = 0.0, hi: float = 1.0
    ) -> float:
        return clamp(self._finite_float(value, default), lo, hi)
