"""Base interface for conversation imports."""

from dataclasses import dataclass


@dataclass
class ImportedMessage:
    """A single user/assistant exchange extracted from an external source."""
    user_input: str
    assistant_response: str
    timestamp: str  # ISO format
    source: str     # "chatgpt", "claude", "gemini", etc.
    conversation_title: str = ""


class BaseImporter:
    """Interface for conversation importers."""

    source_name: str = "unknown"

    def parse(self, file_path: str) -> list[ImportedMessage]:
        """Parse an export file and return a list of messages."""
        raise NotImplementedError
