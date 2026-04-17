import math
from datetime import datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from src.memory.decay import (
    FORGET_THRESHOLD,
    HALF_LIFE_MINIMAL,
    HALF_LIFE_NORMAL,
    INTERFERENCE_PENALTY,
    REACTIVATION_BOOST,
    RETRIEVAL_INDUCED_COMPETITOR_PENALTY,
    RETRIEVAL_THRESHOLD,
    DecayEngine,
)
from src.memory.episodic import EpisodicMemory
from src.persona.state import PersonaState


def make_memory():
    return EpisodicMemory(":memory:")


def store_fragment(memory: EpisodicMemory, user_input: str = "pain au levain") -> str:
    return memory.store(
        user_message=user_input,
        response="noted",
        session_id="session-1",
        persona_state=PersonaState(),
    )


def test_apply_decay_matches_exponential_half_life(monkeypatch):
    memory = make_memory()
    fragment_id = store_fragment(memory)
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ?, timestamp = ?, last_decay_at = ? WHERE id = ?",
        (
            0.8,
            (frozen_now - timedelta(days=HALF_LIFE_NORMAL)).isoformat(),
            (frozen_now - timedelta(days=HALF_LIFE_NORMAL)).isoformat(),
            fragment_id,
        ),
    )
    memory.conn.commit()

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    engine = DecayEngine(memory.conn, mode="normal")
    assert engine.apply_decay() == 1

    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()
    assert row["retrieval_weight"] == 0.4


def test_reactivate_boost_increases_retrieval_strength(monkeypatch):
    memory = make_memory()
    fragment_id = store_fragment(memory)
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ?, last_decay_at = ? WHERE id = ?",
        (0.25, frozen_now.isoformat(), fragment_id),
    )
    memory.conn.commit()

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    engine = DecayEngine(memory.conn)
    engine.reactivate(fragment_id)

    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()
    assert row["retrieval_weight"] == 0.25 + REACTIVATION_BOOST


def test_reactivate_falls_back_to_timestamp_when_last_decay_at_is_malformed(monkeypatch):
    memory = make_memory()
    fragment_id = store_fragment(memory, user_input="souvenir resilient")
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    baseline_weight = 0.8
    timestamp = frozen_now - timedelta(days=30)
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ?, timestamp = ?, last_decay_at = ? WHERE id = ?",
        (baseline_weight, timestamp.isoformat(), "not-a-timestamp", fragment_id),
    )
    memory.conn.commit()

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    DecayEngine(memory.conn, mode="normal").reactivate(fragment_id)
    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()

    expected = min(
        baseline_weight * (0.5 ** (30 / HALF_LIFE_NORMAL)) + REACTIVATION_BOOST,
        1.0,
    )
    assert math.isclose(row["retrieval_weight"], expected, rel_tol=1e-9)


def test_decay_modes_cover_sponge_normal_and_minimal(monkeypatch):
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    results = {}
    for mode in ("sponge", "normal", "minimal"):
        memory = make_memory()
        fragment_id = store_fragment(memory, user_input=mode)
        memory.conn.execute(
            "UPDATE conversations SET retrieval_weight = ?, timestamp = ?, last_decay_at = ? WHERE id = ?",
            (
                1.0,
                (frozen_now - timedelta(days=30)).isoformat(),
                (frozen_now - timedelta(days=30)).isoformat(),
                fragment_id,
            ),
        )
        memory.conn.commit()

        DecayEngine(memory.conn, mode=mode).apply_decay()
        row = memory.conn.execute(
            "SELECT retrieval_weight FROM conversations WHERE id = ?",
            (fragment_id,),
        ).fetchone()
        results[mode] = row["retrieval_weight"]

    assert results["sponge"] == 1.0
    assert results["normal"] == 0.5 ** (30 / HALF_LIFE_NORMAL)
    assert results["minimal"] == 0.5 ** (30 / HALF_LIFE_MINIMAL)


def test_invalid_decay_mode_falls_back_to_normal(monkeypatch):
    memory = make_memory()
    fragment_id = store_fragment(memory, user_input="mode inconnu")
    frozen_now = datetime(2026, 4, 17, 12, 0, 0)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return frozen_now
            return tz.fromutc(frozen_now.replace(tzinfo=tz))

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ?, timestamp = ?, last_decay_at = ? WHERE id = ?",
        (
            1.0,
            (frozen_now - timedelta(days=30)).isoformat(),
            (frozen_now - timedelta(days=30)).isoformat(),
            fragment_id,
        ),
    )
    memory.conn.commit()

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    DecayEngine(memory.conn, mode="mystery").apply_decay()
    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()

    assert row["retrieval_weight"] == 0.5 ** (30 / HALF_LIFE_NORMAL)


def test_apply_decay_is_incremental_across_multiple_days(monkeypatch):
    memory = make_memory()
    fragment_id = store_fragment(memory, user_input="souvenir incrementiel")
    day_ten = datetime(2026, 4, 10, 12, 0, 0)
    day_eleven = day_ten + timedelta(days=1)

    class FrozenDateTime(datetime):
        current = day_ten

        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls.current
            return tz.fromutc(cls.current.replace(tzinfo=tz))

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ?, timestamp = ?, last_decay_at = ? WHERE id = ?",
        (
            1.0,
            (day_ten - timedelta(days=10)).isoformat(),
            (day_ten - timedelta(days=10)).isoformat(),
            fragment_id,
        ),
    )
    memory.conn.commit()

    monkeypatch.setattr("src.memory.decay.datetime", FrozenDateTime)

    engine = DecayEngine(memory.conn, mode="normal")
    assert engine.apply_decay() == 1

    FrozenDateTime.current = day_eleven
    assert engine.apply_decay() == 1

    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()
    expected = 0.5 ** (11 / HALF_LIFE_NORMAL)
    assert math.isclose(row["retrieval_weight"], expected, rel_tol=1e-9)


def test_search_excludes_fragments_below_retrieval_threshold():
    memory = make_memory()
    kept_id = store_fragment(memory, user_input="projet boulangerie")
    hidden_id = store_fragment(memory, user_input="projet boulangerie")
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (RETRIEVAL_THRESHOLD, kept_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (RETRIEVAL_THRESHOLD - 0.01, hidden_id),
    )
    memory.conn.commit()

    results = memory.search("projet boulangerie", n_results=10)

    assert [row["id"] for row in results] == [kept_id]


def test_get_stats_marks_fragments_below_forget_threshold_as_forgotten():
    memory = make_memory()
    forgotten_id = store_fragment(memory, user_input="vieux souvenir")
    fading_id = store_fragment(memory, user_input="souvenir fragile")
    active_id = store_fragment(memory, user_input="souvenir vif")
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (FORGET_THRESHOLD / 2, forgotten_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        ((RETRIEVAL_THRESHOLD + FORGET_THRESHOLD) / 2, fading_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.9, active_id),
    )
    memory.conn.commit()

    stats = DecayEngine(memory.conn).get_stats()

    assert stats["forgotten"] == 1
    assert stats["fading"] == 1
    assert stats["accessible"] == 1


def test_null_retrieval_weight_defaults_to_accessible_and_reactivates():
    memory = make_memory()
    fragment_id = store_fragment(memory, user_input="souvenir ancien")
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = NULL WHERE id = ?",
        (fragment_id,),
    )
    memory.conn.commit()

    stats_before = DecayEngine(memory.conn).get_stats()
    assert stats_before["accessible"] == 1

    DecayEngine(memory.conn).reactivate(fragment_id)
    row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()

    assert row["retrieval_weight"] == 1.0


def test_reactivate_related_logs_search_failures(caplog):
    engine = DecayEngine(make_memory().conn)

    class FailingEpisodic:
        def search(self, *_args, **_kwargs):
            raise RuntimeError("fts unavailable")

    with caplog.at_level("WARNING", logger="delirium.memory.decay"):
        engine.reactivate_related("boulangerie", FailingEpisodic())

    assert "fts unavailable" in caplog.text


def test_interference_strategy_weakens_competing_memories():
    memory = make_memory()
    strongest_id = store_fragment(memory, user_input="projet boulangerie")
    competitor_id = store_fragment(memory, user_input="projet boulangerie")
    outsider_id = store_fragment(memory, user_input="astronomie")

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.6, strongest_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.5, competitor_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.4, outsider_id),
    )
    memory.conn.commit()

    engine = DecayEngine(memory.conn, strategy="interference")
    engine.reactivate_related("projet boulangerie", memory)

    strongest_row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (strongest_id,),
    ).fetchone()
    competitor_row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (competitor_id,),
    ).fetchone()
    outsider_row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (outsider_id,),
    ).fetchone()

    assert math.isclose(
        strongest_row["retrieval_weight"],
        min(0.6 + REACTIVATION_BOOST, 1.0),
        rel_tol=1e-9,
    )
    assert competitor_row["retrieval_weight"] == max(0.5 - INTERFERENCE_PENALTY, 0.0)
    assert outsider_row["retrieval_weight"] == 0.4


def test_retrieval_induced_strategy_strengthens_target_and_suppresses_competitors():
    memory = make_memory()
    target_id = store_fragment(memory, user_input="souvenir voyage")
    competitor_id = store_fragment(memory, user_input="souvenir voyage")

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.55, target_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.5, competitor_id),
    )
    memory.conn.commit()

    engine = DecayEngine(memory.conn, strategy="retrieval_induced")
    engine.reactivate_related("souvenir voyage", memory)

    target_row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (target_id,),
    ).fetchone()
    competitor_row = memory.conn.execute(
        "SELECT retrieval_weight FROM conversations WHERE id = ?",
        (competitor_id,),
    ).fetchone()

    assert math.isclose(
        target_row["retrieval_weight"],
        min(0.55 + REACTIVATION_BOOST, 1.0),
        rel_tol=1e-9,
    )
    assert competitor_row["retrieval_weight"] == max(
        0.5 - RETRIEVAL_INDUCED_COMPETITOR_PENALTY,
        0.0,
    )


def test_invalid_strategy_falls_back_to_decay_without_penalizing_competitors():
    memory = make_memory()
    first_id = store_fragment(memory, user_input="memoire partagee")
    second_id = store_fragment(memory, user_input="memoire partagee")
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.4, first_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.3, second_id),
    )
    memory.conn.commit()

    engine = DecayEngine(memory.conn, strategy="mystery")
    engine.reactivate_related("memoire partagee", memory)

    rows = memory.conn.execute(
        "SELECT id, retrieval_weight FROM conversations WHERE id IN (?, ?) ORDER BY id",
        (first_id, second_id),
    ).fetchall()
    weights = {row["id"]: row["retrieval_weight"] for row in rows}

    assert math.isclose(
        weights[first_id],
        min(0.4 + REACTIVATION_BOOST, 1.0),
        rel_tol=1e-9,
    )
    assert math.isclose(
        weights[second_id],
        min(0.3 + REACTIVATION_BOOST, 1.0),
        rel_tol=1e-9,
    )


def test_invalid_legacy_weights_are_clamped_when_touched():
    memory = make_memory()
    heavy_id = store_fragment(memory, user_input="souvenir lourd")
    weak_id = store_fragment(memory, user_input="souvenir concurrent")
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (1.7, heavy_id),
    )
    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (-0.2, weak_id),
    )
    memory.conn.commit()

    engine = DecayEngine(memory.conn, strategy="retrieval_induced")
    engine.reactivate_related("souvenir", memory)

    rows = memory.conn.execute(
        "SELECT id, retrieval_weight FROM conversations WHERE id IN (?, ?)",
        (heavy_id, weak_id),
    ).fetchall()
    weights = {row["id"]: row["retrieval_weight"] for row in rows}

    assert weights[heavy_id] == 1.0
    assert weights[weak_id] == 0.0


@given(
    initial_weight=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    days_short=st.floats(min_value=0.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    extra_days=st.floats(min_value=0.0, max_value=180.0, allow_nan=False, allow_infinity=False),
    half_life=st.sampled_from((HALF_LIFE_NORMAL, HALF_LIFE_MINIMAL)),
)
def test_decay_curve_stays_bounded_and_monotonic(initial_weight, days_short, extra_days, half_life):
    weight_short = initial_weight * (0.5 ** (days_short / half_life))
    weight_long = initial_weight * (0.5 ** ((days_short + extra_days) / half_life))

    assert 0.0 <= weight_short <= 1.0
    assert 0.0 <= weight_long <= 1.0
    assert weight_long <= weight_short + 1e-12
