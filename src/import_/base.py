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


def collect_nested_text(value) -> str:
    """Flatten common nested text payload shapes into newline-separated text."""
    parts: list[str] = []
    append_nested_text(value, parts)
    return "\n".join(parts)


def first_text(*values) -> str:
    """Return the first non-empty text extracted from the provided values."""
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, (list, dict)):
            text = collect_nested_text(value)
            if text:
                return text
    return ""


def append_nested_text(value, parts: list[str]) -> None:
    """Append nested text values from strings, lists, and dict payloads."""
    if isinstance(value, str):
        text = value.strip()
        if text:
            parts.append(text)
        return

    if isinstance(value, list):
        for item in value:
            append_nested_text(item, parts)
        return

    if not isinstance(value, dict):
        return

    for key in ("text", "content", "value", "message", "output"):
        nested = value.get(key)
        before = len(parts)
        append_nested_text(nested, parts)
        if len(parts) > before:
            break
