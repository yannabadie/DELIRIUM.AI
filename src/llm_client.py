import re
from openai import OpenAI, AsyncOpenAI
from src.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL, MINIMAX_MODEL_FAST

_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)


def _strip_think_tags(text: str) -> str:
    """Remove <think>...</think> blocks from MiniMax M2.7 output."""
    return _THINK_RE.sub("", text).strip()


def _check_api_key():
    if not MINIMAX_API_KEY:
        raise RuntimeError(
            "MINIMAX_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )


class LLMClient:
    """Synchronous MiniMax client via OpenAI SDK for S1 responses."""

    def __init__(self):
        _check_api_key()
        self.client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    def chat(self, system: str, messages: list[dict], model: str | None = None,
             stream: bool = False) -> str:
        model = model or MINIMAX_MODEL
        full_messages = [{"role": "system", "content": system}] + messages

        if stream:
            return self._chat_stream(full_messages, model)

        response = self.client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return _strip_think_tags(response.choices[0].message.content or "")

    def chat_stream_iter(self, system: str, messages: list[dict],
                         model: str | None = None):
        """Yield cleaned tokens one by one. Caller handles display."""
        model = model or MINIMAX_MODEL
        full_messages = [{"role": "system", "content": system}] + messages

        stream = self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            stream=True,
        )

        in_think = False
        for chunk in stream:
            delta = chunk.choices[0].delta
            if not delta.content:
                continue
            token = delta.content
            if "<think>" in token:
                in_think = True
                # Keep any text before <think>
                before = token.split("<think>")[0]
                if before.strip():
                    yield before
            if in_think:
                if "</think>" in token:
                    in_think = False
                    # Keep any text after </think>
                    after = token.split("</think>", 1)[-1]
                    if after.strip():
                        yield after
                continue
            yield token

    def _chat_stream(self, messages: list[dict], model: str) -> str:
        """Stream response, printing tokens as they arrive. Returns full text."""
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        chunks = []
        in_think = False
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                token = delta.content
                if "<think>" in token:
                    in_think = True
                if in_think:
                    if "</think>" in token:
                        in_think = False
                    chunks.append(token)
                    continue
                print(token, end="", flush=True)
                chunks.append(token)
        print()
        return _strip_think_tags("".join(chunks))


class AsyncLLMClient:
    """Async MiniMax client for S2 analysis (runs in background)."""

    def __init__(self):
        _check_api_key()
        self.client = AsyncOpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)

    async def chat(self, system: str, messages: list[dict],
                   model: str | None = None) -> str:
        model = model or MINIMAX_MODEL_FAST
        full_messages = [{"role": "system", "content": system}] + messages

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
        )
        return _strip_think_tags(response.choices[0].message.content or "")
