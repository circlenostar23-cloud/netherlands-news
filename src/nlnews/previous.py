"""What recent episodes already covered, so today's episode brings updates instead of repeats.

Each published episode's `briefing.md` is attached to its GitHub release, which is the only
record that survives between Actions runs (data/ is thrown away). A story from a recent
episode can come back only as a follow-up with a real development, written as just the news.
"""

import difflib
import re
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from nlnews.config import DATA_DIR
from nlnews.models import Article, PriorStory

_STORY = re.compile(r"^## \d+\. (.+)$", re.M)
_PICK = re.compile(r"^- \*\*(.+?)\*\*", re.M)
_CHECKED = re.compile(r"^\*\*Checked:\*\* (.+ → (?!not confirmed).+)$", re.M)


def _briefing_md(day: date) -> str | None:
    """The briefing as published (the release), else a local build of that day."""
    from nlnews.publish import _gh, _repo
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _gh("release", "download", f"ep-{day.isoformat()}", "--pattern", "briefing.md",
                "--dir", tmp, "--repo", _repo())
            return (Path(tmp) / "briefing.md").read_text()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        local = DATA_DIR / day.isoformat() / "briefing.md"
        return local.read_text() if local.exists() else None


def parse(day: date, md: str) -> list[PriorStory]:
    md = md.split("\n## What's on in Amsterdam", 1)[0]
    heads = list(_STORY.finditer(md))
    stories = []
    for h, nxt in zip(heads, heads[1:] + [None]):
        body = md[h.end():nxt.start() if nxt else len(md)]
        paras = [p.strip() for p in body.split("\n\n") if p.strip()]
        summary = next((p for p in paras if not p.startswith(("*", "-"))), "")
        stories.append(PriorStory(
            date=day.isoformat(),
            headline=h.group(1).strip(),
            summary=summary,
            checked=_CHECKED.findall(body),
            urls=re.findall(r"^- (https?://\S+)$", body, re.M),
        ))
    return stories


def load(day: date, days: int = 2) -> list[PriorStory]:
    """Stories from the episodes of the last `days` days, most recent first."""
    out = []
    for back in range(1, days + 1):
        d = day - timedelta(days=back)
        if md := _briefing_md(d):
            out += parse(d, md)
    return out


def agenda_picks(day: date, days: int = 3) -> list[str]:
    """Names of the What's on picks from the episodes of the last `days` days."""
    picks = []
    for back in range(1, days + 1):
        if md := _briefing_md(day - timedelta(days=back)):
            section = md.split("\n## What's on in Amsterdam", 1)[1:]
            picks += _PICK.findall(section[0]) if section else []
    return list(dict.fromkeys(picks))


def _norm(url: str) -> str:
    u = urlsplit(url)
    return f"{u.netloc.removeprefix('www.')}{u.path.rstrip('/')}"


def drop_covered(articles: list[Article], prior: list[PriorStory]) -> list[Article]:
    """Articles an earlier episode already used carry no news; any real update has a newer article."""
    used = {_norm(u) for p in prior for u in p.urls}
    return [a for a in articles if _norm(a.url) not in used]


def match(headline: str, prior: list[PriorStory]) -> PriorStory | None:
    by_head = {p.headline: p for p in prior}
    close = difflib.get_close_matches(headline, list(by_head), n=1, cutoff=0.6)
    return by_head.get(headline) or (by_head[close[0]] if close else None)


def render(p: PriorStory) -> str:
    return "\n".join([f"Already reported on {p.date}: {p.summary}", *(f"Also established: {c}" for c in p.checked)])
