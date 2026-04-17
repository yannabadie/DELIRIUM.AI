import json

import numpy as np

from src.memory.episodic import EpisodicMemory
from src.persona.state import PersonaState


def make_memory() -> EpisodicMemory:
    return EpisodicMemory(":memory:")


def make_state(**overrides) -> PersonaState:
    base = {
        "H": 0.2,
        "phase": "reflection",
        "trigger": "unit-test",
    }
    base.update(overrides)
    return PersonaState(**base)


def test_store_search_and_session_counters_round_trip_fragments():
    memory = make_memory()

    first_id = memory.store(
        user_message="I keep thinking about the silver orchard at dusk",
        response="The orchard keeps coming back to you.",
        session_id="session-a",
        persona_state=make_state(H=0.4, phase="probing"),
        source="delirium",
    )
    second_id = memory.store(
        user_message="The orchard turned into a glass labyrinth",
        response="That image is sharper now.",
        session_id="session-a",
        persona_state=make_state(H=0.6, phase="reflection"),
        source="import",
    )
    memory.store(
        user_message="A separate session remembers the red tram",
        response="The tram belongs to another thread.",
        session_id="session-b",
        persona_state=make_state(),
    )

    assert first_id != second_id
    assert memory.get_session_message_count("session-a") == 2
    assert memory.get_session_message_count("session-b") == 1
    assert memory.get_total_sessions() == 2
    assert memory.get_fragment_count() == 3
    assert memory.get_fragment_count(source="import") == 1

    search_results = memory.search("orchard glass", n_results=5)

    assert [row["id"] for row in search_results] == [second_id]
    assert search_results[0]["source"] == "import"
    assert search_results[0]["phase"] == "reflection"

    recent_messages = memory.get_recent("session-a")

    assert recent_messages == [
        {"role": "user", "content": "I keep thinking about the silver orchard at dusk"},
        {"role": "assistant", "content": "The orchard keeps coming back to you."},
        {"role": "user", "content": "The orchard turned into a glass labyrinth"},
        {"role": "assistant", "content": "That image is sharper now."},
    ]


def test_get_recent_limit_returns_most_recent_fragments_in_chat_order():
    memory = make_memory()
    state = make_state()

    memory.store("first user", "first reply", "session-a", state)
    memory.store("second user", "second reply", "session-a", state)
    memory.store("third user", "third reply", "session-a", state)

    recent_messages = memory.get_recent("session-a", limit=2)

    assert recent_messages == [
        {"role": "user", "content": "second user"},
        {"role": "assistant", "content": "second reply"},
        {"role": "user", "content": "third user"},
        {"role": "assistant", "content": "third reply"},
    ]


def test_get_all_with_embeddings_round_trips_numpy_vectors():
    memory = make_memory()
    embedding = np.array([0.25, -0.5, 1.25], dtype=np.float32)

    fragment_id = memory.store(
        user_message="Embedding payload",
        response="Stored with vector.",
        session_id="session-emb",
        persona_state=make_state(),
        embedding=embedding,
        source="delirium",
    )

    rows = memory.get_all_with_embeddings()

    assert len(rows) == 1
    assert rows[0]["id"] == fragment_id
    assert rows[0]["session_id"] == "session-emb"
    np.testing.assert_array_equal(rows[0]["embedding"], embedding)


def test_get_all_with_embeddings_skips_rows_with_corrupted_embedding_blobs():
    memory = make_memory()
    valid_embedding = np.array([0.1, 0.2, 0.3], dtype=np.float32)

    valid_id = memory.store(
        user_message="Valid embedding payload",
        response="Keeps its vector.",
        session_id="session-emb",
        persona_state=make_state(),
        embedding=valid_embedding,
    )
    corrupted_id = memory.store(
        user_message="Corrupted embedding payload",
        response="Blob is manually damaged.",
        session_id="session-emb",
        persona_state=make_state(),
        embedding=np.array([0.4, 0.5, 0.6], dtype=np.float32),
    )

    memory.conn.execute(
        "UPDATE conversations SET embedding = ? WHERE id = ?",
        (b"\x01\x02\x03", corrupted_id),
    )
    memory.conn.commit()

    rows = memory.get_all_with_embeddings()

    assert [row["id"] for row in rows] == [valid_id]
    np.testing.assert_array_equal(rows[0]["embedding"], valid_embedding)


def test_update_helpers_persist_embedding_and_sycophancy_score():
    memory = make_memory()
    fragment_id = memory.store(
        user_message="Mutable fragment",
        response="Starts without derived fields.",
        session_id="session-update",
        persona_state=make_state(),
    )

    updated_embedding = np.array([1.5, 0.0, -2.5], dtype=np.float32)

    memory.update_embedding(fragment_id, updated_embedding)
    memory.update_sycophancy_score(fragment_id, 0.37)

    row = memory.conn.execute(
        "SELECT sycophancy_score FROM conversations WHERE id = ?",
        (fragment_id,),
    ).fetchone()

    assert row["sycophancy_score"] == 0.37
    np.testing.assert_array_equal(
        memory.get_all_with_embeddings()[0]["embedding"],
        updated_embedding,
    )


def test_search_escapes_fts_syntax_and_filters_blank_queries():
    memory = make_memory()
    kept_id = memory.store(
        user_message='The orchard\'s "echo" keeps returning',
        response="Quoted fragments still index cleanly.",
        session_id="session-search",
        persona_state=make_state(),
    )

    search_results = memory.search('orchard\'s "echo"', n_results=5)

    assert len(search_results) == 1
    assert search_results[0]["id"] == kept_id
    assert search_results[0]["user_input"] == 'The orchard\'s "echo" keeps returning'
    assert memory.search("   ", n_results=5) == []


def test_search_filters_out_fragments_below_retrieval_weight_threshold():
    memory = make_memory()
    kept_id = memory.store(
        user_message="orchard memory stays retrievable",
        response="high weight fragment",
        session_id="session-search-weights",
        persona_state=make_state(),
    )
    filtered_id = memory.store(
        user_message="orchard memory should be forgotten",
        response="low weight fragment",
        session_id="session-search-weights",
        persona_state=make_state(),
    )

    memory.conn.execute(
        "UPDATE conversations SET retrieval_weight = ? WHERE id = ?",
        (0.05, filtered_id),
    )
    memory.conn.commit()

    default_results = memory.search("orchard memory", n_results=5)
    inclusive_results = memory.search(
        "orchard memory",
        n_results=5,
        min_retrieval_weight=0.0,
    )

    assert [row["id"] for row in default_results] == [kept_id]
    assert default_results[0]["retrieval_weight"] == 1.0
    assert {row["id"] for row in inclusive_results} == {kept_id, filtered_id}


def test_collisions_can_be_detected_ranked_and_marked_delivered():
    memory = make_memory()
    state = make_state()
    fragment_a = memory.store("mirror room", "response a", "session-a", state)
    fragment_b = memory.store("mirror hallway", "response b", "session-b", state)
    fragment_c = memory.store("clock tower", "response c", "session-c", state)

    first_collision = memory.store_collision(
        fragment_a,
        fragment_b,
        score=0.61,
        connection="mirror imagery",
    )
    memory.store_collision(
        fragment_b,
        fragment_c,
        score=0.93,
        connection="distorted architecture",
    )

    assert memory.get_collision_count() == 2
    assert memory.collision_already_exists(fragment_a, fragment_b) is True
    assert memory.collision_already_exists(fragment_b, fragment_a) is True
    assert memory.collision_already_exists(fragment_a, fragment_c) is False

    pending = memory.get_pending_collision()

    assert pending["fragment_a_id"] == fragment_b
    assert pending["fragment_b_id"] == fragment_c
    assert pending["connection"] == "distorted architecture"
    assert pending["a_input"] == "mirror hallway"
    assert pending["b_input"] == "clock tower"

    memory.mark_collision_delivered(first_collision, "session-z")

    assert memory.collision_delivered_this_session("session-z") is True
    assert memory.collision_delivered_this_session("session-y") is False


def test_purge_collisions_clears_pending_queue_and_reports_deleted_count():
    memory = make_memory()
    state = make_state()
    fragment_a = memory.store("alpha", "response a", "session-a", state)
    fragment_b = memory.store("beta", "response b", "session-b", state)
    fragment_c = memory.store("gamma", "response c", "session-c", state)

    memory.store_collision(fragment_a, fragment_b, score=0.41, connection="letters")
    memory.store_collision(fragment_b, fragment_c, score=0.72, connection="sequence")

    assert memory.purge_collisions() == 2
    assert memory.get_collision_count() == 0
    assert memory.get_pending_collision() is None


def test_persona_state_persistence_returns_latest_saved_state():
    memory = make_memory()

    older = make_state(H=-0.2, phase="silent", trigger="older")
    newer = make_state(H=0.9, phase="sparring", trigger="newer")

    memory.save_persona_state(older)
    memory.save_persona_state(newer)

    loaded = memory.load_latest_persona_state()

    assert loaded is not None
    assert loaded.H == 0.9
    assert loaded.phase == "sparring"
    assert loaded.trigger == "newer"


def test_load_latest_persona_state_skips_corrupted_newer_rows():
    memory = make_memory()
    valid_state = make_state(H=0.4, phase="reflection", trigger="valid")

    memory.save_persona_state(valid_state)
    memory.conn.execute(
        "INSERT INTO persona_history (id, state_json, timestamp) VALUES (?, ?, ?)",
        ("corrupted-state", "{not valid json", "9999-12-31T23:59:59"),
    )
    memory.conn.commit()

    loaded = memory.load_latest_persona_state()

    assert loaded is not None
    assert loaded.H == 0.4
    assert loaded.phase == "reflection"
    assert loaded.trigger == "valid"


def test_log_execution_persists_json_for_fragment_and_global_events():
    memory = make_memory()
    fragment_id = memory.store(
        user_message="Need logs",
        response="Logging enabled.",
        session_id="session-log",
        persona_state=make_state(),
    )

    memory.log_execution(fragment_id, "s2_analysis", {"score": 0.8, "theme": "orchard"})
    memory.log_execution(None, "github_import", {"count": 2})

    rows = memory.conn.execute(
        "SELECT fragment_id, log_type, content FROM execution_logs ORDER BY timestamp ASC"
    ).fetchall()

    assert len(rows) == 2
    assert rows[0]["fragment_id"] == fragment_id
    assert rows[0]["log_type"] == "s2_analysis"
    assert json.loads(rows[0]["content"]) == {"score": 0.8, "theme": "orchard"}
    assert rows[1]["fragment_id"] is None
    assert json.loads(rows[1]["content"]) == {"count": 2}
