"""Structured-output LLM calls. See WRITER in config.py for the available backends."""

import json
import os
import subprocess
import tempfile
from typing import TypeVar

from pydantic import BaseModel

from nlnews.config import CLAUDE_CODE_MODEL, CLAUDE_MODEL, GEMINI_TEXT_MODEL, WRITER

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


def _ask_gemini(system: str, user: str, schema: type[T], effort: str, max_tokens: int, web: bool,
                timeout: int) -> T:
    from google import genai

    client = _clients.setdefault("gemini", genai.Client(api_key=os.environ.get("GEMINI_API_KEY")))
    interaction = client.interactions.create(
        model=GEMINI_TEXT_MODEL,
        system_instruction=system,
        input=user,
        response_format={"type": "text", "mime_type": "application/json",
                         "schema": _inline_refs(schema.model_json_schema())},
        generation_config={"thinking_level": effort, "max_output_tokens": max_tokens},
        **({"tools": [{"type": "google_search"}]} if web else {}),
    )
    print(f"  [{GEMINI_TEXT_MODEL}]")
    return schema.model_validate_json(interaction.output_text)


def _ask_claude(system: str, user: str, schema: type[T], effort: str, max_tokens: int, web: bool,
                timeout: int) -> T:
    import anthropic

    if web:
        raise RuntimeError("web search isn't wired up for the Claude API backend")

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


def _ask_claude_code(system: str, user: str, schema: type[T], effort: str, max_tokens: int, web: bool,
                     timeout: int) -> T:
    """Headless Claude Code (`claude -p`) — runs on a Claude subscription instead of API billing."""
    cmd = [
        "claude", "-p",
        "--model", CLAUDE_CODE_MODEL,
        "--effort", effort,
        "--system-prompt", system,
        "--json-schema", json.dumps(schema.model_json_schema()),
        "--output-format", "json",
        *(["--tools", "WebSearch,WebFetch", "--allowedTools", "WebSearch,WebFetch"] if web else ["--tools", ""]),
        "--no-session-persistence",
    ]
    # Run from an empty dir so no project files or CLAUDE.md leak into the context
    with tempfile.TemporaryDirectory() as cwd:
        proc = subprocess.run(cmd, input=user, capture_output=True, text=True, cwd=cwd, timeout=timeout)
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude CLI failed (exit {proc.returncode}): {proc.stderr[-500:] or proc.stdout[-500:]}")
    if out.get("is_error"):
        raise RuntimeError(f"claude CLI error: {out.get('result')}")
    print(f"  [claude-code/{CLAUDE_CODE_MODEL}] {out.get('duration_ms', 0) / 1000:.0f}s")
    if out.get("structured_output") is not None:
        return schema.model_validate(out["structured_output"])
    return schema.model_validate_json(out["result"])


BACKENDS = {"claude-code": _ask_claude_code, "claude": _ask_claude, "gemini": _ask_gemini}


def ask(system: str, user: str, schema: type[T], *, effort: str = "medium", max_tokens: int = 16000,
        web: bool = False, timeout: int = 900, fallback: bool = True) -> T:
    """`web=True` lets the model search and read the web before answering. `timeout` (seconds) only
    bounds the claude-code backend; `fallback=False` skips the Gemini retry when a call fails."""
    try:
        return BACKENDS[WRITER](system, user, schema, effort, max_tokens, web, timeout)
    except Exception as exc:
        if WRITER == "gemini" or not fallback:
            raise
        # Subscription limits or an expired token shouldn't cost you the morning episode
        print(f"  {WRITER} failed ({exc}); falling back to Gemini")
        return _ask_gemini(system, user, schema, effort, max_tokens, web, timeout)
