import sqlite3

from src.memory.semantic import SemanticMemory


def make_semantic_memory() -> SemanticMemory:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return SemanticMemory(conn)


def test_update_from_s2_tracks_themes_loops_and_confident_correlations():
    memory = make_semantic_memory()

    memory.update_from_s2(
        "fragment-1",
        {
            "themes_latents": ["orchard", "mirror"],
            "correlation": {
                "hypothesis": "The orchard keeps coupling with reflections.",
                "confidence": 0.72,
            },
            "loop_detected": True,
            "loop_theme": "mirror",
        },
    )
    memory.update_from_s2(
        "fragment-2",
        {
            "themes_latents": ["orchard"],
            "loop_detected": True,
            "loop_theme": "mirror",
        },
    )

    active_themes = memory.get_active_themes(threshold=0.1)
    loops = memory.get_loops()
    correlations = memory.get_correlations()

    assert active_themes == [
        {"label": "orchard", "weight": 0.2},
        {"label": "mirror", "weight": 0.1},
    ]
    assert loops == [
        {
            "theme": "mirror",
            "occurrences": 2,
            "first_seen": loops[0]["first_seen"],
            "last_seen": loops[0]["last_seen"],
        }
    ]
    assert correlations == [
        {
            "hypothesis": "The orchard keeps coupling with reflections.",
            "confidence": 0.72,
            "state": "H",
            "created_at": correlations[0]["created_at"],
            "updated_at": correlations[0]["updated_at"],
            "evidence": [],
        }
    ]


def test_get_active_themes_applies_threshold_and_orders_by_weight():
    memory = make_semantic_memory()

    memory.add_or_reinforce_theme("orchard", 0.2)
    memory.add_or_reinforce_theme("mirror", 0.7)
    memory.add_or_reinforce_theme("orchard", 0.5)

    active_themes = memory.get_active_themes(threshold=0.3)

    assert [theme["weight"] for theme in active_themes] == [0.7, 0.7]
    assert {theme["label"] for theme in active_themes} == {"mirror", "orchard"}
    assert memory.get_active_themes(threshold=0.71) == []


def test_add_or_reinforce_theme_caps_new_theme_weight_at_one():
    memory = make_semantic_memory()

    memory.add_or_reinforce_theme("flooded station", 1.7)

    assert memory.get_active_themes(threshold=0.0) == [
        {"label": "flooded station", "weight": 1.0}
    ]


def test_add_or_reinforce_theme_clamps_weights_at_zero_for_negative_updates():
    memory = make_semantic_memory()

    memory.add_or_reinforce_theme("fading motif", -0.4)
    memory.add_or_reinforce_theme("returning motif", 0.25)
    memory.add_or_reinforce_theme("returning motif", -0.8)

    rows = memory.conn.execute(
        "SELECT label, weight FROM themes ORDER BY label ASC"
    ).fetchall()

    assert [dict(row) for row in rows] == [
        {"label": "fading motif", "weight": 0.0},
        {"label": "returning motif", "weight": 0.0},
    ]


def test_update_from_s2_ignores_low_confidence_correlation_and_missing_loop():
    memory = make_semantic_memory()

    memory.update_from_s2(
        "fragment-low",
        {
            "themes_latents": ["tram"],
            "correlation": {
                "hypothesis": "This should stay below threshold.",
                "confidence": 0.2,
            },
            "loop_detected": False,
        },
    )

    assert memory.get_correlations() == []
    assert memory.get_loops() == []
    assert memory.get_active_themes(threshold=0.1) == [{"label": "tram", "weight": 0.1}]


def test_get_correlations_tolerates_invalid_evidence_json():
    memory = make_semantic_memory()
    memory.conn.execute(
        "INSERT INTO correlations (id, hypothesis, confidence, state, evidence_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "corr-1",
            "Malformed evidence should degrade gracefully.",
            0.55,
            "H",
            "{not valid json",
            "2026-04-17T10:00:00",
            "2026-04-17T10:00:01",
        ),
    )
    memory.conn.commit()

    assert memory.get_correlations() == [
        {
            "hypothesis": "Malformed evidence should degrade gracefully.",
            "confidence": 0.55,
            "state": "H",
            "created_at": "2026-04-17T10:00:00",
            "updated_at": "2026-04-17T10:00:01",
            "evidence": [],
        }
    ]


def test_get_correlations_tolerates_null_evidence_json():
    memory = make_semantic_memory()
    memory.conn.execute(
        "INSERT INTO correlations (id, hypothesis, confidence, state, evidence_json, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "corr-null",
            "NULL evidence payloads should degrade gracefully.",
            0.67,
            "H",
            None,
            "2026-04-17T10:00:04",
            "2026-04-17T10:00:05",
        ),
    )
    memory.conn.commit()

    assert memory.get_correlations() == [
        {
            "hypothesis": "NULL evidence payloads should degrade gracefully.",
            "confidence": 0.67,
            "state": "H",
            "created_at": "2026-04-17T10:00:04",
            "updated_at": "2026-04-17T10:00:05",
            "evidence": [],
        }
    ]
