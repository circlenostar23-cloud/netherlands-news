import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = ROOT / "prompts"
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
TZ = ZoneInfo("Europe/Amsterdam")

load_dotenv(ROOT / ".env")

# Which model writes the briefing + script:
#   "claude-code" — Claude via the Claude Code CLI on your Claude Pro/Max subscription
#                   (needs CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`)
#   "gemini"      — Gemini API free tier
#   "claude"      — Claude API (paid separately from a subscription)
# Defaults to claude-code when a subscription token is present, else gemini.
WRITER = os.environ.get("NLNEWS_WRITER") or ("claude-code" if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN") else "gemini")
CLAUDE_CODE_MODEL = os.environ.get("NLNEWS_CLAUDE_CODE_MODEL", "opus")
GEMINI_TEXT_MODEL = os.environ.get("NLNEWS_GEMINI_MODEL", "gemini-3.8-flash")
CLAUDE_MODEL = os.environ.get("NLNEWS_CLAUDE_MODEL", "claude-sonnet-5")
TTS_MODEL = os.environ.get("NLNEWS_TTS_MODEL", "gemini-3.8-flash-tts")

SHOW_TITLE = "Dutch Daily Briefing"
# How many of each episode's stories are lighter fare (culture, sport, science, offbeat), as "min-max"
LIGHT_STORIES = tuple(int(n) for n in os.environ.get("NLNEWS_LIGHT_STORIES", "2-3").split("-"))
HOSTS = {
    # speaker name -> Gemini prebuilt voice
    "Maya": "Kore",
    "Sam": "Puck",
}
# Fallback voices (Microsoft neural, via edge-tts) when Gemini TTS fails, e.g. at its daily limit
FALLBACK_VOICES = {
    "Maya": "en-US-AvaMultilingualNeural",
    "Sam": "en-US-AndrewMultilingualNeural",
}


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    lang: str
    section: str
    weight: float = 1.0
    hours: int | None = None  # look-back override for slow feeds whose stories stay fresh for days


def load_sources() -> list[Source]:
    raw = yaml.safe_load((ROOT / "sources.yaml").read_text())
    return [Source(**s) for s in raw["sources"]]


def load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text()


def day_dir(day: date) -> Path:
    d = DATA_DIR / day.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d


def require_env(*names: str) -> dict[str, str]:
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(f"Missing required environment variables: {', '.join(missing)}")
    return {n: os.environ[n] for n in names}
