import asyncio
from collections import deque
import json
from types import MappingProxyType

from src.persona.state import PersonaState
import src.s2.analyzer as analyzer_module
from src.s2.analyzer import DEFAULT_S2_RESULT, S2_ANALYSIS_TIMEOUT_SECONDS, S2Analyzer


class StubAsyncClient:
    def __init__(self, response="", exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    async def chat(self, system: str, messages: list[dict], model: str | None = None) -> str:
        self.calls.append({
            "system": system,
            "messages": messages,
            "model": model,
        })
        if self.exc is not None:
            raise self.exc
        return self.response


class StubSemanticMemory:
    def __init__(self):
        self.updated = []

    def update_from_s2(self, fragment_id: str, s2_result: dict):
        self.updated.append((fragment_id, s2_result))


class StubEpisodicMemory:
    def __init__(self):
        self.saved_states = []
        self.logs = []

    def get_session_message_count(self, session_id: str) -> int:
        return 4

    def get_total_sessions(self) -> int:
        return 2

    def save_persona_state(self, state):
        self.saved_states.append(state)

    def log_execution(self, fragment_id: str, log_type: str, content: dict):
        self.logs.append((fragment_id, log_type, content))


class StubPersonaEngine:
    def __init__(self):
        self.transitions = []

    def transition(self, s2_result: dict, time_ctx: dict):
        self.transitions.append((s2_result, time_ctx))
        return PersonaState()


def make_analyzer(response: str = ""):
    client = StubAsyncClient(response=response)
    episodic = StubEpisodicMemory()
    semantic = StubSemanticMemory()
    persona = StubPersonaEngine()
    return S2Analyzer(client, episodic, semantic, persona), client, episodic, semantic, persona


def test_parse_s2_output_accepts_valid_json_and_normalizes_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        """```json
        {
          "intention": {"label": "testing", "confidence": 0.8},
          "danger_level": 9,
          "themes_latents": ["obsession"],
          "recurring_minor_elements": [
            {
              "content": "le tournevis mystique",
              "count": 2,
              "importance": 0.2,
              "user_reaction": "amused"
            }
          ]
        }
        ```"""
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 3
    assert parsed["themes_latents"] == ["obsession"]
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "le tournevis mystique",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_accepts_predecoded_dict_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "danger_level": 2,
            "recurring_minor_elements": [
                {
                    "content": "la tasse metronome",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            ],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_uses_direct_extract_for_plain_predecoded_payloads(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_snapshot(value, memo=None, *, top_level=True):
        raise AssertionError("plain dict payloads should bypass snapshot cloning")

    monkeypatch.setattr(analyzer, "_snapshot_predecoded_payload", fail_snapshot)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "danger_level": 2,
            "recurring_minor_elements": [
                {
                    "content": "la tasse metronome",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            ],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_short_circuits_top_level_predecoded_mapping(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("schema-shaped top-level mappings should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "danger_level": 2,
            "recurring_minor_elements": [],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []


def test_parse_s2_output_short_circuits_iterator_scan_for_top_level_predecoded_mapping(
    monkeypatch,
):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_contains(_value):
        raise AssertionError("schema-shaped top-level mappings should bypass iterator scans")

    monkeypatch.setattr(analyzer, "_contains_one_shot_iterators", fail_contains)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "danger_level": 2,
            "recurring_minor_elements": [],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []


def test_parse_s2_output_reuses_top_level_s2_canonicalization(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()
    original_canonicalize = analyzer_module.canonicalize_contract_dict_keys
    top_level_calls = 0

    def count_canonicalize(value, alias_map, **kwargs):
        nonlocal top_level_calls
        if alias_map is analyzer_module._S2_RESULT_FIELD_ALIASES:
            top_level_calls += 1
        return original_canonicalize(value, alias_map, **kwargs)

    monkeypatch.setattr(analyzer_module, "canonicalize_contract_dict_keys", count_canonicalize)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "dangerLevel": 2,
            "recurringMinorElements": [],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []
    assert top_level_calls == 1


def test_parse_s2_output_reuses_top_level_s2_normalization(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()
    original_normalize = analyzer._normalize_s2_result
    normalize_calls = 0

    def count_normalize(value, *, canonicalized=False):
        nonlocal normalize_calls
        normalize_calls += 1
        return original_normalize(value, canonicalized=canonicalized)

    monkeypatch.setattr(analyzer, "_normalize_s2_result", count_normalize)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "dangerLevel": 2,
            "recurringMinorElements": [],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []
    assert normalize_calls == 1


def test_parse_s2_output_short_circuits_top_level_mapping_view(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("schema-shaped mapping views should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    payload = {
        "intention": {"label": "testing", "confidence": 0.8},
        "dangerLevel": 2,
        "recurringMinorElements": [],
    }

    parsed = analyzer._parse_s2_output(payload.items())

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []


def test_parse_s2_output_recovers_nested_top_level_collection_wrapping_generator_pairs():
    analyzer, _, _, _, _ = make_analyzer()

    def pair_generator():
        yield ("intention", {"label": "repair", "confidence": 0.6})
        yield ("dangerLevel", 2)
        yield ("themes_latents", ["probe"])
        yield ("recurringMinorElements", [])

    parsed = analyzer._parse_s2_output([[pair_generator()]])

    assert parsed["intention"] == {"label": "repair", "confidence": 0.6}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["probe"]
    assert parsed["recurring_minor_elements"] == []


def test_parse_s2_output_short_circuits_top_level_raw_recurring_entry(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("raw recurring entries should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    parsed = analyzer._parse_s2_output(
        {
            "content": "la tasse metronome",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_short_circuits_top_level_raw_recurring_mapping_view(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("raw recurring mapping views should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    parsed = analyzer._parse_s2_output(
        {
            "content": "la tasse metronome",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }.items()
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_short_circuits_top_level_raw_recurring_list(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("raw recurring lists should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    parsed = analyzer._parse_s2_output(
        [
            {
                "content": "la tasse metronome",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            }
        ]
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_short_circuits_iterator_scan_for_top_level_raw_recurring_list(
    monkeypatch,
):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_contains(_value):
        raise AssertionError("wrapperless recurring lists should bypass iterator scans")

    monkeypatch.setattr(analyzer, "_contains_one_shot_iterators", fail_contains)

    parsed = analyzer._parse_s2_output(
        [
            {
                "content": "la tasse metronome",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            }
        ]
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_short_circuits_top_level_raw_recurring_list_without_generic_rewalk(
    monkeypatch,
):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("raw recurring lists should bypass BFS extraction")

    def fail_rewalk(_value):
        raise AssertionError("raw recurring lists should not re-enter the generic normalizer")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)
    monkeypatch.setattr(analyzer, "_normalize_recurring_minor_elements", fail_rewalk)

    parsed = analyzer._parse_s2_output(
        [
            {
                "content": "la tasse metronome",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
            {
                "content": "la tasse metronome",
                "count": 5,
                "importance": 0.1,
                "user_reaction": "callback",
            },
        ]
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 5,
            "importance": 0.1,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_short_circuits_stringified_raw_recurring_list(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_extract(_value):
        raise AssertionError("stringified raw recurring lists should bypass BFS extraction")

    monkeypatch.setattr(analyzer, "_extract_s2_payload", fail_extract)

    parsed = analyzer._parse_s2_output(
        json.dumps(
            [
                {
                    "content": "la tasse metronome",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            ]
        )
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_normalize_recurring_minor_elements_short_circuits_direct_collection(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    def fail_coerce(_value):
        raise AssertionError("direct recurring collections should bypass generic coercion")

    monkeypatch.setattr("src.s2.analyzer.coerce_recurring_minor_elements", fail_coerce)

    normalized = analyzer._normalize_recurring_minor_elements(
        [
            {
                "content": "la tasse metronome",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
            {
                "content": "la tasse metronome",
                "count": 5,
                "importance": 0.1,
                "user_reaction": "callback",
            },
        ]
    )

    assert normalized == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 5,
            "importance": 0.1,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_normalizes_top_level_predecoded_mapping_once(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    original_normalize = analyzer._normalize_s2_result
    normalize_calls = 0

    def track_normalize(result, *, canonicalized=False):
        nonlocal normalize_calls
        normalize_calls += 1
        return original_normalize(result, canonicalized=canonicalized)

    monkeypatch.setattr(analyzer, "_normalize_s2_result", track_normalize)

    parsed = analyzer._parse_s2_output(
        {
            "intention": {"label": "testing", "confidence": 0.8},
            "danger_level": 2,
            "recurring_minor_elements": [],
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []
    assert normalize_calls == 1


def test_parse_s2_output_attempts_safe_top_level_predecoded_probe_once(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    original_direct_extract = analyzer._extract_top_level_predecoded_payload
    original_extract_payload = analyzer._extract_s2_payload
    original_normalize_recurring_only = analyzer._normalize_recurring_only_s2_payload
    direct_extract_calls = 0
    extract_payload_calls = 0
    recurring_only_calls = 0
    snapshot_calls = 0

    def track_direct_extract(value):
        nonlocal direct_extract_calls
        direct_extract_calls += 1
        return original_direct_extract(value)

    def track_extract_payload(value):
        nonlocal extract_payload_calls
        extract_payload_calls += 1
        return original_extract_payload(value)

    def track_recurring_only(value):
        nonlocal recurring_only_calls
        recurring_only_calls += 1
        return original_normalize_recurring_only(value)

    def fail_snapshot(_value):
        nonlocal snapshot_calls
        snapshot_calls += 1
        raise AssertionError("safe predecoded payload should not be snapshotted")

    monkeypatch.setattr(analyzer, "_extract_top_level_predecoded_payload", track_direct_extract)
    monkeypatch.setattr(analyzer, "_extract_s2_payload", track_extract_payload)
    monkeypatch.setattr(analyzer, "_normalize_recurring_only_s2_payload", track_recurring_only)
    monkeypatch.setattr(analyzer, "_snapshot_predecoded_payload", fail_snapshot)

    assert analyzer._parse_s2_output({"debug": "ignore me"}) == DEFAULT_S2_RESULT
    assert direct_extract_calls == 1
    assert extract_payload_calls == 1
    assert recurring_only_calls == 1
    assert snapshot_calls == 0


def test_parse_s2_output_skips_top_level_recurring_probe_for_sparse_nested_wrapper(monkeypatch):
    analyzer, _, _, _, _ = make_analyzer()

    original_direct = analyzer._normalize_direct_recurring_only_s2_payload
    direct_calls = 0

    def track_direct(value):
        nonlocal direct_calls
        direct_calls += 1
        return original_direct(value)

    monkeypatch.setattr(analyzer, "_normalize_direct_recurring_only_s2_payload", track_direct)

    parsed = analyzer._parse_s2_output(
        {
            "metadata": {"source": "model"},
            "analysis": {
                "intention": {"label": "repair", "confidence": 0.7},
                "danger_level": 2,
                "themes_latents": ["wrapper recovery"],
                "recurring_minor_elements": [],
            },
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["wrapper recovery"]
    assert direct_calls == 0


def test_parse_s2_output_accepts_mapping_proxy_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        MappingProxyType(
            {
                "intention": MappingProxyType({"label": "testing", "confidence": 0.8}),
                "dangerLevel": 2,
                "recurringMinorElements": [
                    MappingProxyType(
                        {
                            "content": "la tasse metronome",
                            "count": 2,
                            "importance": 0.2,
                            "userReaction": "engaged",
                        }
                    )
                ],
            }
        )
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_accepts_predecoded_mapping_view_payload():
    analyzer, _, _, _, _ = make_analyzer()

    payload = {
        "intention": {"label": "testing", "confidence": 0.8},
        "dangerLevel": 2,
        "recurringMinorElements": [
            {
                "content": "la tasse metronome",
                "count": 2,
                "importance": 0.2,
                "userReaction": "engaged",
            }
        ],
    }

    parsed = analyzer._parse_s2_output(payload.items())

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_extracts_nested_mapping_view_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "wrapper": {
                "intention": {"label": "testing", "confidence": 0.8},
                "dangerLevel": 2,
                "recurringMinorElements": [],
            }.items()
        }
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == []


def test_parse_s2_output_accepts_mapping_backed_recurring_minor_elements_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 2,
            "recurring_minor_elements": {
                "alpha": {
                    "content": "la tasse metronome",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            },
        }
    )

    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_accepts_mapping_values_view_recurring_minor_elements_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 2,
            "recurring_minor_elements": {
                "alpha": {
                    "content": "la tasse metronome",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            }.values(),
        }
    )

    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_accepts_double_encoded_top_level_json_report():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            json.dumps(
                {
                    "intention": {"label": "testing", "confidence": 0.8},
                    "danger_level": 2,
                    "themes_latents": ["double encoded"],
                    "recurring_minor_elements": [],
                }
            )
        )
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["double encoded"]


def test_parse_s2_output_recovers_json_object_wrapped_in_extra_prose():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        """Analyse interne:

        {
          "intention": {"label": "repair", "confidence": 0.6},
          "danger_level": 1,
          "recurring_minor_elements": []
        }

        Fin du rapport."""
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.6}
    assert parsed["danger_level"] == 1


def test_parse_s2_output_prefers_the_most_s2_shaped_json_object_from_prose():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        """Example d'objet invalide a ignorer:
        {"note": "pas le vrai rapport", "debug": true}

        Rapport final:
        {
          "intention": {"label": "repair", "confidence": 0.7},
          "danger_level": 2,
          "themes_latents": ["pattern drift"],
          "recurring_minor_elements": []
        }
        """
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["pattern drift"]


def test_parse_s2_output_prefers_populated_report_over_schema_like_placeholder_object():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        """Schema example:
        {
          "intention": "object",
          "danger_level": "integer",
          "themes_latents": "array",
          "recurring_minor_elements": "array"
        }

        Actual report:
        {
          "intention": {"label": "repair", "confidence": 0.9},
          "danger_level": 1,
          "themes_latents": ["contract drift"],
          "recurring_minor_elements": []
        }
        """
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.9}
    assert parsed["danger_level"] == 1
    assert parsed["themes_latents"] == ["contract drift"]


def test_parse_s2_output_accepts_single_line_fenced_json():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        '```json {"danger_level": 2, "recurring_minor_elements": []} ```'
    )

    assert parsed["danger_level"] == 2


def test_parse_s2_output_strips_utf8_bom_before_decoding():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        '\ufeff{"danger_level": 1, "themes_latents": ["repair"]}'
    )

    assert parsed["danger_level"] == 1
    assert parsed["themes_latents"] == ["repair"]


def test_parse_s2_output_extracts_nested_report_object_from_json_wrapper():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "analysis": {
                    "intention": {"label": "repair", "confidence": 0.7},
                    "danger_level": 2,
                    "themes_latents": ["wrapper recovery"],
                    "recurring_minor_elements": [],
                },
                "metadata": {"source": "model"},
            }
        )
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["wrapper recovery"]


def test_parse_s2_output_extracts_report_from_tuple_wrapped_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "candidates": (
                {
                    "intention": {"label": "repair", "confidence": 0.7},
                    "danger_level": 2,
                    "themes_latents": ("tuple wrapper",),
                    "recurring_minor_elements": (
                        {
                            "content": "la clef ceremonielle",
                            "count": 2,
                            "importance": 0.2,
                            "user_reaction": "engaged",
                        },
                    ),
                },
            ),
            "metadata": {"source": "tuple"},
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["tuple wrapper"]
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la clef ceremonielle",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_extracts_report_from_deque_wrapped_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "candidates": deque([
                {
                    "intention": {"label": "repair", "confidence": 0.7},
                    "danger_level": 2,
                    "themes_latents": ["deque wrapper"],
                    "recurring_minor_elements": [
                        {
                            "content": "la clef ceremonielle",
                            "count": 2,
                            "importance": 0.2,
                            "user_reaction": "engaged",
                        },
                    ],
                },
            ]),
            "metadata": {"source": "deque"},
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["deque wrapper"]
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la clef ceremonielle",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_extracts_report_from_values_view_wrapped_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "candidates": {
                "primary": {
                    "intention": {"label": "repair", "confidence": 0.7},
                    "danger_level": 2,
                    "themes_latents": ["values view"],
                    "recurring_minor_elements": [],
                },
            }.values(),
            "metadata": {"source": "values"},
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["values view"]


def test_parse_s2_output_prefers_nested_report_over_sparse_predecoded_wrapper():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 1,
            "analysis": {
                "intention": {"label": "repair", "confidence": 0.75},
                "danger_level": 2,
                "themes_latents": ["nested wins"],
                "recurring_minor_elements": [],
            },
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.75}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["nested wins"]


def test_parse_s2_output_prefers_embedded_json_report_over_sparse_predecoded_wrapper():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 1,
            "analysis": json.dumps(
                {
                    "intention": {"label": "repair", "confidence": 0.8},
                    "danger_level": 2,
                    "themes_latents": ["embedded nested wins"],
                    "recurring_minor_elements": [],
                }
            ),
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["embedded nested wins"]


def test_parse_s2_output_extracts_report_from_generator_wrapped_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        (
            item for item in [
                {
                    "intention": {"label": "repair", "confidence": 0.7},
                    "danger_level": 2,
                    "themes_latents": ["generator wrapper"],
                    "recurring_minor_elements": [],
                },
            ]
        )
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.7}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["generator wrapper"]


def test_parse_s2_output_accepts_generator_backed_recurring_minor_elements_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 2,
            "recurring_minor_elements": (
                item for item in [
                    {
                        "content": "la tasse metronome",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "engaged",
                    },
                ]
            ),
        }
    )

    assert parsed["danger_level"] == 2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse metronome",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_successive_calls_keep_candidate_tracking_local():
    analyzer, _, _, _, _ = make_analyzer()

    first = analyzer._parse_s2_output(
        {
            "analysis": """```json
            {
              "intention": {"label": "first", "confidence": 0.55},
              "danger_level": 1,
              "themes_latents": ["first pass"],
              "recurring_minor_elements": []
            }
            ```"""
        }
    )
    second = analyzer._parse_s2_output(
        {
            "analysis": """```json
            {
              "intention": {"label": "second", "confidence": 0.85},
              "danger_level": 2,
              "themes_latents": ["second pass"],
              "recurring_minor_elements": []
            }
            ```"""
        }
    )

    assert first["intention"] == {"label": "first", "confidence": 0.55}
    assert second["intention"] == {"label": "second", "confidence": 0.85}
    assert second["danger_level"] == 2
    assert second["themes_latents"] == ["second pass"]


def test_parse_s2_output_prefers_nested_report_over_shallow_wrapper_with_schema_key():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "danger_level": 0,
                "analysis": {
                    "intention": {"label": "repair", "confidence": 0.75},
                    "danger_level": 2,
                    "themes_latents": ["nested wins"],
                    "recurring_minor_elements": [],
                },
            }
        )
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.75}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["nested wins"]


def test_parse_s2_output_extracts_report_object_from_nested_json_string_wrapper():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "analysis": """```json
            {
              "intention": {"label": "repair", "confidence": 0.65},
              "dangerLevel": 2,
              "themes_latents": ["string wrapper recovery"],
              "recurringMinorElements": []
            }
            ```""",
            "metadata": {"source": "tool-wrapper"},
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.65}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["string wrapper recovery"]


def test_parse_s2_output_decodes_embedded_json_strings_for_object_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "intention": '{"label": "repair", "confidence": 0.65}',
                "ipc_position": '```json {"agency": 0.4, "communion": 0.6} ```',
                "correlation": '{"hypothesis": "ritual loop", "confidence": 0.7}',
                "recurring_minor_elements": [],
            }
        )
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.65}
    assert parsed["ipc_position"] == {"agency": 0.4, "communion": 0.6}
    assert parsed["correlation"] == {
        "hypothesis": "ritual loop",
        "confidence": 0.7,
    }


def test_parse_s2_output_decodes_embedded_json_strings_for_list_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "themes_latents": '["pattern drift", "pattern drift", "repair"]',
                "danger_signals": '```json ["mirror pressure", "mirror pressure"] ```',
                "cold_weaver_topics": '["ritual callback"]',
                "recurring_minor_elements": [],
            }
        )
    )

    assert parsed["themes_latents"] == ["pattern drift", "repair"]
    assert parsed["danger_signals"] == ["mirror pressure"]
    assert parsed["cold_weaver_topics"] == ["ritual callback"]


def test_parse_s2_output_prefers_populated_nested_string_report_over_schema_placeholder():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "analysis": """{
              "intention": "object",
              "danger_level": "integer",
              "themes_latents": "array",
              "recurring_minor_elements": "array"
            }""",
            "final_report": """{
              "intention": {"label": "repair", "confidence": 0.9},
              "dangerLevel": 1,
              "themes_latents": ["placeholder bypass"],
              "recurringMinorElements": []
            }""",
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.9}
    assert parsed["danger_level"] == 1
    assert parsed["themes_latents"] == ["placeholder bypass"]


def test_parse_s2_output_prefers_meaningful_nested_report_over_full_schema_placeholder():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "analysis_schema": {
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
            },
            "report": {
                "intention": {"label": "repair", "confidence": 0.55},
                "danger_level": 1,
                "themes_latents": ["nested signal wins"],
                "recurring_minor_elements": [],
            },
        }
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.55}
    assert parsed["danger_level"] == 1
    assert parsed["themes_latents"] == ["nested signal wins"]


def test_parse_s2_output_extracts_report_object_from_top_level_json_list():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            [
                {"note": "schema example"},
                {
                    "intention": {"label": "repair", "confidence": 0.6},
                    "danger_level": 1,
                    "recurring_minor_elements": [],
                },
            ]
        )
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.6}
    assert parsed["danger_level"] == 1


def test_parse_s2_output_extracts_report_object_from_prose_wrapped_json_list():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        """Rapport interne:

        [
          {"note": "schema example"},
          {
            "intention": {"label": "repair", "confidence": 0.62},
            "danger_level": 2,
            "themes_latents": ["list wrapper recovery"],
            "recurring_minor_elements": []
          }
        ]

        Fin."""
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.62}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["list wrapper recovery"]


def test_parse_s2_output_extracts_report_from_top_level_collection_view_wrapper():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "debug": {"note": "ignore this"},
            "report": {
                "intention": {"label": "repair", "confidence": 0.72},
                "danger_level": 2,
                "themes_latents": {
                    "alpha": "pattern drift",
                    "beta": "pattern drift",
                    "gamma": "repair",
                }.values(),
                "danger_signals": deque([
                    "mirror pressure",
                    "mirror pressure",
                    "rupture",
                ]),
                "cold_weaver_topics": deque(["ritual callback"]),
                "recurring_minor_elements": [],
            },
        }.values()
    )

    assert parsed["intention"] == {"label": "repair", "confidence": 0.72}
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["pattern drift", "repair"]
    assert parsed["danger_signals"] == ["mirror pressure", "rupture"]
    assert parsed["cold_weaver_topics"] == ["ritual callback"]


def test_parse_s2_output_returns_defaults_for_invalid_or_empty_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    assert analyzer._parse_s2_output("") == DEFAULT_S2_RESULT
    assert analyzer._parse_s2_output("{not-json") == DEFAULT_S2_RESULT
    assert analyzer._parse_s2_output("[]") == DEFAULT_S2_RESULT


def test_parse_s2_output_returns_defaults_for_unexpected_non_text_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    assert analyzer._parse_s2_output(123) == DEFAULT_S2_RESULT
    assert analyzer._parse_s2_output(["not", "an", "object"]) == DEFAULT_S2_RESULT


def test_parse_s2_output_returns_isolated_default_mutables():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output("")
    parsed["defensiveness_markers"].append("marker")
    parsed["themes_latents"].append("theme")

    fresh = analyzer._parse_s2_output("{}")

    assert DEFAULT_S2_RESULT["defensiveness_markers"] == []
    assert DEFAULT_S2_RESULT["themes_latents"] == []
    assert fresh["defensiveness_markers"] == []
    assert fresh["themes_latents"] == []


def test_parse_s2_output_returns_isolated_default_nested_dicts():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output("")
    parsed["intention"]["label"] = "mutated"
    parsed["ipc_position"]["agency"] = 0.8

    fresh = analyzer._parse_s2_output("{}")

    assert DEFAULT_S2_RESULT["intention"] == {"label": "unknown", "confidence": 0.0}
    assert DEFAULT_S2_RESULT["ipc_position"] == {"agency": 0.0, "communion": 0.0}
    assert fresh["intention"] == {"label": "unknown", "confidence": 0.0}
    assert fresh["ipc_position"] == {"agency": 0.0, "communion": 0.0}


def test_default_s2_result_returns_isolated_shallow_copies():
    first = analyzer_module._default_s2_result()
    second = analyzer_module._default_s2_result()

    assert first == DEFAULT_S2_RESULT
    assert second == DEFAULT_S2_RESULT
    assert first is not second
    assert first["intention"] is not second["intention"]
    assert first["ipc_position"] is not second["ipc_position"]
    assert first["themes_latents"] is not second["themes_latents"]
    assert first["recurring_minor_elements"] is not second["recurring_minor_elements"]


def test_parse_s2_output_accepts_camel_case_contract_keys():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "intention": {
                    "Label": "testing",
                    "Confidence": "0.8",
                },
                "dangerLevel": 2,
                "loopDetected": "true",
                "ipcPosition": {
                    "Agency": "0.3",
                    "Communion": "-0.1",
                },
                "correlation": {
                    "Hypothesis": "  stress avant lancement  ",
                    "Confidence": "0.6",
                },
                "recommendedHDelta": "0.2",
                "recurringMinorElements": [
                    {
                        "Content": "la fourchette quantique",
                        "Type": "Object Callback",
                        "Count": "2",
                        "Importance": "0.2",
                        "UserReaction": "callBack",
                    }
                ],
            }
        )
    )

    assert parsed["intention"] == {"label": "testing", "confidence": 0.8}
    assert parsed["danger_level"] == 2
    assert parsed["loop_detected"] is True
    assert parsed["ipc_position"] == {"agency": 0.3, "communion": -0.1}
    assert parsed["correlation"] == {
        "hypothesis": "stress avant lancement",
        "confidence": 0.6,
    }
    assert parsed["recommended_H_delta"] == 0.2
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_prefers_populated_alias_recurring_field_over_empty_canonical_duplicate():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "danger_level": 0,
            "recurring_minor_elements": [],
            "recurringMinorElements": [
                {
                    "content": "la fourchette quantique",
                    "type": "Object Callback",
                    "count": "2",
                    "importance": "0.2",
                    "userReaction": "callBack",
                }
            ],
        }
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_preserves_numeric_zero_recurring_content():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": 0,
                        "type": "ritual",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "engaged",
                    }
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "0",
            "type": "ritual",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_decodes_stringified_recurring_minor_elements_field():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": json.dumps(
                    [
                        {
                            "content": "la lampe temoine",
                            "type": "ritual",
                            "count": 2,
                            "importance": 0.2,
                            "user_reaction": "engaged",
                        }
                    ]
                )
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la lampe temoine",
            "type": "ritual",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_normalize_recurring_minor_elements_ignores_cyclic_predecoded_lists():
    analyzer, _, _, _, _ = make_analyzer()
    cyclic = []
    cyclic.append(
        {
            "content": "la cuillere orbitale",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    )
    cyclic.append(cyclic)

    normalized = analyzer._normalize_recurring_minor_elements(cyclic)

    assert normalized == [
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_handles_cyclic_mixed_wrapper_entry_payloads():
    analyzer, _, _, _, _ = make_analyzer()
    recurring = {
        "content": "la cuillere orbitale",
        "count": 2,
        "importance": 0.2,
        "user_reaction": "amused",
    }
    wrapper = {"entries": recurring}
    recurring["items"] = wrapper

    parsed = analyzer._parse_s2_output({"recurring_minor_elements": recurring})

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_accepts_top_level_raw_recurring_minor_elements_list():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        [
            {
                "content": "la cuillere orbitale",
                "type": "in_joke",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "amused",
            }
        ]
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_accepts_top_level_raw_recurring_minor_element_object():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_decodes_top_level_stringified_raw_recurring_minor_elements_list():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            [
                {
                    "content": "la cuillere orbitale",
                    "type": "in_joke",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused",
                }
            ]
        )
    )

    assert parsed["danger_level"] == 0
    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la cuillere orbitale",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_decodes_prose_wrapped_stringified_recurring_minor_elements_field():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": """Rapport:
                [
                  {
                    "content": "la lampe temoin",
                    "type": "ritual",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged"
                  }
                ]
                Fin."""
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la lampe temoin",
            "type": "ritual",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_decodes_code_fenced_stringified_recurring_minor_elements_field():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": """```json
                [
                  {
                    "content": "la tasse binaire",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused"
                  }
                ]
                ```"""
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_prefers_populated_recurring_field_payload_over_trailing_empty_list():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": """Rapport:
                [
                  {
                    "content": "la tasse binaire",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused"
                  }
                ]

                Exemple:
                []""",
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_prefers_real_recurring_field_payload_over_trailing_schema_example():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": """Rapport:
                [
                  {
                    "content": "la tasse binaire",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused"
                  }
                ]

                Schema example:
                [
                  {
                    "content": "...",
                    "type": "in_joke",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused"
                  }
                ]""",
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_decodes_stringified_recurring_entries_and_wrappers():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    json.dumps(
                        {
                            "content": "la tasse binaire",
                            "type": "object_callback",
                            "count": 2,
                            "importance": 0.2,
                            "user_reaction": "amused",
                        }
                    ),
                    {
                        "elements": {
                            "content": "le bouton fantome",
                            "type": "in_joke",
                            "count": 3,
                            "importance": 0.1,
                            "user_reaction": "callback",
                        }
                    },
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "le bouton fantome",
            "type": "in_joke",
            "count": 3,
            "importance": 0.1,
            "user_reaction": "callback",
        },
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        },
    ]


def test_parse_s2_output_accepts_frozenset_backed_recurring_minor_elements():
    analyzer, _, _, _, _ = make_analyzer()

    recurring = frozenset(
        {
            json.dumps(
                {
                    "content": "la tasse binaire",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused",
                }
            ),
            json.dumps(
                {
                    "content": "le bouton fantome",
                    "type": "in_joke",
                    "count": 3,
                    "importance": 0.1,
                    "user_reaction": "callback",
                }
            ),
        }
    )

    parsed = analyzer._parse_s2_output({"recurring_minor_elements": recurring})

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "le bouton fantome",
            "type": "in_joke",
            "count": 3,
            "importance": 0.1,
            "user_reaction": "callback",
        },
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        },
    ]


def test_parse_s2_output_preserves_mixed_wrapper_entry_payloads():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": {
                    "content": "la tasse binaire",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "callback",
                    "items": [],
                }
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_default_s2_result_schema_contains_expected_fields():
    expected_fields = {
        "intention",
        "defensiveness_score",
        "defensiveness_markers",
        "danger_level",
        "danger_signals",
        "themes_latents",
        "loop_detected",
        "loop_theme",
        "loop_count",
        "correlation",
        "ipc_position",
        "axis_crossing",
        "sycophancy_risk",
        "fanfaronade_score",
        "cold_weaver_topics",
        "recurring_minor_elements",
        "trigger_description",
        "recommended_H_delta",
        "recommended_phase",
    }

    assert set(DEFAULT_S2_RESULT) == expected_fields


def test_parse_s2_output_drops_unknown_top_level_keys_after_normalization():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "danger_level": 2,
                "themes_latents": ["repair"],
                "recurring_minor_elements": [],
                "debug_blob": {"step": "postprocess"},
                "unexpected_scalar": "ignore me",
            }
        )
    )

    assert set(parsed) == set(DEFAULT_S2_RESULT)
    assert parsed["danger_level"] == 2
    assert parsed["themes_latents"] == ["repair"]


def test_danger_level_is_normalized_into_allowed_range():
    analyzer, _, _, _, _ = make_analyzer()

    assert analyzer._parse_s2_output(json.dumps({"danger_level": -1}))["danger_level"] == 0
    assert analyzer._parse_s2_output(json.dumps({"danger_level": 2.9}))["danger_level"] == 2
    assert analyzer._parse_s2_output(json.dumps({"danger_level": 99}))["danger_level"] == 3


def test_parse_s2_output_rejects_non_finite_numeric_values():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        '{"danger_level": Infinity, "recommended_H_delta": NaN, "sycophancy_risk": Infinity}'
    )

    assert parsed["danger_level"] == 0
    assert parsed["recommended_H_delta"] == 0.0
    assert parsed["sycophancy_risk"] == 0.0


def test_parse_s2_output_coerces_boolean_like_string_values():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "loop_detected": "false",
                "axis_crossing": "YES",
            }
        )
    )

    assert parsed["loop_detected"] is False
    assert parsed["axis_crossing"] is True


def test_parse_s2_output_coerces_numeric_and_null_like_boolean_strings():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "loop_detected": "0.0",
                "axis_crossing": "1.0",
            }
        )
    )
    parsed_with_null = analyzer._parse_s2_output(
        json.dumps(
            {
                "loop_detected": "null",
                "axis_crossing": "none",
            }
        )
    )

    assert parsed["loop_detected"] is False
    assert parsed["axis_crossing"] is True
    assert parsed_with_null["loop_detected"] is False
    assert parsed_with_null["axis_crossing"] is False


def test_parse_s2_output_defaults_container_and_non_finite_boolean_values():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "loop_detected": [],
                "axis_crossing": "NaN",
            }
        )
    )

    assert parsed["loop_detected"] is False
    assert parsed["axis_crossing"] is False


def test_parse_s2_output_defaults_unknown_boolean_strings_and_other_object_types():
    analyzer, _, _, _, _ = make_analyzer()

    class TruthySentinel:
        def __bool__(self):
            return True

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "loop_detected": "sometimes",
            }
        )
    )

    assert parsed["loop_detected"] is False
    assert analyzer._coerce_bool(TruthySentinel()) is False


def test_parse_s2_output_defaults_container_valued_scalar_text_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "intention": {"label": {"unexpected": "value"}, "confidence": 0.7},
                "trigger_description": {"nested": "value"},
                "loop_theme": ["spiral"],
                "recommended_phase": {"phase": "repair"},
            }
        )
    )

    assert parsed["intention"] == {"label": "unknown", "confidence": 0.7}
    assert parsed["trigger_description"] == "routine"
    assert parsed["loop_theme"] is None
    assert parsed["recommended_phase"] is None


def test_parse_s2_output_normalizes_recommended_phase_to_known_persona_phases():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recommended_phase": "  SPARRING  ",
            }
        )
    )

    assert parsed["recommended_phase"] == "sparring"


def test_parse_s2_output_rejects_unknown_recommended_phase_values():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recommended_phase": "baseline",
            }
        )
    )

    assert parsed["recommended_phase"] is None


def test_parse_s2_output_normalizes_string_list_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "defensiveness_markers": [
                    "  deni  ",
                    "deni",
                    {"nested": "value"},
                    True,
                    "",
                    "meta-commentaires",
                ],
                "danger_signals": ["  escalation  ", "ESCALATION", None],
                "themes_latents": ["  besoin  de  controle ", ["nested"], "Besoin de controle"],
                "cold_weaver_topics": ["  launches  ", "launches", {"topic": "ops"}],
            }
        )
    )

    assert parsed["defensiveness_markers"] == ["deni", "meta-commentaires"]
    assert parsed["danger_signals"] == ["escalation"]
    assert parsed["themes_latents"] == ["besoin de controle"]
    assert parsed["cold_weaver_topics"] == ["launches"]


def test_parse_s2_output_normalizes_correlation_payload():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "correlation": {
                    "hypothesis": "  stress monte avant les lancements  ",
                    "confidence": "0.8",
                    "evidence": {"unexpected": "value"},
                }
            }
        )
    )

    assert parsed["correlation"] == {
        "hypothesis": "stress monte avant les lancements",
        "confidence": 0.8,
    }


def test_parse_s2_output_drops_correlation_without_text_hypothesis():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "correlation": {
                    "hypothesis": {"nested": "value"},
                    "confidence": 0.9,
                }
            }
        )
    )

    assert parsed["correlation"] is None


def test_parse_s2_output_normalizes_recurring_minor_element_strings():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "  la fourchette quantique  ",
                        "type": "  object_callback  ",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "  CALLBACK  ",
                    }
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_deduplicates_equivalent_recurring_minor_elements():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "  la  fourchette quantique  ",
                        "type": "object_callback",
                        "count": 2,
                        "importance": 0.4,
                        "user_reaction": "neutral",
                    },
                    {
                        "content": "la fourchette   quantique",
                        "type": "  object_callback  ",
                        "count": 5,
                        "importance": 0.1,
                        "user_reaction": "callback",
                    },
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 5,
            "importance": 0.1,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_deduplicates_recurring_elements_using_strongest_reaction():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "la fourchette quantique",
                        "type": "object_callback",
                        "count": 3,
                        "importance": 0.2,
                        "user_reaction": "amused",
                    },
                    {
                        "content": "  la  fourchette quantique  ",
                        "type": " object_callback ",
                        "count": 3,
                        "importance": 0.2,
                        "user_reaction": "callback",
                    },
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_sorts_recurring_elements_deterministically_after_normalization():
    analyzer, _, _, _, _ = make_analyzer()

    payload = {
        "recurring_minor_elements": [
            {
                "content": "le zebre methodique",
                "type": "ritual",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
            {
                "content": "la fourchette quantique",
                "type": "object_callback",
                "count": 4,
                "importance": 0.1,
                "user_reaction": "amused",
            },
            {
                "content": "la balance absurde",
                "type": "in_joke",
                "count": 4,
                "importance": 0.1,
                "user_reaction": "callback",
            },
        ]
    }

    forward = analyzer._parse_s2_output(json.dumps(payload))["recurring_minor_elements"]
    reverse = analyzer._parse_s2_output(
        json.dumps({"recurring_minor_elements": list(reversed(payload["recurring_minor_elements"]))})
    )["recurring_minor_elements"]

    expected = [
        {
            "content": "la balance absurde",
            "type": "in_joke",
            "count": 4,
            "importance": 0.1,
            "user_reaction": "callback",
        },
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 4,
            "importance": 0.1,
            "user_reaction": "amused",
        },
        {
            "content": "le zebre methodique",
            "type": "ritual",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        },
    ]

    assert forward == expected
    assert reverse == expected


def test_parse_s2_output_normalizes_unknown_recurring_element_reactions_to_neutral():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "la fourchette quantique",
                        "type": "object_callback",
                        "count": 3,
                        "importance": 0.2,
                        "user_reaction": "curious",
                    }
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "neutral",
        }
    ]


def test_parse_s2_output_defaults_unknown_recurring_element_types_to_in_joke():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "la fourchette quantique",
                        "type": "totem-insolite",
                        "count": 3,
                        "importance": 0.2,
                        "user_reaction": "engaged",
                    }
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "in_joke",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]


def test_parse_s2_output_normalizes_separator_variants_for_type_and_reaction():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": "la fourchette quantique",
                        "type": "Object Callback",
                        "count": 3,
                        "importance": 0.2,
                        "user_reaction": "call back",
                    }
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]


def test_parse_s2_output_ignores_container_valued_recurring_element_text_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": {"nested": "value"},
                        "type": ["object_callback"],
                        "count": 3,
                        "importance": 0.1,
                        "user_reaction": {"state": "engaged"},
                    },
                    {
                        "content": "le parapluie epistemique",
                        "type": "in_joke",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "amused",
                    },
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "le parapluie epistemique",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_parse_s2_output_rejects_boolean_recurring_element_fields():
    analyzer, _, _, _, _ = make_analyzer()

    parsed = analyzer._parse_s2_output(
        json.dumps(
            {
                "recurring_minor_elements": [
                    {
                        "content": True,
                        "type": False,
                        "count": True,
                        "importance": False,
                        "user_reaction": True,
                    },
                    {
                        "content": "le parapluie epistemique",
                        "type": "in_joke",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "amused",
                    },
                ]
            }
        )
    )

    assert parsed["recurring_minor_elements"] == [
        {
            "content": "le parapluie epistemique",
            "type": "in_joke",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "amused",
        }
    ]


def test_analyze_returns_defaults_and_logs_timeout(monkeypatch):
    analyzer, _, episodic, semantic, persona = make_analyzer(response="{}")
    seen_timeout_seconds = []

    class ImmediateTimeout:
        async def __aenter__(self):
            raise TimeoutError

        async def __aexit__(self, exc_type, exc, tb):
            return False

    def fake_timeout(seconds):
        seen_timeout_seconds.append(seconds)
        return ImmediateTimeout()

    monkeypatch.setattr("src.s2.analyzer.asyncio.timeout", fake_timeout)
    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-1",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result == DEFAULT_S2_RESULT
    assert seen_timeout_seconds == [S2_ANALYSIS_TIMEOUT_SECONDS]
    assert semantic.updated == []
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == [
        ("frag-1", "s2_timeout", {"timeout_seconds": S2_ANALYSIS_TIMEOUT_SECONDS})
    ]


def test_analyze_returns_defaults_and_logs_prompt_loading_failures(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(response="{}")

    def fail_prompt():
        raise RuntimeError("prompt missing contract token")

    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", fail_prompt)

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-2",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result == DEFAULT_S2_RESULT
    assert client.calls == []
    assert semantic.updated == []
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == [
        ("frag-2", "s2_error", {"error": "prompt missing contract token"})
    ]


def test_analyze_returns_defaults_when_prompt_failure_logging_also_fails(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(response="{}")

    def fail_prompt():
        raise RuntimeError("prompt missing contract token")

    def fail_log_execution(fragment_id: str, log_type: str, content: dict):
        raise RuntimeError("episodic log unavailable")

    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", fail_prompt)
    episodic.log_execution = fail_log_execution

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-2b",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result == DEFAULT_S2_RESULT
    assert client.calls == []
    assert semantic.updated == []
    assert persona.transitions == []
    assert episodic.saved_states == []


def test_analyze_returns_defaults_and_logs_parse_failures(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(response="{}")

    def fail_parse(_raw):
        raise RuntimeError("parser exploded")

    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")
    monkeypatch.setattr(analyzer, "_parse_s2_output", fail_parse)

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-2c",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result == DEFAULT_S2_RESULT
    assert len(client.calls) == 1
    assert semantic.updated == []
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == [
        ("frag-2c", "s2_parse_error", {"error": "parser exploded"})
    ]


def test_analyze_returns_defaults_when_parse_failure_logging_also_fails(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(response="{}")

    def fail_parse(_raw):
        raise RuntimeError("parser exploded")

    def fail_log_execution(fragment_id: str, log_type: str, content: dict):
        raise RuntimeError("episodic log unavailable")

    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")
    monkeypatch.setattr(analyzer, "_parse_s2_output", fail_parse)
    episodic.log_execution = fail_log_execution

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-2d",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result == DEFAULT_S2_RESULT
    assert len(client.calls) == 1
    assert semantic.updated == []
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == []


def test_analyze_updates_memories_and_logs_normalized_result_on_success(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(
        response=json.dumps(
            {
                "dangerLevel": 2,
                "themes_latents": ["pattern drift", "pattern drift"],
                "recurringMinorElements": [
                    {
                        "content": "la fourchette quantique",
                        "type": "Object Callback",
                        "count": "2",
                        "importance": "0.2",
                        "userReaction": "callBack",
                    }
                ],
            }
        )
    )

    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-3",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[{"role": "user", "content": "Salut"}],
            session_id="session-1",
        )
    )

    assert result["danger_level"] == 2
    assert result["themes_latents"] == ["pattern drift"]
    assert result["recurring_minor_elements"] == [
        {
            "content": "la fourchette quantique",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
        }
    ]
    assert len(client.calls) == 1
    assert semantic.updated == [("frag-3", result)]
    assert persona.transitions == [
        (
            result,
            {
                "messages_this_session": 4,
                "total_sessions": 2,
                "ignored_injections": 0,
            },
        )
    ]
    assert len(episodic.saved_states) == 1
    assert episodic.logs == [("frag-3", "s2_analysis", result)]


def test_analyze_returns_normalized_result_when_success_logging_fails(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(
        response=json.dumps(
            {
                "danger_level": 2,
                "themes_latents": ["pattern drift"],
                "recurring_minor_elements": [],
            }
        )
    )

    def fail_log_execution(fragment_id: str, log_type: str, content: dict):
        raise RuntimeError("episodic log unavailable")

    episodic.log_execution = fail_log_execution
    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-3b",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result["danger_level"] == 2
    assert result["themes_latents"] == ["pattern drift"]
    assert len(client.calls) == 1
    assert semantic.updated == [("frag-3b", result)]
    assert persona.transitions == [
        (
            result,
            {
                "messages_this_session": 4,
                "total_sessions": 2,
                "ignored_injections": 0,
            },
        )
    ]
    assert len(episodic.saved_states) == 1
    assert episodic.logs == []


def test_analyze_returns_parsed_result_and_logs_postprocess_error(monkeypatch):
    analyzer, _, episodic, semantic, persona = make_analyzer(
        response=json.dumps(
            {
                "danger_level": 1,
                "themes_latents": ["repair"],
                "recurring_minor_elements": [],
            }
        )
    )

    def fail_update(fragment_id: str, s2_result: dict):
        raise RuntimeError("semantic store unavailable")

    semantic.update_from_s2 = fail_update
    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-4",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result["danger_level"] == 1
    assert result["themes_latents"] == ["repair"]
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == [
        (
            "frag-4",
            "s2_postprocess_error",
            {
                "error": "semantic store unavailable",
                "s2_result": result,
            },
        )
    ]


def test_analyze_returns_parsed_result_when_postprocess_error_logging_fails(monkeypatch):
    analyzer, _, episodic, semantic, persona = make_analyzer(
        response=json.dumps(
            {
                "danger_level": 1,
                "themes_latents": ["repair"],
                "recurring_minor_elements": [],
            }
        )
    )

    def fail_update(fragment_id: str, s2_result: dict):
        raise RuntimeError("semantic store unavailable")

    def fail_log_execution(fragment_id: str, log_type: str, content: dict):
        raise RuntimeError("episodic log unavailable")

    semantic.update_from_s2 = fail_update
    episodic.log_execution = fail_log_execution
    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    result = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-4b",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert result["danger_level"] == 1
    assert result["themes_latents"] == ["repair"]
    assert persona.transitions == []
    assert episodic.saved_states == []
    assert episodic.logs == []


def test_analyze_reuses_same_analyzer_cleanly_after_invalid_then_valid_payload(monkeypatch):
    analyzer, client, episodic, semantic, persona = make_analyzer(response="{not-json")
    monkeypatch.setattr("src.s2.analyzer.get_s2_prompt", lambda: "valid s2 prompt recurring_minor_elements")

    first = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-5",
            user_message="Salut",
            s1_response="Salut toi",
            session_messages=[],
            session_id="session-1",
        )
    )

    client.response = json.dumps(
        {
            "danger_level": 2,
            "themes_latents": ["second pass"],
            "recurring_minor_elements": [
                {
                    "content": "la lampe temoin",
                    "type": "ritual",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            ],
        }
    )
    second = asyncio.run(
        analyzer.analyze(
            fragment_id="frag-6",
            user_message="Rebonjour",
            s1_response="Toujours la",
            session_messages=[],
            session_id="session-1",
        )
    )

    assert first == DEFAULT_S2_RESULT
    assert first is not DEFAULT_S2_RESULT
    assert second["danger_level"] == 2
    assert second["themes_latents"] == ["second pass"]
    assert second["recurring_minor_elements"] == [
        {
            "content": "la lampe temoin",
            "type": "ritual",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "engaged",
        }
    ]
    assert len(client.calls) == 2
    assert semantic.updated == [("frag-5", first), ("frag-6", second)]
    assert persona.transitions == [
        (
            first,
            {
                "messages_this_session": 4,
                "total_sessions": 2,
                "ignored_injections": 0,
            },
        ),
        (
            second,
            {
                "messages_this_session": 4,
                "total_sessions": 2,
                "ignored_injections": 0,
            },
        ),
    ]
    assert episodic.logs == [
        ("frag-5", "s2_analysis", first),
        ("frag-6", "s2_analysis", second),
    ]
