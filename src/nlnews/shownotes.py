"""The episode's show notes: the script's description, chapter timestamps, links to read more
on each story, and runners-up that didn't fit. Written in Markdown for the GitHub release;
publish.py turns it into HTML for the feed."""

from nlnews.chapters import clock
from nlnews.models import Article, Briefing, Chapter, EpisodeScript, StorySelection

MAX_LINKS = 2  # per story


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


def _story_titles(script: EpisodeScript, briefing: Briefing) -> list[str]:
    """The segment title for each briefing story, so links match the chapter names. Falls back
    to the briefing's headlines when the script's segments don't line up with its stories."""
    n = len(briefing.stories)
    extra = 2 + bool(briefing.agenda)  # cold open, sign-off, What's on
    if len(script.segments) == n + extra:
        return [s.title for s in script.segments[1:1 + n]]
    return [s.headline for s in briefing.stories]


def build(description: str, script: EpisodeScript, briefing: Briefing, selection: StorySelection,
          articles: list[Article], chapters: list[Chapter]) -> str:
    by_url = {a.url: a for a in articles}
    by_id = {a.id: a for a in articles}
    out = [description]
    if chapters:
        out += ["", "**Chapters**", *(f"- {clock(c.start)} {c.title}" for c in chapters)]
    more = [(t, _links(s.urls, by_url)) for t, s in zip(_story_titles(script, briefing), briefing.stories)]
    if more := [f"- {t}: {', '.join(links)}" for t, links in more if links]:
        out += ["", "**Read more**", *more]
    also = [(r.working_title, _links([by_id[i].url for i in r.article_ids if i in by_id], by_url))
            for r in selection.runners_up]
    if also := [f"- {t}: {', '.join(links)}" for t, links in also if links]:
        out += ["", "**Also in the news**", *also]
    return "\n".join(out)
