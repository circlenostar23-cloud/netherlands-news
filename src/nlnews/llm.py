"""Structured-output LLM calls. Gemini (free tier) by default; set NLNEWS_WRITER=claude to use Claude."""

import os
from typing import TypeVar

from pydantic import BaseModel

from nlnews.config import CLAUDE_MODEL, GEMINI_TEXT_MODEL, WRITER

T = TypeVar("T", bound=BaseModel)
_clients: dict = {}


def _inline_refs(schema: dict) -> dict:
    """Resolve Pydantic's $defs/$ref so the schema is self-contained."""
    defs = schema.pop("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def _ask_gemini(system: str, user: str, schema: type[T], effort: str, max_tokens: int) -> T:
    from google import genai

    client = _clients.setdefault("gemini", genai.Client(api_key=os.environ.get("GEMINI_API_KEY")))
    interaction = client.interactions.create(
        model=GEMINI_TEXT_MODEL,
        system_instruction=system,
        input=user,
        response_format={"type": "text", "mime_type": "application/json",
                         "schema": _inline_refs(schema.model_json_schema())},
        generation_config={"thinking_level": effort, "max_output_tokens": max_tokens},
    )
    print(f"  [{GEMINI_TEXT_MODEL}]")
    return schema.model_validate_json(interaction.output_text)


def _ask_claude(system: str, user: str, schema: type[T], effort: str, max_tokens: int) -> T:
    import anthropic

    client = _clients.setdefault("claude", anthropic.Anthropic())
    response = client.messages.parse(
        model=CLAUDE_MODEL,
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
    print(f"  [{CLAUDE_MODEL}] in={u.input_tokens} out={u.output_tokens}")
    return response.parsed_output


def ask(system: str, user: str, schema: type[T], *, effort: str = "medium", max_tokens: int = 16000) -> T:
    fn = _ask_claude if WRITER == "claude" else _ask_gemini
    return fn(system, user, schema, effort, max_tokens)
