"""Honcho bridge — fact layer for World Vision.

Pushes conversation messages to Honcho for structured fact extraction.
Queries Honcho for grounded user model facts to feed World Vision synthesis.
Non-blocking, fail-safe — Delirium works fine without Honcho.
"""

import logging
from typing import Optional

from src.config import HONCHO_ENABLED, HONCHO_BASE_URL, HONCHO_WORKSPACE

logger = logging.getLogger("delirium.honcho")

_honcho = None
_user_peer = None
_assistant_peer = None
_session_cache: dict[str, object] = {}


def _get_honcho():
    global _honcho
    if _honcho is not None:
        return _honcho
    if not HONCHO_ENABLED:
        return None
    try:
        from honcho import Honcho
        _honcho = Honcho(
            base_url=HONCHO_BASE_URL,
            workspace_id=HONCHO_WORKSPACE,
            environment="local",
        )
        logger.info("Honcho connected at %s (workspace: %s)", HONCHO_BASE_URL, HONCHO_WORKSPACE)
        return _honcho
    except Exception as e:
        logger.warning("Honcho unavailable: %s", e)
        return None


def _get_peers():
    global _user_peer, _assistant_peer
    if _user_peer is not None:
        return _user_peer, _assistant_peer
    h = _get_honcho()
    if not h:
        return None, None
    try:
        _user_peer = h.peer("user")
        _assistant_peer = h.peer("delirium")
        return _user_peer, _assistant_peer
    except Exception as e:
        logger.warning("Honcho peer creation failed: %s", e)
        return None, None


def _get_session(session_id: str):
    if session_id in _session_cache:
        return _session_cache[session_id]
    h = _get_honcho()
    if not h:
        return None
    try:
        session = h.session(session_id)
        _session_cache[session_id] = session
        return session
    except Exception as e:
        logger.warning("Honcho session failed: %s", e)
        return None


def push_message(session_id: str, user_message: str, assistant_response: str) -> bool:
    """Push a conversation turn to Honcho. Non-blocking, fail-safe."""
    if not HONCHO_ENABLED:
        return False
    user_peer, assistant_peer = _get_peers()
    session = _get_session(session_id)
    if not user_peer or not session:
        return False
    try:
        session.add_messages([
            user_peer.message(user_message[:2000]),
            assistant_peer.message(assistant_response[:2000]),
        ])
        return True
    except Exception as e:
        logger.warning("Honcho push failed: %s", e)
        return False


def query_user_model(question: str) -> Optional[str]:
    """Query Honcho for structured facts about the user."""
    if not HONCHO_ENABLED:
        return None
    user_peer, _ = _get_peers()
    if not user_peer:
        return None
    try:
        response = user_peer.chat(question)
        # Strip <think> tags if present
        if response and "<think>" in response:
            import re
            response = re.sub(r"<think>.*?</think>\s*", "", response, flags=re.DOTALL)
        return response.strip() if response else None
    except Exception as e:
        logger.warning("Honcho query failed: %s", e)
        return None


def get_facts_for_world_vision() -> Optional[str]:
    """Get structured facts to feed World Vision synthesis."""
    return query_user_model(
        "Summarize everything you know about this user: "
        "personality, recurring themes, blind spots, "
        "emotional patterns, concerning trends. Be factual and specific."
    )
