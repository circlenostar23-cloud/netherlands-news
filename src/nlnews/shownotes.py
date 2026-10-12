"""The episode's show notes: the script's description, then links to read more on each story, What's on in Amsterdam with links (plus shortlisted events that weren't voiced),
and runners-up that didn't fit, each with a one-line summary. Written in Markdown for the GitHub release;
publish.py turns it into HTML for the feed. The chapters aren't listed: they're in the MP3,
and Apple Podcasts left timestamps in the description as plain text for this feed."""

from pydantic import BaseModel

from nlnews.config import load_prompt
from nlnews.llm import ask
from nlnews.models import Article, Briefing, EpisodeScript, StorySelection

MAX_LINKS = 2  # per story
DIVIDER = "— — —"  # before each link section; podcast apps drop <hr>


class NoteLine(BaseModel):
    id: str
    line: str


class NoteLines(BaseModel):
    lines: list[NoteLine]


def _summaries(items: dict[str, tuple[str, str]]) -> dict[str, str]:
    """One sentence per item, from (title, text), in a single call. Without them the notes
    still list every title and link."""
    if not items:
        return {}
    body = "\n\n".join(f"[{k}] {title}\n{text.strip()[:800]}" for k, (title, text) in items.items())
    try:
        result = ask(load_prompt("shownotes"), body, NoteLines, effort="low", max_tokens=4000)
    except Exception as exc:
        print(f"  show-note summaries failed ({exc}); listing titles only")
        return {}
    return {l.id: l.line.strip() for l in result.lines if l.id in items and l.line.strip()}


def _item(title: str, summary: str, links: list[str]) -> str:
    return f"- {title}" + (f": {summary}" if summary else "") + (f" ({', '.join(links)})" if links else "")


def _links(urls: list[str], by_url: dict[str, Article]) -> list[str]:
    """The story's own articles, not research sources: an English-language one first if there
    is one, then one more from a different outlet."""
    found = [by_url[u] for u in dict.fromkeys(urls) if u in by_url]
    found.sort(key=lambda a: a.lang != "en")  # stable, so each language keeps the briefing's order
    picked, outlets = [], set()
    for a in found:
        if a.source not in outlets and len(picked) < MAX_LINKS:
            picked.append(a)
            outlets.add(a.source)
    return [f"[{a.source}]({a.url})" for a in picked]


def _event(name: str, url: str, details: str, summary: str) -> str:
    name = name.replace("[", "(").replace("]", ")")  # would break the link
    title = f"[{name}]({url})" if url else name
    return f"- {title}" + (f": {summary}" if summary else "") + (f" ({details})" if details else "")


def _story_titles(script: EpisodeScript, briefing: Briefing) -> list[str]:
    """The segment title for each briefing story, so links match the chapter names. Falls back
    to the briefing's headlines when the script's segments don't line up with its stories."""
    n = len(briefing.stories)
    extra = 2 + bool(briefing.agenda)  # cold open, sign-off, What's on
    if len(script.segments) == n + extra:
        return [s.title for s in script.segments[1:1 + n]]
    return [s.headline for s in briefing.stories]


def build(description: str, script: EpisodeScript, briefing: Briefing, selection: StorySelection,
          articles: list[Article]) -> str:
    by_url = {a.url: a for a in articles}
    by_id = {a.id: a for a in articles}
    stories = [(f"s{i}", t, s.summary, _links(s.urls, by_url))
               for i, (t, s) in enumerate(zip(_story_titles(script, briefing), briefing.stories))]
    stories = [x for x in stories if x[3]]
    runners = []
    for i, r in enumerate(selection.runners_up):
        found = [by_id[a] for a in r.article_ids if a in by_id]
        if links := _links([a.url for a in found], by_url):
            runners.append((f"r{i}", r.working_title, "\n".join(f"{a.title}. {a.summary}" for a in found[:2]), links))
    events, more = [], []
    if briefing.agenda:
        events = [(f"e{i}", e.name, e.url, ", ".join(x for x in (e.when, e.where) if x), e.blurb)
                  for i, e in enumerate(briefing.agenda.events)]
        # a pick the agenda step didn't recognise among the shortlist can reappear here
        picked = {e.url for e in briefing.agenda.events if e.url} | {e.name.lower() for e in briefing.agenda.events}
        more = [(f"m{i}", e.name, e.url, e.details, e.about) for i, e in enumerate(briefing.agenda.more)
                if e.url not in picked and not any(e.name.lower() in p for p in picked)]

    summary = _summaries({k: (t, text) for k, t, text, _ in stories + runners}
                         | {k: (n, text) for k, n, _, _, text in events + more})
    sections = []
    if stories:
        sections.append(["**READ MORE**", *(_item(t, summary.get(k, ""), l) for k, t, _, l in stories)])
    if events:
        sections.append([f"**WHAT'S ON IN AMSTERDAM** ({briefing.agenda.window})",
                         *(_event(n, u, d, summary.get(k, "")) for k, n, u, d, _ in events)])
    if more:
        sections.append(["**MORE ON IN AMSTERDAM**", *(_event(n, u, d, summary.get(k, "")) for k, n, u, d, _ in more)])
    if runners:
        sections.append(["**ALSO IN THE NEWS**", *(_item(t, summary.get(k, ""), l) for k, t, _, l in runners)])
    return "\n".join([description, *(line for sec in sections for line in ["", DIVIDER, "", *sec])])
