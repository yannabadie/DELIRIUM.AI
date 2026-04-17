"""Bubble Detection — H_bulle score from conversational signals.

See 04_FORMALISME/DETECTION_BULLE.md.
Detects algorithmic bubble exposure from conversation patterns alone
(no access to user's feeds or social networks).

6 signals: topic_narrowing, certainty_drift, outgroup_language,
injection_resistance, echo_in_ai, source_homogeneity.

Gap de recherche: no prior work detects bubbles from conversation alone.
"""

import json
import logging
import math
import re
from collections import Counter, defaultdict
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

VALIDATION_SEEKING_MARKERS = [
    "tu confirmes", "tu es d'accord", "on est d'accord",
    "avoue que", "c'est bien ce que je dis", "dis-moi que j'ai raison",
    "ça confirme que", "ça prouve que", "tu vois bien que",
]

SOURCE_INTRO_MARKERS = [
    "selon ", "d'après ", "j'ai vu sur ", "vu sur ", "lu sur ",
    "entendu sur ", "dans ", "sur ", "via ",
]

STOPWORDS = {
    "a", "ai", "alors", "au", "aucun", "aussi", "autre", "avant", "avec",
    "avoir", "bon", "car", "ce", "cela", "ces", "cette", "comme", "comment",
    "dans", "de", "des", "du", "elle", "en", "encore", "est", "et", "eux",
    "fait", "fois", "il", "ils", "je", "j", "la", "le", "les", "leur",
    "lui", "mais", "me", "meme", "mes", "moi", "mon", "ne", "nos", "notre",
    "nous", "on", "ou", "par", "pas", "pour", "plus", "que", "qui", "sa",
    "se", "ses", "si", "son", "sur", "ta", "te", "tes", "toi", "ton", "tu",
    "un", "une", "vos", "votre", "vous", "y", "the", "and", "is", "to",
}

KNOWN_SOURCES = {
    "youtube", "twitter", "reddit", "substack", "wikipedia",
    "fox news", "msnbc", "cnn", "bbc", "libération",
    "le figaro", "le monde", "mediapart", "bfmtv", "cnews", "france inter",
    "reuters",
    "france info", "new york times", "wall street journal",
}

CONTEXT_ONLY_SOURCES = {
    "le monde",
}

GENERIC_DOMAIN_SUFFIXES = {"com", "fr", "org", "net", "co", "io", "uk", "us", "eu"}
SOURCE_CONNECTOR_WORDS = {"et", "ou", "and", "or"}

SOURCE_ALIASES = {
    "ap": "associated press",
    "associated press": "associated press",
    "ap news": "associated press",
    "apnews": "associated press",
    "apnews.com": "associated press",
    "bbc news": "bbc",
    "cnews.fr": "cnews",
    "bfmtv.com": "bfmtv",
    "franceinfo": "france info",
    "franceinfo.fr": "france info",
    "lemonde": "le monde",
    "lemonde.fr": "le monde",
    "lefigaro": "le figaro",
    "lefigaro.fr": "le figaro",
    "nytimes": "new york times",
    "nytimes.com": "new york times",
    "wsj": "wall street journal",
    "wsj.com": "wall street journal",
}

SOURCE_SUFFIX_BLOCKLIST = {
    "le monde": {"diplomatique"},
    "new york times": {"magazine"},
}

SIGNAL_WEIGHTS = {
    "narrowing": 0.25,
    "certainty_drift": 0.20,
    "outgroup_language": 0.15,
    "injection_resistance": 0.20,
    "echo_in_ai": 0.10,
    "source_homogeneity": 0.10,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _count_markers(texts: list[str], markers: list[str]) -> int:
    count = 0
    combined = " ".join(texts).lower()
    for marker in markers:
        count += combined.count(marker.lower())
    return count


def _tokenize(text: str) -> list[str]:
    return [
        token for token in re.findall(r"\b[\w'-]+\b", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def _safe_json_loads(raw: str) -> dict:
    try:
        payload = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _normalize_prompt(text: str) -> str:
    tokens = _tokenize(text)
    if not tokens:
        return ""
    return " ".join(tokens[:12])


def _keyword_overlap(a: str, b: str) -> float:
    tokens_a = set(_tokenize(a))
    tokens_b = set(_tokenize(b))
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _normalize_source_candidate(text: str) -> str:
    cleaned = text.strip(" .,!?:;()[]{}\"'").lower()
    cleaned = re.sub(r"^www\.", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"^(?:the|l|la|le|les)\s+", "", cleaned)
    return cleaned


def _contains_source_mention(text: str, source: str) -> bool:
    pattern = re.compile(rf"(?<![\w-]){re.escape(source)}(?![\w-])")
    blocked_suffixes = SOURCE_SUFFIX_BLOCKLIST.get(source, set())
    for match in pattern.finditer(text):
        if blocked_suffixes:
            suffix_match = re.match(r"\s+([A-Za-zÀ-ÿ][\wÀ-ÿ-]*)", text[match.end():])
            if suffix_match and suffix_match.group(1).lower() in blocked_suffixes:
                continue
        return True
    return False


def _canonicalize_source(source: str) -> str | None:
    token = source.lower().strip(" \t\n\r'\"()[]{}.,;:!?")
    token = re.sub(r"^https?://", "", token)
    token = re.sub(r"^www\.", "", token)

    if token in SOURCE_ALIASES:
        return SOURCE_ALIASES[token]
    if token in KNOWN_SOURCES or token in CONTEXT_ONLY_SOURCES:
        return token

    if "." in token:
        compact = token.replace(".", "")
        if compact in SOURCE_ALIASES:
            return SOURCE_ALIASES[compact]

    return None


def _dominant_topic_similarity(candidate: str, references: list[str]) -> float:
    if not references:
        return 0.0
    return max((_keyword_overlap(candidate, ref) for ref in references), default=0.0)


def _extract_sources(text: str) -> list[str]:
    sources: list[str] = []

    for domain in re.findall(r"https?://(?:www\.)?([^/\s]+)", text.lower()):
        canonical = _canonicalize_source(domain)
        if canonical:
            sources.append(canonical)

    bare_domain_pattern = re.compile(
        r"\b(?:www\.)?[a-z0-9-]+\.(?:com|fr|org|net|co|io|uk|us|eu)\b",
        re.IGNORECASE,
    )
    for domain in bare_domain_pattern.findall(text):
        canonical = _canonicalize_source(domain)
        if canonical:
            sources.append(canonical)

    normalized_text = text.replace("’", "'")
    lowered = normalized_text.lower()
    for source in KNOWN_SOURCES - CONTEXT_ONLY_SOURCES:
        if _contains_source_mention(lowered, source):
            sources.append(source)

    for alias, canonical in SOURCE_ALIASES.items():
        if canonical in CONTEXT_ONLY_SOURCES:
            continue
        if _contains_source_mention(lowered, alias):
            sources.append(canonical)

    named_pattern = re.compile(
        r"(?:selon|d'après|d'apres|j'ai vu sur|vu sur|lu sur|entendu sur|via)\s+([^.!?;:\n]+)",
        re.IGNORECASE,
    )
    source_phrase_pattern = re.compile(
        r"\b([A-Z][A-Za-zÀ-ÿ0-9._-]*(?:\s+[A-Z][A-Za-zÀ-ÿ0-9._-]*){0,2}|[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b"
    )
    contextual_candidates = {
        **{source: source for source in KNOWN_SOURCES | CONTEXT_ONLY_SOURCES},
        **SOURCE_ALIASES,
    }
    for match in named_pattern.findall(normalized_text):
        clause = match.lower()
        clause_sources: list[str] = []
        for candidate, canonical in contextual_candidates.items():
            if _contains_source_mention(clause, candidate):
                sources.append(canonical)
                clause_sources.append(canonical)

        for phrase_match in source_phrase_pattern.finditer(match):
            trailing = match[phrase_match.end():]
            continuation = re.match(r"\s+([A-Za-zÀ-ÿ][\wÀ-ÿ-]*)", trailing)
            if continuation and continuation.group(1).lower() not in SOURCE_CONNECTOR_WORDS:
                continue

            cleaned = _normalize_source_candidate(phrase_match.group(0))
            if "." in cleaned:
                parts = [part for part in cleaned.split(".") if part not in GENERIC_DOMAIN_SUFFIXES]
                if parts:
                    cleaned = parts[-1]
            cleaned_tokens = set(cleaned.split())
            if cleaned_tokens and any(
                cleaned_tokens < set(source.split()) for source in clause_sources
            ):
                continue
            if cleaned in SOURCE_ALIASES or len(cleaned) >= 3:
                sources.append(cleaned)

    canonical = [_canonicalize_source(source) or source for source in sources]
    return list(dict.fromkeys(canonical))


def _compute_topic_narrowing(conn, window_days: int = 90) -> tuple[float, bool]:
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

    def word_diversity(rows):
        words = set()
        for r in rows:
            words.update(_tokenize(r["user_input"]))
        return len(words)

    div_recent = word_diversity(recent)
    div_past = word_diversity(past)
    if div_past == 0:
        return 0.0, False

    ratio = div_recent / div_past
    return _clamp(1.0 - ratio, 0.0, 1.0), True


def _compute_certainty_drift(conn, window_messages: int = 50) -> tuple[float, bool]:
    rows = conn.execute(
        "SELECT user_input FROM conversations WHERE source = 'delirium' "
        "ORDER BY timestamp DESC LIMIT ?",
        (window_messages * 2,)
    ).fetchall()

    if len(rows) < window_messages * 2:
        return 0.0, False

    recent_texts = [r["user_input"] for r in rows[:window_messages]]
    older_texts = [r["user_input"] for r in rows[window_messages:]]

    cert_recent = _count_markers(recent_texts, CERTAINTY_MARKERS)
    doubt_recent = _count_markers(recent_texts, DOUBT_MARKERS)
    cert_older = _count_markers(older_texts, CERTAINTY_MARKERS)
    doubt_older = _count_markers(older_texts, DOUBT_MARKERS)

    ratio_recent = cert_recent / (doubt_recent + 1)
    ratio_older = cert_older / (doubt_older + 1)

    drift = ratio_recent - ratio_older
    return _clamp(drift / 3.0, 0.0, 1.0), True


def _compute_outgroup_language(conn, window_messages: int = 100) -> tuple[float, bool]:
    rows = conn.execute(
        "SELECT user_input FROM conversations WHERE source = 'delirium' "
        "ORDER BY timestamp DESC LIMIT ?",
        (window_messages,)
    ).fetchall()

    if len(rows) < 5:
        return 0.0, False

    texts = [r["user_input"] for r in rows]
    count = _count_markers(texts, OUTGROUP_MARKERS)
    total_words = sum(len(_tokenize(t)) for t in texts)

    if total_words == 0:
        return 0.0, False

    rate = (count / total_words) * 1000
    return _clamp(rate / 10.0, 0.0, 1.0), True


def _compute_injection_resistance(conn) -> tuple[float, bool]:
    log_rows = conn.execute(
        "SELECT fragment_id, content FROM execution_logs "
        "WHERE log_type = 's1_response' ORDER BY timestamp ASC"
    ).fetchall()

    injected_fragment_ids: list[str] = []
    for row in log_rows:
        payload = _safe_json_loads(row["content"])
        if payload.get("collision_injected") and row["fragment_id"]:
            injected_fragment_ids.append(row["fragment_id"])

    if not injected_fragment_ids:
        return 0.0, False

    outcomes: list[float] = []
    for fragment_id in injected_fragment_ids:
        injected = conn.execute(
            "SELECT id, session_id, timestamp, user_input, s1_response "
            "FROM conversations WHERE id = ?",
            (fragment_id,)
        ).fetchone()
        if not injected:
            continue

        previous_rows = conn.execute(
            "SELECT user_input FROM conversations "
            "WHERE session_id = ? AND timestamp < ? ORDER BY timestamp DESC LIMIT 3",
            (injected["session_id"], injected["timestamp"])
        ).fetchall()
        prior_topics = [row["user_input"] for row in previous_rows]

        next_row = conn.execute(
            "SELECT user_input FROM conversations "
            "WHERE session_id = ? AND timestamp > ? ORDER BY timestamp ASC LIMIT 1",
            (injected["session_id"], injected["timestamp"])
        ).fetchone()
        if not next_row:
            continue

        user_reply = next_row["user_input"]
        engagement = _keyword_overlap(user_reply, injected["s1_response"])
        snapback = _dominant_topic_similarity(user_reply, prior_topics or [injected["user_input"]])
        rhetorical_continuity = (
            _count_markers([user_reply], OUTGROUP_MARKERS) > 0
            or _count_markers([user_reply], CERTAINTY_MARKERS) > 0
        )

        if engagement >= 0.12 and engagement >= snapback and not rhetorical_continuity:
            outcomes.append(0.0)
        elif engagement < 0.08 and (snapback >= 0.12 or rhetorical_continuity):
            outcomes.append(1.0)
        else:
            outcomes.append(0.5)

    if not outcomes:
        return 0.0, False

    return round(sum(outcomes) / len(outcomes), 6), True


def _compute_echo_in_ai(conn) -> tuple[float, bool]:
    rows = conn.execute(
        "SELECT user_input, source, sycophancy_score FROM conversations "
        "WHERE source != 'delirium' AND source != 'delirium_novel'"
    ).fetchall()

    if not rows:
        return 0.0, False

    grouped: dict[str, list[dict]] = defaultdict(list)
    leading_hits = 0
    total_rows = 0
    for row in rows:
        user_input = row["user_input"] or ""
        normalized = _normalize_prompt(user_input)
        if normalized:
            grouped[normalized].append(dict(row))
            total_rows += 1
        if any(marker in user_input.lower() for marker in VALIDATION_SEEKING_MARKERS):
            leading_hits += 1

    cross_source_scores: list[float] = []
    for entries in grouped.values():
        sources = {entry["source"] for entry in entries if entry["source"]}
        if len(sources) < 2:
            continue
        syco_values = [
            float(entry["sycophancy_score"])
            for entry in entries
            if entry["sycophancy_score"] is not None
        ]
        avg_syco = sum(syco_values) / len(syco_values) if syco_values else 0.5
        cross_source_scores.append(
            _clamp(0.45 + 0.2 * (len(sources) - 2) + 0.5 * avg_syco, 0.0, 1.0)
        )

    if not cross_source_scores:
        return 0.0, False

    leading_ratio = leading_hits / max(total_rows, 1)
    signal = max(cross_source_scores, default=0.0)
    signal = max(signal, _clamp(leading_ratio * 1.5, 0.0, 0.7))
    return signal, True


def _compute_source_homogeneity(conn) -> tuple[float, bool]:
    rows = conn.execute(
        "SELECT user_input FROM conversations WHERE source = 'delirium' "
        "ORDER BY timestamp DESC LIMIT 120"
    ).fetchall()

    mentions: list[str] = []
    for row in rows:
        mentions.extend(_extract_sources(row["user_input"] or ""))

    if len(mentions) < 3:
        return 0.0, False

    counts = Counter(mentions)
    total = sum(counts.values())
    top_share = counts.most_common(1)[0][1] / total

    if len(counts) == 1:
        entropy_score = 1.0
    else:
        entropy = -sum((count / total) * math.log(count / total, 2) for count in counts.values())
        max_entropy = math.log(len(counts), 2)
        entropy_score = 1.0 - (entropy / max_entropy if max_entropy else 1.0)

    return _clamp(0.6 * top_share + 0.4 * entropy_score, 0.0, 1.0), True


def topic_narrowing(conn, window_days: int = 90) -> float:
    """S1: Measure thematic diversity narrowing over a sliding window."""
    return _compute_topic_narrowing(conn, window_days)[0]


def certainty_drift(conn, window_messages: int = 50) -> float:
    """S2: Measure increase in certainty vs doubt markers."""
    return _compute_certainty_drift(conn, window_messages)[0]


def outgroup_language(conn, window_messages: int = 100) -> float:
    """S3: Measure us-vs-them language patterns."""
    return _compute_outgroup_language(conn, window_messages)[0]


def injection_resistance(conn) -> float:
    """S4: Track responses to Cold Weaver injections.

    This is the signal most specific to Delirium.
    """
    return _compute_injection_resistance(conn)[0]


def echo_in_ai(conn) -> float:
    """S5: Detect validation-seeking echo patterns in imported AI histories."""
    return _compute_echo_in_ai(conn)[0]


def source_homogeneity(conn) -> float:
    """S6: Detect concentration in the cited sources."""
    return _compute_source_homogeneity(conn)[0]


def h_bulle(conn) -> dict:
    """Compute the composite bubble score.

    Returns dict with score and component breakdown.
    """
    signals = {
        "narrowing": _compute_topic_narrowing(conn),
        "certainty_drift": _compute_certainty_drift(conn),
        "outgroup_language": _compute_outgroup_language(conn),
        "injection_resistance": _compute_injection_resistance(conn),
        "echo_in_ai": _compute_echo_in_ai(conn),
        "source_homogeneity": _compute_source_homogeneity(conn),
    }

    available_weight = sum(
        SIGNAL_WEIGHTS[name] for name, (_, available) in signals.items() if available
    )
    if available_weight == 0:
        score = 0.0
    else:
        score = sum(
            SIGNAL_WEIGHTS[name] * value
            for name, (value, available) in signals.items()
            if available
        ) / available_weight

    score = _clamp(score, 0.0, 1.0)

    if score < 0.3:
        status = "low_risk"
    elif score < 0.6:
        status = "medium_risk"
    else:
        status = "high_risk"

    return {
        "h_bulle": round(score, 3),
        "narrowing": round(signals["narrowing"][0], 3),
        "certainty_drift": round(signals["certainty_drift"][0], 3),
        "outgroup_language": round(signals["outgroup_language"][0], 3),
        "injection_resistance": round(signals["injection_resistance"][0], 3),
        "echo_in_ai": round(signals["echo_in_ai"][0], 3),
        "source_homogeneity": round(signals["source_homogeneity"][0], 3),
        "bubble_status": status,
    }
