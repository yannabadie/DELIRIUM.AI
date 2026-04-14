"""Essential property tests for PersonaEngine.

Validates core invariants: H boundedness, NaN safety, serialization,
determinism, and initial state validity.
"""

import math
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from src.persona.engine import PersonaEngine
from src.persona.state import PersonaState


def _make_s2(intention=0.0, danger=0.0, defensiveness=0.0):
    return {
        "intention": intention,
        "danger_level": danger,
        "defensiveness": defensiveness,
        "confrontation_delta": 0.0,
        "empathy_delta": 0.0,
    }


def _make_time(messages=1, sessions=1, ignored=0):
    return {
        "messages_this_session": messages,
        "total_sessions": sessions,
        "ignored_injections": ignored,
    }


@given(
    steps=st.integers(min_value=1, max_value=50),
    intention=st.floats(min_value=-1, max_value=1),
    danger=st.floats(min_value=0, max_value=1),
)
@settings(max_examples=200)
def test_h_stays_bounded(steps, intention, danger):
    """H must stay in [-1, 1] after any sequence of transitions."""
    assume(math.isfinite(intention) and math.isfinite(danger))
    engine = PersonaEngine()
    for _ in range(steps):
        engine.transition(_make_s2(intention=intention, danger=danger), _make_time())
    state = engine.get_current_state()
    assert -1.0 <= state.H <= 1.0


@given(
    intention=st.floats(allow_nan=True, allow_infinity=True),
    danger=st.floats(allow_nan=True, allow_infinity=True),
    defensiveness=st.floats(allow_nan=True, allow_infinity=True),
)
@settings(max_examples=200)
def test_no_nan_in_state(intention, danger, defensiveness):
    """No NaN or Inf in any PersonaState field after arbitrary input."""
    engine = PersonaEngine()
    engine.transition(
        _make_s2(intention=intention, danger=danger, defensiveness=defensiveness),
        _make_time(),
    )
    state = engine.get_current_state()
    for field in ["H", "fatigue", "confrontation", "empathy"]:
        val = getattr(state, field)
        assert math.isfinite(val), f"{field}={val} is not finite"


def test_serialization_roundtrip():
    """PersonaState survives dict -> PersonaState roundtrip."""
    engine = PersonaEngine()
    engine.transition(_make_s2(intention=0.5, danger=0.1), _make_time(messages=3))
    original = engine.get_current_state()
    rebuilt = PersonaState(**original.__dict__)
    assert rebuilt.H == original.H
    assert rebuilt.fatigue == original.fatigue
    assert rebuilt.confrontation == original.confrontation
    assert rebuilt.empathy == original.empathy
    assert rebuilt.phase == original.phase


def test_deterministic_transitions():
    """Same inputs produce same output."""
    s2 = _make_s2(intention=0.3, danger=0.2, defensiveness=0.1)
    time_ctx = _make_time(messages=5, sessions=2)

    engine_a = PersonaEngine()
    engine_a.transition(s2, time_ctx)

    engine_b = PersonaEngine()
    engine_b.transition(s2, time_ctx)

    sa = engine_a.get_current_state()
    sb = engine_b.get_current_state()
    # Exclude timestamp — it is wall-clock stamped, not a determinism concern.
    for field in ["H", "fatigue", "confrontation", "empathy", "phase", "trigger"]:
        assert getattr(sa, field) == getattr(sb, field), f"mismatch on {field}"


def test_initial_state_valid():
    """Fresh PersonaState has all fields within documented bounds."""
    state = PersonaState()
    assert -1.0 <= state.H <= 1.0
    assert 0.0 <= state.fatigue <= 1.0
    assert 0.0 <= state.confrontation <= 1.0
    assert 0.0 <= state.empathy <= 1.0
    assert state.phase in ("probing", "silent", "reflection", "sparring")
