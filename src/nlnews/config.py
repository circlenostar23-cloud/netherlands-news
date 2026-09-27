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

# Which model writes the briefing + script: "gemini" (free tier) or "claude" (paid API)
WRITER = os.environ.get("NLNEWS_WRITER", "gemini")
GEMINI_TEXT_MODEL = os.environ.get("NLNEWS_GEMINI_MODEL", "gemini-3.8-flash")
CLAUDE_MODEL = os.environ.get("NLNEWS_CLAUDE_MODEL", "claude-sonnet-5")
TTS_MODEL = os.environ.get("NLNEWS_TTS_MODEL", "gemini-3.8-flash-tts")

SHOW_TITLE = "Dutch Daily Briefing"
HOSTS = {
    # speaker name -> Gemini prebuilt voice
    "Maya": "Kore",
    "Sam": "Puck",
}


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    lang: str
    section: str
    weight: float = 1.0


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
