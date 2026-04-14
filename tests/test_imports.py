import json
from pathlib import Path

from src.import_.base import collect_nested_text
from src.import_.claude_ai import ClaudeImporter
from src.import_.generic import GenericImporter


CLAUDE_EXPORT_PATH = Path("/mnt/c/Code/DELIRIUM.AI/claude/conversations.json")


def test_claude_importer_extracts_pairs_from_real_export():
    importer = ClaudeImporter()
    messages = importer.parse(str(CLAUDE_EXPORT_PATH))

    assert messages
    assert all(message.user_input for message in messages)
    assert all(message.assistant_response for message in messages)
    assert all(message.source == "claude" for message in messages)
    assert any(message.timestamp.endswith("Z") for message in messages)


def test_generic_importer_roundtrips_claude_messages(tmp_path):
    claude_messages = ClaudeImporter().parse(str(CLAUDE_EXPORT_PATH))[:3]
    payload = [
        {
            "user_input": message.user_input,
            "assistant_response": message.assistant_response,
            "timestamp": message.timestamp,
            "source": message.source,
            "conversation_title": message.conversation_title,
        }
        for message in claude_messages
    ]
    generic_path = tmp_path / "roundtrip.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert [(m.user_input, m.assistant_response) for m in parsed] == [
        (m.user_input, m.assistant_response) for m in claude_messages
    ]
    assert [m.timestamp for m in parsed] == [m.timestamp for m in claude_messages]
    assert [m.conversation_title for m in parsed] == [
        m.conversation_title for m in claude_messages
    ]


def test_claude_importer_prefers_visible_content_blocks_over_flat_text():
    data = {
        "name": "Structured Claude Response",
        "created_at": "2025-08-07T17:31:01Z",
        "chat_messages": [
            {
                "sender": "human",
                "text": "Inspect this repository",
                "created_at": "2025-08-07T17:31:01Z",
            },
            {
                "sender": "assistant",
                "text": "Private chain-of-thought\n\nVisible answer",
                "content": [
                    {"type": "thinking", "thinking": "Private chain-of-thought"},
                    {"type": "text", "text": "Visible answer"},
                    {"type": "tool_use", "name": "search"},
                    {"type": "tool_result", "content": "Tool transcript"},
                    {"type": "text", "text": "Second visible paragraph"},
                ],
                "created_at": "2025-08-07T17:31:02Z",
            },
        ],
    }

    parsed = ClaudeImporter()._extract_from_data(data, "synthetic.json")

    assert len(parsed) == 1
    assert parsed[0].assistant_response == (
        "Visible answer\nTool transcript\nSecond visible paragraph"
    )


def test_claude_importer_ignores_thinking_and_tool_use_blocks():
    data = {
        "name": "Hidden reasoning should not import",
        "created_at": "2026-02-16T11:19:52Z",
        "chat_messages": [
            {
                "sender": "human",
                "text": "Add the hyperlinks",
                "created_at": "2026-02-16T11:19:52Z",
            },
            {
                "sender": "assistant",
                "text": (
                    "Private chain-of-thought\n```\n"
                    "This block is not supported on your current device yet.\n"
                    "```\n\nVisible answer in raw text"
                ),
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Private chain-of-thought",
                    },
                    {
                        "type": "tool_use",
                        "name": "Filesystem:directory_tree",
                        "input": {"path": "/tmp"},
                    },
                    {
                        "type": "tool_result",
                        "content": [
                            {"type": "text", "text": "Visible tool transcript"},
                        ],
                    },
                ],
                "created_at": "2026-02-16T11:19:53Z",
            },
        ],
    }

    parsed = ClaudeImporter()._extract_from_data(data, "tool-result.json")

    assert len(parsed) == 1
    assert parsed[0].assistant_response == "Visible tool transcript"


def test_claude_importer_ignores_token_budget_and_flag_blocks():
    data = {
        "name": "Non-visible Claude metadata blocks",
        "created_at": "2026-04-14T12:00:00Z",
        "chat_messages": [
            {
                "sender": "human",
                "text": "Summarize the repo",
                "created_at": "2026-04-14T12:00:00Z",
            },
            {
                "sender": "assistant",
                "content": [
                    {"type": "token_budget"},
                    {"type": "flag"},
                    {"type": "text", "text": "Visible answer"},
                    {"type": "tool_result", "content": [{"text": "Visible tool output"}]},
                ],
                "created_at": "2026-04-14T12:00:01Z",
            },
        ],
    }

    parsed = ClaudeImporter()._extract_from_data(data, "non-visible-blocks.json")

    assert len(parsed) == 1
    assert parsed[0].assistant_response == "Visible answer\nVisible tool output"


def test_claude_importer_accepts_conversation_wrapper():
    data = {
        "conversation": {
            "name": "Wrapped Claude Conversation",
            "created_at": "2026-02-17T09:00:00Z",
            "chat_messages": [
                {
                    "sender": "human",
                    "text": "Hello",
                    "created_at": "2026-02-17T09:00:00Z",
                },
                {
                    "sender": "assistant",
                    "content": [{"type": "text", "text": "Hi there"}],
                    "created_at": "2026-02-17T09:00:01Z",
                },
            ],
        }
    }

    parsed = ClaudeImporter()._extract_from_data(data, "wrapped.json")

    assert len(parsed) == 1
    assert parsed[0].user_input == "Hello"
    assert parsed[0].assistant_response == "Hi there"
    assert parsed[0].conversation_title == "Wrapped Claude Conversation"


def test_claude_importer_accepts_nested_singular_wrapper():
    data = {
        "data": {
            "conversation": {
                "name": "Nested Wrapped Claude Conversation",
                "created_at": "2026-02-17T10:00:00Z",
                "chat_messages": [
                    {
                        "sender": "human",
                        "text": "Ping",
                        "created_at": "2026-02-17T10:00:00Z",
                    },
                    {
                        "sender": "assistant",
                        "content": [{"type": "text", "text": "Pong"}],
                        "created_at": "2026-02-17T10:00:01Z",
                    },
                ],
            }
        }
    }

    parsed = ClaudeImporter()._extract_from_data(data, "nested-wrapped.json")

    assert len(parsed) == 1
    assert parsed[0].user_input == "Ping"
    assert parsed[0].assistant_response == "Pong"
    assert parsed[0].conversation_title == "Nested Wrapped Claude Conversation"


def test_claude_importer_falls_back_to_assistant_timestamp():
    data = {
        "name": "Assistant timestamp fallback",
        "created_at": "2026-02-17T12:00:00Z",
        "chat_messages": [
            {
                "sender": "human",
                "text": "Question without timestamp",
            },
            {
                "sender": "assistant",
                "content": [{"type": "text", "text": "Answer with timestamp"}],
                "created_at": "2026-02-17T12:00:01Z",
            },
        ],
    }

    parsed = ClaudeImporter()._extract_from_data(data, "assistant-timestamp.json")

    assert len(parsed) == 1
    assert parsed[0].timestamp == "2026-02-17T12:00:01Z"


def test_claude_importer_sanitizes_flat_text_fallback():
    data = {
        "name": "Fallback text only",
        "created_at": "2026-02-15T19:41:34Z",
        "chat_messages": [
            {
                "sender": "human",
                "text": "Continue",
                "created_at": "2026-02-15T19:41:34Z",
            },
            {
                "sender": "assistant",
                "text": (
                    "Visible summary paragraph.\n"
                    "```\nThis block is not supported on your current device yet.\n```\n"
                    "\nSecond visible paragraph.\n"
                    "Viewing artifacts created via the Analysis Tool web feature preview "
                    "isn't yet supported on mobile.\n"
                ),
                "content": [
                    {
                        "type": "thinking",
                        "thinking": "Hidden reasoning only",
                    }
                ],
                "created_at": "2026-02-15T19:41:35Z",
            },
        ],
    }

    parsed = ClaudeImporter()._extract_from_data(data, "flat-fallback.json")

    assert len(parsed) == 1
    assert parsed[0].assistant_response == (
        "Visible summary paragraph.\n\nSecond visible paragraph."
    )


def test_generic_importer_accepts_wrapper_dict_and_preserves_title(tmp_path):
    payload = {
        "source": "wrapped-source",
        "conversation_title": "Wrapper Title",
        "messages": [
            {
                "user": "hello",
                "assistant": "world",
                "timestamp": "2025-01-01T00:00:00Z",
            }
        ]
    }
    generic_path = tmp_path / "wrapped.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 1
    assert parsed[0].conversation_title == "Wrapper Title"
    assert parsed[0].source == "wrapped-source"


def test_generic_importer_accepts_singular_conversation_wrapper(tmp_path):
    payload = {
        "source": "wrapped-source",
        "conversation_title": "Wrapper Title",
        "conversation": {
            "user_input": "hello",
            "assistant_response": "world",
            "timestamp": "2025-01-01T00:00:00Z",
        },
    }
    generic_path = tmp_path / "wrapped-single-conversation.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 1
    assert parsed[0].user_input == "hello"
    assert parsed[0].assistant_response == "world"
    assert parsed[0].conversation_title == "Wrapper Title"
    assert parsed[0].source == "wrapped-source"


def test_generic_importer_accepts_structured_blocks_for_roundtrip(tmp_path):
    payload = [
        {
            "user": [
                {"type": "text", "text": "first line"},
                {"type": "text", "content": "second line"},
            ],
            "assistant_response": [
                "plain intro",
                {"type": "text", "value": "plain outro"},
            ],
            "timestamp": "2025-01-01T00:00:00Z",
            "conversation_title": "Structured",
        }
    ]
    generic_path = tmp_path / "structured.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 1
    assert parsed[0].user_input == "first line\nsecond line"
    assert parsed[0].assistant_response == "plain intro\nplain outro"
    assert parsed[0].conversation_title == "Structured"


def test_generic_importer_recurses_nested_block_payloads(tmp_path):
    payload = {
        "title": "Nested Wrapper",
        "data": [
            {
                "prompt": {
                    "content": [
                        {"text": "outer user"},
                        {"content": [{"value": "inner user"}]},
                    ]
                },
                "output": {
                    "message": {
                        "content": [
                            {"text": "outer assistant"},
                            {
                                "content": [
                                    {"text": "inner assistant"},
                                    {"message": "final assistant"},
                                ]
                            },
                        ]
                    }
                },
            }
        ],
    }
    generic_path = tmp_path / "nested.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 1
    assert parsed[0].user_input == "outer user\ninner user"
    assert parsed[0].assistant_response == (
        "outer assistant\ninner assistant\nfinal assistant"
    )
    assert parsed[0].conversation_title == "Nested Wrapper"


def test_generic_importer_flattens_nested_conversation_wrappers(tmp_path):
    payload = {
        "source": "top-source",
        "conversations": [
            {
                "conversation_title": "Nested Conversation",
                "messages": [
                    {
                        "user_input": "first question",
                        "assistant_response": "first answer",
                    },
                    {
                        "user": {"text": "second question"},
                        "assistant": {"content": [{"text": "second answer"}]},
                        "timestamp": "2025-01-02T00:00:00Z",
                    },
                ],
            }
        ],
    }
    generic_path = tmp_path / "conversation_wrappers.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 2
    assert [m.user_input for m in parsed] == ["first question", "second question"]
    assert [m.assistant_response for m in parsed] == ["first answer", "second answer"]
    assert all(m.source == "top-source" for m in parsed)
    assert all(m.conversation_title == "Nested Conversation" for m in parsed)


def test_generic_importer_accepts_transcript_style_messages(tmp_path):
    payload = {
        "source": "chatlike",
        "conversation_title": "Transcript Wrapper",
        "messages": [
            {"role": "system", "content": "Instructions"},
            {
                "role": "user",
                "content": [{"type": "text", "text": "First question"}],
                "created_at": "2025-01-03T00:00:00Z",
            },
            {"role": "assistant", "content": "First answer"},
            {"sender": "human", "text": "Second question"},
            {
                "author": {"role": "assistant"},
                "content": [{"value": "Second answer"}],
            },
        ],
    }
    generic_path = tmp_path / "transcript.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 2
    assert [m.user_input for m in parsed] == ["First question", "Second question"]
    assert [m.assistant_response for m in parsed] == ["First answer", "Second answer"]
    assert parsed[0].timestamp == "2025-01-03T00:00:00Z"
    assert all(m.source == "chatlike" for m in parsed)
    assert all(m.conversation_title == "Transcript Wrapper" for m in parsed)


def test_generic_importer_falls_back_to_assistant_or_wrapper_timestamp_for_transcripts(tmp_path):
    payload = {
        "source": "chatlike",
        "conversation_title": "Transcript Timestamp Fallbacks",
        "timestamp": "2025-01-05T00:00:00Z",
        "messages": [
            {"role": "user", "content": "Question without timestamp"},
            {
                "role": "assistant",
                "content": "Answer with timestamp",
                "timestamp": "2025-01-04T00:00:00Z",
            },
            {"role": "user", "content": "Question using wrapper timestamp"},
            {"role": "assistant", "content": "Answer without timestamp"},
        ],
    }
    generic_path = tmp_path / "transcript-timestamp-fallbacks.json"
    generic_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = GenericImporter().parse(str(generic_path))

    assert len(parsed) == 2
    assert [m.timestamp for m in parsed] == [
        "2025-01-04T00:00:00Z",
        "2025-01-05T00:00:00Z",
    ]
    assert [m.user_input for m in parsed] == [
        "Question without timestamp",
        "Question using wrapper timestamp",
    ]
    assert [m.assistant_response for m in parsed] == [
        "Answer with timestamp",
        "Answer without timestamp",
    ]


def test_shared_nested_text_helper_matches_importer_expectations():
    payload = [
        {"text": "outer"},
        {"content": [{"value": "inner"}, {"message": "tail"}]},
    ]

    assert collect_nested_text(payload) == "outer\ninner\ntail"
    assert GenericImporter._as_text(payload) == "outer\ninner\ntail"
    assert ClaudeImporter._extract_text_from_blocks(
        [{"type": "tool_result", "content": payload}]
    ) == "outer\ninner\ntail"
