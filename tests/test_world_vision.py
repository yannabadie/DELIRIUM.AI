import json
import sqlite3

import pytest

from src.memory.world_vision import WorldVision


def make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


class StubLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def chat(self, system, messages, model=None):
        self.calls.append({
            "system": system,
            "messages": messages,
            "model": model,
        })
        return self.responses.pop(0)


def test_parse_vision_accepts_valid_json_with_code_fences():
    world_vision = WorldVision(make_conn(), StubLLM([]))

    parsed = world_vision._parse_vision(
        """```json
        {
          "who_they_are": {"summary": "Tactile thinker", "confidence": 0.8},
          "blind_spots": [{"description": "Avoids conflict"}],
          "next_priorities": [{"type": "project", "target": "Ship the draft"}]
        }
        ```"""
    )

    assert parsed["who_they_are"]["summary"] == "Tactile thinker"
    assert parsed["blind_spots"][0]["description"] == "Avoids conflict"
    assert parsed["next_priorities"][0]["target"] == "Ship the draft"
    assert parsed["synthesized_at"]


def test_parse_vision_normalizes_partial_objects():
    world_vision = WorldVision(make_conn(), StubLLM([]))

    parsed = world_vision._parse_vision(json.dumps({
        "who_they_are": {"summary": "Builder"},
        "blind_spots": "not-a-list",
    }))

    assert parsed["who_they_are"] == {"summary": "Builder", "confidence": 0.0}
    assert parsed["blind_spots"] == []
    assert parsed["next_priorities"] == []
    assert parsed["synthesized_at"]


def test_parse_vision_rejects_non_object_json():
    world_vision = WorldVision(make_conn(), StubLLM([]))

    parsed = world_vision._parse_vision('["wrong", "shape"]')

    assert parsed["who_they_are"]["summary"] == "Pas encore assez de données."
    assert parsed["blind_spots"] == []
    assert parsed["next_priorities"] == []


@pytest.mark.parametrize(
    ("s2_result", "sessions_since", "expected"),
    [
        (None, 10, True),
        ({"danger_level": 2}, 0, True),
        ({"loop_detected": True}, 0, True),
        ({"axis_crossing": True}, 0, True),
        ({"danger_level": 1, "loop_detected": False, "axis_crossing": False}, 3, False),
    ],
)
def test_should_resynthesize_triggers_on_sessions_danger_loops_and_axis(s2_result, sessions_since, expected):
    world_vision = WorldVision(make_conn(), StubLLM([]))

    assert world_vision.should_resynthesize(s2_result, sessions_since) is expected


def test_get_summary_for_s1_formats_summary_blind_spots_and_priorities():
    conn = make_conn()
    world_vision = WorldVision(conn, StubLLM([]))
    payload = {
        "version": 3,
        "who_they_are": {"summary": "Travaille par obsession brieve", "confidence": 0.7},
        "blind_spots": [
            {"description": "Prend les detours pour eviter le conflit"},
            {"description": "Confond urgence et importance"},
        ],
        "next_priorities": [
            {"type": "conversation", "target": "Dire ce qu'il veut vraiment"},
            {"type": "project", "target": "Finir le prototype"},
        ],
    }
    conn.execute(
        "INSERT INTO world_vision (id, version, vision_json, created_at) VALUES (?, ?, ?, ?)",
        ("vision-1", 3, json.dumps(payload), "2026-04-16T12:00:00"),
    )
    conn.commit()

    summary = world_vision.get_summary_for_s1()

    assert summary == (
        "Cet humain : Travaille par obsession brieve\n"
        "Angles morts : Prend les detours pour eviter le conflit | Confond urgence et importance\n"
        "Priorités : conversation: Dire ce qu'il veut vraiment, project: Finir le prototype"
    )


def test_world_vision_fallbacks_when_optional_tables_are_missing():
    world_vision = WorldVision(make_conn(), StubLLM([]))

    assert world_vision.get_sessions_since_last_vision() == 0
    assert world_vision.get_danger_history() == {
        "sample_size": 0,
        "max_danger_level": 0,
        "high_danger_count": 0,
        "recent_levels": [],
        "recent_triggers": [],
    }


def test_get_summary_for_s1_ignores_corrupted_stored_json():
    conn = make_conn()
    world_vision = WorldVision(conn, StubLLM([]))
    conn.execute(
        "INSERT INTO world_vision (id, version, vision_json, created_at) VALUES (?, ?, ?, ?)",
        ("vision-bad", 1, "{not-json", "2026-04-16T12:00:00"),
    )
    conn.commit()

    assert world_vision.get_current() is None
    assert world_vision.get_summary_for_s1() is None


def test_resynthesize_versions_entries_without_overwriting_and_passes_payload(monkeypatch):
    monkeypatch.setattr("src.memory.world_vision.get_vision_prompt", lambda: "vision system prompt")
    llm = StubLLM([
        json.dumps({
            "who_they_are": {"summary": "Version one", "confidence": 0.7},
            "blind_spots": [{"description": "First blind spot"}],
            "next_priorities": [{"type": "project", "target": "Ship v1"}],
        }),
        json.dumps({
            "who_they_are": {"summary": "Version two", "confidence": 0.9},
            "blind_spots": [{"description": "Second blind spot"}],
            "next_priorities": [{"type": "conversation", "target": "Ask directly"}],
        }),
    ])
    conn = make_conn()
    world_vision = WorldVision(conn, llm)

    first = world_vision.resynthesize(
        themes=[{"label": "work", "weight": 0.6}],
        correlations=[{"hypothesis": "Stress rises around launches", "confidence": 0.8}],
        loops=[{"theme": "approval", "occurrences": 3}],
        danger_history={"recent_levels": [0, 2, 1], "high_danger_count": 1},
        fragment_count=11,
    )
    second = world_vision.resynthesize([], [], [], fragment_count=12)

    rows = conn.execute(
        "SELECT version, vision_json FROM world_vision ORDER BY version ASC"
    ).fetchall()

    assert first["version"] == 1
    assert second["version"] == 2
    assert [row["version"] for row in rows] == [1, 2]
    assert json.loads(rows[0]["vision_json"])["who_they_are"]["summary"] == "Version one"
    assert json.loads(rows[1]["vision_json"])["who_they_are"]["summary"] == "Version two"

    first_call = llm.calls[0]
    payload = json.loads(first_call["messages"][0]["content"])
    assert first_call["system"] == "vision system prompt"
    assert payload["themes"][0]["label"] == "work"
    assert payload["correlations"][0]["hypothesis"] == "Stress rises around launches"
    assert payload["loops"][0]["theme"] == "approval"
    assert payload["danger_history"]["high_danger_count"] == 1
    assert payload["fragment_count"] == 11
