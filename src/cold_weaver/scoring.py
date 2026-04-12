"""Collision scoring — SerenQA-inspired (Relevance x Novelty x Surprise).

See ARCHITECTURE_HARNESS.md and 04_FORMALISME/SCORE_FANFARONADE.md.
"""

import numpy as np
from src.embeddings import cosine_similarity


# Sweet spot for semantic distance between fragments
SURPRISE_LOW = 0.3
SURPRISE_HIGH = 0.7

# Minimum score to deliver a collision
DELIVERY_THRESHOLD = 0.6


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


def score_novelty(combined_embedding: np.ndarray,
                  all_embeddings: list[np.ndarray],
                  threshold: float = 0.8) -> float:
    """Novelty: is this combination new? High if no existing fragment is close.

    If any existing fragment has cosine > threshold with the combined embedding,
    the combination is not novel.
    """
    if not all_embeddings:
        return 1.0

    max_sim = 0.0
    for emb in all_embeddings:
        sim = cosine_similarity(combined_embedding, emb)
        max_sim = max(max_sim, sim)

    if max_sim > threshold:
        return 0.0
    # Linear decay: novelty drops as similarity approaches threshold
    return 1.0 - (max_sim / threshold)


def score_relevance(embedding_a: np.ndarray, embedding_b: np.ndarray,
                    theme_embeddings: list[np.ndarray]) -> float:
    """Relevance: do both fragments relate to an active theme?

    At least one shared theme with cosine > 0.5 = relevant.
    """
    if not theme_embeddings:
        return 0.5  # neutral when no themes tracked yet

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
        return 0.5
    return 0.2


def collision_score(embedding_a: np.ndarray, embedding_b: np.ndarray,
                    all_embeddings: list[np.ndarray],
                    theme_embeddings: list[np.ndarray]) -> float:
    """Full collision score = Relevance x Novelty x Surprise.

    Returns [0, 1]. Deliver if > DELIVERY_THRESHOLD.
    """
    sim = cosine_similarity(embedding_a, embedding_b)

    surprise = score_surprise(sim)
    if surprise == 0.0:
        return 0.0  # early exit: outside sweet spot

    # Combined embedding = average of A and B (represents the collision)
    combined = (embedding_a + embedding_b) / 2.0
    norm = np.linalg.norm(combined)
    if norm > 0:
        combined = combined / norm

    novelty = score_novelty(combined, all_embeddings)
    relevance = score_relevance(embedding_a, embedding_b, theme_embeddings)

    return relevance * novelty * surprise
