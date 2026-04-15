from src.llm_client import LLMClient


def test_chat_uses_behavioral_first_message_when_messages_are_empty():
    client = LLMClient.__new__(LLMClient)
    client.client = None

    reply = client.chat(system="system prompt", messages=[])

    assert "note" in reply.lower()
    assert "courses" in reply.lower()
    assert "?" in reply
