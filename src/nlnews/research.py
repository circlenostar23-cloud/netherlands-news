"""Fact-check pass: look up each story's open questions on the web before the script is written.

The briefing writer only sees the morning's articles, which can leave gaps (a paywalled
source that only gave us its RSS summary) or disagree with each other. Stories with open
questions get one web-enabled model call each, in parallel. A story whose lookup fails or
times out is kept as written, so this step can delay the episode by a few minutes but never stop it.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import date

from nlnews.config import load_prompt
from nlnews.llm import ask
from nlnews.models import Briefing, ResearchedStory, Story


def _research(day: date, story: Story) -> Story:
    system = load_prompt("research").format(date=day.strftime("%A %d %B %Y"))
    try:
        r = ask(system, story.model_dump_json(indent=2, exclude={"findings"}), ResearchedStory,
                effort="medium", web=True, timeout=240, fallback=False)
    except Exception as exc:  # a failed lookup shouldn't cost the episode
        print(f"  research failed for '{story.headline}' (…{str(exc)[-200:]}); keeping it as written")
        return story
    answered = [f for f in r.findings if f.answer and f.sources]
    return story.model_copy(update={
        "summary": r.summary,
        "context": r.context,
        "findings": r.findings,
        "open_questions": [f.question for f in r.findings if f not in answered],
        "urls": story.urls + [u for f in answered for u in f.sources if u not in story.urls],
    })


def fill_gaps(day: date, briefing: Briefing) -> Briefing:
    todo = [s for s in briefing.stories if s.open_questions]
    if not todo:
        print("  research: no open questions")
        return briefing
    print(f"  research: {sum(len(s.open_questions) for s in todo)} open questions across {len(todo)} stories")
    # All stories at once, so the whole step takes at most one call's timeout (~4 min)
    with ThreadPoolExecutor(max_workers=len(todo)) as pool:
        stories = list(pool.map(lambda s: _research(day, s) if s.open_questions else s, briefing.stories))
    for s in stories:
        for f in s.findings:
            print(f"    {'✓' if f.answer and f.sources else '?'} {f.question}")
    return briefing.model_copy(update={"stories": stories})
