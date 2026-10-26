"""Podcast feed publishing.

Each episode MP3 is stored as a GitHub Release asset (tag `ep-YYYY-MM-DD`). The feed is
rebuilt from the release list every run, so there's no state to keep in the repo; the
workflow then deploys `site/` to GitHub Pages.

The feed's enclosures point at copies of the MP3s on Pages, not at the release assets:
release downloads redirect to signed URLs that expire within minutes, and Apple Podcasts
caches the redirect target, so playback later fails with "can't play on this device".
Safari's player can't play the release assets either (they're served as
application/octet-stream), so dnlevitz.com plays the same copies. They sit at the public
`episodes/` path, for the last PAGES_EPISODES daily episodes; only the feed itself is under
the secret path.
"""

import html
import json
import os
import re
import subprocess
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from nlnews.config import SHOW_TITLE, SITE_DIR, require_env

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PODCAST = "https://podcastindex.org/namespace/1.0"
META = re.compile(r"<!-- nlnews (\{.*?\}) -->")
ET.register_namespace("itunes", ITUNES)
ET.register_namespace("podcast", PODCAST)
DAILY = re.compile(r"^ep-\d{4}-\d{2}-\d{2}$")  # not side runs such as ep-2026-09-29-ms
PAGES_EPISODES = 120  # daily episodes kept on Pages: ~6.5 MB each, under Pages' 1 GB limit


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def _repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or json.loads(_gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]


def upload_episode(tag: str, title: str, description: str, mp3: Path, duration: int, briefing_md: Path,
                   transcript: Path | None = None, calendar: Path | None = None) -> None:
    """Create (or update) the episode's release. Watching the repo's releases on GitHub
    turns this into an email notification with the MP3 and briefing attached as downloads."""
    meta = json.dumps({"duration": duration})
    notes = f"{description}\n\n<!-- nlnews {meta} -->"
    assets = [str(mp3), f"{briefing_md}#Briefing (NotebookLM source)"]
    if transcript and transcript.exists():
        assets.append(f"{transcript}#Transcript")
    if calendar and calendar.exists():  # the next episode reads it to tell openings from running shows
        assets.append(f"{calendar}#What's on: runs seen in the calendar")
    try:
        _gh("release", "view", tag, "--repo", _repo())
        _gh("release", "upload", tag, *assets, "--clobber", "--repo", _repo())
        _gh("release", "edit", tag, "--title", title, "--notes", notes, "--repo", _repo())
    except subprocess.CalledProcessError:
        _gh("release", "create", tag, *assets, "--title", title, "--notes", notes, "--repo", _repo())


def _html(notes: str) -> str:
    """The release notes' bit of Markdown as HTML for podcast apps: a paragraph per line,
    **bold** and [links](url)."""
    def inline(text: str) -> str:
        text = html.escape(text, quote=False)
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
                      lambda m: f'<a href="{m[2].replace('"', '%22')}">{m[1]}</a>', text)  # already escaped
    return "".join(f"<p>{inline(re.sub(r'^- ', '', l.strip()))}</p>" for l in notes.splitlines() if l.strip())


def feed_url() -> str | None:
    base, secret = os.environ.get("SITE_BASE_URL"), os.environ.get("FEED_SECRET_PATH")
    return f"{base.rstrip('/')}/{secret}/feed.xml" if base and secret else None


def build_feed(max_episodes: int = 30) -> Path:
    env = require_env("SITE_BASE_URL", "FEED_SECRET_PATH")
    base, secret = env["SITE_BASE_URL"].rstrip("/"), env["FEED_SECRET_PATH"]
    episodes_dir = SITE_DIR / "episodes"
    episodes_dir.mkdir(parents=True, exist_ok=True)
    releases = []
    for page in range(1, 100):
        batch = json.loads(_gh("api", f"repos/{_repo()}/releases?per_page=100&page={page}"))
        releases += batch
        if len(batch) < 100 or sum(bool(DAILY.match(r["tag_name"])) for r in releases) >= PAGES_EPISODES:
            break

    def copy(rel: dict, ext: str) -> Path | None:
        """The release's MP3 or transcript, copied to Pages; every deploy replaces the whole site."""
        match = (lambda n: n.endswith(".mp3")) if ext == ".mp3" else (lambda n: n == "transcript.vtt")
        if not (asset := next((a for a in rel["assets"] if match(a["name"])), None)):
            return None
        local = episodes_dir / f"{rel['tag_name']}{ext}"
        if not local.exists() or local.stat().st_size != asset["size"]:
            _gh("release", "download", rel["tag_name"], "--pattern", asset["name"],
                "--output", str(local), "--clobber", "--repo", _repo())
        return local

    for rel in [r for r in releases if DAILY.match(r["tag_name"])][:PAGES_EPISODES]:  # what dnlevitz.com plays
        copy(rel, ".mp3")
        copy(rel, ".vtt")

    rss = ET.Element("rss", {"version": "2.0"})
    ch = ET.SubElement(rss, "channel")
    for tag, text in [
        ("title", SHOW_TITLE),
        ("link", base),
        ("language", "en"),
        ("description", "A daily English-language briefing on news from the Netherlands, for internationals and newcomers."),
        (f"{{{ITUNES}}}author", SHOW_TITLE),
        (f"{{{ITUNES}}}explicit", "false"),
        (f"{{{ITUNES}}}block", "yes"),  # keep it out of the Apple Podcasts directory
    ]:
        ET.SubElement(ch, tag).text = text
    ET.SubElement(ch, f"{{{ITUNES}}}image", {"href": f"{base}/cover.png"})
    ET.SubElement(ch, f"{{{ITUNES}}}category", {"text": "News"})

    for rel in releases[:max_episodes]:
        if not rel["tag_name"].startswith("ep-") or not (mp3 := copy(rel, ".mp3")):
            continue
        m = META.search(rel.get("body") or "")
        meta = json.loads(m.group(1)) if m else {}
        desc = META.sub("", rel.get("body") or "").strip()
        item = ET.SubElement(ch, "item")
        ET.SubElement(item, "title").text = rel["name"]
        ET.SubElement(item, "description").text = _html(desc)
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = rel["tag_name"]
        published = datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00"))
        ET.SubElement(item, "pubDate").text = format_datetime(published)
        ET.SubElement(item, "enclosure", {"url": f"{base}/episodes/{mp3.name}",
                                          "length": str(mp3.stat().st_size), "type": "audio/mpeg"})
        if "duration" in meta:
            ET.SubElement(item, f"{{{ITUNES}}}duration").text = str(meta["duration"])
        if local := copy(rel, ".vtt"):
            ET.SubElement(item, f"{{{PODCAST}}}transcript", {"url": f"{base}/episodes/{local.name}",
                                                             "type": "text/vtt", "language": "en"})

    out = SITE_DIR / secret / "feed.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(rss).write(out, encoding="utf-8", xml_declaration=True)
    return out
