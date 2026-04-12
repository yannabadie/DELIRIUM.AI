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

from src.import_.base import BaseImporter, ImportedMessage

logger = logging.getLogger("delirium.import.generic")


class GenericImporter(BaseImporter):
    """Import conversations from a simple JSON format."""

    source_name = "generic"

    def parse(self, file_path: str) -> list[ImportedMessage]:
        path = Path(file_path)

        if path.suffix != ".json":
            raise ValueError(f"Expected .json file, got: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("Expected a JSON array of message objects")

        messages = []
        for i, entry in enumerate(data):
            if not isinstance(entry, dict):
                logger.warning("Skipping entry %d: not a dict", i)
                continue

            user_text = entry.get("user", "").strip()
            assistant_text = entry.get("assistant", "").strip()

            if not user_text or not assistant_text:
                logger.warning("Skipping entry %d: missing user or assistant field", i)
                continue

            messages.append(ImportedMessage(
                user_input=user_text,
                assistant_response=assistant_text,
                timestamp=entry.get("timestamp", ""),
                source=entry.get("source", "generic"),
                conversation_title=entry.get("title", ""),
            ))

        logger.info("Extracted %d message pairs from %s", len(messages), path.name)
        return messages
