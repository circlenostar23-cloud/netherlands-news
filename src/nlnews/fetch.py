"""Pull recent items from every configured RSS feed."""

import hashlib
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import trafilatura

from nlnews.config import Source, load_sources
from nlnews.models import Article

log = logging.getLogger(__name__)
USER_AGENT = "Mozilla/5.0 (compatible; nlnews/0.1; personal podcast digest)"
_TAG = re.compile(r"<[^>]+>")


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", text or ""))).strip()


def _published(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    # NL Times uses "27 September 2026 - 11:25" (Amsterdam local time)
    raw = entry.get("published", "")
    try:
        from nlnews.config import TZ
        return datetime.strptime(raw, "%d %B %Y - %H:%M").replace(tzinfo=TZ)
    except ValueError:
        return None


def _fetch_feed(src: Source, hours: int) -> list[Article]:
    since = datetime.now(timezone.utc) - timedelta(hours=src.hours or hours)
    feed = feedparser.parse(src.url, agent=USER_AGENT)
    if feed.bozo and not feed.entries:
        log.warning("Feed failed: %s (%s)", src.url, feed.bozo_exception)
        return []
    out = []
    for e in feed.entries:
        pub = _published(e)
        if pub and pub < since:
            continue
        url = e.get("link", "")
        out.append(Article(
            id=hashlib.sha1(url.encode()).hexdigest()[:10],
            source=src.name,
            lang=src.lang,
            section=src.section,
            weight=src.weight,
            url=url,
            title=_clean(e.get("title", "")),
            summary=_clean(e.get("summary", ""))[:600],
            published=pub,
        ))
    log.info("%-12s %-45s %d items", src.name, src.url.split("//")[1][:45], len(out))
    return out


def fetch_all(hours: int = 26) -> list[Article]:
    """All feed items from the last `hours` (or a source's own override), deduplicated by URL."""
    sources = load_sources()
    with ThreadPoolExecutor(max_workers=8) as pool:
        batches = pool.map(lambda s: _fetch_feed(s, hours), sources)
    seen: dict[str, Article] = {}
    for batch in batches:
        for a in batch:
            # Same article often appears in several section feeds; keep the first (more specific ones win below)
            if a.id not in seen or seen[a.id].section == "national":
                seen[a.id] = a
    return list(seen.values())


def _extract(article: Article) -> Article:
    try:
        downloaded = trafilatura.fetch_url(article.url)
        text = trafilatura.extract(downloaded, include_comments=False) if downloaded else None
    except Exception as exc:  # network hiccups shouldn't kill the run
        log.warning("Extract failed for %s: %s", article.url, exc)
        text = None
    return article.model_copy(update={"full_text": text or article.summary})


def fetch_full_text(articles: list[Article]) -> list[Article]:
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(_extract, articles))
