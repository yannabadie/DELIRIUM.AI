from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field, field_validator

from src.config import MINIMAX_API_KEY as CONFIG_MINIMAX_API_KEY
from src.service import (
    DeliriumApiBackend,
    LiveConversationSession,
    OfflineConversationSession,
    SessionManager,
)


MINIMAX_API_KEY = CONFIG_MINIMAX_API_KEY


def build_delirium_service(session_id: str):
    if MINIMAX_API_KEY:
        try:
            return LiveConversationSession(session_id)
        except Exception:
            return OfflineConversationSession(session_id)
    return OfflineConversationSession(session_id)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _decode_websocket_payload(raw_message: dict[str, Any]) -> dict[str, Any]:
    if raw_message["type"] == "websocket.disconnect":
        raise WebSocketDisconnect

    text = raw_message.get("text")
    if text is None and raw_message.get("bytes") is not None:
        try:
            text = raw_message["bytes"].decode("utf-8")
        except UnicodeDecodeError:
            return {}

    if text is None:
        return {}

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return {"message": text}

    if isinstance(payload, dict):
        return payload
    if isinstance(payload, str):
        return {"message": payload}
    return {"message": text}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    session_id: str | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="message")

    @field_validator("session_id")
    @classmethod
    def normalize_session_id(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


class ImportRequest(BaseModel):
    source: str
    path: str | None = None
    username: str | None = None
    session_id: str | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return _normalize_required_text(value, field_name="source").lower()

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _normalize_required_text(value, field_name="path")

    @field_validator("username", "session_id")
    @classmethod
    def normalize_optional_fields(cls, value: str | None) -> str | None:
        return _normalize_optional_text(value)


def _resolve_app_dependencies(
    session_manager: SessionManager | Any | None,
    api_backend: DeliriumApiBackend | None,
) -> tuple[SessionManager | Any, DeliriumApiBackend]:
    manager = session_manager
    backend = api_backend

    if manager is None and backend is not None:
        manager = getattr(backend, "session_manager", None)

    if manager is None:
        manager = SessionManager(build_delirium_service)

    if backend is None:
        backend = DeliriumApiBackend(session_manager=manager)
    else:
        setattr(backend, "session_manager", manager)

    return manager, backend


def _set_app_dependencies(
    app: FastAPI,
    session_manager: SessionManager | Any | None,
    api_backend: DeliriumApiBackend | None,
) -> tuple[SessionManager | Any, DeliriumApiBackend]:
    manager, backend = _resolve_app_dependencies(session_manager, api_backend)
    app.state.session_manager = manager
    app.state.api_backend = backend
    app.state._dependency_binding = (id(manager), id(backend))
    return manager, backend


def _get_runtime_dependencies(app: FastAPI) -> tuple[SessionManager | Any, DeliriumApiBackend]:
    current_manager = getattr(app.state, "session_manager", None)
    current_backend = getattr(app.state, "api_backend", None)
    bound_manager_id, bound_backend_id = getattr(app.state, "_dependency_binding", (None, None))

    manager_changed = current_manager is not None and id(current_manager) != bound_manager_id
    backend_changed = current_backend is not None and id(current_backend) != bound_backend_id

    if backend_changed and not manager_changed and current_backend is not None:
        backend_manager = getattr(current_backend, "session_manager", None)
        return _set_app_dependencies(
            app,
            backend_manager if backend_manager is not None else current_manager,
            current_backend,
        )

    return _set_app_dependencies(app, current_manager, current_backend)


def create_app(
    session_manager: SessionManager | Any | None = None,
    api_backend: DeliriumApiBackend | None = None,
) -> FastAPI:
    app = FastAPI(title="DELIRIUM API", version="0.1.0")
    _set_app_dependencies(app, session_manager, api_backend)

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "status": "healthy"}

    @app.post("/chat")
    async def chat(request: ChatRequest) -> dict[str, Any]:
        _manager, backend = _get_runtime_dependencies(app)
        return await run_in_threadpool(backend.chat, request.message, request.session_id)

    @app.get("/status")
    async def status(session_id: str | None = Query(default=None)) -> dict[str, Any]:
        _manager, backend = _get_runtime_dependencies(app)
        return await run_in_threadpool(
            backend.status,
            _normalize_optional_text(session_id),
        )

    @app.post("/import")
    async def import_conversations(request: ImportRequest) -> dict[str, Any]:
        _manager, backend = _get_runtime_dependencies(app)
        try:
            return await run_in_threadpool(
                backend.import_data,
                request.source,
                path=request.path,
                username=request.username,
                session_id=request.session_id,
            )
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/export")
    async def export_conversations(session_id: str | None = Query(default=None)) -> dict[str, Any]:
        _manager, backend = _get_runtime_dependencies(app)
        return await run_in_threadpool(
            backend.export_history,
            _normalize_optional_text(session_id),
        )

    @app.websocket("/ws")
    async def websocket_chat(websocket: WebSocket) -> None:
        await websocket.accept()
        connection_session_id = _normalize_optional_text(websocket.query_params.get("session_id"))
        try:
            while True:
                incoming = _decode_websocket_payload(await websocket.receive())
                raw_message = incoming.get("message")
                message = raw_message.strip() if isinstance(raw_message, str) else ""
                if not message:
                    await websocket.send_json({"type": "error", "detail": "message is required"})
                    continue
                explicit_session_id = _normalize_optional_text(
                    None if incoming.get("session_id") is None else str(incoming.get("session_id"))
                )
                _manager, backend = _get_runtime_dependencies(app)
                events = await run_in_threadpool(
                    backend.stream_chat,
                    message,
                    explicit_session_id or connection_session_id,
                )
                for event in events:
                    if event.get("type") == "message":
                        connection_session_id = event["session_id"]
                    await websocket.send_json(event)
        except WebSocketDisconnect:
            return

    return app


app = create_app()
