"""Collision scoring — Surprise x Relevance (SerenQA-inspired).

Novelty removed: midpoint-based novelty is broken for dense corpora (N>500).
The surprise sweet spot [0.3, 0.7] already ensures non-trivial connections.

See ARCHITECTURE_HARNESS.md and PROMPT_CLAUDE_CODE_FIX_SCORING.md.
"""

import re

import numpy as np
from src.embeddings import cosine_similarity


# Sweet spot for semantic distance between fragments
SURPRISE_LOW = 0.3
SURPRISE_HIGH = 0.7

# Minimum score to deliver a collision
DELIVERY_THRESHOLD = 0.5

# Minimum message length (chars) to be considered for collisions
MIN_MESSAGE_LENGTH = 30

# Procedural messages to exclude
_PROCEDURAL_RE = re.compile(
    r"^(?:bonjour|salut|hello|hi|merci|thanks|ok|d'accord|oui|non|"
    r"voilà|c'est bon|parfait|super|génial|bien reçu|"
    r"compris|entendu|noté|bonne journée|à bientôt|au revoir|bye)[\s.!?]*$",
    re.IGNORECASE,
)


def is_substantive(text: str) -> bool:
    """Check if a message contains a substantive idea (not just procedural noise)."""
    text = text.strip()
    if len(text) < MIN_MESSAGE_LENGTH:
        return False
    if _PROCEDURAL_RE.match(text):
        return False
    return True


def score_surprise(sim: float) -> float:
    """Surprise score: peaks in the sweet spot [0.3, 0.7].

    Too close (>0.7) = trivial connection.
    Too far (<0.3) = random noise.
    Sweet spot = genuinely interesting collision.
    """
    if sim < SURPRISE_LOW or sim > SURPRISE_HIGH:
        return 0.0
    # Triangle function peaking at 0.5
    midpoint = (SURPRISE_LOW + SURPRISE_HIGH) / 2
    half_width = (SURPRISE_HIGH - SURPRISE_LOW) / 2
    return 1.0 - abs(sim - midpoint) / half_width


def score_relevance(text_a: str, text_b: str,
                    embedding_a: np.ndarray, embedding_b: np.ndarray,
                    theme_embeddings: list[np.ndarray]) -> float:
    """Relevance: are both fragments substantive and thematically connected?

    Without themes: 1.0 if both messages are substantive, 0.0 otherwise.
    With themes: boost if both relate to an active theme.
    """
    # Filter procedural noise
    if not is_substantive(text_a) or not is_substantive(text_b):
        return 0.0

    if not theme_embeddings:
        return 1.0  # no themes = trust surprise alone

    a_relevant = False
    b_relevant = False

    for theme_emb in theme_embeddings:
        if cosine_similarity(embedding_a, theme_emb) > 0.4:
            a_relevant = True
        if cosine_similarity(embedding_b, theme_emb) > 0.4:
            b_relevant = True
        if a_relevant and b_relevant:
            return 1.0

    if a_relevant or b_relevant:
        return 0.7
    return 0.5  # still relevant if substantive, just not theme-matched


def collision_score(embedding_a: np.ndarray, embedding_b: np.ndarray,
                    text_a: str, text_b: str,
                    theme_embeddings: list[np.ndarray]) -> float:
    """Collision score = Surprise x Relevance.

    Returns [0, 1]. Deliver if > DELIVERY_THRESHOLD.
    """
    sim = cosine_similarity(embedding_a, embedding_b)

    surprise = score_surprise(sim)
    if surprise == 0.0:
        return 0.0

    relevance = score_relevance(text_a, text_b, embedding_a, embedding_b,
                                theme_embeddings)
    if relevance == 0.0:
        return 0.0

    return surprise * relevance
