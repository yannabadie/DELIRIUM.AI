"""Claude.ai conversation import.

Parses JSON files from Claude.ai export (Settings > Export Data).
The export ZIP contains individual JSON files per conversation.

Known formats:
- List of conversations: [{uuid, name, created_at, updated_at, chat_messages: [{sender, text, ...}]}]
- Single conversation object with similar structure
- Variations with "content" blocks instead of "text"

The parser is robust to format variations and logs errors per conversation.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.import_.base import BaseImporter, ImportedMessage

logger = logging.getLogger("delirium.import.claude_ai")


class ClaudeImporter(BaseImporter):
    """Import conversations from a Claude.ai export."""

    source_name = "claude"

    def parse(self, file_path: str) -> list[ImportedMessage]:
        path = Path(file_path)

        if path.suffix == ".zip":
            return self._parse_zip(path)
        elif path.suffix == ".json":
            return self._parse_json_file(path)
        elif path.is_dir():
            return self._parse_directory(path)
        else:
            raise ValueError(f"Unsupported: {path}. Expected .json, .zip, or directory")

    def _parse_zip(self, zip_path: Path) -> list[ImportedMessage]:
        import zipfile
        messages = []
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if name.endswith(".json"):
                    try:
                        with zf.open(name) as f:
                            data = json.load(f)
                        messages.extend(self._extract_from_data(data, name))
                    except (json.JSONDecodeError, Exception) as e:
                        logger.warning("Skipping %s: %s", name, e)
        logger.info("Extracted %d message pairs from ZIP %s", len(messages), zip_path.name)
        return messages

    def _parse_json_file(self, json_path: Path) -> list[ImportedMessage]:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        messages = self._extract_from_data(data, json_path.name)
        logger.info("Extracted %d message pairs from %s", len(messages), json_path.name)
        return messages

    def _parse_directory(self, dir_path: Path) -> list[ImportedMessage]:
        messages = []
        for json_file in sorted(dir_path.glob("*.json")):
            try:
                with open(json_file, encoding="utf-8") as f:
                    data = json.load(f)
                messages.extend(self._extract_from_data(data, json_file.name))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Skipping %s: %s", json_file.name, e)
        logger.info("Extracted %d message pairs from directory %s", len(messages), dir_path)
        return messages

    def _extract_from_data(self, data, source_name: str) -> list[ImportedMessage]:
        """Handle multiple Claude export format variations."""
        # If it's a list, it could be a list of conversations or a list of messages
        if isinstance(data, list):
            messages = []
            for item in data:
                if isinstance(item, dict):
                    messages.extend(self._extract_conversation(item))
            return messages
        elif isinstance(data, dict):
            return self._extract_conversation(data)
        return []

    def _extract_conversation(self, conv: dict) -> list[ImportedMessage]:
        """Extract user/assistant pairs from a single conversation object."""
        title = conv.get("name") or conv.get("title") or conv.get("uuid", "Untitled")
        created = conv.get("created_at") or conv.get("create_time") or ""

        # Find the messages list — Claude uses various key names
        raw_messages = (
            conv.get("chat_messages")
            or conv.get("messages")
            or conv.get("content")
            or []
        )

        if not isinstance(raw_messages, list):
            return []

        # Normalize each message to {role, text}
        normalized = []
        for msg in raw_messages:
            role, text = self._normalize_message(msg)
            if role and text:
                normalized.append({"role": role, "text": text, "raw": msg})

        # Pair human/assistant
        results = []
        i = 0
        while i < len(normalized) - 1:
            if normalized[i]["role"] == "human" and normalized[i + 1]["role"] == "assistant":
                ts = self._extract_timestamp(normalized[i]["raw"], created)
                results.append(ImportedMessage(
                    user_input=normalized[i]["text"],
                    assistant_response=normalized[i + 1]["text"],
                    timestamp=ts,
                    source="claude",
                    conversation_title=str(title),
                ))
                i += 2
            else:
                i += 1

        return results

    def _normalize_message(self, msg: dict) -> tuple[str | None, str | None]:
        """Normalize a Claude message to (role, text). Handles format variations."""
        if not isinstance(msg, dict):
            return None, None

        # Role detection
        sender = msg.get("sender") or msg.get("role") or msg.get("author") or ""
        if isinstance(sender, dict):
            sender = sender.get("role", "")
        sender = sender.lower()

        if sender in ("human", "user"):
            role = "human"
        elif sender in ("assistant", "ai", "claude"):
            role = "assistant"
        else:
            return None, None

        # Text extraction
        text = msg.get("text")
        if text and isinstance(text, str):
            return role, text.strip()

        # content field — can be string, list of strings, or list of content blocks
        content = msg.get("content")
        if isinstance(content, str):
            return role, content.strip()
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    parts.append(part.get("text", ""))
            text = "\n".join(p for p in parts if p.strip())
            if text:
                return role, text

        return None, None

    def _extract_timestamp(self, msg: dict, fallback: str) -> str:
        """Extract ISO timestamp from a message."""
        for key in ("created_at", "timestamp", "create_time"):
            val = msg.get(key)
            if val:
                if isinstance(val, (int, float)):
                    try:
                        return datetime.fromtimestamp(val).isoformat()
                    except (ValueError, OSError):
                        continue
                elif isinstance(val, str):
                    return val
        return fallback or ""
