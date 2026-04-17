import src.main as main_module
from src.main import Delirium
from src.memory.bubble import classify_injection_followup
from src.memory.working import WorkingMemory
from src.persona.state import PersonaState


class RecordingWorkingMemory:
    def __init__(self):
        self.calls = []

    def compose_s1_prompt(
        self,
        persona_state,
        relevant_memories,
        active_themes,
        pending_collision=None,
        **kwargs,
    ):
        state_snapshot = {
            "bubble_break_enabled": getattr(persona_state, "bubble_break_enabled", None),
            "bubble_risk_status": getattr(persona_state, "bubble_risk_status", None),
            "bubble_break_intensity": getattr(persona_state, "bubble_break_intensity", None),
            "bubble_ignore_streak": getattr(persona_state, "bubble_ignore_streak", None),
        }
        self.calls.append(
            {
                "state": persona_state,
                "state_snapshot": state_snapshot,
                "relevant_memories": relevant_memories,
                "active_themes": active_themes,
                "pending_collision": pending_collision,
                "kwargs": kwargs,
            }
        )
        return "s1 prompt"


class StubEpisodicMemory:
    def __init__(self, session_counts):
        self.conn = object()
        self.logs = []
        self.stores = []
        self._session_counts = list(session_counts)
        self._last_session_count = self._session_counts[-1]
        self._store_index = 0

    def search(self, _query, n_results=5):
        return []

    def get_pending_collision(self):
        return None

    def get_recent(self, _session_id, limit=20):
        return []

    def get_total_sessions(self):
        return 4

    def get_session_message_count(self, _session_id):
        if self._session_counts:
            self._last_session_count = self._session_counts.pop(0)
        return self._last_session_count

    def store(self, user_message, response, session_id, state, **kwargs):
        self._store_index += 1
        fragment_id = f"frag-{self._store_index}"
        self.stores.append(
            {
                "fragment_id": fragment_id,
                "user_message": user_message,
                "response": response,
                "session_id": session_id,
                "state": state,
                "kwargs": kwargs,
            }
        )
        return fragment_id

    def log_execution(self, fragment_id, log_type, content):
        self.logs.append((fragment_id, log_type, content))


class StubGags:
    def get_gag_context_for_s1(self):
        return None

    def detect_seed(self, s2_result):
        return None


class StubS2Analyzer:
    def __init__(self):
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
        return {"danger_level": 0, "recurring_minor_elements": []}


def make_delirium_for_bubble_tests(
    *,
    state=None,
    session_counts=(4,),
    responses=("assistant reply",),
):
    delirium = Delirium.__new__(Delirium)
    persona_state = state or PersonaState()
    response_queue = list(responses)
    working = RecordingWorkingMemory()

    delirium.persona_engine = type(
        "StubPersonaEngine",
        (),
        {"get_current_state": lambda self: persona_state},
    )()
    delirium.decay = type(
        "StubDecay",
        (),
        {
            "apply_decay": lambda self: None,
            "reactivate_related": lambda self, *args, **kwargs: None,
        },
    )()
    delirium.episodic = StubEpisodicMemory(session_counts)
    delirium.semantic = type("StubSemantic", (), {"get_active_themes": lambda self: []})()
    delirium.working = working
    delirium.world_vision = type("StubVision", (), {"get_summary_for_s1": lambda self: None})()
    delirium.gags = StubGags()
    delirium.s2 = StubS2Analyzer()
    delirium.embedder = type("StubEmbedder", (), {"embed": lambda self, _text: [1.0, 0.0]})()
    delirium._collision_delivered = False
    delirium.session_id = "session-1"
    delirium._maybe_resynthesize_world_vision = lambda loop, fragment_id, s2_result: None
    delirium._stream_response = lambda _system, _messages: response_queue.pop(0)

    return delirium, persona_state, working


def test_medium_risk_triggers_bubble_injection_flag(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.48, "bubble_status": "medium_risk"},
    )

    delirium, _, working = make_delirium_for_bubble_tests()

    delirium.process_message("On tourne encore autour du meme sujet politique.")

    injected_state = working.calls[0]["state_snapshot"]
    assert injected_state["bubble_break_enabled"] is True
    assert injected_state["bubble_risk_status"] == "medium_risk"
    assert injected_state["bubble_break_intensity"] == "gentle"


def test_high_risk_triggers_stronger_bubble_injection(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.81, "bubble_status": "high_risk"},
    )

    delirium, _, working = make_delirium_for_bubble_tests()

    delirium.process_message("Oui mais eux mentent encore, c'est clair.")

    injected_state = working.calls[0]["state_snapshot"]
    assert injected_state["bubble_break_enabled"] is True
    assert injected_state["bubble_risk_status"] == "high_risk"
    assert injected_state["bubble_break_intensity"] == "strong"


def test_bubble_injection_happens_at_most_once_per_session(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.83, "bubble_status": "high_risk"},
    )

    delirium, _, working = make_delirium_for_bubble_tests(
        session_counts=(4, 9),
        responses=("Rien à voir mais les pieuvres changent de couleur pour cooperer.", "assistant reply"),
    )

    delirium.process_message("Le vrai sujet c'est toujours eux.")
    delirium.process_message("Bref, comme je disais, ils cachent tout.")

    assert working.calls[0]["state_snapshot"]["bubble_break_enabled"] is True
    assert working.calls[1]["state_snapshot"]["bubble_break_enabled"] is False


def test_ascii_rien_a_voir_reply_still_consumes_session_budget(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.83, "bubble_status": "high_risk"},
    )

    delirium, _, working = make_delirium_for_bubble_tests(
        session_counts=(4, 9),
        responses=("Rien a voir mais les pieuvres changent de couleur.", "assistant reply"),
    )

    delirium.process_message("Le vrai sujet c'est toujours eux.")
    delirium.process_message("Bref, comme je disais, ils cachent tout.")

    assert working.calls[0]["state_snapshot"]["bubble_break_enabled"] is True
    assert working.calls[1]["state_snapshot"]["bubble_break_enabled"] is False


def test_punctuated_rien_a_voir_reply_still_consumes_session_budget(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.83, "bubble_status": "high_risk"},
    )

    delirium, _, working = make_delirium_for_bubble_tests(
        session_counts=(4, 9),
        responses=("Rien à voir... mais les pieuvres changent de couleur.", "assistant reply"),
    )

    delirium.process_message("Le vrai sujet c'est toujours eux.")
    delirium.process_message("Bref, comme je disais, ils cachent tout.")

    assert working.calls[0]["state_snapshot"]["bubble_break_enabled"] is True
    assert working.calls[1]["state_snapshot"]["bubble_break_enabled"] is False


def test_three_consecutive_ignores_stop_future_bubble_injections(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.76, "bubble_status": "high_risk"},
    )

    state = PersonaState(bubble_ignore_streak=3)
    delirium, _, working = make_delirium_for_bubble_tests(state=state)

    delirium.process_message("C'est toujours la meme preuve, encore.")

    injected_state = working.calls[0]["state_snapshot"]
    assert injected_state["bubble_ignore_streak"] == 3
    assert injected_state["bubble_break_enabled"] is False


def test_non_injection_reply_clears_one_shot_bubble_break_flag(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": 0.48, "bubble_status": "medium_risk"},
    )

    delirium, state, _working = make_delirium_for_bubble_tests(
        responses=("assistant reply",),
    )

    delirium.process_message("On tourne encore autour du meme sujet politique.")

    assert state.bubble_break_enabled is False


def test_compose_s1_prompt_includes_bubble_break_context_format():
    prompt = WorkingMemory().compose_s1_prompt(
        PersonaState(
            bubble_break_enabled=True,
            bubble_risk_status="high_risk",
            bubble_break_intensity="strong",
            bubble_ignore_streak=1,
        ),
        [],
        [{"label": "politique", "weight": 0.9}],
        thread_messages=[
            {
                "role": "user",
                "content": "Je reviens encore a ce scandale, eux ils mentent tout le temps.",
            }
        ],
    )

    assert "═══ INJECTION LATÉRALE ANTI-BULLE ═══" in prompt
    assert '"Rien à voir mais..."' in prompt
    assert "Risque détecté : high_risk" in prompt
    assert "crochet net" in prompt.lower()


def test_delirium_init_clears_session_scoped_bubble_flags_from_saved_state(monkeypatch):
    saved_state = PersonaState(
        bubble_risk_score=0.81,
        bubble_risk_status="high_risk",
        bubble_break_enabled=True,
        bubble_break_intensity="strong",
        bubble_ignore_streak=2,
    )

    class _Conn:
        def execute(self, *_args, **_kwargs):
            return self

        def fetchone(self):
            return {"ts": None}

    class _Episodic:
        def __init__(self, _path):
            self.conn = _Conn()

        def load_latest_persona_state(self):
            return saved_state

    class _Decay:
        def __init__(self, *_args, **_kwargs):
            pass

        def apply_decay(self):
            return None

    class _Gags:
        def __init__(self, _conn):
            pass

        def apply_decay(self):
            return None

    monkeypatch.setattr(main_module, "LLMClient", lambda: object())
    monkeypatch.setattr(main_module, "AsyncLLMClient", lambda: object())
    monkeypatch.setattr(main_module, "EpisodicMemory", _Episodic)
    monkeypatch.setattr(main_module, "SemanticMemory", lambda _conn: object())
    monkeypatch.setattr(main_module, "WorkingMemory", lambda: object())
    monkeypatch.setattr(main_module, "DecayEngine", _Decay)
    monkeypatch.setattr(main_module, "WorldVision", lambda _conn, _llm: object())
    monkeypatch.setattr(main_module, "GagTracker", _Gags)
    monkeypatch.setattr(main_module, "S2Analyzer", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(main_module, "get_embedder", lambda: object())
    monkeypatch.setattr(main_module, "compute_retrait_state", lambda _last_ts: "active")

    delirium = Delirium()
    state = delirium.persona_engine.get_current_state()

    assert state.bubble_risk_score == 0.81
    assert state.bubble_risk_status == "high_risk"
    assert state.bubble_ignore_streak == 2
    assert state.bubble_break_enabled is False
    assert state.bubble_break_intensity == "off"
    assert delirium._bubble_injections_this_session == 0
    assert delirium._pending_bubble_injection is None


def test_invalid_bubble_signal_payload_falls_back_to_safe_defaults(monkeypatch):
    monkeypatch.setattr("src.import_.enricher.enrich_text", lambda text: text)
    monkeypatch.setattr(main_module, "cosine_similarity", lambda _left, _right: 1.0)
    monkeypatch.setattr(
        main_module,
        "h_bulle",
        lambda _conn: {"h_bulle": "not-a-number", "bubble_status": "extreme_risk"},
    )

    delirium, state, working = make_delirium_for_bubble_tests()

    delirium.process_message("Je reviens encore au meme sujet.")

    injected_state = working.calls[0]["state_snapshot"]
    assert state.bubble_risk_score == 0.0
    assert state.bubble_risk_status == "low_risk"
    assert state.bubble_break_intensity == "off"
    assert injected_state["bubble_break_enabled"] is False


def test_compose_s1_prompt_ignores_malformed_theme_anchor_payloads():
    prompt = WorkingMemory().compose_s1_prompt(
        PersonaState(
            bubble_break_enabled=True,
            bubble_risk_status="medium_risk",
            bubble_break_intensity="gentle",
        ),
        [],
        [{}, {"label": "politique"}],
        thread_messages=[
            {"role": "user", "content": "Je reviens encore au meme sujet."},
        ],
    )

    assert "Angle adjacent suggere :" in prompt
    assert "politique" in prompt


def test_classify_injection_followup_tolerates_missing_text_payloads():
    outcome = classify_injection_followup(
        None,
        None,
        prior_topics=[None, "politique"],
    )

    assert outcome == "ambiguous"
