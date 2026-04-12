"""ChatGPT conversation import.

Parses the conversations.json file from ChatGPT export
(Settings > Data Controls > Export Data).

Structure: [{title, create_time, mapping: {node_id: {message: {content: {parts: [...]}, author: {role}}}}}]
"""

import json
import logging
from datetime import datetime
from pathlib import Path

from src.import_.base import BaseImporter, ImportedMessage

logger = logging.getLogger("delirium.import.chatgpt")


class ChatGPTImporter(BaseImporter):
    """Import conversations from a ChatGPT export."""

    source_name = "chatgpt"

    def parse(self, file_path: str) -> list[ImportedMessage]:
        path = Path(file_path)

        # Handle both the zip and direct JSON
        if path.suffix == ".zip":
            return self._parse_zip(path)
        elif path.name == "conversations.json" or path.suffix == ".json":
            return self._parse_json(path)
        else:
            raise ValueError(f"Unsupported file: {path}. Expected conversations.json or .zip")

    def _parse_zip(self, zip_path: Path) -> list[ImportedMessage]:
        import zipfile
        with zipfile.ZipFile(zip_path) as zf:
            if "conversations.json" not in zf.namelist():
                raise ValueError("conversations.json not found in zip archive")
            with zf.open("conversations.json") as f:
                data = json.load(f)
        return self._extract_messages(data)

    def _parse_json(self, json_path: Path) -> list[ImportedMessage]:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        return self._extract_messages(data)

    def _extract_messages(self, conversations: list[dict]) -> list[ImportedMessage]:
        messages = []

        for conv in conversations:
            title = conv.get("title", "Untitled")
            create_time = conv.get("create_time", 0)

            # Build ordered message list from the mapping tree
            mapping = conv.get("mapping", {})
            ordered = self._linearize_mapping(mapping)

            # Pair user messages with assistant responses
            i = 0
            while i < len(ordered) - 1:
                user_msg = ordered[i]
                assistant_msg = ordered[i + 1]

                if user_msg["role"] == "user" and assistant_msg["role"] == "assistant":
                    ts = user_msg.get("create_time") or create_time or 0
                    try:
                        timestamp = datetime.fromtimestamp(ts).isoformat() if ts else ""
                    except (ValueError, OSError):
                        timestamp = ""

                    messages.append(ImportedMessage(
                        user_input=user_msg["text"],
                        assistant_response=assistant_msg["text"],
                        timestamp=timestamp,
                        source="chatgpt",
                        conversation_title=title,
                    ))
                    i += 2
                else:
                    i += 1

        logger.info("Extracted %d message pairs from %d conversations",
                    len(messages), len(conversations))
        return messages

    def _linearize_mapping(self, mapping: dict) -> list[dict]:
        """Convert the ChatGPT tree-structured mapping into a linear message list."""
        # Find root node (no parent)
        nodes = {}
        children_map = {}
        for node_id, node in mapping.items():
            nodes[node_id] = node
            parent = node.get("parent")
            if parent:
                children_map.setdefault(parent, []).append(node_id)

        # Find root
        root = None
        for node_id, node in mapping.items():
            if node.get("parent") is None:
                root = node_id
                break

        if root is None:
            return []

        # DFS traversal
        result = []
        stack = [root]
        while stack:
            node_id = stack.pop(0)
            node = nodes.get(node_id, {})
            msg = node.get("message")

            if msg and msg.get("content") and msg["content"].get("parts"):
                role = msg.get("author", {}).get("role", "")
                if role in ("user", "assistant"):
                    text_parts = [
                        p for p in msg["content"]["parts"]
                        if isinstance(p, str) and p.strip()
                    ]
                    if text_parts:
                        result.append({
                            "role": role,
                            "text": "\n".join(text_parts),
                            "create_time": msg.get("create_time"),
                        })

            # Add children to process
            for child_id in children_map.get(node_id, []):
                stack.append(child_id)

        return result
