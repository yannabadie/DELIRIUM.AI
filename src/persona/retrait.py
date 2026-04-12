"""Retrait Engine — How Delirium "leaves" and "returns".

See 03_ARCHITECTURE/ARCHITECTURE_RETRAIT.md.
4 states: active, distant, withdrawn, dormant.
"""

import logging
from datetime import datetime

from src.persona.state import PersonaState

logger = logging.getLogger("delirium.persona.retrait")

# State thresholds (days since last interaction)
DISTANT_DAYS = 7
WITHDRAWN_DAYS = 21
DORMANT_DAYS = 45


def compute_retrait_state(last_interaction_iso: str | None) -> str:
    """Compute retrait state from the last interaction timestamp."""
    if not last_interaction_iso:
        return "active"  # first ever session

    try:
        last = datetime.fromisoformat(last_interaction_iso)
    except (ValueError, TypeError):
        return "active"

    days = (datetime.now() - last).days

    if days < DISTANT_DAYS:
        return "active"
    elif days < WITHDRAWN_DAYS:
        return "distant"
    elif days < DORMANT_DAYS:
        return "withdrawn"
    else:
        return "dormant"


def adjust_persona_for_retrait(state: PersonaState, retrait: str) -> PersonaState:
    """Adjust persona state based on retrait level."""
    if retrait == "distant":
        state.fatigue = min(state.fatigue + 0.3, 0.8)
        state.listen_ratio = max(state.listen_ratio, 0.8)
        state.H = min(state.H, 0.0)  # no audacity after absence
    elif retrait == "withdrawn":
        state.fatigue = 0.9
        state.creativity = 0.1
        state.confrontation = 0.0
        state.H = -0.3
    elif retrait == "dormant":
        state.fatigue = 1.0
        state.creativity = 0.0
        state.confrontation = 0.0
        state.H = -0.5
    return state


def get_retrait_context(retrait: str, days_absent: int,
                        forgotten_topics: list[dict],
                        pending_collision: dict | None) -> str:
    """Build context string for the return message prompt."""
    if retrait == "active":
        return ""

    parts = [f"L'utilisateur revient après {days_absent} jours d'absence."]
    parts.append(f"État de retrait : {retrait}.")

    if retrait == "distant":
        parts.append("Ton : direct, pas de drama, montre que la vie a continué.")
    elif retrait == "withdrawn":
        parts.append("Ton : légèrement sec. Le temps a passé. Tu as rangé le carnet.")
    elif retrait == "dormant":
        parts.append("Ton : sobre. Tu as oublié des trucs — c'est normal, dit-le.")

    if forgotten_topics:
        count = len(forgotten_topics)
        parts.append(f"Tu as oublié {count} sujets (RS basse). C'est honnête.")

    if pending_collision:
        parts.append("Tu as une collision Cold Weaver en attente — mentionne-la.")

    # Forbidden behaviors on return
    parts.append("INTERDIT : 'tu m'as manqué', 'où étais-tu', 'j'espère que tu vas bien'.")
    parts.append("INTERDIT : émotions (tristesse, joie du retour). États seulement.")

    return "\n".join(parts)
