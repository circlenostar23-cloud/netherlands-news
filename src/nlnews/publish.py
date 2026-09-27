"""Podcast feed publishing.

Each episode MP3 is stored as a GitHub Release asset (tag `ep-YYYY-MM-DD`). The feed is
rebuilt from the release list every run, so there's no state to keep in the repo; the
workflow then deploys `site/` to GitHub Pages.
"""

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
META = re.compile(r"<!-- nlnews (\{.*?\}) -->")
ET.register_namespace("itunes", ITUNES)


def _gh(*args: str) -> str:
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def _repo() -> str:
    return os.environ.get("GITHUB_REPOSITORY") or json.loads(_gh("repo", "view", "--json", "nameWithOwner"))["nameWithOwner"]


def upload_episode(tag: str, title: str, description: str, mp3: Path, duration: int, briefing_md: Path) -> None:
    """Create (or update) the episode's release. Watching the repo's releases on GitHub
    turns this into an email notification with the MP3 and briefing attached as downloads."""
    meta = json.dumps({"duration": duration})
    notes = f"{description}\n\n<!-- nlnews {meta} -->"
    assets = [str(mp3), f"{briefing_md}#Briefing (NotebookLM source)"]
    try:
        _gh("release", "view", tag, "--repo", _repo())
        _gh("release", "upload", tag, *assets, "--clobber", "--repo", _repo())
        _gh("release", "edit", tag, "--title", title, "--notes", notes, "--repo", _repo())
    except subprocess.CalledProcessError:
        _gh("release", "create", tag, *assets, "--title", title, "--notes", notes, "--repo", _repo())


def feed_url() -> str | None:
    base, secret = os.environ.get("SITE_BASE_URL"), os.environ.get("FEED_SECRET_PATH")
    return f"{base.rstrip('/')}/{secret}/feed.xml" if base and secret else None


def build_feed(max_episodes: int = 30) -> Path:
    env = require_env("SITE_BASE_URL", "FEED_SECRET_PATH")
    base = env["SITE_BASE_URL"].rstrip("/")
    releases = json.loads(_gh("api", f"repos/{_repo()}/releases?per_page={max_episodes}"))

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

    for rel in releases:
        if not rel["tag_name"].startswith("ep-"):
            continue
        asset = next((a for a in rel["assets"] if a["name"].endswith(".mp3")), None)
        if not asset:
            continue
        m = META.search(rel.get("body") or "")
        meta = json.loads(m.group(1)) if m else {}
        desc = META.sub("", rel.get("body") or "").strip()
        item = ET.SubElement(ch, "item")
        ET.SubElement(item, "title").text = rel["name"]
        ET.SubElement(item, "description").text = desc
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = rel["tag_name"]
        published = datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00"))
        ET.SubElement(item, "pubDate").text = format_datetime(published)
        ET.SubElement(item, "enclosure", {"url": asset["browser_download_url"],
                                          "length": str(asset["size"]), "type": "audio/mpeg"})
        if "duration" in meta:
            ET.SubElement(item, f"{{{ITUNES}}}duration").text = str(meta["duration"])

    out = SITE_DIR / env["FEED_SECRET_PATH"] / "feed.xml"
    out.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(rss).write(out, encoding="utf-8", xml_declaration=True)
    return out
