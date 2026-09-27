"""Thin wrapper around Claude structured outputs."""

from typing import TypeVar

import anthropic
from pydantic import BaseModel

from nlnews.config import MODEL

T = TypeVar("T", bound=BaseModel)
_client: anthropic.Anthropic | None = None


def client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def ask(system: str, user: str, schema: type[T], *, effort: str = "medium", max_tokens: int = 16000) -> T:
    response = client().messages.parse(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"effort": effort},
        output_format=schema,
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Claude hit max_tokens before finishing; raise max_tokens")
    u = response.usage
    print(f"  [{MODEL}] in={u.input_tokens} out={u.output_tokens}")
    return response.parsed_output
