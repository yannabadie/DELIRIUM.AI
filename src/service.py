from __future__ import annotations

import inspect
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable
from uuid import uuid4

from src.config import MINIMAX_API_KEY
from src.guardrails import behavioral_reply, fallback_reply, guardrail_reply
from src.memory.bubble import h_bulle
from src.persona.state import PersonaState


SESSION_IDLE_TIMEOUT = timedelta(minutes=30)
_TOKEN_RE = re.compile(r"\S+\s*")


def _chunk_response(text: str) -> list[str]:
    chunks = _TOKEN_RE.findall(text)
    return chunks or [text]


def _history_to_export(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "role": item["role"],
            "content": item["content"],
            "timestamp": item["timestamp"],
            "source": item.get("source", "delirium"),
        }
        for item in messages
    ]


def _load_importer(source: str):
    normalized = source.strip().lower()
    if normalized == "generic":
        from src.import_.generic import GenericImporter

        return GenericImporter()
    if normalized == "chatgpt":
        from src.import_.chatgpt import ChatGPTImporter

        return ChatGPTImporter()
    if normalized == "claude":
        from src.import_.claude_ai import ClaudeImporter

        return ClaudeImporter()
    raise ValueError(f"Unsupported import source: {source}")


class OfflineConversationSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = self.created_at
        self.persona = PersonaState()
        self.messages: list[dict[str, Any]] = []

    def touch(self) -> None:
        self.last_activity = datetime.now()

    def _history(self) -> list[dict[str, str]]:
        return [{"role": item["role"], "content": item["content"]} for item in self.messages]

    def chat(self, message: str) -> str:
        history = self._history()
        response = (
            guardrail_reply(message, history=history)
            or behavioral_reply(message, history=history)
            or fallback_reply(message, history=history)
        )
        now = datetime.now().isoformat()
        self.messages.append(
            {"role": "user", "content": message, "timestamp": now, "source": "delirium"}
        )
        self.messages.append(
            {"role": "assistant", "content": response, "timestamp": now, "source": "delirium"}
        )
        self.touch()
        return response

    def import_messages(self, source: str, *, path: str | None = None, username: str | None = None) -> dict:
        if source == "github":
            raise ValueError("GitHub import requires live API-backed sessions")
        if not path:
            raise ValueError("Import path is required")
        importer = _load_importer(source)
        imported = importer.parse(path)
        for message in imported:
            timestamp = message.timestamp or datetime.now().isoformat()
            self.messages.append(
                {
                    "role": "user",
                    "content": message.user_input,
                    "timestamp": timestamp,
                    "source": message.source or source,
                }
            )
            self.messages.append(
                {
                    "role": "assistant",
                    "content": message.assistant_response,
                    "timestamp": timestamp,
                    "source": message.source or source,
                }
            )
        self.touch()
        return {
            "session_id": self.session_id,
            "source": source,
            "imported": len(imported),
            "username": username,
        }

    def status(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.messages) // 2,
            "persona": self.persona.to_dict(),
            "bubble": {"score": 0.0, "status": "low_risk"},
            "themes": [],
            "world_vision": None,
            "mode": "offline",
        }

    def export(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "messages": _history_to_export(self.messages),
        }

    def close(self) -> None:
        return None


class LiveConversationSession:
    def __init__(self, session_id: str):
        from src.main import Delirium

        self.delirium = Delirium()
        self.delirium.session_id = session_id
        self.session_id = session_id

    def touch(self) -> None:
        self.delirium._last_message_at = datetime.now()

    def chat(self, message: str) -> str:
        response = self.delirium.process_message(message)
        self.touch()
        return response

    def import_messages(self, source: str, *, path: str | None = None, username: str | None = None) -> dict:
        if source == "github":
            if not username:
                raise ValueError("GitHub import requires a username")
            self.delirium.cmd_import_github(username)
            imported = self.delirium.episodic.get_fragment_count("github")
            self.touch()
            return {
                "session_id": self.session_id,
                "source": source,
                "imported": imported,
                "username": username,
            }

        if not path:
            raise ValueError("Import path is required")

        importer = _load_importer(source)
        imported = importer.parse(path)
        dummy_state = PersonaState()
        for message in imported:
            self.delirium.episodic.store(
                user_message=message.user_input,
                response=message.assistant_response,
                session_id=self.session_id,
                persona_state=dummy_state,
                source=message.source or source,
            )
        self.touch()
        return {
            "session_id": self.session_id,
            "source": source,
            "imported": len(imported),
            "username": username,
        }

    def status(self) -> dict[str, Any]:
        state = self.delirium.persona_engine.get_current_state()
        bubble = h_bulle(self.delirium.episodic.conn)
        themes = self.delirium.semantic.get_active_themes()
        vision = self.delirium.world_vision.get_current()
        return {
            "session_id": self.session_id,
            "created_at": None,
            "message_count": self.delirium.episodic.get_session_message_count(self.session_id),
            "persona": state.to_dict(),
            "bubble": {
                "score": bubble.get("h_bulle", 0.0),
                "status": bubble.get("bubble_status", "low_risk"),
            },
            "themes": themes,
            "world_vision": vision,
            "mode": "live",
        }

    def export(self) -> dict[str, Any]:
        rows = self.delirium.episodic.conn.execute(
            "SELECT timestamp, user_input, s1_response, source "
            "FROM conversations WHERE session_id = ? ORDER BY timestamp ASC",
            (self.session_id,),
        ).fetchall()
        messages: list[dict[str, Any]] = []
        for row in rows:
            messages.append(
                {
                    "role": "user",
                    "content": row["user_input"],
                    "timestamp": row["timestamp"],
                    "source": row["source"],
                }
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": row["s1_response"],
                    "timestamp": row["timestamp"],
                    "source": row["source"],
                }
            )
        return {"session_id": self.session_id, "messages": messages}

    def close(self) -> None:
        self.delirium.close()


def build_delirium_service(session_id: str):
    if MINIMAX_API_KEY:
        try:
            return LiveConversationSession(session_id)
        except Exception:
            return OfflineConversationSession(session_id)
    return OfflineConversationSession(session_id)


@dataclass
class SessionEntry:
    session: OfflineConversationSession | LiveConversationSession | Any
    last_seen: datetime


class SessionManager:
    def __init__(self, service_factory: Callable[..., Any] = build_delirium_service) -> None:
        self._service_factory = service_factory
        self._sessions: dict[str, SessionEntry] = {}

    def _build_session(self, session_id: str):
        try:
            parameters = inspect.signature(self._service_factory).parameters
        except (TypeError, ValueError):
            parameters = {}

        if parameters:
            session = self._service_factory(session_id)
        else:
            session = self._service_factory()

        resolved = getattr(session, "session_id", None) or session_id or str(uuid4())
        setattr(session, "session_id", resolved)
        return resolved, session

    def _purge_expired(self) -> None:
        now = datetime.now()
        expired = [
            key
            for key, entry in self._sessions.items()
            if now - entry.last_seen > SESSION_IDLE_TIMEOUT
        ]
        for key in expired:
            entry = self._sessions.pop(key)
            _close_session(entry.session)

    def get_or_create(self, session_id: str | None = None):
        self._purge_expired()
        now = datetime.now()
        resolved = session_id or str(uuid4())
        entry = self._sessions.get(resolved)
        created = entry is None
        if created:
            effective_session_id, session = self._build_session(resolved)
            resolved = effective_session_id
            entry = SessionEntry(session=session, last_seen=now)
            self._sessions[resolved] = entry
        else:
            entry.last_seen = now
        touch = getattr(entry.session, "touch", None)
        if callable(touch):
            touch()
        return resolved, entry.session, created


def _close_session(session: Any) -> None:
    close = getattr(session, "close", None)
    if callable(close):
        close()


def _call_chat(session: Any, message: str) -> str:
    if hasattr(session, "chat"):
        return session.chat(message)
    return session.process_message(message)


def _call_status(session: Any) -> dict[str, Any]:
    if hasattr(session, "status"):
        return dict(session.status())
    return dict(session.get_status_snapshot())


def _call_export(session: Any) -> dict[str, Any]:
    if hasattr(session, "export"):
        return dict(session.export())
    return dict(session.export_history())


def _call_import(
    session: Any,
    source: str,
    *,
    path: str | None = None,
    username: str | None = None,
) -> dict[str, Any]:
    if hasattr(session, "import_messages"):
        return dict(session.import_messages(source, path=path, username=username))
    return dict(session.import_data(source, path or ""))


class DeliriumApiBackend:
    def __init__(
        self,
        *,
        service_factory: Callable[..., Any] = build_delirium_service,
        session_manager: SessionManager | Any | None = None,
    ) -> None:
        self.session_manager = (
            session_manager if session_manager is not None else SessionManager(service_factory)
        )
        self._last_session_id: str | None = None

    def _remember(self, session_id: str) -> None:
        self._last_session_id = session_id

    def _resolve_session_hint(self, session_id: str | None = None) -> str | None:
        return session_id or self._last_session_id

    def chat(self, message: str, session_id: str | None = None) -> dict[str, Any]:
        resolved, session, created = self.session_manager.get_or_create(session_id)
        self._remember(resolved)
        response = _call_chat(session, message)
        return {
            "session_id": resolved,
            "response": response,
            "reply": response,
            "assistant_response": response,
            "created": created,
        }

    def status(self, session_id: str | None = None) -> dict[str, Any]:
        resolved, session, _created = self.session_manager.get_or_create(
            self._resolve_session_hint(session_id)
        )
        self._remember(resolved)
        payload = _call_status(session)
        payload["session_id"] = resolved
        if "persona" in payload and "persona_state" not in payload:
            payload["persona_state"] = payload["persona"]
        bubble = payload.get("bubble")
        if isinstance(bubble, dict):
            payload.setdefault("bubble_score", bubble.get("score"))
            payload.setdefault("bubble_status", bubble.get("status"))
        if "themes" in payload and "active_themes" not in payload:
            payload["active_themes"] = payload["themes"]
        return payload

    def import_data(
        self,
        source: str,
        path: str | None = None,
        username: str | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        resolved, session, _created = self.session_manager.get_or_create(session_id)
        self._remember(resolved)
        payload = _call_import(session, source, path=path, username=username)
        payload["session_id"] = resolved
        return payload

    def export_history(self, session_id: str | None = None) -> dict[str, Any]:
        resolved, session, _created = self.session_manager.get_or_create(
            self._resolve_session_hint(session_id)
        )
        self._remember(resolved)
        payload = _call_export(session)
        payload["session_id"] = resolved
        history = payload.get("history")
        messages = payload.get("messages")
        if history is None and messages is not None:
            payload["history"] = messages
        if messages is None and history is not None:
            payload["messages"] = history
        if payload.get("messages") is None:
            payload["messages"] = []
            payload["history"] = []
        return payload

    def stream_chat(self, message: str, session_id: str | None = None) -> list[dict[str, Any]]:
        result = self.chat(message, session_id=session_id)
        events = [
            {"type": "token", "session_id": result["session_id"], "token": token}
            for token in _chunk_response(result["response"])
        ]
        events.append(
            {
                "type": "message",
                "session_id": result["session_id"],
                "response": result["response"],
                "created": result["created"],
            }
        )
        return events
