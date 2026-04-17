"""S2 Analyzer — Async metacognition module.

Runs after each S1 response. Produces structured JSON analysis.
See ARCHITECTURE_IA.md section 2.
"""

import asyncio
from collections import deque
from collections.abc import Mapping
import json
import logging
import math

from src.config import get_s2_prompt, MINIMAX_MODEL_FAST
from src.llm_client import AsyncLLMClient
from src.persona.engine import PersonaEngine
from src.persona.gag_contract import (
    bounded_float,
    canonicalize_contract_dict_keys,
    coerce_mapping_candidate,
    coerce_recurring_minor_elements,
    CONTAINER_VALUE_TYPES,
    is_non_mapping_collection,
    is_non_mapping_container,
    is_non_mapping_iterator,
    finite_float,
    finite_int,
    normalize_contract_key_parts,
    normalize_recurring_minor_element,
    normalize_text_value,
    recurring_minor_element_key,
    RECURRING_MINOR_ELEMENTS_CANONICAL_SCORERS,
    reaction_priority,
    strip_json_code_fences,
)
from src.persona.state import PERSONA_PHASES
from src.memory.episodic import EpisodicMemory
from src.memory.semantic import SemanticMemory

logger = logging.getLogger("delirium.s2")
S2_ANALYSIS_TIMEOUT_SECONDS = 30

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
    "recurring_minor_elements": [],
    "trigger_description": "routine",
    "recommended_H_delta": 0.0,
    "recommended_phase": None,
}
_DEFAULT_S2_RESULT_KEYS = frozenset(key.casefold() for key in DEFAULT_S2_RESULT)
_S2_RESULT_FIELD_ALIASES = {
    normalize_contract_key_parts(key): key
    for key in DEFAULT_S2_RESULT
}
_INTENTION_FIELD_ALIASES = {
    ("label",): "label",
    ("confidence",): "confidence",
}
_IPC_POSITION_FIELD_ALIASES = {
    ("agency",): "agency",
    ("communion",): "communion",
}
_CORRELATION_FIELD_ALIASES = {
    ("hypothesis",): "hypothesis",
    ("confidence",): "confidence",
}
_LIST_FIELDS = (
    "defensiveness_markers",
    "danger_signals",
    "themes_latents",
    "cold_weaver_topics",
)
_BOOLEAN_FIELDS = (
    "loop_detected",
    "axis_crossing",
)
_BOOLEAN_TRUE_STRINGS = {"1", "true", "yes", "on"}
_BOOLEAN_FALSE_STRINGS = {"0", "false", "no", "off", ""}
_RECOMMENDED_PHASE_ALIASES = {
    phase.casefold(): phase
    for phase in PERSONA_PHASES
}

def _default_s2_result() -> dict:
    """Return an isolated fallback payload for each analyzer call."""
    return {
        key: value.copy() if isinstance(value, (dict, list)) else value
        for key, value in DEFAULT_S2_RESULT.items()
    }


class S2Analyzer:
    """Runs S2 metacognition asynchronously after each S1 response."""

    def __init__(self, async_client: AsyncLLMClient, episodic: EpisodicMemory,
                 semantic: SemanticMemory, persona_engine: PersonaEngine):
        self.client = async_client
        self.episodic = episodic
        self.semantic = semantic
        self.persona_engine = persona_engine

    def _log_execution_safely(self, fragment_id: str, log_type: str, content: dict) -> bool:
        try:
            self.episodic.log_execution(fragment_id, log_type, content)
        except Exception as exc:
            logger.error("S2 execution logging failed for %s: %s", log_type, exc)
            return False
        return True

    async def analyze(self, fragment_id: str, user_message: str,
                      s1_response: str, session_messages: list[dict],
                      session_id: str):
        """Run S2 analysis and return the parsed result."""
        try:
            s2_prompt = get_s2_prompt()

            # Build conversation context for S2
            context = {
                "last_user_message": user_message,
                "last_s1_response": s1_response,
                "session_history": session_messages[-10:],  # last 10 exchanges
            }
            request_messages = [{
                "role": "user",
                "content": json.dumps(context, ensure_ascii=False),
            }]
        except Exception as exc:
            logger.error("S2 analysis failed before request: %s", exc)
            self._log_execution_safely(
                fragment_id, "s2_error", {"error": str(exc)}
            )
            return _default_s2_result()

        try:
            async with asyncio.timeout(S2_ANALYSIS_TIMEOUT_SECONDS):
                raw = await self.client.chat(
                    system=s2_prompt,
                    messages=request_messages,
                    model=MINIMAX_MODEL_FAST,
                )
        except TimeoutError:
            logger.error("S2 analysis timed out after %ss", S2_ANALYSIS_TIMEOUT_SECONDS)
            self._log_execution_safely(
                fragment_id,
                "s2_timeout",
                {"timeout_seconds": S2_ANALYSIS_TIMEOUT_SECONDS},
            )
            return _default_s2_result()
        except Exception as exc:
            logger.error("S2 analysis failed before parsing: %s", exc)
            self._log_execution_safely(
                fragment_id, "s2_error", {"error": str(exc)}
            )
            return _default_s2_result()

        try:
            s2_result = self._parse_s2_output(raw)
        except Exception as exc:
            logger.error("S2 parsing failed: %s", exc)
            self._log_execution_safely(
                fragment_id,
                "s2_parse_error",
                {"error": str(exc)},
            )
            return _default_s2_result()

        try:
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
        except Exception as exc:
            logger.error("S2 post-processing failed: %s", exc)
            self._log_execution_safely(
                fragment_id,
                "s2_postprocess_error",
                {"error": str(exc), "s2_result": s2_result},
            )
            return s2_result

        self._log_execution_safely(fragment_id, "s2_analysis", s2_result)

        logger.info(
            "S2 done: danger=%d, H_delta=%.2f, themes=%s",
            s2_result.get("danger_level", 0),
            s2_result.get("recommended_H_delta", 0),
            s2_result.get("themes_latents", []),
        )
        return s2_result

    def _parse_s2_output(self, raw) -> dict:
        """Parse S2 JSON output, with fallback to defaults."""
        predecoded_result = self._extract_predecoded_s2_result(raw)
        if predecoded_result is not None:
            return predecoded_result

        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8", errors="replace")
        elif raw is None:
            raw = ""
        elif not isinstance(raw, str):
            logger.warning("S2 output has unexpected type %s, using defaults", type(raw).__name__)
            return _default_s2_result()

        text = strip_json_code_fences(raw.strip()).lstrip("\ufeff").strip()

        if not text:
            logger.warning("S2 output is empty, using defaults")
            return _default_s2_result()

        decoded_result = self._decode_json_object(text)
        if decoded_result is None:
            logger.warning("S2 output is not valid JSON, using defaults")
            return _default_s2_result()

        direct_recurring_only = self._normalize_direct_recurring_only_s2_payload(decoded_result)
        if direct_recurring_only is not None:
            return direct_recurring_only

        result = self._extract_s2_payload(decoded_result)
        if result is None:
            logger.warning("S2 output must be a JSON object, using defaults")
            return _default_s2_result()

        return self._normalize_extracted_s2_result(result)

    def _extract_predecoded_s2_result(self, raw) -> dict | None:
        """Normalize plain predecoded payloads without cloning unless required."""
        if not isinstance(raw, Mapping) and not is_non_mapping_container(raw):
            return None

        attempted_top_level_direct_extract = False
        if (
            (isinstance(raw, Mapping) or is_non_mapping_collection(raw))
            and not self._has_top_level_one_shot_iterators(raw)
            and not self._has_nested_top_level_collection_iterators(raw)
        ):
            attempted_top_level_direct_extract = True
            direct_result = self._extract_top_level_predecoded_payload(raw)
            if direct_result is not None:
                return direct_result

        contains_one_shot_iterators = self._contains_one_shot_iterators(raw)
        if not contains_one_shot_iterators and not attempted_top_level_direct_extract:
            direct_result = self._extract_top_level_predecoded_payload(raw)
            if direct_result is not None:
                return direct_result

        if (
            (isinstance(raw, Mapping) or is_non_mapping_collection(raw))
            and not contains_one_shot_iterators
        ):
            result = self._extract_s2_payload(raw)
            if result is not None:
                return self._normalize_extracted_s2_result(result)
            recurring_only = self._normalize_recurring_only_s2_payload(raw)
            if recurring_only is not None:
                return recurring_only
            logger.warning("S2 output is not a usable JSON object, using defaults")
            return _default_s2_result()

        predecoded = self._snapshot_predecoded_payload(raw)
        if predecoded is None:
            return None

        result = self._extract_s2_payload(predecoded)
        if result is None:
            recurring_only = self._normalize_recurring_only_s2_payload(predecoded)
            if recurring_only is not None:
                return recurring_only
        if result is None:
            logger.warning("S2 output is not a usable JSON object, using defaults")
            return _default_s2_result()

        return self._normalize_extracted_s2_result(result)

    def _extract_top_level_predecoded_payload(self, raw) -> dict | None:
        """Short-circuit direct schema-shaped top-level payloads before BFS extraction."""
        raw_is_mapping = isinstance(raw, Mapping)
        direct_mapping = raw if raw_is_mapping else self._coerce_sequence_mapping_candidate(raw)
        if direct_mapping is not None:
            canonicalized = self._canonicalize_s2_result_mapping(direct_mapping)
            has_nested_container = self._has_unrecognized_nested_top_level_container(
                canonicalized,
                canonicalized=True,
            )
            normalized_mapping = self._normalize_schema_shaped_s2_mapping(
                canonicalized,
                canonicalized=True,
            )
            if normalized_mapping is not None:
                if has_nested_container:
                    return None
                return normalized_mapping

            if has_nested_container:
                return None

            recurring_only = self._normalize_direct_recurring_only_s2_payload(canonicalized)
            if recurring_only is not None:
                return recurring_only

            if raw_is_mapping:
                return None

        return self._normalize_direct_recurring_only_s2_payload(raw)

    def _has_top_level_one_shot_iterators(self, value) -> bool:
        """Check only the first wrapper layer before trying cheap top-level paths."""
        if isinstance(value, Mapping):
            return any(is_non_mapping_iterator(item) for item in value.values())

        if is_non_mapping_collection(value):
            return any(is_non_mapping_iterator(item) for item in value)

        return False

    def _has_nested_top_level_collection_iterators(self, value) -> bool:
        """Avoid direct probes that can consume iterators buried under one collection layer."""
        if not is_non_mapping_collection(value):
            return False

        return any(
            is_non_mapping_collection(item) and self._contains_one_shot_iterators(item)
            for item in value
        )

    def _has_unrecognized_nested_top_level_container(
        self,
        value: Mapping,
        *,
        canonicalized: bool = False,
    ) -> bool:
        """Defer to BFS when a sparse wrapper hides a richer report under unknown keys."""
        if not canonicalized:
            value = self._canonicalize_s2_result_mapping(value)

        for key, item in value.items():
            if key in DEFAULT_S2_RESULT:
                continue
            if (
                isinstance(item, Mapping)
                or is_non_mapping_container(item)
                or self._decode_embedded_json_candidate(item, set()) is not None
            ):
                return True
        return False

    def _contains_one_shot_iterators(self, value) -> bool:
        """Detect nested iterators that must be snapshotted before normalization."""
        seen_container_ids: set[int] = set()
        queue = deque([value])
        while queue:
            current = queue.popleft()
            if is_non_mapping_iterator(current):
                return True

            if isinstance(current, Mapping):
                current_id = id(current)
                if current_id in seen_container_ids:
                    continue
                seen_container_ids.add(current_id)
                queue.extend(
                    item
                    for item in current.values()
                    if isinstance(item, Mapping) or is_non_mapping_container(item)
                )
                continue

            if is_non_mapping_collection(current):
                current_id = id(current)
                if current_id in seen_container_ids:
                    continue
                seen_container_ids.add(current_id)
                queue.extend(
                    item
                    for item in current
                    if isinstance(item, Mapping) or is_non_mapping_container(item)
                )

        return False

    def _snapshot_predecoded_payload(
        self,
        value,
        memo: dict[int, tuple[object, object]] | None = None,
        *,
        top_level: bool = True,
    ):
        if memo is None:
            memo = {}

        if isinstance(value, Mapping):
            value_id = id(value)
            existing = memo.get(value_id)
            if existing is not None and existing[0] is value:
                return existing[1]

            snapshot: dict = {}
            memo[value_id] = (value, snapshot)
            for key, item in value.items():
                snapshot[key] = self._snapshot_predecoded_payload(
                    item,
                    memo,
                    top_level=False,
                )
            return snapshot

        if is_non_mapping_container(value):
            value_id = id(value)
            existing = memo.get(value_id)
            if existing is not None and existing[0] is value:
                return existing[1]

            snapshot: list = []
            memo[value_id] = (value, snapshot)
            for item in value:
                snapshot.append(
                    self._snapshot_predecoded_payload(
                        item,
                        memo,
                        top_level=False,
                    )
                )
            return snapshot

        mapping_candidate = coerce_mapping_candidate(value)
        if mapping_candidate is not None:
            return self._snapshot_predecoded_payload(
                mapping_candidate,
                memo,
                top_level=False,
            )

        return None if top_level else value

    def _canonicalize_s2_result_mapping(self, value: Mapping) -> dict:
        return canonicalize_contract_dict_keys(
            value,
            _S2_RESULT_FIELD_ALIASES,
            canonical_value_scorers=RECURRING_MINOR_ELEMENTS_CANONICAL_SCORERS,
        )

    def _normalize_extracted_s2_result(
        self,
        result: Mapping,
        *,
        canonicalized: bool = False,
    ) -> dict:
        return self._normalize_s2_result(
            result if canonicalized else self._canonicalize_s2_result_mapping(result),
            canonicalized=True,
        )

    def _decode_json_object(self, text: str) -> dict | list | None:
        if text.startswith(("{", "[", "\"")):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(decoded, dict) or is_non_mapping_collection(decoded):
                    return decoded
                if isinstance(decoded, str):
                    return self._decode_json_object(decoded)

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
            score = self._score_decoded_json_candidate(result)
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
        if isinstance(decoded, dict) or is_non_mapping_collection(decoded):
            return decoded
        if isinstance(decoded, str):
            return self._decode_json_object(decoded)
        return None

    def _score_decoded_json_candidate(self, value) -> int:
        if isinstance(value, Mapping):
            return self._score_decoded_json_object(value)

        if is_non_mapping_container(value):
            extracted = self._extract_s2_payload(value)
            if extracted is None:
                return 0
            return self._score_decoded_json_object(extracted)

        return 0

    def _extract_s2_payload(self, value) -> dict | None:
        best_object = None
        best_score = 0
        best_size = -1
        seen_container_ids: set[int] = set()
        seen_text_candidates: set[str] = set()
        queue = deque([value])
        while queue:
            current = queue.popleft()
            if isinstance(current, Mapping):
                current_id = id(current)
                if current_id in seen_container_ids:
                    continue
                seen_container_ids.add(current_id)
                score = self._score_decoded_json_object(current)
                size = len(current)
                if score > best_score or (score == best_score and size > best_size):
                    best_object = current
                    best_score = score
                    best_size = size
                queue.extend(
                    item
                    for item in current.values()
                    if isinstance(item, (Mapping, str, bytes, bytearray))
                    or is_non_mapping_container(item)
                )
                continue

            if is_non_mapping_container(current):
                current_id = id(current)
                if current_id in seen_container_ids:
                    continue
                seen_container_ids.add(current_id)
                mapping_candidate = self._coerce_sequence_mapping_candidate(current)
                if mapping_candidate is not None:
                    queue.append(mapping_candidate)
                    continue
                queue.extend(
                    item
                    for item in current
                    if isinstance(item, (Mapping, str, bytes, bytearray))
                    or is_non_mapping_container(item)
                )
                continue

            decoded = self._decode_embedded_json_candidate(current, seen_text_candidates)
            if decoded is not None:
                queue.append(decoded)

        return best_object if best_score > 0 else None

    def _coerce_sequence_mapping_candidate(self, value) -> dict | None:
        mapping_candidate = coerce_mapping_candidate(value)
        return (
            mapping_candidate
            if mapping_candidate is not None
            and self._score_decoded_json_object(mapping_candidate) > 0
            else None
        )

    def _decode_embedded_json_candidate(
        self,
        value,
        seen_text_candidates: set[str],
    ) -> dict | list | None:
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8", errors="replace")
        elif not isinstance(value, str):
            return None

        text = strip_json_code_fences(value.strip()).lstrip("\ufeff").strip()
        if not text or text in seen_text_candidates:
            return None
        if not (text.startswith(("{", "[")) or "{" in text or "[" in text):
            return None

        seen_text_candidates.add(text)
        return self._decode_json_object(text)

    def _score_decoded_json_object(
        self,
        value: Mapping,
        *,
        canonicalized: bool = False,
        normalized: Mapping | None = None,
    ) -> int:
        score, _normalized = self._score_schema_shaped_s2_mapping(
            value,
            canonicalized=canonicalized,
            normalized=normalized,
        )
        return score

    def _normalize_schema_shaped_s2_mapping(
        self,
        value: Mapping,
        *,
        canonicalized: bool = False,
    ) -> dict | None:
        score, normalized = self._score_schema_shaped_s2_mapping(
            value,
            canonicalized=canonicalized,
        )
        return normalized if score > 0 else None

    def _score_schema_shaped_s2_mapping(
        self,
        value: Mapping,
        *,
        canonicalized: bool = False,
        normalized: Mapping | None = None,
    ) -> tuple[int, dict | None]:
        if not isinstance(value, Mapping):
            return 0, None

        if not canonicalized:
            value = self._canonicalize_s2_result_mapping(value)
        recognized_keys = {
            str(key).casefold()
            for key in value
            if str(key).casefold() in _DEFAULT_S2_RESULT_KEYS
        }
        if not recognized_keys:
            return 0, None

        # Prefer objects that both match the S2 schema and retain non-default
        # information after normalization over schema examples or debug blobs.
        if normalized is None:
            normalized = self._normalize_s2_result(value, canonicalized=True)
        meaningful_fields = sum(
            1
            for key in DEFAULT_S2_RESULT
            if key.casefold() in recognized_keys and normalized[key] != DEFAULT_S2_RESULT[key]
        )
        # Prefer objects with actual normalized signal over larger schema-shaped
        # placeholders or wrappers that merely enumerate known keys.
        return meaningful_fields * 1000 + len(recognized_keys), normalized

    def _normalize_s2_result(self, result: Mapping, *, canonicalized: bool = False) -> dict:
        if not canonicalized:
            result = canonicalize_contract_dict_keys(result, _S2_RESULT_FIELD_ALIASES)
        normalized = _default_s2_result()
        for field in DEFAULT_S2_RESULT:
            if field in result:
                normalized[field] = result[field]

        intention = canonicalize_contract_dict_keys(
            self._decode_embedded_json_value(normalized.get("intention")),
            _INTENTION_FIELD_ALIASES,
        )
        normalized["intention"] = {
            "label": self._normalize_text_field(intention.get("label"), "unknown"),
            "confidence": bounded_float(intention.get("confidence", 0.0), 0.0, 1.0),
        }

        normalized["defensiveness_score"] = bounded_float(
            normalized.get("defensiveness_score", 0.0), 0.0, 1.0
        )
        normalized["danger_level"] = max(
            0,
            min(3, finite_int(normalized.get("danger_level", 0))),
        )
        normalized["loop_count"] = max(finite_int(normalized.get("loop_count", 0)), 0)
        normalized["sycophancy_risk"] = bounded_float(
            normalized.get("sycophancy_risk", 0.0), 0.0, 1.0
        )
        normalized["fanfaronade_score"] = bounded_float(
            normalized.get("fanfaronade_score", 0.0), 0.0, 1.0
        )
        normalized["recommended_H_delta"] = bounded_float(
            normalized.get("recommended_H_delta", 0.0), -0.5, 0.5
        )
        normalized["trigger_description"] = self._normalize_text_field(
            normalized.get("trigger_description", "routine"),
            "routine",
        )

        for field in _LIST_FIELDS:
            normalized[field] = self._normalize_text_list_field(normalized.get(field))

        for field in _BOOLEAN_FIELDS:
            normalized[field] = self._coerce_bool(
                normalized.get(field, DEFAULT_S2_RESULT[field]),
                DEFAULT_S2_RESULT[field],
            )

        ipc = canonicalize_contract_dict_keys(
            self._decode_embedded_json_value(normalized.get("ipc_position")),
            _IPC_POSITION_FIELD_ALIASES,
        )
        normalized["ipc_position"] = {
            "agency": finite_float(ipc.get("agency", 0.0)),
            "communion": finite_float(ipc.get("communion", 0.0)),
        }

        normalized["correlation"] = self._normalize_correlation(normalized.get("correlation"))
        normalized["loop_theme"] = self._normalize_optional_text_field(
            normalized.get("loop_theme")
        )
        normalized["recommended_phase"] = self._normalize_recommended_phase(
            normalized.get("recommended_phase")
        )
        normalized["recurring_minor_elements"] = self._normalize_recurring_minor_elements(
            normalized.get("recurring_minor_elements")
        )

        return normalized

    def _normalize_recurring_minor_elements(self, value) -> list[dict]:
        direct_collection = self._normalize_direct_recurring_collection(value)
        if direct_collection is not None:
            return direct_collection

        normalized = []
        seen: dict[tuple[str, str], dict] = {}
        seen_container_ids: set[int] = set()
        queue = deque(coerce_recurring_minor_elements(value))
        while queue:
            item = queue.popleft()

            if is_non_mapping_container(item):
                item_id = id(item)
                if item_id in seen_container_ids:
                    continue
                seen_container_ids.add(item_id)
                queue.extend(item)
                continue

            if isinstance(item, (str, bytes, bytearray)):
                queue.extend(coerce_recurring_minor_elements(item))
                continue

            if isinstance(item, Mapping):
                item_id = id(item)
                if item_id in seen_container_ids:
                    continue
                seen_container_ids.add(item_id)
                coerced_items = coerce_recurring_minor_elements(item)
                if coerced_items:
                    nested_items = [
                        candidate for candidate in coerced_items
                        if candidate is not item
                    ]
                    if nested_items:
                        queue.extend(nested_items)

            entry = normalize_recurring_minor_element(item)
            if entry is None:
                continue
            key = recurring_minor_element_key(entry)
            if key is None:
                continue
            if key in seen:
                existing = seen[key]
                existing["count"] = max(existing["count"], entry["count"])
                existing["importance"] = min(existing["importance"], entry["importance"])
                if reaction_priority(entry["user_reaction"]) > reaction_priority(
                    existing["user_reaction"]
                ):
                    existing["user_reaction"] = entry["user_reaction"]
                continue
            seen[key] = entry
            normalized.append(entry)
        return self._sort_normalized_recurring_minor_elements(normalized)

    def _sort_normalized_recurring_minor_elements(self, normalized: list[dict]) -> list[dict]:
        return sorted(
            normalized,
            key=lambda entry: (
                -entry["count"],
                entry["importance"],
                -reaction_priority(entry["user_reaction"]),
                entry["type"].casefold(),
                entry["content"].casefold(),
            ),
        )

    def _normalize_direct_recurring_collection(self, value) -> list[dict] | None:
        if not is_non_mapping_collection(value):
            return None

        normalized = []
        seen: dict[tuple[str, str], dict] = {}
        saw_item = False
        for item in value:
            saw_item = True
            entry = normalize_recurring_minor_element(item)
            if entry is None:
                return None
            key = recurring_minor_element_key(entry)
            if key is None:
                return None
            if key in seen:
                existing = seen[key]
                existing["count"] = max(existing["count"], entry["count"])
                existing["importance"] = min(existing["importance"], entry["importance"])
                if reaction_priority(entry["user_reaction"]) > reaction_priority(
                    existing["user_reaction"]
                ):
                    existing["user_reaction"] = entry["user_reaction"]
                continue
            seen[key] = entry
            normalized.append(entry)

        if not saw_item:
            return None

        return self._sort_normalized_recurring_minor_elements(normalized)

    def _normalize_direct_recurring_only_s2_payload(self, value) -> dict | None:
        """Recover wrapperless top-level recurring payloads without BFS extraction."""
        direct_entry = normalize_recurring_minor_element(value)
        if direct_entry is not None:
            normalized = _default_s2_result()
            normalized["recurring_minor_elements"] = [direct_entry]
            return normalized

        direct_recurring = self._normalize_direct_recurring_collection(value)
        if direct_recurring is None:
            return None

        normalized = _default_s2_result()
        normalized["recurring_minor_elements"] = direct_recurring
        return normalized

    def _normalize_recurring_only_s2_payload(self, value) -> dict | None:
        """Recover top-level recurring-only payloads into the full S2 schema."""
        recurring = self._normalize_recurring_minor_elements(value)
        if not recurring:
            return None

        normalized = _default_s2_result()
        normalized["recurring_minor_elements"] = recurring
        return normalized

    def _normalize_text_list_field(self, value) -> list[str]:
        value = self._decode_embedded_json_value(value)
        if not is_non_mapping_container(value):
            return []

        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            text = self._normalize_optional_text_field(
                item,
                collapse_internal_whitespace=True,
            )
            if not text:
                continue
            key = text.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(text)
        return normalized

    def _normalize_correlation(self, value) -> dict | None:
        value = self._decode_embedded_json_value(value)
        value = canonicalize_contract_dict_keys(value, _CORRELATION_FIELD_ALIASES)
        if not value:
            return None

        hypothesis = self._normalize_optional_text_field(
            value.get("hypothesis"),
            collapse_internal_whitespace=True,
        )
        if not hypothesis:
            return None

        return {
            "hypothesis": hypothesis,
            "confidence": bounded_float(value.get("confidence", 0.0), 0.0, 1.0),
        }

    def _normalize_text_field(
        self, value, default: str = "", *, collapse_internal_whitespace: bool = False
    ) -> str:
        return normalize_text_value(
            value,
            default,
            collapse_internal_whitespace=collapse_internal_whitespace,
        )

    def _normalize_optional_text_field(
        self, value, *, collapse_internal_whitespace: bool = False
    ) -> str | None:
        text = self._normalize_text_field(
            value,
            "",
            collapse_internal_whitespace=collapse_internal_whitespace,
        )
        return text or None

    def _normalize_recommended_phase(self, value) -> str | None:
        phase = self._normalize_optional_text_field(value)
        if not phase:
            return None
        return _RECOMMENDED_PHASE_ALIASES.get(phase.casefold())

    def _decode_embedded_json_value(self, value):
        decoded = self._decode_embedded_json_candidate(value, set())
        return decoded if decoded is not None else value

    def _coerce_bool(self, value, default: bool = False) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        if isinstance(value, CONTAINER_VALUE_TYPES):
            return default
        if isinstance(value, (int, float)):
            if not math.isfinite(value):
                return default
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in _BOOLEAN_TRUE_STRINGS:
                return True
            if lowered in _BOOLEAN_FALSE_STRINGS:
                return False
            if lowered in {"none", "null"}:
                return default
            try:
                numeric = float(lowered)
            except (TypeError, ValueError, OverflowError):
                return default
            if not math.isfinite(numeric):
                return default
            return bool(numeric)
        return default
