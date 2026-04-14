import math
from datetime import datetime
from unittest.mock import patch

from hypothesis import given, strategies as st

from src.persona.engine import PersonaEngine
from src.persona.state import PersonaState, clamp


NUMERIC_STATE_FIELDS = (
    "H",
    "listen_ratio",
    "creativity",
    "confrontation",
    "empathy",
    "fatigue",
    "defensiveness_detected",
)

BOUNDED_STATE_FIELDS = {
    "H": (-1.0, 1.0),
    "listen_ratio": (0.0, 1.0),
    "creativity": (0.0, 1.0),
    "confrontation": (0.0, 1.0),
    "empathy": (0.0, 1.0),
    "fatigue": (0.0, 1.0),
}

VALID_PHASES = {"probing", "silent", "reflection", "sparring"}


analysis_strategy = st.fixed_dictionaries(
    {
        "recommended_H_delta": st.floats(
            min_value=-1000.0,
            max_value=1000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        "danger_level": st.integers(min_value=0, max_value=5),
        "defensiveness_score": st.floats(
            min_value=0.0,
            max_value=1.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        "trigger_description": st.text(max_size=50),
    }
)

safe_h_analysis_strategy = st.fixed_dictionaries(
    {
        "recommended_H_delta": st.floats(
            min_value=-1000.0,
            max_value=1000.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        "danger_level": st.integers(min_value=0, max_value=1),
        "defensiveness_score": st.floats(
            min_value=0.0,
            max_value=1.0,
            allow_nan=False,
            allow_infinity=False,
        ),
        "trigger_description": st.text(max_size=50),
    }
)

time_context_strategy = st.fixed_dictionaries(
    {
        "messages_this_session": st.integers(min_value=0, max_value=500),
        "total_sessions": st.integers(min_value=0, max_value=500),
        "ignored_injections": st.integers(min_value=0, max_value=50),
    }
)

pathological_number_strategy = st.one_of(
    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    st.just(float("nan")),
    st.just(float("inf")),
    st.just(float("-inf")),
)

mixed_external_scalar_strategy = st.one_of(
    pathological_number_strategy,
    st.none(),
    st.text(max_size=20),
    st.booleans(),
)

mixed_analysis_strategy = st.fixed_dictionaries(
    {
        "recommended_H_delta": mixed_external_scalar_strategy,
        "danger_level": mixed_external_scalar_strategy,
        "defensiveness_score": mixed_external_scalar_strategy,
        "trigger_description": st.text(max_size=50),
    }
)

mixed_time_context_strategy = st.fixed_dictionaries(
    {
        "messages_this_session": mixed_external_scalar_strategy,
        "total_sessions": mixed_external_scalar_strategy,
        "ignored_injections": mixed_external_scalar_strategy,
    }
)

transition_sequences = st.lists(
    st.tuples(analysis_strategy, time_context_strategy),
    min_size=1,
    max_size=50,
)

mixed_transition_sequences = st.lists(
    st.tuples(mixed_analysis_strategy, mixed_time_context_strategy),
    min_size=1,
    max_size=20,
)

sparse_mixed_transition_sequences = st.lists(
    st.tuples(
        mixed_analysis_strategy,
        st.fixed_dictionaries(
            {
                "recommended_H_delta": st.booleans(),
                "danger_level": st.booleans(),
                "defensiveness_score": st.booleans(),
                "trigger_description": st.booleans(),
            }
        ),
        mixed_time_context_strategy,
        st.fixed_dictionaries(
            {
                "messages_this_session": st.booleans(),
                "total_sessions": st.booleans(),
                "ignored_injections": st.booleans(),
            }
        ),
    ),
    min_size=1,
    max_size=20,
)

state_strategy = st.builds(
    PersonaState,
    H=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    listen_ratio=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    creativity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    confrontation=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    empathy=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    fatigue=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    phase=st.sampled_from(sorted(VALID_PHASES)),
    defensiveness_detected=st.floats(
        min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False
    ),
    timestamp=st.just(datetime(2026, 1, 1, 12, 0, 0)),
    trigger=st.text(max_size=50),
)

partial_state_field_flags_strategy = st.fixed_dictionaries(
    {
        "H": st.booleans(),
        "listen_ratio": st.booleans(),
        "creativity": st.booleans(),
        "confrontation": st.booleans(),
        "empathy": st.booleans(),
        "fatigue": st.booleans(),
        "phase": st.booleans(),
        "defensiveness_detected": st.booleans(),
        "trigger": st.booleans(),
    }
)

analysis_field_flags_strategy = st.fixed_dictionaries(
    {
        "recommended_H_delta": st.booleans(),
        "danger_level": st.booleans(),
        "defensiveness_score": st.booleans(),
        "trigger_description": st.booleans(),
    }
)

time_context_field_flags_strategy = st.fixed_dictionaries(
    {
        "messages_this_session": st.booleans(),
        "total_sessions": st.booleans(),
        "ignored_injections": st.booleans(),
    }
)

unknown_serialized_fields_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20).filter(
        lambda key: key not in PersonaState.__dataclass_fields__
    ),
    values=st.one_of(
        st.none(),
        st.booleans(),
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=50),
    ),
    max_size=10,
)

transition_extra_values_strategy = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
    st.text(max_size=50),
)

analysis_extras_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20).filter(
        lambda key: key
        not in {
            "recommended_H_delta",
            "danger_level",
            "defensiveness_score",
            "trigger_description",
        }
    ),
    values=transition_extra_values_strategy,
    max_size=10,
)

time_context_extras_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20).filter(
        lambda key: key not in {"messages_this_session", "total_sessions", "ignored_injections"}
    ),
    values=transition_extra_values_strategy,
    max_size=10,
)


def make_frozen_datetime(hour: int):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            frozen = cls(2026, 1, 1, hour, 0, 0)
            if tz is not None:
                return frozen.astimezone(tz)
            return frozen

    return FrozenDateTime


def phase_for_total_sessions(total_sessions: int) -> str:
    if total_sessions == 0:
        return "probing"
    if total_sessions < 10:
        return "silent"
    if total_sessions < 20:
        return "reflection"
    return "sparring"


def time_bucket_h_delta(hour: int) -> float:
    if 0 <= hour < 6:
        return -0.2
    if 6 <= hour < 12:
        return 0.1
    return 0.0


def assert_state_is_finite_and_bounded(state: PersonaState):
    for field in NUMERIC_STATE_FIELDS:
        value = getattr(state, field)
        assert math.isfinite(value), f"{field} must stay finite"

    for field, (lower, upper) in BOUNDED_STATE_FIELDS.items():
        value = getattr(state, field)
        assert lower <= value <= upper, f"{field} escaped its bounds"

    assert state.phase in VALID_PHASES
    assert isinstance(state.timestamp, datetime)


def sanitize_finite_float(value, default=0.0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def sanitize_finite_int(value, default=0):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(value):
        return default
    return int(value)


def sanitize_bounded_float(value, default=0.0, lo=0.0, hi=1.0):
    return clamp(sanitize_finite_float(value, default), lo, hi)


def expected_transition_state(initial_state, analysis, time_context, hour):
    recommended_h_delta = sanitize_finite_float(
        analysis.get("recommended_H_delta", 0.0), 0.0
    )
    danger_level = sanitize_finite_int(analysis.get("danger_level", 0), 0)
    defensiveness_score = sanitize_bounded_float(
        analysis.get("defensiveness_score", 0.0), 0.0, 0.0, 1.0
    )
    session_length = sanitize_finite_int(
        time_context.get("messages_this_session", 0), 0
    )
    total_sessions = sanitize_finite_int(time_context.get("total_sessions", 0), 0)
    ignored_injections = sanitize_finite_int(
        time_context.get("ignored_injections", 0), 0
    )

    phase_factors = {
        "probing": -0.5,
        "silent": -0.3,
        "reflection": 0.0,
        "sparring": 0.3,
    }

    expected_h = clamp(
        initial_state.H * 0.7
        + recommended_h_delta * 0.15
        + phase_factors.get(initial_state.phase, 0.0) * 0.1
        + time_bucket_h_delta(hour) * 0.05,
        -1.0,
        1.0,
    )
    expected_empathy = initial_state.empathy
    expected_confrontation = initial_state.confrontation
    expected_creativity = initial_state.creativity
    expected_listen_ratio = initial_state.listen_ratio

    if danger_level >= 2:
        expected_h = min(expected_h, -0.5)
        expected_empathy = max(initial_state.empathy, 0.8)
        expected_confrontation = 0.0
        expected_creativity = 0.0
    if danger_level >= 3:
        expected_h = -1.0

    if defensiveness_score > 0.6:
        # The engine uses current.confrontation here, so this branch can
        # override the earlier danger reset back up to 0.1.
        expected_confrontation = min(initial_state.confrontation, 0.1)
        expected_listen_ratio = max(initial_state.listen_ratio, 0.8)

    return PersonaState(
        H=expected_h,
        listen_ratio=expected_listen_ratio,
        creativity=expected_creativity,
        confrontation=expected_confrontation,
        empathy=expected_empathy,
        fatigue=clamp(
            initial_state.fatigue
            + session_length * 0.02
            + ignored_injections * 0.1
            - 0.3,
            0.0,
            1.0,
        ),
        phase=phase_for_total_sessions(total_sessions),
        defensiveness_detected=defensiveness_score,
        timestamp=datetime(2026, 1, 1, hour, 0, 0),
        trigger=analysis.get("trigger_description", "routine"),
    )


@given(value=mixed_external_scalar_strategy)
def test_numeric_sanitization_helpers_match_documented_test_oracles(value):
    engine = PersonaEngine()

    assert engine._finite_float(value) == sanitize_finite_float(value, 0.0)
    assert engine._finite_int(value) == sanitize_finite_int(value, 0)
    assert engine._bounded_float(value) == sanitize_bounded_float(value, 0.0, 0.0, 1.0)


@given(state=state_strategy)
def test_persona_state_round_trips_through_dict_serialization(state):
    restored = PersonaState.from_dict(state.to_dict())
    assert restored == state


@given(state=state_strategy, extras=unknown_serialized_fields_strategy)
def test_persona_state_from_dict_ignores_unknown_serialized_fields(state, extras):
    serialized = state.to_dict()
    serialized.update(extras)

    restored = PersonaState.from_dict(serialized)

    assert restored == state


@given(state=state_strategy, included_fields=partial_state_field_flags_strategy)
def test_persona_state_from_dict_uses_defaults_for_omitted_known_fields(
    state, included_fields
):
    serialized = state.to_dict()
    partial = {"timestamp": serialized["timestamp"]}
    for field, include in included_fields.items():
        if include:
            partial[field] = serialized[field]

    restored = PersonaState.from_dict(partial)
    expected = PersonaState(timestamp=state.timestamp)
    for field, include in included_fields.items():
        if include:
            setattr(expected, field, getattr(state, field))

    assert restored == expected


@given(
    initial_state=state_strategy,
    analysis=analysis_strategy,
    time_context=time_context_strategy,
)
def test_transition_replaces_engine_state_without_mutating_caller_owned_state(
    initial_state, analysis, time_context
):
    original_snapshot = PersonaState.from_dict(initial_state.to_dict())

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        new_state = engine.transition(analysis, time_context)

    assert initial_state == original_snapshot
    assert new_state is engine.get_current_state()
    assert new_state is not initial_state


@given(transitions=transition_sequences)
def test_transition_outputs_remain_finite_and_bounded(transitions):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()

        for analysis, time_context in transitions:
            state = engine.transition(analysis, time_context)
            assert_state_is_finite_and_bounded(state)


@given(initial_state=state_strategy, transitions=transition_sequences)
def test_arbitrary_valid_initial_states_remain_finite_and_bounded_over_sequences(
    initial_state, transitions
):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(initial_state)

        for analysis, time_context in transitions:
            state = engine.transition(analysis, time_context)
            assert_state_is_finite_and_bounded(state)


@given(initial_state=state_strategy, transitions=transition_sequences)
def test_transition_is_deterministic_when_time_is_frozen(initial_state, transitions):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        left_engine = PersonaEngine()
        right_engine = PersonaEngine()
        left_engine.set_state(initial_state)
        right_engine.set_state(PersonaState.from_dict(initial_state.to_dict()))

        for analysis, time_context in transitions:
            left_state = left_engine.transition(analysis, time_context)
            right_state = right_engine.transition(analysis, time_context)
            assert left_state.to_dict() == right_state.to_dict()


@given(transitions=transition_sequences)
def test_h_stays_bounded_across_arbitrary_transition_sequences(transitions):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()

        for analysis, time_context in transitions:
            state = engine.transition(analysis, time_context)
            assert -1.0 <= state.H <= 1.0


@given(analysis=analysis_strategy, time_context=time_context_strategy)
def test_phase_and_override_rules_hold_for_each_transition(analysis, time_context):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        state = engine.transition(analysis, time_context)

    total_sessions = time_context["total_sessions"]
    if total_sessions == 0:
        assert state.phase == "probing"
    elif total_sessions < 10:
        assert state.phase == "silent"
    elif total_sessions < 20:
        assert state.phase == "reflection"
    else:
        assert state.phase == "sparring"

    danger_level = analysis["danger_level"]
    if danger_level >= 2:
        assert state.H <= -0.5
        assert state.empathy >= 0.8
        assert state.creativity == 0.0
        if analysis["defensiveness_score"] <= 0.6:
            assert state.confrontation == 0.0
        else:
            assert 0.0 <= state.confrontation <= 0.1
    if danger_level >= 3:
        assert state.H == -1.0

    if analysis["defensiveness_score"] > 0.6:
        assert state.confrontation <= 0.1
        assert state.listen_ratio >= 0.8


@given(
    initial_state=state_strategy,
    analysis=analysis_strategy,
    time_context=time_context_strategy,
)
def test_fatigue_follows_documented_clamped_formula(
    initial_state, analysis, time_context
):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        state = engine.transition(analysis, time_context)

    expected_fatigue = clamp(
        initial_state.fatigue
        + time_context["messages_this_session"] * 0.02
        + time_context["ignored_injections"] * 0.1
        - 0.3,
        0.0,
        1.0,
    )

    assert state.fatigue == expected_fatigue


@given(hour=st.integers(min_value=0, max_value=23))
def test_time_to_h_delta_uses_documented_time_buckets(hour):
    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        h_delta = engine._time_to_h_delta({})

    if 0 <= hour < 6:
        assert h_delta == -0.2
    elif 6 <= hour < 12:
        assert h_delta == 0.1
    else:
        assert h_delta == 0.0


@given(
    initial_h=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    analysis=safe_h_analysis_strategy,
    total_sessions=st.integers(min_value=0, max_value=500),
    hour=st.integers(min_value=0, max_value=23),
)
def test_h_update_matches_exact_clamped_linear_formula_in_stable_phase(
    initial_h, analysis, total_sessions, hour
):
    stable_phase = phase_for_total_sessions(total_sessions)
    initial_state = PersonaState(
        H=initial_h,
        phase=stable_phase,
        timestamp=datetime(2026, 1, 1, 12, 0, 0),
    )
    time_context = {
        "messages_this_session": 0,
        "total_sessions": total_sessions,
        "ignored_injections": 0,
    }
    phase_factors = {
        "probing": -0.5,
        "silent": -0.3,
        "reflection": 0.0,
        "sparring": 0.3,
    }

    expected_h = clamp(
        initial_h * 0.7
        + analysis["recommended_H_delta"] * 0.15
        + phase_factors[stable_phase] * 0.1
        + time_bucket_h_delta(hour) * 0.05,
        -1.0,
        1.0,
    )

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        state = engine.transition(analysis, time_context)

    assert state.H == expected_h


@given(
    initial_h=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    analysis=safe_h_analysis_strategy,
    total_sessions=st.integers(min_value=0, max_value=500),
    hour=st.integers(min_value=0, max_value=23),
)
def test_repeated_identical_h_updates_contract_toward_fixed_point(
    initial_h, analysis, total_sessions, hour
):
    stable_phase = phase_for_total_sessions(total_sessions)
    time_context = {
        "messages_this_session": 0,
        "total_sessions": total_sessions,
        "ignored_injections": 0,
    }
    phase_factors = {
        "probing": -0.5,
        "silent": -0.3,
        "reflection": 0.0,
        "sparring": 0.3,
    }
    offset = (
        analysis["recommended_H_delta"] * 0.15
        + phase_factors[stable_phase] * 0.1
        + time_bucket_h_delta(hour) * 0.05
    )
    fixed_point = clamp(offset / 0.3, -1.0, 1.0)

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(
            PersonaState(
                H=initial_h,
                phase=stable_phase,
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
            )
        )

        previous_distance = abs(initial_h - fixed_point)
        for _ in range(8):
            state = engine.transition(analysis, time_context)
            current_distance = abs(state.H - fixed_point)
            assert current_distance <= previous_distance + 1e-12
            previous_distance = current_distance


@given(
    initial_h=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    recommended_h_delta=st.floats(
        min_value=-1.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    steps=st.integers(min_value=1, max_value=20),
)
def test_repeated_safe_h_updates_match_exact_closed_form(initial_h, recommended_h_delta, steps):
    analysis = {
        "recommended_H_delta": recommended_h_delta,
        "danger_level": 0,
        "defensiveness_score": 0.0,
        "trigger_description": "closed-form",
    }
    time_context = {
        "messages_this_session": 0,
        "total_sessions": 10,
        "ignored_injections": 0,
    }
    fixed_point = 0.5 * recommended_h_delta
    expected_h = fixed_point + (0.7 ** steps) * (initial_h - fixed_point)

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(
            PersonaState(
                H=initial_h,
                phase="reflection",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
            )
        )

        for _ in range(steps):
            state = engine.transition(analysis, time_context)

    assert abs(expected_h) <= 1.0
    assert math.isclose(state.H, expected_h, rel_tol=1e-12, abs_tol=1e-12)


@given(
    initial_h=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    recommended_h_delta=st.floats(
        min_value=-1.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    steps=st.integers(min_value=1, max_value=20),
)
def test_safe_h_replay_matches_exact_closed_form_at_every_prefix(
    initial_h, recommended_h_delta, steps
):
    analysis = {
        "recommended_H_delta": recommended_h_delta,
        "danger_level": 0,
        "defensiveness_score": 0.0,
        "trigger_description": "prefix-closed-form",
    }
    time_context = {
        "messages_this_session": 0,
        "total_sessions": 10,
        "ignored_injections": 0,
    }
    fixed_point = 0.5 * recommended_h_delta

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(
            PersonaState(
                H=initial_h,
                phase="reflection",
                timestamp=datetime(2026, 1, 1, 12, 0, 0),
            )
        )

        for step in range(1, steps + 1):
            state = engine.transition(analysis, time_context)
            expected_h = fixed_point + (0.7 ** step) * (initial_h - fixed_point)
            assert math.isclose(state.H, expected_h, rel_tol=1e-12, abs_tol=1e-12)


@given(
    initial_state=state_strategy,
    recommended_h_delta=st.floats(
        min_value=-1.0,
        max_value=1.0,
        allow_nan=False,
        allow_infinity=False,
    ),
    total_sessions=st.integers(min_value=0, max_value=500),
    hour=st.integers(min_value=0, max_value=23),
    steps=st.integers(min_value=1, max_value=10),
)
def test_safe_transition_replay_matches_exact_full_state_update_at_every_prefix(
    initial_state, recommended_h_delta, total_sessions, hour, steps
):
    stable_phase = phase_for_total_sessions(total_sessions)
    analysis = {
        "recommended_H_delta": recommended_h_delta,
        "danger_level": 0,
        "defensiveness_score": 0.0,
        "trigger_description": "full-state-prefix-replay",
    }
    time_context = {
        "messages_this_session": 0,
        "total_sessions": total_sessions,
        "ignored_injections": 0,
    }
    phase_factors = {
        "probing": -0.5,
        "silent": -0.3,
        "reflection": 0.0,
        "sparring": 0.3,
    }
    frozen_timestamp = datetime(2026, 1, 1, hour, 0, 0)
    initial_state = PersonaState(
        H=initial_state.H,
        listen_ratio=initial_state.listen_ratio,
        creativity=initial_state.creativity,
        confrontation=initial_state.confrontation,
        empathy=initial_state.empathy,
        fatigue=initial_state.fatigue,
        phase=stable_phase,
        defensiveness_detected=initial_state.defensiveness_detected,
        timestamp=initial_state.timestamp,
        trigger=initial_state.trigger,
    )
    offset = (
        recommended_h_delta * 0.15
        + phase_factors[stable_phase] * 0.1
        + time_bucket_h_delta(hour) * 0.05
    )

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)

        for step in range(1, steps + 1):
            state = engine.transition(analysis, time_context)
            expected_h = clamp(
                (0.7 ** step) * initial_state.H + offset * (1 - 0.7 ** step) / 0.3,
                -1.0,
                1.0,
            )
            expected_fatigue = clamp(initial_state.fatigue - 0.3 * step, 0.0, 1.0)

            assert math.isclose(state.H, expected_h, rel_tol=1e-12, abs_tol=1e-12)
            assert state.listen_ratio == initial_state.listen_ratio
            assert state.creativity == initial_state.creativity
            assert state.confrontation == initial_state.confrontation
            assert state.empathy == initial_state.empathy
            assert math.isclose(
                state.fatigue, expected_fatigue, rel_tol=1e-12, abs_tol=1e-12
            )
            assert state.phase == stable_phase
            assert state.defensiveness_detected == 0.0
            assert state.timestamp == frozen_timestamp
            assert state.trigger == analysis["trigger_description"]


@given(
    initial_state=state_strategy,
    analysis=analysis_strategy,
    time_context=time_context_strategy,
)
def test_transition_output_round_trips_through_state_dict(
    initial_state, analysis, time_context
):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        state = engine.transition(analysis, time_context)

    restored = PersonaState.from_dict(state.to_dict())
    assert restored == state


@given(
    initial_state=state_strategy,
    analysis=analysis_strategy,
    analysis_fields=analysis_field_flags_strategy,
    time_context=time_context_strategy,
    time_context_fields=time_context_field_flags_strategy,
)
def test_transition_omitted_input_keys_match_explicit_neutral_defaults(
    initial_state, analysis, analysis_fields, time_context, time_context_fields
):
    sparse_analysis = {
        field: analysis[field] for field, include in analysis_fields.items() if include
    }
    sparse_time_context = {
        field: time_context[field]
        for field, include in time_context_fields.items()
        if include
    }
    padded_analysis = {
        "recommended_H_delta": 0.0,
        "danger_level": 0,
        "defensiveness_score": 0.0,
        "trigger_description": "routine",
        **sparse_analysis,
    }
    padded_time_context = {
        "messages_this_session": 0,
        "total_sessions": 0,
        "ignored_injections": 0,
        **sparse_time_context,
    }

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        sparse_engine = PersonaEngine()
        padded_engine = PersonaEngine()
        sparse_engine.set_state(initial_state)
        padded_engine.set_state(PersonaState.from_dict(initial_state.to_dict()))

        sparse_state = sparse_engine.transition(sparse_analysis, sparse_time_context)
        padded_state = padded_engine.transition(padded_analysis, padded_time_context)

    assert sparse_state.to_dict() == padded_state.to_dict()


@given(
    initial_state=state_strategy,
    analysis=st.fixed_dictionaries(
        {
            "recommended_H_delta": pathological_number_strategy,
            "danger_level": pathological_number_strategy,
            "defensiveness_score": pathological_number_strategy,
            "trigger_description": st.text(max_size=50),
        }
    ),
    time_context=st.fixed_dictionaries(
        {
            "messages_this_session": pathological_number_strategy,
            "total_sessions": pathological_number_strategy,
            "ignored_injections": pathological_number_strategy,
        }
    ),
)
def test_transition_sanitizes_non_finite_external_numeric_inputs(
    initial_state, analysis, time_context
):
    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        state = engine.transition(analysis, time_context)

    assert_state_is_finite_and_bounded(state)


@given(
    initial_state=state_strategy,
    analysis=st.fixed_dictionaries(
        {
            "recommended_H_delta": pathological_number_strategy,
            "danger_level": pathological_number_strategy,
            "defensiveness_score": pathological_number_strategy,
            "trigger_description": st.text(max_size=50),
        }
    ),
    time_context=st.fixed_dictionaries(
        {
            "messages_this_session": pathological_number_strategy,
            "total_sessions": pathological_number_strategy,
            "ignored_injections": pathological_number_strategy,
        }
    ),
)
def test_transition_matches_explicitly_sanitized_equivalent_inputs(
    initial_state, analysis, time_context
):
    sanitized_analysis = {
        "recommended_H_delta": sanitize_finite_float(
            analysis["recommended_H_delta"], 0.0
        ),
        "danger_level": sanitize_finite_int(analysis["danger_level"], 0),
        "defensiveness_score": sanitize_bounded_float(
            analysis["defensiveness_score"], 0.0, 0.0, 1.0
        ),
        "trigger_description": analysis["trigger_description"],
    }
    sanitized_time_context = {
        "messages_this_session": sanitize_finite_int(
            time_context["messages_this_session"], 0
        ),
        "total_sessions": sanitize_finite_int(time_context["total_sessions"], 0),
        "ignored_injections": sanitize_finite_int(
            time_context["ignored_injections"], 0
        ),
    }

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        raw_engine = PersonaEngine()
        sanitized_engine = PersonaEngine()
        raw_engine.set_state(initial_state)
        sanitized_engine.set_state(PersonaState.from_dict(initial_state.to_dict()))

        raw_state = raw_engine.transition(analysis, time_context)
        sanitized_state = sanitized_engine.transition(
            sanitized_analysis, sanitized_time_context
        )

    assert raw_state.to_dict() == sanitized_state.to_dict()


@given(
    initial_state=state_strategy,
    analysis=mixed_analysis_strategy,
    time_context=mixed_time_context_strategy,
)
def test_transition_matches_explicitly_sanitized_mixed_scalar_inputs(
    initial_state, analysis, time_context
):
    sanitized_analysis = {
        "recommended_H_delta": sanitize_finite_float(
            analysis["recommended_H_delta"], 0.0
        ),
        "danger_level": sanitize_finite_int(analysis["danger_level"], 0),
        "defensiveness_score": sanitize_bounded_float(
            analysis["defensiveness_score"], 0.0, 0.0, 1.0
        ),
        "trigger_description": analysis["trigger_description"],
    }
    sanitized_time_context = {
        "messages_this_session": sanitize_finite_int(
            time_context["messages_this_session"], 0
        ),
        "total_sessions": sanitize_finite_int(time_context["total_sessions"], 0),
        "ignored_injections": sanitize_finite_int(
            time_context["ignored_injections"], 0
        ),
    }

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        raw_engine = PersonaEngine()
        sanitized_engine = PersonaEngine()
        raw_engine.set_state(initial_state)
        sanitized_engine.set_state(PersonaState.from_dict(initial_state.to_dict()))

        raw_state = raw_engine.transition(analysis, time_context)
        sanitized_state = sanitized_engine.transition(
            sanitized_analysis, sanitized_time_context
        )

    assert raw_state.to_dict() == sanitized_state.to_dict()


@given(
    initial_state=state_strategy,
    analysis=mixed_analysis_strategy,
    analysis_extras=analysis_extras_strategy,
    time_context=mixed_time_context_strategy,
    time_context_extras=time_context_extras_strategy,
)
def test_transition_ignores_unknown_analysis_and_time_context_keys(
    initial_state, analysis, analysis_extras, time_context, time_context_extras
):
    analysis_with_extras = dict(analysis, **analysis_extras)
    time_context_with_extras = dict(time_context, **time_context_extras)

    with patch("src.persona.engine.datetime", make_frozen_datetime(12)):
        plain_engine = PersonaEngine()
        extra_engine = PersonaEngine()
        plain_engine.set_state(initial_state)
        extra_engine.set_state(PersonaState.from_dict(initial_state.to_dict()))

        plain_state = plain_engine.transition(analysis, time_context)
        extra_state = extra_engine.transition(
            analysis_with_extras, time_context_with_extras
        )

    assert extra_state.to_dict() == plain_state.to_dict()


@given(
    initial_state=state_strategy,
    analysis=mixed_analysis_strategy,
    time_context=mixed_time_context_strategy,
    hour=st.integers(min_value=0, max_value=23),
)
def test_transition_matches_exact_single_step_state_oracle_for_mixed_inputs(
    initial_state, analysis, time_context, hour
):
    expected_state = expected_transition_state(
        initial_state, analysis, time_context, hour
    )

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)
        actual_state = engine.transition(analysis, time_context)

    assert actual_state == expected_state


@given(
    initial_state=state_strategy,
    transitions=mixed_transition_sequences,
    hour=st.integers(min_value=0, max_value=23),
)
def test_transition_sequences_match_exact_prefix_oracle_for_mixed_inputs(
    initial_state, transitions, hour
):
    expected_state = PersonaState.from_dict(initial_state.to_dict())

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)

        for analysis, time_context in transitions:
            actual_state = engine.transition(analysis, time_context)
            expected_state = expected_transition_state(
                expected_state, analysis, time_context, hour
            )
            assert actual_state == expected_state


@given(
    initial_state=state_strategy,
    transitions=sparse_mixed_transition_sequences,
    hour=st.integers(min_value=0, max_value=23),
)
def test_sparse_mixed_transition_sequences_match_exact_prefix_oracle(
    initial_state, transitions, hour
):
    expected_state = PersonaState.from_dict(initial_state.to_dict())

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)

        for (
            analysis,
            analysis_fields,
            time_context,
            time_context_fields,
        ) in transitions:
            sparse_analysis = {
                field: analysis[field]
                for field, include in analysis_fields.items()
                if include
            }
            sparse_time_context = {
                field: time_context[field]
                for field, include in time_context_fields.items()
                if include
            }

            actual_state = engine.transition(sparse_analysis, sparse_time_context)
            expected_state = expected_transition_state(
                expected_state, sparse_analysis, sparse_time_context, hour
            )
            assert actual_state == expected_state


@given(
    initial_state=state_strategy,
    transitions=mixed_transition_sequences,
    hour=st.integers(min_value=0, max_value=23),
)
def test_returned_transition_states_remain_immutable_snapshots_across_future_updates(
    initial_state, transitions, hour
):
    history = []

    with patch("src.persona.engine.datetime", make_frozen_datetime(hour)):
        engine = PersonaEngine()
        engine.set_state(initial_state)

        for analysis, time_context in transitions:
            state = engine.transition(analysis, time_context)
            history.append((state, PersonaState.from_dict(state.to_dict())))

            for prior_state, snapshot in history:
                assert prior_state == snapshot

    assert len({id(state) for state, _ in history}) == len(history)
