import asyncio
from types import SimpleNamespace

import src.main as main_module
from src.main import Delirium


class StubEpisodicMemory:
    def __init__(self):
        self.logs = []
        self.stores = []

    def search(self, _query, n_results=5):
        return []

    def get_pending_collision(self):
        return None

    def get_recent(self, _session_id, limit=20):
        return [{"role": "assistant", "content": "memo"}]

    def store(self, user_message, response, session_id, state, **kwargs):
        self.stores.append(
            {
                "user_message": user_message,
                "response": response,
                "session_id": session_id,
                "state": state,
                "kwargs": kwargs,
            }
        )
        return "frag-1"

    def log_execution(self, fragment_id, log_type, content):
        self.logs.append((fragment_id, log_type, content))


class StubS2Analyzer:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def analyze(self, fragment_id, user_message, s1_response, session_messages, session_id):
        self.calls.append(
            {
                "fragment_id": fragment_id,
                "user_message": user_message,
                "s1_response": s1_response,
                "session_messages": session_messages,
                "session_id": session_id,
            }
        )
        return self.result


class StubGags:
    def __init__(self, seed=None, register_result=("gag-1", True), register_exc=None):
        self.seed = seed
        self.register_result = register_result
        self.register_exc = register_exc
        self.detect_calls = []
        self.register_calls = []

    def get_gag_context_for_s1(self):
        return None

    def detect_seed(self, s2_result):
        self.detect_calls.append(s2_result)
        return self.seed

    def register_or_refresh_gag(self, seed, gag_type, *, user_callback=False):
        self.register_calls.append(
            {
                "seed": seed,
                "type": gag_type,
                "user_callback": user_callback,
            }
        )
        if self.register_exc is not None:
            raise self.register_exc
        return self.register_result


def make_delirium_for_process_tests(gags, s2_result):
    delirium = Delirium.__new__(Delirium)
    state = SimpleNamespace(H=0.2, phase="baseline")
    delirium.persona_engine = SimpleNamespace(get_current_state=lambda: state)
    delirium.decay = SimpleNamespace(reactivate_related=lambda *args, **kwargs: None)
    delirium.episodic = StubEpisodicMemory()
    delirium.semantic = SimpleNamespace(get_active_themes=lambda: [])
    delirium.working = SimpleNamespace(compose_s1_prompt=lambda *args, **kwargs: "s1 prompt")
    delirium.world_vision = SimpleNamespace(get_summary_for_s1=lambda: None)
    delirium.gags = gags
    delirium.s2 = StubS2Analyzer(s2_result)
    delirium.embedder = SimpleNamespace(embed=lambda _text: [1.0, 0.0])
    delirium._collision_delivered = False
    delirium.session_id = "session-1"
    delirium._stream_response = lambda _system, _messages: "assistant reply"
    delirium._maybe_resynthesize_world_vision = (
        lambda loop, fragment_id, s2_result: None
    )
    return delirium


def test_process_message_registers_detected_gag_after_s2_analysis(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    s2_result = {
        "danger_level": 1,
        "recurring_minor_elements": [
            {
                "content": "la fourchette quantique",
                "count": 2,
                "importance": 0.2,
                "user_reaction": "callback",
            }
        ],
    }
    gags = StubGags(
        seed={
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
        },
        register_result=("gag-42", True),
    )
    delirium = make_delirium_for_process_tests(gags, s2_result)

    response = delirium.process_message("bonjour")

    assert response == "assistant reply"
    assert gags.detect_calls == [s2_result]
    assert gags.register_calls == [
        {
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
        }
    ]
    assert delirium.s2.calls == [
        {
            "fragment_id": "frag-1",
            "user_message": "bonjour",
            "s1_response": "assistant reply",
            "session_messages": [
                {"role": "assistant", "content": "memo"},
                {"role": "user", "content": "bonjour"},
                {"role": "assistant", "content": "assistant reply"},
            ],
            "session_id": "session-1",
        }
    ]
    assert delirium.episodic.logs == [
        (
            "frag-1",
            "s1_response",
            {
                "H": 0.2,
                "phase": "baseline",
                "collision_injected": False,
                "response_novelty": 0.0,
            },
        ),
        (
            "frag-1",
            "gag_detected",
            {
                "gag_id": "gag-42",
                "seed": "la fourchette quantique",
                "type": "object_callback",
                "user_callback": True,
                "created": True,
            },
        ),
    ]


def test_process_message_logs_gag_error_without_aborting_response(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    s2_result = {"danger_level": 0, "recurring_minor_elements": []}
    gags = StubGags(
        seed={
            "seed": "la tasse litigieuse",
            "type": "ritual",
            "user_callback": False,
        },
        register_exc=RuntimeError("gag storage unavailable"),
    )
    delirium = make_delirium_for_process_tests(gags, s2_result)

    response = delirium.process_message("bonjour encore")

    assert response == "assistant reply"
    assert gags.detect_calls == [s2_result]
    assert gags.register_calls == [
        {
            "seed": "la tasse litigieuse",
            "type": "ritual",
            "user_callback": False,
        }
    ]
    assert delirium.episodic.logs == [
        (
            "frag-1",
            "s1_response",
            {
                "H": 0.2,
                "phase": "baseline",
                "collision_injected": False,
                "response_novelty": 0.0,
            },
        ),
        ("frag-1", "gag_error", {"error": "gag storage unavailable"}),
    ]


def test_process_message_returns_response_when_gag_detected_logging_fails(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    gags = StubGags(
        seed={
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
        },
        register_result=("gag-99", True),
    )
    delirium = make_delirium_for_process_tests(
        gags,
        {"danger_level": 1, "recurring_minor_elements": []},
    )

    original_log_execution = delirium.episodic.log_execution

    def selective_log_failure(fragment_id, log_type, content):
        if log_type == "gag_detected":
            raise RuntimeError("episodic log unavailable")
        original_log_execution(fragment_id, log_type, content)

    delirium.episodic.log_execution = selective_log_failure

    response = delirium.process_message("bonjour encore")

    assert response == "assistant reply"
    assert gags.detect_calls == [{"danger_level": 1, "recurring_minor_elements": []}]
    assert gags.register_calls == [
        {
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
        }
    ]
    assert delirium.episodic.logs == [
        (
            "frag-1",
            "s1_response",
            {
                "H": 0.2,
                "phase": "baseline",
                "collision_injected": False,
                "response_novelty": 0.0,
            },
        ),
    ]


def test_process_message_returns_response_when_gag_error_logging_fails(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    gags = StubGags(
        seed={
            "seed": "la tasse litigieuse",
            "type": "ritual",
            "user_callback": False,
        },
        register_exc=RuntimeError("gag storage unavailable"),
    )
    delirium = make_delirium_for_process_tests(
        gags,
        {"danger_level": 0, "recurring_minor_elements": []},
    )

    original_log_execution = delirium.episodic.log_execution

    def selective_log_failure(fragment_id, log_type, content):
        if log_type == "gag_error":
            raise RuntimeError("episodic log unavailable")
        original_log_execution(fragment_id, log_type, content)

    delirium.episodic.log_execution = selective_log_failure

    response = delirium.process_message("bonjour encore")

    assert response == "assistant reply"
    assert gags.detect_calls == [{"danger_level": 0, "recurring_minor_elements": []}]
    assert gags.register_calls == [
        {
            "seed": "la tasse litigieuse",
            "type": "ritual",
            "user_callback": False,
        }
    ]
    assert delirium.episodic.logs == [
        (
            "frag-1",
            "s1_response",
            {
                "H": 0.2,
                "phase": "baseline",
                "collision_injected": False,
                "response_novelty": 0.0,
            },
        ),
    ]


def test_process_message_returns_response_when_s1_response_logging_fails(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    gags = StubGags(seed=None)
    delirium = make_delirium_for_process_tests(
        gags,
        {"danger_level": 0, "recurring_minor_elements": []},
    )

    def selective_log_failure(fragment_id, log_type, content):
        if log_type == "s1_response":
            raise RuntimeError("episodic log unavailable")
        delirium.episodic.logs.append((fragment_id, log_type, content))

    delirium.episodic.log_execution = selective_log_failure

    response = delirium.process_message("bonjour encore")

    assert response == "assistant reply"
    assert gags.detect_calls == [{"danger_level": 0, "recurring_minor_elements": []}]
    assert gags.register_calls == []
    assert delirium.episodic.logs == []


def test_world_vision_resynthesis_survives_success_logging_failure():
    delirium = Delirium.__new__(Delirium)
    delirium.semantic = SimpleNamespace(
        get_active_themes=lambda threshold=0.0: ["motif"],
        get_correlations=lambda: [],
        get_loops=lambda: [],
    )
    delirium.world_vision = SimpleNamespace(
        get_sessions_since_last_vision=lambda: 3,
        should_resynthesize=lambda s2_result, sessions_since: True,
        resynthesize=lambda *args: {"version": 2},
        get_danger_history=lambda: [1, 2],
    )
    delirium.episodic = SimpleNamespace(
        get_fragment_count=lambda: 7,
        log_execution=lambda fragment_id, log_type, content: (
            (_ for _ in ()).throw(RuntimeError("episodic log unavailable"))
            if log_type == "world_vision_resynthesized"
            else None
        ),
    )

    loop = asyncio.new_event_loop()
    try:
        delirium._maybe_resynthesize_world_vision(loop, "frag-1", {"danger_level": 2})
    finally:
        loop.close()


def test_world_vision_resynthesis_survives_error_logging_failure():
    delirium = Delirium.__new__(Delirium)
    delirium.semantic = SimpleNamespace(
        get_active_themes=lambda threshold=0.0: ["motif"],
        get_correlations=lambda: [],
        get_loops=lambda: [],
    )
    delirium.world_vision = SimpleNamespace(
        get_sessions_since_last_vision=lambda: 3,
        should_resynthesize=lambda s2_result, sessions_since: True,
        resynthesize=lambda *args: (_ for _ in ()).throw(RuntimeError("vision unavailable")),
        get_danger_history=lambda: [1, 2],
    )
    delirium.episodic = SimpleNamespace(
        get_fragment_count=lambda: 7,
        log_execution=lambda fragment_id, log_type, content: (
            (_ for _ in ()).throw(RuntimeError("episodic log unavailable"))
            if log_type == "world_vision_resynthesis_error"
            else None
        ),
    )

    loop = asyncio.new_event_loop()
    try:
        delirium._maybe_resynthesize_world_vision(loop, "frag-1", {"danger_level": 2})
    finally:
        loop.close()


def test_process_message_normalizes_detected_gag_payload_before_register_and_log(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    gags = StubGags(
        seed={
            "seed": "  la fourchette quantique  \n",
            "type": "Object Callback",
            "user_callback": "yes",
        },
        register_result=("gag-77", False),
    )
    delirium = make_delirium_for_process_tests(
        gags,
        {"danger_level": 0, "recurring_minor_elements": []},
    )

    response = delirium.process_message("salut")

    assert response == "assistant reply"
    assert gags.register_calls == [
        {
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
        }
    ]
    assert delirium.episodic.logs[-1] == (
        "frag-1",
        "gag_detected",
        {
            "gag_id": "gag-77",
            "seed": "la fourchette quantique",
            "type": "object_callback",
            "user_callback": True,
            "created": False,
        },
    )


def test_process_message_ignores_malformed_detected_gag_payload(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)

    gags = StubGags(seed={"seed": "   ", "type": "ritual", "user_callback": True})
    delirium = make_delirium_for_process_tests(
        gags,
        {"danger_level": 0, "recurring_minor_elements": []},
    )

    response = delirium.process_message("bonjour bis")

    assert response == "assistant reply"
    assert gags.detect_calls == [{"danger_level": 0, "recurring_minor_elements": []}]
    assert gags.register_calls == []
    assert delirium.episodic.logs == [
        (
            "frag-1",
            "s1_response",
            {
                "H": 0.2,
                "phase": "baseline",
                "collision_injected": False,
                "response_novelty": 0.0,
            },
        ),
    ]


def test_generate_first_message_returns_response_when_first_message_logging_fails(monkeypatch):
    printed = []
    monkeypatch.setattr(main_module, "behavioral_reply", lambda instruction: "premier bonjour")
    monkeypatch.setattr(main_module.console, "print", lambda *args, **kwargs: printed.append(args))

    delirium = Delirium.__new__(Delirium)
    state = SimpleNamespace(H=0.2, phase="baseline")
    delirium.persona_engine = SimpleNamespace(get_current_state=lambda: state)
    delirium.retrait_state = "active"
    delirium.world_vision = SimpleNamespace(get_summary_for_s1=lambda: None)
    delirium.gags = SimpleNamespace(get_gag_context_for_s1=lambda: None)
    delirium.working = SimpleNamespace(compose_s1_prompt=lambda *args, **kwargs: "s1 prompt")
    delirium.embedder = SimpleNamespace(embed=lambda _text: [1.0, 0.0])
    delirium.session_id = "session-1"
    delirium.episodic = StubEpisodicMemory()

    original_log_execution = delirium.episodic.log_execution

    def selective_log_failure(fragment_id, log_type, content):
        if log_type == "first_message":
            raise RuntimeError("episodic log unavailable")
        original_log_execution(fragment_id, log_type, content)

    delirium.episodic.log_execution = selective_log_failure

    response = delirium.generate_first_message()

    assert response == "premier bonjour"
    assert delirium.episodic.logs == []
    assert delirium.episodic.stores == [
        {
            "user_message": "[premier_message]",
            "response": "premier bonjour",
            "session_id": "session-1",
            "state": state,
            "kwargs": {"embedding": [1.0, 0.0]},
        }
    ]
    assert printed[1] == ("[delirium]Delirium:[/delirium] ",)
