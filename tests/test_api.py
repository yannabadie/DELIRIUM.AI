import asyncio
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api import create_app


class FakeSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict[str, str]] = []

    def touch(self) -> None:
        return None

    def chat(self, message: str) -> str:
        response = f"echo:{message}"
        self.messages.extend(
            [
                {"role": "user", "content": message, "timestamp": "2026-04-19T17:00:00"},
                {
                    "role": "assistant",
                    "content": response,
                    "timestamp": "2026-04-19T17:00:00",
                },
            ]
        )
        return response

    def import_messages(self, source: str, *, path: str | None = None, username: str | None = None) -> dict:
        if path:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            for item in payload:
                self.messages.extend(
                    [
                        {
                            "role": "user",
                            "content": item["user"],
                            "timestamp": "2026-04-19T17:00:00",
                            "source": item.get("source", source),
                        },
                        {
                            "role": "assistant",
                            "content": item["assistant"],
                            "timestamp": "2026-04-19T17:00:00",
                            "source": item.get("source", source),
                        },
                    ]
                )
        return {
            "session_id": self.session_id,
            "source": source,
            "imported": len(self.messages) // 2 if path else 1,
            "path": path,
            "username": username,
        }

    def status(self) -> dict:
        return {
            "session_id": self.session_id,
            "persona": {"phase": "probing", "H": 0.0},
            "bubble": {"score": 0.0, "status": "low_risk"},
            "themes": ["echo"],
            "mode": "fake",
        }

    def export(self) -> dict:
        return {
            "session_id": self.session_id,
            "messages": list(self.messages),
        }

    def close(self) -> None:
        return None


class FakeSessionManager:
    def __init__(self):
        self.sessions: dict[str, FakeSession] = {}

    def get_or_create(self, session_id: str | None = None):
        resolved = session_id or "session-test"
        created = resolved not in self.sessions
        if created:
            self.sessions[resolved] = FakeSession(resolved)
        return resolved, self.sessions[resolved], created


def _assert_no_running_loop() -> None:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return
    raise RuntimeError("session work is running on the FastAPI event loop")


class LoopSensitiveSession(FakeSession):
    def touch(self) -> None:
        _assert_no_running_loop()

    def chat(self, message: str) -> str:
        _assert_no_running_loop()
        return super().chat(message)

    def import_messages(self, source: str, *, path: str | None = None, username: str | None = None) -> dict:
        _assert_no_running_loop()
        return super().import_messages(source, path=path, username=username)

    def status(self) -> dict:
        _assert_no_running_loop()
        return super().status()

    def export(self) -> dict:
        _assert_no_running_loop()
        return super().export()


class LoopSensitiveSessionManager(FakeSessionManager):
    def get_or_create(self, session_id: str | None = None):
        _assert_no_running_loop()
        resolved = session_id or "session-live"
        created = resolved not in self.sessions
        if created:
            self.sessions[resolved] = LoopSensitiveSession(resolved)
        return resolved, self.sessions[resolved], created


class UniqueSessionManager(FakeSessionManager):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def get_or_create(self, session_id: str | None = None):
        if session_id is None:
            self.counter += 1
            session_id = f"session-{self.counter}"
        return super().get_or_create(session_id)


class FalseySessionManager(FakeSessionManager):
    def __bool__(self) -> bool:
        return False


class RuntimeInjectedSessionManager(FakeSessionManager):
    def get_or_create(self, session_id: str | None = None):
        resolved = session_id or "runtime-session"
        created = resolved not in self.sessions
        if created:
            self.sessions[resolved] = FakeSession(resolved)
        return resolved, self.sessions[resolved], created


@pytest.fixture()
def client() -> TestClient:
    app = create_app(session_manager=FakeSessionManager())
    return TestClient(app)


def test_health_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["status"] in {"healthy", "ok"}


def test_chat_status_and_export_flow(client: TestClient):
    chat = client.post("/chat", json={"message": "bonjour"})
    assert chat.status_code == 200

    body = chat.json()
    assert body["session_id"]
    assert isinstance(body["response"], str)
    assert body["response"] == "echo:bonjour"
    assert body["reply"] == body["response"]
    assert body["assistant_response"] == body["response"]

    status = client.get("/status", params={"session_id": body["session_id"]})
    assert status.status_code == 200
    status_json = status.json()
    assert status_json["session_id"] == body["session_id"]
    assert "persona" in status_json
    assert status_json["persona_state"] == status_json["persona"]
    assert "bubble" in status_json
    assert status_json["bubble_score"] == status_json["bubble"]["score"]
    assert status_json["bubble_status"] == status_json["bubble"]["status"]
    assert status_json["active_themes"] == status_json["themes"]

    exported = client.get("/export", params={"session_id": body["session_id"]})
    assert exported.status_code == 200
    export_json = exported.json()
    assert export_json["session_id"] == body["session_id"]
    assert export_json["history"] == export_json["messages"]
    assert export_json["history"] == [
        {"role": "user", "content": "bonjour", "timestamp": "2026-04-19T17:00:00"},
        {
            "role": "assistant",
            "content": "echo:bonjour",
            "timestamp": "2026-04-19T17:00:00",
        },
    ]


def test_async_routes_offload_session_work_from_event_loop():
    app = create_app(session_manager=LoopSensitiveSessionManager())

    with TestClient(app) as client:
        chat = client.post("/chat", json={"message": "bonjour"})
        assert chat.status_code == 200
        session_id = chat.json()["session_id"]

        status = client.get("/status", params={"session_id": session_id})
        assert status.status_code == 200

        exported = client.get("/export", params={"session_id": session_id})
        assert exported.status_code == 200


def test_generic_import_endpoint(client: TestClient, tmp_path: Path):
    fixture = tmp_path / "generic.json"
    fixture.write_text(
        '[{"user":"Salut","assistant":"Ca roule.","source":"generic"}]',
        encoding="utf-8",
    )

    response = client.post(
        "/import",
        json={"source": "generic", "path": str(fixture)},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "generic"
    assert payload["imported"] == 1


def test_import_persists_history_for_followup_export(tmp_path: Path):
    fixture = tmp_path / "generic.json"
    fixture.write_text(
        '[{"user":"Salut","assistant":"Ca roule.","source":"generic"}]',
        encoding="utf-8",
    )
    app = create_app(session_manager=FakeSessionManager())

    with TestClient(app) as client:
        imported = client.post(
            "/import",
            json={"source": "generic", "path": str(fixture)},
        )
        assert imported.status_code == 200

        exported = client.get("/export")

    assert exported.status_code == 200
    assert exported.json()["messages"] == [
        {
            "role": "user",
            "content": "Salut",
            "timestamp": "2026-04-19T17:00:00",
            "source": "generic",
        },
        {
            "role": "assistant",
            "content": "Ca roule.",
            "timestamp": "2026-04-19T17:00:00",
            "source": "generic",
        },
    ]


def test_chat_rejects_whitespace_only_message(client: TestClient):
    response = client.post("/chat", json={"message": "   "})

    assert response.status_code == 422


def test_chat_normalizes_session_id_whitespace(client: TestClient):
    response = client.post("/chat", json={"message": "bonjour", "session_id": "  custom-id  "})

    assert response.status_code == 200
    assert response.json()["session_id"] == "custom-id"


def test_import_rejects_whitespace_only_source(client: TestClient, tmp_path: Path):
    fixture = tmp_path / "generic.json"
    fixture.write_text("[]", encoding="utf-8")

    response = client.post(
        "/import",
        json={"source": "   ", "path": str(fixture)},
    )

    assert response.status_code == 422


def test_import_rejects_whitespace_only_path(client: TestClient):
    response = client.post(
        "/import",
        json={"source": "generic", "path": "   "},
    )

    assert response.status_code == 422


def test_import_preserves_trimmed_session_id(client: TestClient, tmp_path: Path):
    fixture = tmp_path / "generic.json"
    fixture.write_text("[]", encoding="utf-8")

    response = client.post(
        "/import",
        json={
            "source": "generic",
            "path": str(fixture),
            "session_id": "  imported-session  ",
        },
    )

    assert response.status_code == 200
    assert response.json()["session_id"] == "imported-session"


def test_import_maps_oserror_to_400(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    def boom(_self, source: str, *, path: str | None = None, username: str | None = None) -> dict:
        raise OSError("broken file")

    monkeypatch.setattr(FakeSession, "import_messages", boom)

    response = client.post(
        "/import",
        json={"source": "generic", "path": "conversation.json"},
    )

    assert response.status_code == 400
    assert "broken file" in response.json()["detail"]


def test_import_missing_file_returns_400():
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/import",
            json={"source": "generic", "path": "/tmp/does-not-exist.json"},
        )

    assert response.status_code == 400
    assert "no such file" in response.json()["detail"].lower()


def test_websocket_chat_stream(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"message": "bonjour"})

        events = []
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "message":
                break

    assert any(event["type"] == "token" and event["token"] for event in events)
    final = events[-1]
    assert final["type"] == "message"
    assert final["session_id"]
    assert final["response"]


def test_websocket_reuses_connection_session_without_explicit_session_id(client: TestClient):
    app = create_app(session_manager=UniqueSessionManager())

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"message": "bonjour"})

            first_events = []
            while True:
                event = websocket.receive_json()
                first_events.append(event)
                if event["type"] == "message":
                    break

            websocket.send_json({"message": "encore"})

            second_events = []
            while True:
                event = websocket.receive_json()
                second_events.append(event)
                if event["type"] == "message":
                    break

    first_session_id = first_events[-1]["session_id"]
    second_session_id = second_events[-1]["session_id"]

    assert first_session_id == "session-1"
    assert second_session_id == first_session_id


def test_websocket_honors_explicit_session_id_override_within_connection(client: TestClient):
    app = create_app(session_manager=UniqueSessionManager())

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            websocket.send_json({"message": "bonjour"})

            while True:
                event = websocket.receive_json()
                if event["type"] == "message":
                    break

            websocket.send_json({"message": "encore", "session_id": "manual-session"})

            second_events = []
            while True:
                event = websocket.receive_json()
                second_events.append(event)
                if event["type"] == "message":
                    break

    assert second_events[-1]["session_id"] == "manual-session"


def test_websocket_preserves_query_session_id(client: TestClient):
    with client.websocket_connect("/ws?session_id=%20persisted-session%20") as websocket:
        websocket.send_json({"message": "bonjour"})

        events = []
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "message":
                break

    assert events[-1]["session_id"] == "persisted-session"


def test_websocket_accepts_plain_text_frames(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("bonjour")

        events = []
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "message":
                break

    assert any(event["type"] == "token" and event["token"] for event in events)
    assert events[-1]["response"] == "echo:bonjour"


def test_websocket_rejects_null_message_without_closing_connection(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"message": None})
        error_event = websocket.receive_json()

        websocket.send_json({"message": "bonjour"})

        events = [error_event]
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "message":
                break

    assert error_event == {"type": "error", "detail": "message is required"}
    assert events[-1]["response"] == "echo:bonjour"


def test_websocket_rejects_invalid_utf8_bytes_without_closing_connection(client: TestClient):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_bytes(b"\xff")
        error_event = websocket.receive_json()

        websocket.send_json({"message": "bonjour"})

        events = [error_event]
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "message":
                break

    assert error_event == {"type": "error", "detail": "message is required"}
    assert events[-1]["response"] == "echo:bonjour"


def test_default_app_falls_back_to_offline_when_live_session_init_fails(monkeypatch):
    from src import api as api_module

    def explode(_session_id: str):
        raise RuntimeError("live runtime unavailable")

    monkeypatch.setattr(api_module, "MINIMAX_API_KEY", "dummy-key")
    monkeypatch.setattr(api_module, "LiveConversationSession", explode)

    with TestClient(api_module.create_app()) as client:
        chat = client.post("/chat", json={"message": "bonjour"})
        assert chat.status_code == 200
        chat_json = chat.json()
        assert chat_json["response"]

        status = client.get("/status", params={"session_id": chat_json["session_id"]})
        assert status.status_code == 200
        status_json = status.json()
        assert status_json["mode"] == "offline"
        assert status_json["persona_state"] == status_json["persona"]

        exported = client.get("/export", params={"session_id": chat_json["session_id"]})
        assert exported.status_code == 200
        export_json = exported.json()
        assert export_json["history"] == export_json["messages"]


def test_create_app_reuses_backend_session_manager_for_app_state():
    from src.service import DeliriumApiBackend

    manager = FakeSessionManager()
    backend = DeliriumApiBackend(session_manager=manager)

    app = create_app(api_backend=backend)

    assert app.state.api_backend is backend
    assert app.state.session_manager is manager


def test_create_app_preserves_falsey_injected_session_manager():
    manager = FalseySessionManager()

    app = create_app(session_manager=manager)

    assert app.state.session_manager is manager
    assert app.state.api_backend.session_manager is manager


def test_routes_honor_runtime_app_state_session_manager_swap():
    app = create_app(session_manager=FakeSessionManager())
    app.state.session_manager = RuntimeInjectedSessionManager()

    with TestClient(app) as client:
        response = client.post("/chat", json={"message": "bonjour"})

    assert response.status_code == 200
    assert response.json()["session_id"] == "runtime-session"
