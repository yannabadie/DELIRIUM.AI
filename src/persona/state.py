from dataclasses import dataclass, field, asdict
from datetime import datetime

PERSONA_PHASES = ("probing", "silent", "reflection", "sparring")


@dataclass
class PersonaState:
    """Persona state at time T. See ARCHITECTURE_HARNESS.md section 2.1."""

    H: float = 0.0                # [-1, 1] communicational register
    listen_ratio: float = 0.7     # [0, 1] listen vs intervene
    creativity: float = 0.3       # [0, 1] metaphor boldness
    confrontation: float = 0.1    # [0, 1] challenge level
    empathy: float = 0.5          # [0, 1] emotional listening
    fatigue: float = 0.0          # [0, 1] Delirium's weariness

    phase: str = "probing"        # probing | silent | reflection | sparring
    defensiveness_detected: float = 0.0  # PsyFIRE score
    bubble_risk_score: float = 0.0
    bubble_risk_status: str = "low_risk"
    bubble_break_enabled: bool = False
    bubble_break_intensity: str = "off"
    bubble_ignore_streak: int = 0

    timestamp: datetime = field(default_factory=datetime.now)
    trigger: str = ""             # what caused the change

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "PersonaState":
        d = dict(d)
        ts = d.get("timestamp")
        if isinstance(ts, str):
            d["timestamp"] = datetime.fromisoformat(ts)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))
