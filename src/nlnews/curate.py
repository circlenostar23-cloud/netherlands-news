"""Two-pass curation: pick stories from headlines, then write the briefing from full text."""

from datetime import date

from nlnews.config import LIGHT_STORIES, load_prompt
from nlnews.fetch import fetch_full_text
from nlnews.llm import ask
from nlnews.models import Article, Briefing, StorySelection


def select_stories(groups: list[list[Article]], n_min: int = 6, n_max: int = 9,
                   light: tuple[int, int] = LIGHT_STORIES) -> StorySelection:
    lines = []
    for i, group in enumerate(groups):
        lines.append(f"## Cluster {i}")
        for a in group:
            lines.append(f"- [{a.id}] ({a.source}, {a.section}, {a.lang}) {a.title} — {a.summary[:200]}")
    system = load_prompt("select").format(n_min=n_min, n_max=n_max, light_min=light[0], light_max=light[1])
    selection = ask(system, "\n".join(lines), StorySelection, effort="medium")
    n_light = sum(s.kind == "light" for s in selection.stories)
    if not light[0] <= n_light <= light[1]:
        print(f"  warning: {n_light} light stories picked; wanted {light[0]}-{light[1]}")
    return selection


def write_briefing(day: date, selection: StorySelection, articles: list[Article]) -> Briefing:
    by_id = {a.id: a for a in articles}
    wanted = [by_id[i] for s in selection.stories for i in s.article_ids if i in by_id]
    full = {a.id: a for a in fetch_full_text(wanted)}

    parts = [f"Date: {day.strftime('%A %d %B %Y')}"]
    for n, story in enumerate(selection.stories, 1):
        parts.append(f"\n# Story {n}: {story.working_title} (section: {story.section}, kind: {story.kind})")
        for aid in story.article_ids:
            if a := full.get(aid):
                parts.append(f"\n--- {a.source} ({a.lang}) {a.url}\n{a.title}\n\n{a.full_text}")
    briefing = ask(load_prompt("write"), "\n".join(parts), Briefing, effort="medium", max_tokens=32000)
    if len(briefing.stories) < len(selection.stories):
        print(f"  warning: briefing covers {len(briefing.stories)} of {len(selection.stories)} selected stories")
    return briefing


def render_markdown(b: Briefing) -> str:
    """The NotebookLM-ready source document."""
    out = [f"# Netherlands news briefing — {b.date}", "", f"**Today:** {b.top_line}", ""]
    for i, s in enumerate(b.stories, 1):
        out += [f"## {i}. {s.headline}", f"*Section: {s.section} · Sources: {', '.join(s.sources)}*", "",
                s.summary, "", f"**Context for newcomers:** {s.context}", ""]
        if s.key_terms:
            out += ["**Key terms:** " + "; ".join(s.key_terms), ""]
        out += [f"- {u}" for u in s.urls] + [""]
    if b.agenda:
        out += [f"## What's on in Amsterdam ({b.agenda.window})", ""]
        for e in b.agenda.events:
            details = " · ".join(x for x in (e.when, e.where, e.price, e.note) if x)
            out += [f"- **{e.name}** ({details}): {e.blurb} *[{e.source}]*"]
        out.append("")
    return "\n".join(out)
