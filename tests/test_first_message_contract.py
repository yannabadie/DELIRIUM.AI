from src.first_message import FIRST_MESSAGE_INSTRUCTION
from src.llm_client import _effective_last_user_message


def test_llm_client_empty_history_uses_shared_first_message_instruction():
    assert _effective_last_user_message([]) == FIRST_MESSAGE_INSTRUCTION


def test_generate_first_message_passes_shared_instruction_to_behavioral_reply(monkeypatch):
    import src.main as main_module
    from src.main import Delirium

    seen = {}

    def fake_behavioral_reply(instruction):
        seen["instruction"] = instruction
        return "premier bonjour"

    monkeypatch.setattr(main_module, "behavioral_reply", fake_behavioral_reply)
    monkeypatch.setattr(main_module.console, "print", lambda *args, **kwargs: None)

    delirium = Delirium.__new__(Delirium)
    state = type("State", (), {"H": 0.2, "phase": "baseline"})()
    delirium.persona_engine = type("PersonaEngine", (), {"get_current_state": lambda self: state})()
    delirium._ensure_active_session = lambda state: None
    delirium._refresh_retrait_state = lambda state: None
    delirium.retrait_state = "active"
    delirium.world_vision = type("Vision", (), {"get_summary_for_s1": lambda self: None})()
    delirium.gags = type("Gags", (), {"get_gag_context_for_s1": lambda self: None})()
    delirium.working = type("Working", (), {"compose_s1_prompt": lambda self, *args, **kwargs: "s1 prompt"})()
    delirium.decay = type("Decay", (), {"get_forgotten_topics": lambda self: []})()
    delirium.episodic = type(
        "Episodic",
        (),
        {
            "store": lambda self, *args, **kwargs: "frag-1",
            "log_execution": lambda self, *args, **kwargs: None,
            "get_recent_conversation": lambda self, *args, **kwargs: [],
        },
    )()
    delirium.embedder = type("Embedder", (), {"embed": lambda self, text: [0.0]})()
    delirium._safe_embed = lambda text, context=None: [0.0]
    delirium._log_execution_safely = lambda *args, **kwargs: None
    delirium.session_id = "session-1"

    response = delirium.generate_first_message()

    assert response == "premier bonjour"
    assert seen["instruction"] == FIRST_MESSAGE_INSTRUCTION
