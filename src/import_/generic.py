"""Generic conversation import.

Accepts a simple JSON format that can represent any AI conversation source:

[
  {
    "user": "message utilisateur",
    "assistant": "réponse IA",
    "source": "gemini",
    "timestamp": "2025-06-15T14:30:00"
  }
]

Command: /import generic <path>
"""

import json
import logging
from pathlib import Path

from src.import_.base import BaseImporter, ImportedMessage, first_text

logger = logging.getLogger("delirium.import.generic")


class GenericImporter(BaseImporter):
    """Import conversations from a simple JSON format."""

    source_name = "generic"
    _WRAPPER_KEYS = ("messages", "data", "conversation", "conversations")
    _USER_ROLES = {"user", "human"}
    _ASSISTANT_ROLES = {"assistant", "ai", "claude", "model"}

    def parse(self, file_path: str) -> list[ImportedMessage]:
        path = Path(file_path)

        if path.suffix != ".json":
            raise ValueError(f"Expected .json file, got: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        messages = []
        for i, entry, defaults in self._iter_entries(data):
            if not isinstance(entry, dict):
                logger.warning("Skipping entry %d: not a dict", i)
                continue

            user_text = self._as_text(
                entry.get("user"),
                entry.get("user_input"),
                entry.get("prompt"),
            )
            assistant_text = self._as_text(
                entry.get("assistant"),
                entry.get("assistant_response"),
                entry.get("response"),
                entry.get("output"),
            )

            if not user_text or not assistant_text:
                logger.warning("Skipping entry %d: missing user or assistant field", i)
                continue

            messages.append(
                ImportedMessage(
                    user_input=user_text,
                    assistant_response=assistant_text,
                    timestamp=self._as_text(
                        entry.get("timestamp"),
                        defaults.get("timestamp"),
                    )
                    or "",
                    source=self._as_text(
                        entry.get("source"),
                        defaults.get("source"),
                    )
                    or "generic",
                    conversation_title=(
                        self._as_text(
                            entry.get("title"),
                            entry.get("conversation_title"),
                            defaults.get("title"),
                            defaults.get("conversation_title"),
                        )
                        or ""
                    ),
                )
            )

        logger.info("Extracted %d message pairs from %s", len(messages), path.name)
        return messages

    @classmethod
    def _iter_entries(cls, data) -> list[tuple[int, dict, dict[str, object]]]:
        items = list(cls._walk_entries(data, {}))
        if not items:
            raise ValueError("Expected a JSON array or object of message pairs")
        return [(index, entry, defaults) for index, (entry, defaults) in enumerate(items)]

    @classmethod
    def _walk_entries(cls, data, inherited_defaults: dict[str, object]):
        if isinstance(data, list):
            if cls._looks_like_transcript(data):
                yield from cls._iter_transcript_pairs(data, inherited_defaults)
                return
            for item in data:
                yield from cls._walk_entries(item, inherited_defaults)
            return

        if not isinstance(data, dict):
            return

        defaults = cls._merge_defaults(inherited_defaults, data)
        for key in cls._WRAPPER_KEYS:
            nested = data.get(key)
            if isinstance(nested, list):
                yield from cls._walk_entries(nested, defaults)
                return
            if isinstance(nested, dict):
                yield from cls._walk_entries(nested, defaults)
                return

        yield data, defaults

    @classmethod
    def _looks_like_transcript(cls, items: list[object]) -> bool:
        saw_role_message = False
        for item in items:
            if not isinstance(item, dict):
                return False
            if any(key in item for key in ("user", "user_input", "prompt", "assistant", "assistant_response", "response", "output")):
                return False
            if cls._normalize_role(item) and cls._message_text(item):
                saw_role_message = True
        return saw_role_message

    @classmethod
    def _iter_transcript_pairs(cls, items: list[dict], defaults: dict[str, object]):
        pending_user = None
        for item in items:
            role = cls._normalize_role(item)
            text = cls._message_text(item)
            if not role or not text:
                continue

            if role in cls._USER_ROLES:
                pending_user = item
                continue

            if role in cls._ASSISTANT_ROLES and pending_user:
                yield (
                    {
                        "user_input": cls._message_text(pending_user),
                        "assistant_response": text,
                        "timestamp": (
                            cls._message_timestamp(pending_user)
                            or cls._message_timestamp(item)
                            or cls._as_text(defaults.get("timestamp"))
                        ),
                    },
                    defaults,
                )
                pending_user = None

    @classmethod
    def _normalize_role(cls, entry: dict[str, object]) -> str:
        sender = entry.get("role") or entry.get("sender") or entry.get("author") or ""
        if isinstance(sender, dict):
            sender = sender.get("role", "")
        if not isinstance(sender, str):
            return ""
        return sender.strip().lower()

    @classmethod
    def _message_text(cls, entry: dict[str, object]) -> str:
        return cls._as_text(
            entry.get("content"),
            entry.get("text"),
            entry.get("value"),
            entry.get("message"),
            entry.get("output"),
        )

    @staticmethod
    def _message_timestamp(entry: dict[str, object]) -> str:
        return GenericImporter._as_text(
            entry.get("timestamp"),
            entry.get("created_at"),
            entry.get("create_time"),
        )

    @staticmethod
    def _merge_defaults(base: dict[str, object], entry: dict[str, object]) -> dict[str, object]:
        defaults = dict(base)
        for key in ("timestamp", "source", "title", "conversation_title"):
            value = entry.get(key)
            if value not in (None, "", []):
                defaults[key] = value
        return defaults

    @staticmethod
    def _as_text(*values) -> str:
        return first_text(*values)
