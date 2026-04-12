"""Bubble Detection — H_bulle score from conversational signals.

See 04_FORMALISME/DETECTION_BULLE.md.
Detects algorithmic bubble exposure from conversation patterns alone
(no access to user's feeds or social networks).

6 signals: topic_narrowing, certainty_drift, outgroup_language,
injection_resistance, echo_in_ai, source_homogeneity.

Gap de recherche: no prior work detects bubbles from conversation alone.
"""

import logging
import re
from datetime import datetime, timedelta

logger = logging.getLogger("delirium.memory.bubble")

# Certainty / doubt markers (French)
CERTAINTY_MARKERS = [
    "c'est évident", "tout le monde sait", "clairement",
    "bien sûr", "forcément", "c'est un fait", "y'a pas de débat",
    "de toute évidence", "sans aucun doute", "personne peut nier",
]

DOUBT_MARKERS = [
    "je pense", "peut-être", "il me semble", "j'ai l'impression",
    "je sais pas trop", "possible que", "tu crois que",
    "on pourrait dire", "je me demande", "pas sûr",
]

# Outgroup markers
OUTGROUP_MARKERS = [
    "les gens comme eux", "de toute façon ils", "ces gens-là",
    "le problème c'est eux", "nous on", "eux ils",
    "leur camp", "de leur côté",
]


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _count_markers(texts: list[str], markers: list[str]) -> int:
    count = 0
    combined = " ".join(texts).lower()
    for marker in markers:
        count += combined.count(marker.lower())
    return count


def topic_narrowing(conn, window_days: int = 90) -> float:
    """S1: Measure thematic diversity narrowing over a sliding window.

    Compares recent 30 days vs previous 30-90 days.
    """
    now = datetime.now()
    recent_cutoff = (now - timedelta(days=30)).isoformat()
    past_start = (now - timedelta(days=window_days)).isoformat()

    recent = conn.execute(
        "SELECT DISTINCT user_input FROM conversations "
        "WHERE timestamp > ? AND source = 'delirium'",
        (recent_cutoff,)
    ).fetchall()

    past = conn.execute(
        "SELECT DISTINCT user_input FROM conversations "
        "WHERE timestamp > ? AND timestamp <= ? AND source = 'delirium'",
        (past_start, recent_cutoff)
    ).fetchall()

    # Simple diversity: count of distinct words
    def word_diversity(rows):
        words = set()
        for r in rows:
            words.update(r["user_input"].lower().split())
        return len(words)

    div_recent = word_diversity(recent)
    div_past = word_diversity(past)

    if div_past == 0:
        return 0.0

    ratio = div_recent / div_past
    return _clamp(1.0 - ratio, 0.0, 1.0)


def certainty_drift(conn, window_messages: int = 50) -> float:
    """S2: Measure increase in certainty vs doubt markers."""
    rows = conn.execute(
        "SELECT user_input FROM conversations WHERE source = 'delirium' "
        "ORDER BY timestamp DESC LIMIT ?",
        (window_messages * 2,)
    ).fetchall()

    if len(rows) < window_messages:
        return 0.0

    recent_texts = [r["user_input"] for r in rows[:window_messages]]
    older_texts = [r["user_input"] for r in rows[window_messages:]]

    cert_recent = _count_markers(recent_texts, CERTAINTY_MARKERS)
    doubt_recent = _count_markers(recent_texts, DOUBT_MARKERS)
    cert_older = _count_markers(older_texts, CERTAINTY_MARKERS)
    doubt_older = _count_markers(older_texts, DOUBT_MARKERS)

    ratio_recent = cert_recent / (doubt_recent + 1)
    ratio_older = cert_older / (doubt_older + 1)

    drift = ratio_recent - ratio_older
    return _clamp(drift / 3.0, 0.0, 1.0)


def outgroup_language(conn, window_messages: int = 100) -> float:
    """S3: Measure us-vs-them language patterns."""
    rows = conn.execute(
        "SELECT user_input FROM conversations WHERE source = 'delirium' "
        "ORDER BY timestamp DESC LIMIT ?",
        (window_messages,)
    ).fetchall()

    if not rows:
        return 0.0

    texts = [r["user_input"] for r in rows]
    count = _count_markers(texts, OUTGROUP_MARKERS)
    total_words = sum(len(t.split()) for t in texts)

    if total_words == 0:
        return 0.0

    # Normalize: outgroup markers per 1000 words
    rate = (count / total_words) * 1000
    return _clamp(rate / 10.0, 0.0, 1.0)


def injection_resistance(conn) -> float:
    """S4: Track responses to Cold Weaver injections.

    This is the signal most specific to Delirium.
    """
    rows = conn.execute(
        "SELECT content FROM execution_logs "
        "WHERE log_type = 'collision_delivered' "
        "ORDER BY timestamp DESC LIMIT 10"
    ).fetchall()

    if len(rows) < 3:
        return 0.0

    # For now, we can't measure the user response to the injection
    # without S2 analysis. Return 0.0 as placeholder.
    # [NC: integrate with S2 to track injection engagement]
    return 0.0


def h_bulle(conn) -> dict:
    """Compute the composite bubble score.

    Returns dict with score and component breakdown.
    """
    s1 = topic_narrowing(conn)
    s2 = certainty_drift(conn)
    s3 = outgroup_language(conn)
    s4 = injection_resistance(conn)

    # Weights from DETECTION_BULLE.md
    score = (
        0.25 * s1 +    # narrowing — most reliable
        0.20 * s2 +    # certainty — well-anchored linguistically
        0.15 * s3 +    # outgroup — strong signal but false positives
        0.20 * s4 +    # injection resistance — Delirium-specific
        0.10 * 0.0 +   # echo_ai — placeholder [NC]
        0.10 * 0.0     # source_homogeneity — placeholder [NC]
    )

    score = _clamp(score, 0.0, 1.0)

    if score < 0.3:
        status = "low_risk"
    elif score < 0.6:
        status = "medium_risk"
    else:
        status = "high_risk"

    return {
        "h_bulle": round(score, 3),
        "narrowing": round(s1, 3),
        "certainty_drift": round(s2, 3),
        "outgroup_language": round(s3, 3),
        "injection_resistance": round(s4, 3),
        "bubble_status": status,
    }
