import json
import sqlite3
from collections import deque
from datetime import datetime, timedelta
from types import MappingProxyType

import src.persona.gag_contract as gag_contract
from src.persona.gag_contract import (
    extract_recurring_minor_elements,
    normalize_recurring_minor_element,
    reaction_priority,
)
from src.persona.gags import GagTracker


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_gag_lifecycle_seed_register_activate_decay_and_kill():
    conn = make_conn()
    tracker = GagTracker(conn)

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "le mug fendu",
                "type": "object_callback",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "amused",
            }
        ]
    })

    assert seed == {
        "seed": "le mug fendu",
        "type": "object_callback",
        "user_callback": False,
    }

    gag_id = tracker.register_gag(seed["seed"], seed["type"])
    tracker.activate(gag_id, variation="le mug encore vivant", user_callback=True)

    row = conn.execute(
        "SELECT seed_content, type, occurrence_count, user_callback_count, variations, status "
        "FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert row["seed_content"] == "le mug fendu"
    assert row["type"] == "object_callback"
    assert row["occurrence_count"] == 2
    assert row["user_callback_count"] == 1
    assert "le mug encore vivant" in row["variations"]
    assert row["status"] == "active"

    stale_ts = (datetime.now() - timedelta(days=181)).isoformat()
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (stale_ts, gag_id),
    )
    conn.commit()

    assert tracker.apply_decay() == 1

    decayed = conn.execute(
        "SELECT status, death_reason FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()
    assert decayed["status"] == "dead"
    assert decayed["death_reason"] == "forgotten"


def test_gag_decay_kills_gags_at_exactly_180_days_of_inactivity(monkeypatch):
    conn = make_conn()
    tracker = GagTracker(conn)
    gag_id = tracker.register_gag("la bouilloire stoique", "ritual")
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    stale_ts = (frozen_now - timedelta(days=180)).isoformat()
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (stale_ts, gag_id),
    )
    conn.commit()

    monkeypatch.setattr("src.persona.gags.datetime", FrozenDateTime)

    assert tracker.apply_decay() == 1

    decayed = conn.execute(
        "SELECT status, death_reason FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()
    assert decayed["status"] == "dead"
    assert decayed["death_reason"] == "forgotten"


def test_gag_decay_ignores_malformed_last_activated_values():
    conn = make_conn()
    tracker = GagTracker(conn)
    gag_id = tracker.register_gag("le reveil mal calibre", "ritual")

    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        ("not-a-timestamp", gag_id),
    )
    conn.commit()

    assert tracker.apply_decay() == 0

    row = conn.execute(
        "SELECT status, death_reason FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()
    assert row["status"] == "active"
    assert row["death_reason"] is None


def test_detect_seed_uses_recurring_minor_elements():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "la chaussette diplomatique",
                "type": "in_joke",
                "count": 3,
                "importance": 0.1,
                "user_reaction": "callback",
            },
            {
                "content": "le theme principal",
                "type": "theme",
                "count": 5,
                "importance": 0.8,
                "user_reaction": "engaged",
            },
        ]
    })

    assert seed == {
        "seed": "la chaussette diplomatique",
        "type": "in_joke",
        "user_callback": True,
    }


def test_detect_seed_accepts_tuple_recurring_minor_elements():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": (
            {
                "content": "la clef ceremonielle",
                "type": "ritual",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
        )
    })

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_mapping_proxy_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        MappingProxyType(
            {
                "recurringMinorElements": [
                    MappingProxyType(
                        {
                            "content": "la clef ceremonielle",
                            "type": "ritual",
                            "count": 2,
                            "importance": 0.2,
                            "userReaction": "engaged",
                        }
                    )
                ]
            }
        )
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_mapping_view_payload():
    tracker = GagTracker(make_conn())

    payload = {
        "recurringMinorElements": [
            {
                "content": "la clef ceremonielle",
                "type": "ritual",
                "count": 2,
                "importance": 0.2,
                "userReaction": "engaged",
            }
        ]
    }

    seed = tracker.detect_seed(payload.items())

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_deque_wrapped_s2_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        deque(
            [
                {
                    "danger_level": 0,
                    "recurring_minor_elements": [
                        {
                            "content": "la clef ceremonielle",
                            "type": "ritual",
                            "count": 2,
                            "importance": 0.2,
                            "user_reaction": "engaged",
                        }
                    ],
                }
            ]
        )
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_values_view_wrapped_s2_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        {
            "report": {
                "dangerLevel": 0,
                "recurringMinorElements": [
                    {
                        "content": "la clef ceremonielle",
                        "type": "ritual",
                        "count": 2,
                        "importance": 0.2,
                        "userReaction": "engaged",
                    }
                ],
            }
        }.values()
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_generator_wrapped_s2_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        item
        for item in [
            {
                "danger_level": 0,
                "recurring_minor_elements": [
                    {
                        "content": "la clef ceremonielle",
                        "type": "ritual",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "engaged",
                    }
                ],
            }
        ]
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_mapping_backed_recurring_minor_elements_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        {
            "recurring_minor_elements": {
                "alpha": {
                    "content": "la clef ceremonielle",
                    "type": "ritual",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            }
        }
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_mapping_values_view_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        {
            "recurring_minor_elements": {
                "alpha": {
                    "content": "la clef ceremonielle",
                    "type": "ritual",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "engaged",
                }
            }.values()
        }
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_generator_recurring_minor_elements():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed(
        {
            "recurring_minor_elements": (
                item for item in [
                    {
                        "content": "la clef ceremonielle",
                        "type": "ritual",
                        "count": 2,
                        "importance": 0.2,
                        "user_reaction": "engaged",
                    }
                ]
            )
        }
    )

    assert seed == {
        "seed": "la clef ceremonielle",
        "type": "ritual",
        "user_callback": False,
    }


def test_detect_seed_accepts_frozenset_recurring_minor_elements():
    tracker = GagTracker(make_conn())

    recurring = frozenset(
        {
            json.dumps(
                {
                    "content": "la fourchette quantique",
                    "type": "object_callback",
                    "count": 2,
                    "importance": 0.2,
                    "user_reaction": "amused",
                }
            ),
            json.dumps(
                {
                    "content": "le bouton fantome",
                    "type": "ritual",
                    "count": 3,
                    "importance": 0.1,
                    "user_reaction": "callback",
                }
            ),
        }
    )

    seed = tracker.detect_seed({"recurring_minor_elements": recurring})

    assert seed == {
        "seed": "le bouton fantome",
        "type": "ritual",
        "user_callback": True,
    }


def test_detect_seed_selects_strongest_qualifying_candidate_regardless_of_order():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "le clin d'oeil discret",
                "type": "in_joke",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
            {
                "content": "la cafetiere cosmique",
                "type": "object_callback",
                "count": 4,
                "importance": 0.1,
                "user_reaction": "callback",
            },
            {
                "content": "le motif trop central",
                "type": "theme",
                "count": 5,
                "importance": 0.6,
                "user_reaction": "callback",
            },
        ]
    })

    assert seed == {
        "seed": "la cafetiere cosmique",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_breaks_exact_ties_deterministically():
    tracker = GagTracker(make_conn())

    elements = [
        {
            "content": "le zebre methodique",
            "type": "ritual",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "engaged",
        },
        {
            "content": "la balance absurde",
            "type": "object_callback",
            "count": 3,
            "importance": 0.2,
            "user_reaction": "engaged",
        },
    ]

    forward = tracker.detect_seed({"recurring_minor_elements": elements})
    reverse = tracker.detect_seed({"recurring_minor_elements": list(reversed(elements))})

    assert forward == {
        "seed": "la balance absurde",
        "type": "object_callback",
        "user_callback": False,
    }
    assert reverse == forward


def test_detect_seed_ignores_malformed_recurring_elements():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            None,
            "not-a-dict",
            {"content": "", "count": 4, "importance": 0.1, "user_reaction": "amused"},
            {
                "content": "la lampe syndicale",
                "type": "in_joke",
                "count": "2",
                "importance": "0.2",
                "user_reaction": "engaged",
            },
        ]
    })

    assert seed == {
        "seed": "la lampe syndicale",
        "type": "in_joke",
        "user_callback": False,
    }


def test_detect_seed_normalizes_string_fields_before_matching():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "  la boussole absurde  ",
                "type": "  object_callback  ",
                "count": "2",
                "importance": "0.2",
                "user_reaction": "  CALLBACK  ",
            }
        ]
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_normalizes_separator_variants_for_type_and_reaction():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "la boussole absurde",
                "type": "Object Callback",
                "count": "2",
                "importance": "0.2",
                "user_reaction": "call back",
            }
        ]
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_accepts_camel_case_recurring_element_keys():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "Content": "la boussole absurde",
                "Type": "ObjectCallback",
                "Count": "2",
                "Importance": "0.2",
                "UserReaction": "callBack",
            }
        ]
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_accepts_camel_case_top_level_recurring_field():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurringMinorElements": [
            {
                "content": "la boussole absurde",
                "type": "ObjectCallback",
                "count": "2",
                "importance": "0.2",
                "user_reaction": "callBack",
            }
        ]
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_prefers_populated_alias_recurring_field_over_empty_canonical_duplicate():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [],
        "recurringMinorElements": [
            {
                "content": "la boussole absurde",
                "type": "ObjectCallback",
                "count": "2",
                "importance": "0.2",
                "userReaction": "callBack",
            }
        ],
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_extract_recurring_minor_elements_short_circuits_direct_top_level_field(monkeypatch):
    recurring_payload = {
        "recurring_minor_elements": [
            {
                "content": "la boussole absurde",
                "type": "Object Callback",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "callback",
            }
        ]
    }

    def fail_nested_search(_value):
        raise AssertionError("direct top-level recurring field should bypass wrapper search")

    monkeypatch.setattr(
        gag_contract,
        "_extract_best_recurring_minor_elements_candidate",
        fail_nested_search,
    )

    recurring = extract_recurring_minor_elements(recurring_payload)

    assert recurring == recurring_payload["recurring_minor_elements"]


def test_detect_seed_accepts_stringified_recurring_minor_elements_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": json.dumps(
            [
                {
                    "content": "la boussole absurde",
                    "type": "Object Callback",
                    "count": "2",
                    "importance": "0.2",
                    "user_reaction": "call back",
                }
            ]
        )
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_accepts_double_encoded_stringified_recurring_minor_elements_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": json.dumps(
            json.dumps(
                [
                    {
                        "content": "la boussole absurde",
                        "type": "Object Callback",
                        "count": "2",
                        "importance": "0.2",
                        "user_reaction": "call back",
                    }
                ]
            )
        )
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_accepts_prose_wrapped_stringified_recurring_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": """Rapport:
        [
          {
            "content": "la boussole absurde",
            "type": "Object Callback",
            "count": "2",
            "importance": "0.2",
            "user_reaction": "call back"
          }
        ]
        Fin.""",
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_accepts_code_fenced_stringified_recurring_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": """```json
        [
          {
            "content": "la boussole absurde",
            "type": "Object Callback",
            "count": "2",
            "importance": "0.2",
            "user_reaction": "call back"
          }
        ]
        ```""",
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_prefers_populated_stringified_payload_over_trailing_empty_list():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": """Rapport final:
        [
          {
            "content": "la boussole absurde",
            "type": "Object Callback",
            "count": "2",
            "importance": "0.2",
            "user_reaction": "call back"
          }
        ]

        Exemple vide:
        []""",
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_ignores_placeholder_schema_entries():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "...",
                "type": "Object Callback",
                "count": "2",
                "importance": "0.2",
                "user_reaction": "call back",
            }
        ],
    })

    assert seed is None


def test_detect_seed_accepts_wrapper_dict_for_recurring_minor_elements_payload():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": {
            "entries": [
                {
                    "content": "la boussole absurde",
                    "type": "Object Callback",
                    "count": "2",
                    "importance": "0.2",
                    "user_reaction": "call back",
                }
            ]
        }
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_preserves_mixed_wrapper_entry_payloads():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": {
            "content": "la tasse binaire",
            "type": "object_callback",
            "count": 2,
            "importance": 0.2,
            "user_reaction": "callback",
            "items": [],
        }
    })

    assert seed == {
        "seed": "la tasse binaire",
        "type": "object_callback",
        "user_callback": True,
    }


def test_detect_seed_ignores_cyclic_mixed_wrapper_entry_payloads():
    tracker = GagTracker(make_conn())
    recurring = {
        "content": "la tasse binaire",
        "type": "object_callback",
        "count": 2,
        "importance": 0.2,
        "user_reaction": "callback",
    }
    wrapper = {"entries": recurring}
    recurring["items"] = wrapper

    seed = tracker.detect_seed({"recurring_minor_elements": recurring})

    assert seed == {
        "seed": "la tasse binaire",
        "type": "object_callback",
        "user_callback": True,
    }


def test_reaction_priority_normalizes_alias_variants():
    assert reaction_priority("call back") == reaction_priority("callback")
    assert reaction_priority("CALL-BACK") == reaction_priority("callback")
    assert reaction_priority("unknown") == reaction_priority("neutral")


def test_detect_seed_uses_shared_recurring_element_contract_normalization():
    tracker = GagTracker(make_conn())
    raw_element = {
        "content": "  la   boussole absurde  ",
        "type": "Object Callback",
        "count": "2",
        "importance": "0.2",
        "user_reaction": "call back",
    }

    normalized = normalize_recurring_minor_element(raw_element)
    seed = tracker.detect_seed({"recurring_minor_elements": [raw_element]})

    assert normalized == {
        "content": "la boussole absurde",
        "type": "object_callback",
        "count": 2,
        "importance": 0.2,
        "user_reaction": "callback",
    }
    assert seed == {
        "seed": normalized["content"],
        "type": normalized["type"],
        "user_callback": True,
    }


def test_detect_seed_defaults_unknown_type_to_in_joke():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": "la boussole absurde",
                "type": "totem-insolite",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            }
        ]
    })

    assert seed == {
        "seed": "la boussole absurde",
        "type": "in_joke",
        "user_callback": False,
    }


def test_detect_seed_ignores_container_valued_text_fields():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": {"nested": "value"},
                "type": ["ritual"],
                "count": 4,
                "importance": 0.1,
                "user_reaction": {"state": "amused"},
            },
            {
                "content": "la cafetiere stoique",
                "type": "object_callback",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
        ]
    })

    assert seed == {
        "seed": "la cafetiere stoique",
        "type": "object_callback",
        "user_callback": False,
    }


def test_detect_seed_ignores_boolean_valued_recurring_fields():
    tracker = GagTracker(make_conn())

    seed = tracker.detect_seed({
        "recurring_minor_elements": [
            {
                "content": True,
                "type": False,
                "count": True,
                "importance": False,
                "user_reaction": True,
            },
            {
                "content": "la cafetiere stoique",
                "type": "object_callback",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "engaged",
            },
        ]
    })

    assert seed == {
        "seed": "la cafetiere stoique",
        "type": "object_callback",
        "user_callback": False,
    }


def test_detect_seed_preserves_numeric_zero_content_via_shared_normalization():
    tracker = GagTracker(make_conn())
    raw_element = {
        "content": 0,
        "type": "ritual",
        "count": 2,
        "importance": 0.2,
        "user_reaction": "engaged",
    }

    normalized = normalize_recurring_minor_element(raw_element)
    seed = tracker.detect_seed({"recurring_minor_elements": [raw_element]})

    assert normalized == {
        "content": "0",
        "type": "ritual",
        "count": 2,
        "importance": 0.2,
        "user_reaction": "engaged",
    }
    assert seed == {
        "seed": "0",
        "type": "ritual",
        "user_callback": False,
    }


def test_register_or_refresh_gag_reactivates_existing_entries():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la chaise ceremonielle", "ritual")
    original = conn.execute(
        "SELECT occurrence_count, user_callback_count, last_activated FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    refreshed_id, created = tracker.register_or_refresh_gag(
        "la chaise ceremonielle",
        "ritual",
        user_callback=True,
    )

    refreshed = conn.execute(
        "SELECT occurrence_count, user_callback_count, last_activated FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert refreshed_id == gag_id
    assert created is False
    assert refreshed["occurrence_count"] == original["occurrence_count"] + 1
    assert refreshed["user_callback_count"] == original["user_callback_count"] + 1
    assert refreshed["last_activated"] >= original["last_activated"]


def test_register_or_refresh_gag_tracks_initial_user_callback_on_creation():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id, created = tracker.register_or_refresh_gag(
        "la chaise ceremonielle",
        "ritual",
        user_callback=True,
    )

    row = conn.execute(
        "SELECT occurrence_count, user_callback_count FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert created is True
    assert row["occurrence_count"] == 1
    assert row["user_callback_count"] == 1


def test_register_or_refresh_gag_normalizes_equivalent_seed_content():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la chaise ceremonielle", "ritual")
    refreshed_id, created = tracker.register_or_refresh_gag(
        "  la chaise ceremonielle  ",
        "  ritual  ",
    )

    active_rows = conn.execute(
        "SELECT seed_content, type FROM running_gags WHERE status = 'active'"
    ).fetchall()

    assert refreshed_id == gag_id
    assert created is False
    assert len(active_rows) == 1
    assert active_rows[0]["seed_content"] == "la chaise ceremonielle"
    assert active_rows[0]["type"] == "ritual"


def test_register_gag_persists_canonical_seed_for_indexed_lookup():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("  La   chaise ceremonielle  ", "ritual")

    row = conn.execute(
        "SELECT seed_content, canonical_seed FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert row["seed_content"] == "La chaise ceremonielle"
    assert row["canonical_seed"] == "la chaise ceremonielle"


def test_register_gag_normalizes_separator_variants_for_type():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la chaise ceremonielle", "Object Callback")
    row = conn.execute(
        "SELECT type FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert row["type"] == "object_callback"


def test_register_gag_rejects_blank_seed_content():
    conn = make_conn()
    tracker = GagTracker(conn)

    try:
        tracker.register_gag("   ", "ritual")
    except ValueError as exc:
        assert "seed_content" in str(exc)
    else:
        raise AssertionError("register_gag should reject blank seed content")

    row_count = conn.execute("SELECT COUNT(*) AS count FROM running_gags").fetchone()["count"]
    assert row_count == 0


def test_register_or_refresh_gag_rejects_blank_seed_content():
    conn = make_conn()
    tracker = GagTracker(conn)

    try:
        tracker.register_or_refresh_gag("   ", "ritual")
    except ValueError as exc:
        assert "seed_content" in str(exc)
    else:
        raise AssertionError("register_or_refresh_gag should reject blank seed content")

    row_count = conn.execute("SELECT COUNT(*) AS count FROM running_gags").fetchone()["count"]
    assert row_count == 0


def test_register_or_refresh_gag_reuses_seed_despite_case_and_internal_spacing():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la chaise ceremonielle", "ritual")
    refreshed_id, created = tracker.register_or_refresh_gag(
        "  La   chaise   ceremonielle  ",
        "ritual",
    )

    row = conn.execute(
        "SELECT seed_content, occurrence_count FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert refreshed_id == gag_id
    assert created is False
    assert row["seed_content"] == "la chaise ceremonielle"
    assert row["occurrence_count"] == 2


def test_register_or_refresh_gag_falls_back_to_canonical_scan_for_legacy_seed_rows():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = "legacy-gag"
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO running_gags "
        "(id, seed_content, type, first_seen, last_activated, occurrence_count, "
        "user_callback_count, variations, status, death_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            gag_id,
            " La   chaise ceremonielle ",
            "ritual",
            now,
            now,
            1,
            0,
            "[]",
            "active",
            None,
        ),
    )
    conn.commit()

    refreshed_id, created = tracker.register_or_refresh_gag(
        "la chaise ceremonielle",
        "ritual",
    )

    row = conn.execute(
        "SELECT COUNT(*) AS count, occurrence_count, canonical_seed FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert refreshed_id == gag_id
    assert created is False
    assert row["count"] == 1
    assert row["occurrence_count"] == 2
    assert row["canonical_seed"] == "la chaise ceremonielle"


def test_register_or_refresh_gag_prefers_most_recent_legacy_duplicate_when_backfilling():
    conn = make_conn()
    tracker = GagTracker(conn)
    older_ts = "2026-04-15T09:00:00"
    newer_ts = "2026-04-16T09:00:00"
    conn.executemany(
        "INSERT INTO running_gags "
        "(id, seed_content, type, first_seen, last_activated, occurrence_count, "
        "user_callback_count, variations, status, death_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "legacy-older",
                "La chaise ceremonielle",
                "ritual",
                older_ts,
                older_ts,
                1,
                0,
                "[]",
                "active",
                None,
            ),
            (
                "legacy-newer",
                "  la   chaise ceremonielle  ",
                "ritual",
                newer_ts,
                newer_ts,
                3,
                1,
                "[]",
                "active",
                None,
            ),
        ],
    )
    conn.commit()

    refreshed_id, created = tracker.register_or_refresh_gag(
        "la chaise ceremonielle",
        "ritual",
    )

    rows = conn.execute(
        "SELECT id, occurrence_count, canonical_seed FROM running_gags ORDER BY id"
    ).fetchall()
    row_by_id = {row["id"]: row for row in rows}

    assert refreshed_id == "legacy-newer"
    assert created is False
    assert row_by_id["legacy-older"]["occurrence_count"] == 1
    assert row_by_id["legacy-newer"]["occurrence_count"] == 4
    assert row_by_id["legacy-older"]["canonical_seed"] == "la chaise ceremonielle"
    assert row_by_id["legacy-newer"]["canonical_seed"] == "la chaise ceremonielle"


def test_activate_recovers_from_corrupt_variations_payload():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la chaise ceremonielle", "ritual")
    conn.execute(
        "UPDATE running_gags SET variations = ? WHERE id = ?",
        ('{"broken": true}', gag_id),
    )
    conn.commit()

    tracker.activate(gag_id, variation={"not": "text"})
    tracker.activate(gag_id, variation="la chaise reapparait")

    row = conn.execute(
        "SELECT occurrence_count, variations FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert row["occurrence_count"] == 3
    assert row["variations"] == '["la chaise reapparait"]'


def test_activate_deduplicates_equivalent_variations():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_id = tracker.register_gag("la cuillere orbitale")

    tracker.activate(gag_id, variation="  la   cuillere revient  ")
    tracker.activate(gag_id, variation="la cuillere revient")
    tracker.activate(gag_id, variation="LA CUILLERE REVIENT")

    row = conn.execute(
        "SELECT occurrence_count, variations FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()

    assert row["occurrence_count"] == 4
    assert row["variations"] == '["la cuillere revient"]'


def test_gag_context_for_s1_lists_top_three_active_gags():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_ids = [
        tracker.register_gag("gag-1", "in_joke"),
        tracker.register_gag("gag-2", "ritual"),
        tracker.register_gag("gag-3", "object_callback"),
        tracker.register_gag("gag-4", "in_joke"),
    ]

    tracker.activate(gag_ids[0], user_callback=True)
    tracker.activate(gag_ids[0], user_callback=True)
    tracker.activate(gag_ids[1])
    tracker.activate(gag_ids[2])

    timestamps = [
        "2026-04-16T10:00:00",
        "2026-04-16T11:00:00",
        "2026-04-16T12:00:00",
        "2026-04-16T09:00:00",
    ]
    for gag_id, timestamp in zip(gag_ids, timestamps, strict=True):
        conn.execute(
            "UPDATE running_gags SET last_activated = ? WHERE id = ?",
            (timestamp, gag_id),
        )
    conn.commit()

    context = tracker.get_gag_context_for_s1()

    assert context is not None
    assert "RUNNING GAGS ACTIFS" in context
    assert "gag-3" in context
    assert "gag-2" in context
    assert "gag-1" in context
    assert "gag-4" not in context
    assert "fort" in context


def test_gag_context_uses_stable_ordering_for_equal_activation_times():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_ids = [
        tracker.register_gag("gag-b", "in_joke"),
        tracker.register_gag("gag-a", "ritual"),
        tracker.register_gag("gag-c", "object_callback"),
    ]
    shared_ts = "2026-04-16T12:00:00"
    for gag_id in gag_ids:
        conn.execute(
            "UPDATE running_gags SET last_activated = ? WHERE id = ?",
            (shared_ts, gag_id),
        )
    conn.execute(
        "UPDATE running_gags SET user_callback_count = 2, occurrence_count = 5 WHERE id = ?",
        (gag_ids[0],),
    )
    conn.execute(
        "UPDATE running_gags SET user_callback_count = 2, occurrence_count = 5 WHERE id = ?",
        (gag_ids[1],),
    )
    conn.execute(
        "UPDATE running_gags SET user_callback_count = 1, occurrence_count = 9 WHERE id = ?",
        (gag_ids[2],),
    )
    conn.commit()

    active = tracker.get_active_gags()
    context = tracker.get_gag_context_for_s1()

    assert [gag["seed_content"] for gag in active] == ["gag-a", "gag-b", "gag-c"]
    assert context.splitlines()[1:] == [
        "- gag-a (ritual, 5x, fort)",
        "- gag-b (in_joke, 5x, fort)",
        "- gag-c (object_callback, 9x, naissant)",
    ]


def test_register_or_refresh_gag_uses_deterministic_indexed_lookup_for_duplicate_canonical_rows():
    conn = make_conn()
    tracker = GagTracker(conn)
    shared_ts = "2026-04-16T09:00:00"
    conn.executemany(
        "INSERT INTO running_gags "
        "(id, seed_content, canonical_seed, type, first_seen, last_activated, occurrence_count, "
        "user_callback_count, variations, status, death_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "gag-b",
                "La chaise ceremonielle",
                "la chaise ceremonielle",
                "ritual",
                shared_ts,
                shared_ts,
                1,
                0,
                "[]",
                "active",
                None,
            ),
            (
                "gag-a",
                "la chaise ceremonielle",
                "la chaise ceremonielle",
                "ritual",
                shared_ts,
                shared_ts,
                3,
                1,
                "[]",
                "active",
                None,
            ),
        ],
    )
    conn.commit()

    refreshed_id, created = tracker.register_or_refresh_gag(
        "LA   CHAISE CEREMONIELLE",
        "ritual",
    )

    rows = conn.execute(
        "SELECT id, occurrence_count FROM running_gags ORDER BY id"
    ).fetchall()
    row_by_id = {row["id"]: row for row in rows}

    assert refreshed_id == "gag-a"
    assert created is False
    assert row_by_id["gag-a"]["occurrence_count"] == 4
    assert row_by_id["gag-b"]["occurrence_count"] == 1


def test_get_active_gags_limit_preserves_ordering_and_handles_zero():
    conn = make_conn()
    tracker = GagTracker(conn)

    gag_ids = [
        tracker.register_gag("gag-1", "in_joke"),
        tracker.register_gag("gag-2", "ritual"),
        tracker.register_gag("gag-3", "object_callback"),
        tracker.register_gag("gag-4", "in_joke"),
    ]
    timestamps = [
        "2026-04-16T09:00:00",
        "2026-04-16T10:00:00",
        "2026-04-16T11:00:00",
        "2026-04-16T12:00:00",
    ]
    for gag_id, timestamp in zip(gag_ids, timestamps, strict=True):
        conn.execute(
            "UPDATE running_gags SET last_activated = ? WHERE id = ?",
            (timestamp, gag_id),
        )
    conn.commit()

    assert [gag["seed_content"] for gag in tracker.get_active_gags(limit=2)] == [
        "gag-4",
        "gag-3",
    ]
    assert tracker.get_active_gags(limit=0) == []


def test_get_active_gags_breaks_full_sql_ties_with_id_order():
    conn = make_conn()
    tracker = GagTracker(conn)
    shared_ts = "2026-04-16T09:00:00"
    conn.executemany(
        "INSERT INTO running_gags "
        "(id, seed_content, canonical_seed, type, first_seen, last_activated, occurrence_count, "
        "user_callback_count, variations, status, death_reason) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                "gag-b",
                "la chaise ceremonielle",
                "la chaise ceremonielle",
                "ritual",
                shared_ts,
                shared_ts,
                3,
                1,
                "[]",
                "active",
                None,
            ),
            (
                "gag-a",
                "la chaise ceremonielle",
                "la chaise ceremonielle",
                "ritual",
                shared_ts,
                shared_ts,
                3,
                1,
                "[]",
                "active",
                None,
            ),
        ],
    )
    conn.commit()

    active = tracker.get_active_gags()

    assert [gag["id"] for gag in active] == ["gag-a", "gag-b"]


def test_gag_decay_kills_entries_after_180_days_of_inactivity():
    conn = make_conn()
    tracker = GagTracker(conn)
    gag_id = tracker.register_gag("la cuillere orbitale")

    stale_ts = (datetime.now() - timedelta(days=180, seconds=1)).isoformat()
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (stale_ts, gag_id),
    )
    conn.commit()

    killed = tracker.apply_decay()

    row = conn.execute(
        "SELECT status, death_reason FROM running_gags WHERE id = ?",
        (gag_id,),
    ).fetchone()
    assert killed == 1
    assert row["status"] == "dead"
    assert row["death_reason"] == "forgotten"


def test_gag_decay_kills_multiple_stale_entries_in_one_pass():
    conn = make_conn()
    tracker = GagTracker(conn)
    stale_a = tracker.register_gag("la cuillere orbitale")
    stale_b = tracker.register_gag("le tournevis lunar")
    fresh = tracker.register_gag("la lampe recente")

    stale_ts = (datetime.now() - timedelta(days=181)).isoformat()
    fresh_ts = (datetime.now() - timedelta(days=20)).isoformat()
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (stale_ts, stale_a),
    )
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (stale_ts, stale_b),
    )
    conn.execute(
        "UPDATE running_gags SET last_activated = ? WHERE id = ?",
        (fresh_ts, fresh),
    )
    conn.commit()

    killed = tracker.apply_decay()

    rows = conn.execute(
        "SELECT id, status, death_reason FROM running_gags ORDER BY id"
    ).fetchall()
    status_by_id = {row["id"]: (row["status"], row["death_reason"]) for row in rows}

    assert killed == 2
    assert status_by_id[stale_a] == ("dead", "forgotten")
    assert status_by_id[stale_b] == ("dead", "forgotten")
    assert status_by_id[fresh] == ("active", None)
