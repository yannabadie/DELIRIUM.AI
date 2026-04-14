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
from pathlib import Path

from src.import_.base import (
    BaseImporter,
    ImportedMessage,
    append_nested_text,
)

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
        json_files = sorted(dir_path.rglob("*.json"))
        for json_file in json_files:
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
        if isinstance(data, list):
            messages = []
            for item in data:
                if isinstance(item, dict):
                    messages.extend(self._extract_conversation(item))
            return messages
        if isinstance(data, dict):
            if any(key in data for key in ("chat_messages", "messages", "content")):
                return self._extract_conversation(data)

            for key in ("conversation", "conversations", "data"):
                nested = data.get(key)
                if isinstance(nested, (dict, list)):
                    return self._extract_from_data(nested, source_name)

            logger.warning("Unsupported Claude JSON object in %s", source_name)
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

        normalized = []
        for msg in raw_messages:
            role, text = self._normalize_message(msg)
            if role and text:
                normalized.append(
                    {
                        "role": role,
                        "text": text,
                        "raw": msg,
                    }
                )

        results = []
        pending_user = None
        for message in normalized:
            if message["role"] == "human":
                pending_user = message
                continue

            if message["role"] == "assistant" and pending_user:
                ts = self._extract_pair_timestamp(
                    pending_user["raw"],
                    message["raw"],
                    created,
                )
                results.append(
                    ImportedMessage(
                        user_input=pending_user["text"],
                        assistant_response=message["text"],
                        timestamp=ts,
                        source="claude",
                        conversation_title=str(title),
                    )
                )
                pending_user = None

        return results

    def _extract_pair_timestamp(
        self,
        user_msg: dict,
        assistant_msg: dict,
        fallback: str,
    ) -> str:
        return (
            self._extract_timestamp(user_msg, "")
            or self._extract_timestamp(assistant_msg, "")
            or fallback
        )

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

        content = msg.get("content")
        if isinstance(content, list):
            text = self._extract_text_from_blocks(content)
            if text:
                return role, text
        if isinstance(content, str) and content.strip():
            return role, content.strip()

        # Fallback for exports that only expose a flat text field.
        text = msg.get("text")
        if text and isinstance(text, str):
            cleaned = self._clean_flat_text(text)
            if cleaned:
                return role, cleaned

        return None, None

    @staticmethod
    def _extract_text_from_blocks(blocks: list) -> str:
        parts = []
        for block in blocks:
            if isinstance(block, str):
                parts.append(block)
                continue

            if not isinstance(block, dict):
                continue

            block_type = block.get("type")
            if block_type == "text":
                for key in ("text", "content", "value"):
                    if isinstance(block.get(key), str):
                        parts.append(block[key])
                        break
                continue

            if block_type == "tool_result":
                append_nested_text(block.get("content"), parts)
                continue

            content = block.get("content")
            if block_type is None:
                append_nested_text(content, parts)

        return "\n".join(part.strip() for part in parts if isinstance(part, str) and part.strip())

    @staticmethod
    def _clean_flat_text(text: str) -> str:
        lines = []
        in_fence = False
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if stripped in {
                "This block is not supported on your current device yet.",
                "Viewing artifacts created via the Analysis Tool web feature preview isn't yet supported on mobile.",
            }:
                continue
            lines.append(raw_line.rstrip())

        cleaned = "\n".join(lines).strip()
        return cleaned

    def _extract_timestamp(self, msg: dict, fallback: str) -> str:
        """Extract ISO timestamp from a message."""
        for key in ("created_at", "timestamp", "create_time"):
            val = msg.get(key)
            if val:
                if isinstance(val, str):
                    return val
                if isinstance(val, (int, float)):
                    return str(val)

        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            for key in ("start_timestamp", "stop_timestamp"):
                if isinstance(block.get(key), str) and block[key]:
                    return block[key]

        return fallback or ""
