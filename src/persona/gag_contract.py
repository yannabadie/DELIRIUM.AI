"""Shared normalization helpers for the S2 recurring-element gag contract."""

from collections import deque
from collections.abc import Callable, Collection, Iterator, Mapping
import json
import math
import re

CONTAINER_VALUE_TYPES = (Mapping, list, tuple, set, frozenset)
WHITESPACE_RE = re.compile(r"\s+")
CONTRACT_KEY_PARTS_RE = re.compile(r"[A-Za-z0-9]+")
ACRONYM_BOUNDARY_RE = re.compile(r"([A-Z]+)([A-Z][a-z])")
CAMEL_CASE_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
PLACEHOLDER_PUNCTUATION_RE = re.compile(r"^[\.\-_~*/\\|=+<>\[\]\(\)\{\}:;,'\"`]+$")
REACTION_PRIORITY = {
    "neutral": 0,
    "engaged": 1,
    "amused": 2,
    "callback": 3,
}
GAG_TYPE_ALIASES = {
    "in_joke": "in_joke",
    "injoke": "in_joke",
    "object_callback": "object_callback",
    "objectcallback": "object_callback",
    "ritual": "ritual",
    "theme": "theme",
}
VALID_GAG_TYPES = frozenset(GAG_TYPE_ALIASES.values())
REACTION_ALIASES = {
    "neutral": "neutral",
    "engaged": "engaged",
    "amused": "amused",
    "callback": "callback",
    "call_back": "callback",
}
RECURRING_MINOR_ELEMENT_FIELD_ALIASES = {
    ("content",): "content",
    ("type",): "type",
    ("count",): "count",
    ("importance",): "importance",
    ("user", "reaction"): "user_reaction",
}
RECURRING_MINOR_ELEMENTS_FIELD_ALIASES = {
    ("recurring", "minor", "elements"): "recurring_minor_elements",
}
RECURRING_MINOR_ELEMENTS_WRAPPER_ALIASES = {
    ("item",): "items",
    ("items",): "items",
    ("element",): "items",
    ("elements",): "items",
    ("entry",): "items",
    ("entries",): "items",
    ("value",): "items",
    ("values",): "items",
    ("recurring", "minor", "elements"): "items",
}
SEQUENCE_CONTAINER_TYPES = (list, tuple, set, frozenset)


def is_non_mapping_collection(value) -> bool:
    """Identify finite collection views that should be traversed like sequences."""
    return isinstance(value, Collection) and not isinstance(
        value,
        (str, bytes, bytearray, Mapping),
    )


def is_non_mapping_iterator(value) -> bool:
    """Identify one-shot iterator wrappers that should be traversed once."""
    return isinstance(value, Iterator) and not isinstance(
        value,
        (str, bytes, bytearray, Mapping),
    )


def is_non_mapping_container(value) -> bool:
    """Treat collection views and one-shot iterators as sequence-like wrappers."""
    return is_non_mapping_collection(value) or is_non_mapping_iterator(value)


def strip_json_code_fences(text: str) -> str:
    """Unwrap fenced JSON snippets before attempting container decoding."""
    if not (text.startswith("```") and text.endswith("```")):
        return text

    inner = text[3:-3].strip()
    if not inner:
        return ""

    if "\n" in inner:
        first_line, remainder = inner.split("\n", 1)
        if first_line.strip() and not first_line.lstrip().startswith(("{", "[")):
            return remainder.strip()
        return inner.strip()

    if not inner.startswith(("{", "[")):
        parts = inner.split(None, 1)
        if len(parts) == 2 and parts[0].replace("-", "").replace("_", "").isalnum():
            return parts[1].strip()
    return inner.strip()


def normalize_text_value(
    value,
    default: str = "",
    *,
    collapse_internal_whitespace: bool = False,
) -> str:
    """Normalize text-like payloads while rejecting bools and containers."""
    if value is None or isinstance(value, bool) or isinstance(value, CONTAINER_VALUE_TYPES):
        return default

    text = str(value).strip()
    if collapse_internal_whitespace:
        text = WHITESPACE_RE.sub(" ", text)
    return text or default


def _looks_like_placeholder_text(value) -> bool:
    """Reject schema placeholders such as `...` as meaningful contract content."""
    text = normalize_text_value(
        value,
        collapse_internal_whitespace=True,
    )
    if not text:
        return False

    compact = text.replace(" ", "")
    if compact and set(compact) <= {".", "…"}:
        return True

    return bool(PLACEHOLDER_PUNCTUATION_RE.fullmatch(text))


def normalize_contract_key_parts(value) -> tuple[str, ...]:
    """Split contract keys into lowercase parts across separators and camelCase."""
    if value is None or isinstance(value, bool) or isinstance(value, CONTAINER_VALUE_TYPES):
        return ()

    text = str(value)
    text = ACRONYM_BOUNDARY_RE.sub(r"\1 \2", text)
    text = CAMEL_CASE_BOUNDARY_RE.sub(" ", text)
    return tuple(part.casefold() for part in CONTRACT_KEY_PARTS_RE.findall(text))


def canonicalize_contract_dict_keys(
    value,
    alias_map: dict[tuple[str, ...], str],
    *,
    canonical_value_scorers: dict[str, Callable[[object], int | float]] | None = None,
) -> dict:
    """Map variant contract keys onto canonical names while preserving unknown fields."""
    value = coerce_mapping_candidate(value)
    if value is None:
        return {}

    canonicalized: dict = {}
    scorers = canonical_value_scorers or {}
    canonical_names = set(alias_map.values())
    for canonical_name in canonical_names:
        if canonical_name in value:
            canonicalized[canonical_name] = value[canonical_name]

    for key, item in value.items():
        canonical_name = alias_map.get(normalize_contract_key_parts(key))
        if canonical_name:
            if key == canonical_name:
                continue
            if canonical_name in canonicalized:
                scorer = scorers.get(canonical_name)
                if scorer is not None:
                    current_score = scorer(canonicalized[canonical_name])
                    candidate_score = scorer(item)
                    if candidate_score > current_score:
                        canonicalized[canonical_name] = item
                continue
            canonicalized[canonical_name] = item
            continue
        canonicalized.setdefault(key, item)

    return canonicalized


def coerce_mapping_candidate(value) -> dict | None:
    """Decode mapping-like iterables such as `dict_items` into plain dicts."""
    if isinstance(value, Mapping):
        return dict(value)
    if value is None or isinstance(value, (str, bytes, bytearray, bool)):
        return None
    try:
        return dict(value)
    except (TypeError, ValueError):
        return None


def normalize_gag_type(value, default: str = "in_joke") -> str:
    """Map free-form gag type payloads into the supported canonical set."""
    gag_type = normalize_text_value(
        value,
        default,
        collapse_internal_whitespace=True,
    ).lower()
    canonical = gag_type.replace("-", "_").replace(" ", "_")
    normalized = GAG_TYPE_ALIASES.get(canonical, canonical or default)
    return normalized if normalized in VALID_GAG_TYPES else default


def normalize_user_reaction(value, default: str = "neutral") -> str:
    """Map free-form reaction payloads into the canonical priority ordering."""
    reaction = normalize_text_value(
        value,
        default,
        collapse_internal_whitespace=True,
    ).lower()
    canonical = reaction.replace("-", "_").replace(" ", "_")
    normalized = REACTION_ALIASES.get(canonical, canonical)
    if normalized not in REACTION_PRIORITY:
        return default
    return normalized


def reaction_priority(value) -> int:
    """Return the ordering weight used when comparing recurring-element reactions."""
    return REACTION_PRIORITY.get(
        normalize_user_reaction(value, "neutral"),
        REACTION_PRIORITY["neutral"],
    )


def canonical_seed_key(value) -> str:
    """Build the normalized case-insensitive key used to compare gag seed text."""
    return normalize_text_value(
        value,
        collapse_internal_whitespace=True,
    ).casefold()


def finite_float(value, default: float = 0.0) -> float:
    """Coerce finite numeric payloads while rejecting bools and non-finite values."""
    if isinstance(value, bool):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return numeric if math.isfinite(numeric) else default


def finite_int(value, default: int = 0) -> int:
    """Coerce integers through the shared finite-number rules."""
    if isinstance(value, bool):
        return default
    try:
        numeric = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    if not math.isfinite(numeric):
        return default
    try:
        return int(numeric)
    except (TypeError, ValueError, OverflowError):
        return default


def bounded_float(value, lower: float, upper: float, default: float = 0.0) -> float:
    """Clamp a numeric payload into a closed range."""
    return max(lower, min(upper, finite_float(value, default)))


def _score_recurring_container_candidate(value) -> int:
    """Prefer containers that look like real recurring-element payloads."""
    if not isinstance(value, Mapping) and not is_non_mapping_container(value):
        return 0

    meaningful_entries = 0
    normalized_entries = 0
    wrapper_hits = 0
    strongest_count = 0
    best_reaction = 0
    seen_container_ids: set[int] = set()
    queue = deque([value])
    while queue:
        item = queue.popleft()
        if is_non_mapping_container(item):
            item_id = id(item)
            if item_id in seen_container_ids:
                continue
            seen_container_ids.add(item_id)
            queue.extend(item)
            continue

        if not isinstance(item, Mapping):
            continue

        item_id = id(item)
        if item_id in seen_container_ids:
            continue
        seen_container_ids.add(item_id)

        wrapper = canonicalize_contract_dict_keys(
            item,
            RECURRING_MINOR_ELEMENTS_WRAPPER_ALIASES,
        )
        nested_items = wrapper.get("items")
        if nested_items is not None and nested_items is not item:
            wrapper_hits += 1
            queue.append(nested_items)
            continue

        entry = normalize_recurring_minor_element(item)
        if entry is None:
            queue.extend(
                child
                for child in item.values()
                if isinstance(child, (Mapping, str, bytes, bytearray))
                or is_non_mapping_container(child)
            )
            continue

        normalized_entries += 1
        strongest_count = max(strongest_count, entry["count"])
        best_reaction = max(best_reaction, reaction_priority(entry["user_reaction"]))
        if (
            entry["count"] > 0
            or entry["importance"] < 1.0
            or reaction_priority(entry["user_reaction"]) > 0
            or entry["type"] != "in_joke"
        ):
            meaningful_entries += 1

    return (
        meaningful_entries * 1000
        + normalized_entries * 100
        + wrapper_hits * 10
        + strongest_count * 2
        + best_reaction
    )


RECURRING_MINOR_ELEMENTS_CANONICAL_SCORERS = {
    "recurring_minor_elements": _score_recurring_container_candidate,
}


def decode_json_container_candidate(value):
    """Decode a dict/list candidate from plain or prose-wrapped JSON text."""
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    elif not isinstance(value, str):
        return None

    seen_text_candidates: set[str] = set()
    text = value
    while True:
        text = strip_json_code_fences(text.strip()).lstrip("\ufeff").strip()
        if not text or text in seen_text_candidates:
            return None
        seen_text_candidates.add(text)

        if not (text.startswith(("{", "[", "\"")) or "{" in text or "[" in text):
            return None

        if text.startswith(("{", "[", "\"")):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(decoded, (dict, *SEQUENCE_CONTAINER_TYPES)):
                    return decoded
                if isinstance(decoded, str):
                    text = decoded
                    continue

        decoder = json.JSONDecoder()
        best_candidate = None
        fallback_candidate = None
        best_score = -1
        best_start = -1
        best_span = -1
        fallback_start = -1
        fallback_span = -1
        for start, char in enumerate(text):
            if char not in "{[":
                continue
            try:
                result, end = decoder.raw_decode(text, idx=start)
            except json.JSONDecodeError:
                continue
            span = end - start
            if (
                fallback_candidate is None
                or start > fallback_start
                or (start == fallback_start and span > fallback_span)
            ):
                fallback_candidate = result
                fallback_start = start
                fallback_span = span

            score = _score_recurring_container_candidate(result)
            if (
                score > best_score
                or (
                    score == best_score
                    and (start > best_start or (start == best_start and span > best_span))
                )
            ):
                best_candidate = result
                best_score = score
                best_start = start
                best_span = span

        if best_candidate is not None and best_score > 0:
            return best_candidate
        if fallback_candidate is not None:
            return fallback_candidate

        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(decoded, (dict, *SEQUENCE_CONTAINER_TYPES)):
            return decoded
        if isinstance(decoded, str):
            text = decoded
            continue
        return None


def coerce_recurring_minor_elements(value) -> list:
    """Coerce recurring-element payload wrappers and stringified containers into a list."""
    coerced: list = []
    seen_container_ids: set[int] = set()
    queue = deque([value])
    while queue:
        item = queue.popleft()

        if isinstance(item, (str, bytes, bytearray)):
            decoded = decode_json_container_candidate(item)
            if decoded is not None:
                queue.append(decoded)
            continue

        if is_non_mapping_container(item):
            item_id = id(item)
            if item_id in seen_container_ids:
                continue
            seen_container_ids.add(item_id)
            queue.extend(item)
            continue

        if not isinstance(item, Mapping):
            continue

        item_id = id(item)
        if item_id in seen_container_ids:
            continue
        seen_container_ids.add(item_id)

        wrapper = canonicalize_contract_dict_keys(
            item,
            RECURRING_MINOR_ELEMENTS_WRAPPER_ALIASES,
        )
        nested_items = wrapper.get("items")
        normalized_entry = normalize_recurring_minor_element(item)
        if nested_items is not None and nested_items is not item:
            if normalized_entry is not None:
                coerced.append(item)
            queue.append(nested_items)
            continue

        if normalized_entry is not None:
            coerced.append(item)
            continue

        queue.extend(
            child
            for child in item.values()
            if isinstance(child, (Mapping, str, bytes, bytearray))
            or is_non_mapping_container(child)
        )

    return coerced


def _snapshot_recurring_search_value(value, memo: dict[int, object] | None = None):
    """Snapshot wrapper-heavy payloads so one-shot iterators survive scoring."""
    if memo is None:
        memo = {}

    if isinstance(value, Mapping):
        value_id = id(value)
        if value_id in memo:
            return memo[value_id]
        copied: dict = {}
        memo[value_id] = copied
        for key, item in value.items():
            copied[key] = _snapshot_recurring_search_value(item, memo)
        return copied

    if is_non_mapping_container(value):
        value_id = id(value)
        if value_id in memo:
            return memo[value_id]
        copied: list = []
        memo[value_id] = copied
        copied.extend(_snapshot_recurring_search_value(item, memo) for item in value)
        return copied

    return value


def _extract_best_recurring_minor_elements_candidate(value):
    """Find the most plausible recurring-element container inside wrapper-heavy payloads."""
    value = _snapshot_recurring_search_value(value)
    best_candidate = None
    best_score = 0
    best_size = -1
    seen_container_ids: set[int] = set()
    seen_text_candidates: set[str] = set()
    queue = deque([value])
    while queue:
        item = queue.popleft()

        if isinstance(item, Mapping):
            item_id = id(item)
            if item_id in seen_container_ids:
                continue
            seen_container_ids.add(item_id)

            score = _score_recurring_container_candidate(item)
            size = len(item)
            if score > best_score or (score == best_score and size > best_size):
                best_candidate = item
                best_score = score
                best_size = size

            queue.extend(
                child
                for child in item.values()
                if isinstance(child, (Mapping, str, bytes, bytearray))
                or is_non_mapping_container(child)
            )
            continue

        if is_non_mapping_container(item):
            item_id = id(item)
            if item_id in seen_container_ids:
                continue
            seen_container_ids.add(item_id)

            mapping_candidate = coerce_mapping_candidate(item)
            if mapping_candidate is not None:
                queue.append(mapping_candidate)

            queue.extend(
                child
                for child in item
                if isinstance(child, (Mapping, str, bytes, bytearray))
                or is_non_mapping_container(child)
            )
            continue

        if isinstance(item, (str, bytes, bytearray)):
            text = item
            if isinstance(text, (bytes, bytearray)):
                text = text.decode("utf-8", errors="replace")
            if text in seen_text_candidates:
                continue
            seen_text_candidates.add(text)

            decoded = decode_json_container_candidate(item)
            if decoded is not None:
                queue.append(decoded)

    return best_candidate if best_score > 0 else None


def _extract_direct_recurring_minor_elements(value) -> list | None:
    """Fast-path direct recurring payloads before wrapper snapshot/search."""
    if isinstance(value, (str, bytes, bytearray)):
        decoded = decode_json_container_candidate(value)
        if decoded is None:
            return None
        return _extract_direct_recurring_minor_elements(decoded)

    if isinstance(value, Mapping):
        value = canonicalize_contract_dict_keys(
            value,
            RECURRING_MINOR_ELEMENTS_FIELD_ALIASES,
            canonical_value_scorers=RECURRING_MINOR_ELEMENTS_CANONICAL_SCORERS,
        )
        direct_recurring = value.get("recurring_minor_elements")
        if direct_recurring is not None:
            direct_entries = coerce_recurring_minor_elements(direct_recurring)
            if direct_entries:
                return direct_entries

        direct_entry = normalize_recurring_minor_element(value)
        if direct_entry is not None:
            return [direct_entry]
        return None

    if is_non_mapping_container(value):
        return coerce_recurring_minor_elements(value)

    return None


def extract_recurring_minor_elements(value) -> list:
    """Extract recurring-element payloads from an S2 result using contract aliases."""
    direct = _extract_direct_recurring_minor_elements(value)
    if direct is not None:
        return direct

    recurring = _extract_best_recurring_minor_elements_candidate(value)
    if recurring is None:
        recurring = canonicalize_contract_dict_keys(
            value,
            RECURRING_MINOR_ELEMENTS_FIELD_ALIASES,
            canonical_value_scorers=RECURRING_MINOR_ELEMENTS_CANONICAL_SCORERS,
        ).get("recurring_minor_elements", [])
    return coerce_recurring_minor_elements(recurring)


def normalize_recurring_minor_element(value) -> dict | None:
    """Normalize one recurring-element entry into the shared S2/gags contract."""
    value = canonicalize_contract_dict_keys(value, RECURRING_MINOR_ELEMENT_FIELD_ALIASES)
    if not value:
        return None

    content = normalize_text_value(
        value.get("content"),
        collapse_internal_whitespace=True,
    )
    if not content or _looks_like_placeholder_text(content):
        return None

    return {
        "content": content,
        "type": normalize_gag_type(value.get("type"), "in_joke"),
        "count": max(finite_int(value.get("count", 0)), 0),
        "importance": bounded_float(value.get("importance", 1.0), 0.0, 1.0, 1.0),
        "user_reaction": normalize_user_reaction(value.get("user_reaction"), "neutral"),
    }


def recurring_minor_element_key(value) -> tuple[str, str] | None:
    """Return the canonical dedupe key for a normalized recurring element entry."""
    if not isinstance(value, dict):
        return None

    content = normalize_text_value(
        value.get("content"),
        collapse_internal_whitespace=True,
    )
    if not content:
        return None

    gag_type = normalize_gag_type(value.get("type"), "in_joke")
    return (
        content.casefold(),
        gag_type.casefold(),
    )
