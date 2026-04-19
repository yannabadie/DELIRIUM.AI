from __future__ import annotations

from typing import Any


from src.service import DeliriumApiBackend


class FakeService:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict[str, Any]] = []

    def touch(self) -> None:
        return None

    def process_message(self, message: str) -> str:
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

    def get_status_snapshot(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "persona": {"phase": "probing", "H": 0.0},
            "bubble": {"score": 0.0, "status": "low_risk"},
            "themes": ["echo"],
        }

    def export_history(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": list(self.messages),
        }

    def import_data(self, source: str, path: str) -> dict[str, Any]:
        self.messages.extend(
            [
                {"role": "user", "content": f"from:{path}", "timestamp": "2026-04-19T17:00:00"},
                {
                    "role": "assistant",
                    "content": f"imported:{source}",
                    "timestamp": "2026-04-19T17:00:00",
                },
            ]
        )
        return {
            "session_id": self.session_id,
            "source": source,
            "imported": 1,
            "path": path,
        }

    def close(self) -> None:
        return None


class UniqueFactory:
    def __init__(self):
        self.counter = 0

    def __call__(self) -> FakeService:
        self.counter += 1
        return FakeService(f"session-{self.counter}")


class FalseySessionManager:
    def __init__(self):
        self.calls: list[str | None] = []

    def __bool__(self) -> bool:
        return False

    def get_or_create(self, session_id: str | None = None):
        self.calls.append(session_id)
        resolved = session_id or "falsey-session"
        return resolved, FakeService(resolved), not bool(session_id)


def test_backend_reuses_last_session_for_status_and_export_without_explicit_session_id():
    backend = DeliriumApiBackend(service_factory=UniqueFactory())

    chat = backend.chat("bonjour")
    status = backend.status()
    exported = backend.export_history()

    assert status["session_id"] == chat["session_id"] == "session-1"
    assert exported["session_id"] == chat["session_id"]
    assert exported["history"] == exported["messages"]
    assert exported["messages"][0]["content"] == "bonjour"


def test_backend_import_persists_generated_session_for_followup_export():
    backend = DeliriumApiBackend(service_factory=UniqueFactory())

    imported = backend.import_data("generic", "fixture.json")
    exported = backend.export_history(session_id=imported["session_id"])

    assert imported["session_id"] == "session-1"
    assert exported["session_id"] == imported["session_id"]
    assert [message["content"] for message in exported["messages"]] == [
        "from:fixture.json",
        "imported:generic",
    ]


def test_backend_preserves_falsey_injected_session_manager():
    manager = FalseySessionManager()

    backend = DeliriumApiBackend(session_manager=manager)

    assert backend.session_manager is manager
