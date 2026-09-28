"""'What's on in Amsterdam': a few event picks for the end of each episode.

Most days cover just that day, since the listener hears the episode in the morning. Thursday
is the weekend edition (Thursday to Sunday), which also draws on two curated weekend guides.
Candidates come from I amsterdam's cultural calendar, whose events are all marked
"language no problem". Its pages embed the listing as JSON, so no scraping of markup is needed.
"""

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import feedparser
import httpx
import trafilatura

from nlnews.config import TZ, load_prompt
from nlnews.fetch import USER_AGENT
from nlnews.llm import ask
from nlnews.models import Agenda, Shortlist

log = logging.getLogger(__name__)
IAMSTERDAM = "https://www.iamsterdam.com/en/"
WEEKEND_GUIDE = IAMSTERDAM + "whats-on/weekend-guide"
YLBB_FEED = "https://www.yourlittleblackbook.me/feed/"
WEEKEND_EDITION = 3  # Thursday
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/128 Safari/537.36"}
_RSC = re.compile(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', re.S)


def window(day: date) -> list[date]:
    if day.weekday() == WEEKEND_EDITION:
        return [day + timedelta(days=i) for i in range(4)]
    return [day]


def _get(url: str) -> str:
    return httpx.get(url, headers=HEADERS, timeout=30, follow_redirects=True).text


def _calendar_page(day: date, page: int) -> list[dict]:
    """One page of the calendar for a day: events first, then venue listings."""
    html = _get(f"{IAMSTERDAM}whats-on/calendar?date={day.isoformat()}&page={page}")
    payload = "".join(json.loads(f'"{chunk}"') for chunk in _RSC.findall(html))
    start = payload.find('"content":{"items":')
    if start < 0:
        return []
    return json.JSONDecoder().raw_decode(payload, start + len('"content":'))[0]["items"]


def _calendar_day(day: date, max_pages: int = 10) -> list[dict]:
    events = []
    for page in range(1, max_pages + 1):
        items = _calendar_page(day, page)
        events += [it for it in items if it.get("type") == "Event" and it.get("date")]
        if not items or items[-1].get("type") != "Event":  # past the events, into venues
            break
    return events


def _local(ts: str) -> date:
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ).date()


def _candidates(days: list[date]) -> dict[str, dict]:
    """Events worth considering: one-offs and short runs, plus long runs opening or closing
    in the window. Skips long-running exhibitions mid-run and Dutch-language events."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        per_day = list(pool.map(_calendar_day, days))
    out = {}
    for ev in (e for events in per_day for e in events):
        first, last = _local(ev["date"][0]), _local(ev["date"][-1])
        short = (last - first).days <= 7
        if "dutchlanguage" in ev.get("tags", []) or not (short or first in days or last in days):
            continue
        ev["note"] = "" if short else ("opening" if first in days else "final days")
        ev["first"], ev["last"] = first, last
        out[ev["id"][:8]] = ev
    return out


def _line(key: str, ev: dict) -> str:
    info = {h["id"]: h["label"] for h in ev.get("highlights", [])}
    dates = ev["first"].strftime("%a %d %b") + ("" if ev["first"] == ev["last"] else ev["last"].strftime(" – %a %d %b"))
    note = f" ({ev['note']})" if ev["note"] else ""
    return f"[{key}] {ev['title']}{note} | {dates} | {info.get('date', '')} | {info.get('location', '')} | {', '.join(ev.get('tags', []))}"


def _text(url: str, limit: int = 3000) -> str:
    try:
        return (trafilatura.extract(_get(url), include_comments=False) or "")[:limit]
    except httpx.HTTPError as exc:
        log.warning("Agenda fetch failed for %s: %s", url, exc)
        return ""


def _weekend_guides(day: date) -> list[tuple[str, str]]:
    guides = [("I amsterdam weekend guide", _text(WEEKEND_GUIDE, 12000))]
    feed = feedparser.parse(YLBB_FEED, agent=USER_AGENT)
    recent = (e for e in feed.entries if "weekendtips amsterdam" in e.title.lower()
              and e.get("published_parsed") and date(*e.published_parsed[:3]) >= day - timedelta(days=7))
    if entry := next(recent, None):
        guides.append((f"Your Little Black Book: {entry.title}", _text(entry.link, 25000)))
    return [(name, text) for name, text in guides if text]


def build(day: date) -> Agenda | None:
    days = window(day)
    weekend = len(days) > 1
    span = f"{days[0].strftime('%A %d %B %Y')}" + (f" to {days[-1].strftime('%A %d %B %Y')}" if weekend else "")
    try:
        candidates = _candidates(days)
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        log.warning("I amsterdam calendar failed: %s", exc)
        candidates = {}
    guides = _weekend_guides(day) if weekend else []
    print(f"  agenda: {len(candidates)} calendar candidates, {len(guides)} weekend guide(s)")

    sources = []
    if candidates:
        shortlist = ask(load_prompt("agenda_shortlist").format(n=10 if weekend else 8),
                        f"Window: {span}\n\n" + "\n".join(_line(k, ev) for k, ev in candidates.items()),
                        Shortlist, effort="low")
        picked = [k for k in shortlist.ids if k in candidates]
        page = lambda k: _text(IAMSTERDAM + candidates[k]["slug"]) if candidates[k].get("slug") else ""
        with ThreadPoolExecutor(max_workers=4) as pool:
            texts = list(pool.map(page, picked))
        sources += [(f"I amsterdam calendar: {_line(k, candidates[k])}", text or "(no description)")
                    for k, text in zip(picked, texts)]
    sources += guides
    if not sources:
        print("  agenda: nothing to pick from")
        return None

    n = (4, 5) if weekend else (2, 3)
    system = load_prompt("agenda").format(n_min=n[0], n_max=n[1])
    body = f"Window: {span}\n" + "\n".join(f"\n# {name}\n\n{text}" for name, text in sources)
    agenda = ask(system, body, Agenda, effort="medium")
    print(f"  agenda: {len(agenda.events)} picks for {agenda.window}")
    return agenda if agenda.events else None
