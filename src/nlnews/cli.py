"""`python -m nlnews run` — the whole daily pipeline, with per-stage caching in data/<date>/."""

import argparse
import json
import logging
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, TypeAdapter

from nlnews.config import TZ, day_dir
from nlnews.models import Article, Briefing, EpisodeScript, PriorStory, StorySelection

STAGES = ["fetch", "briefing", "script", "audio", "all"]


def _cached(path: Path, fresh: bool, build, model):
    """Load a stage's output from disk, or build and save it."""
    if path.exists() and not fresh:
        print(f"• {path.name} (cached)")
        return TypeAdapter(model).validate_json(path.read_text())
    print(f"• building {path.name}")
    result = build()
    data = result.model_dump_json(indent=2) if isinstance(result, BaseModel) else \
        TypeAdapter(model).dump_json(result, indent=2).decode()
    path.write_text(data)
    return result


def run(args) -> None:
    from nlnews import agenda as agendamod, cluster, curate, fetch, previous, research, script as scriptmod

    day = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date()
    d = day_dir(day)
    print(f"Episode {day} → {d}")

    articles = _cached(d / "articles.json", args.fresh, lambda: fetch.fetch_all(args.hours), list[Article])
    print(f"  {len(articles)} articles")
    if args.stop_after == "fetch":
        return

    # What the last couple of episodes covered, so repeats come back only as real updates
    prior = _cached(d / "previous.json", args.fresh, lambda: previous.load(day), list[PriorStory])
    fresh_articles = previous.drop_covered(articles, prior)
    print(f"  {len(prior)} stories in recent episodes; {len(articles) - len(fresh_articles)} articles already used")

    selection = _cached(d / "selection.json", args.fresh,
                        lambda: curate.select_stories(cluster.cluster(fresh_articles), prior), StorySelection)
    for s in selection.stories:
        print(f"  - [{s.kind}/{s.section}] {s.working_title}" + (" (follow-up)" if s.follow_up_of else ""))
    draft = lambda: _cached(d / "briefing.draft.json", args.fresh,
                            lambda: curate.write_briefing(day, selection, articles, prior), Briefing)
    briefing = _cached(d / "briefing.json", args.fresh, lambda: research.fill_gaps(day, draft()), Briefing)
    if not briefing.agenda:
        try:
            briefing.agenda = agendamod.build(day, previous.agenda_picks(day))
        except Exception as exc:  # the What's on segment is optional; don't lose the episode over it
            print(f"  agenda failed ({exc}); skipping What's on")
        (d / "briefing.json").write_text(briefing.model_dump_json(indent=2))
    briefing_md = d / "briefing.md"
    briefing_md.write_text(curate.render_markdown(briefing))
    print(f"  NotebookLM source: {briefing_md}")
    if args.stop_after == "briefing":
        return

    script = _cached(d / "script.json", args.fresh, lambda: scriptmod.write_script(briefing), EpisodeScript)
    (d / "script.md").write_text(scriptmod.render_text(script))
    print(f"  script: {scriptmod.word_count(script)} words, {len(script.segments)} segments")
    if args.stop_after == "script":
        return

    from nlnews import tts
    title = f"{day.strftime('%a %d %b')}: {script.episode_title}"
    mp3, voices_file = d / "episode.mp3", d / "voices.txt"
    if args.fresh or not mp3.exists():
        _, voices = tts.synthesize_episode(script, d, title)
        voices_file.write_text(voices)
    voices = voices_file.read_text().strip() if voices_file.exists() else "gemini"
    duration = tts.duration_seconds(mp3)
    print(f"  audio: {mp3} ({duration // 60}m{duration % 60:02d}s, {mp3.stat().st_size / 1e6:.1f} MB, {voices} voices)")
    description = script.description
    if voices in ("fallback", "mixed"):
        part = "Partly voiced" if voices == "mixed" else "Voiced"
        description += f"\n\n({part} with backup Microsoft voices because Gemini's voices were unavailable.)"
    if args.stop_after == "audio":
        return

    from nlnews import deliver, publish
    feed = None
    if not args.no_publish:
        publish.upload_episode(f"ep-{day.isoformat()}", title, description, mp3, duration, briefing_md)
        print(f"  feed written: {publish.build_feed()}")
        feed = publish.feed_url()
    if args.no_email or not deliver.configured():
        print("  email skipped (not configured)")
    else:
        deliver.send_email(briefing, briefing_md, mp3, feed)
        print("  email sent")


def feed(_args) -> None:
    from nlnews import publish
    print(publish.build_feed())


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    for noisy in ("trafilatura", "urllib3", "courlan", "htmldate"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    p = argparse.ArgumentParser(prog="nlnews")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="Run the daily pipeline")
    r.add_argument("--date", help="Episode date (YYYY-MM-DD); defaults to today in Amsterdam")
    r.add_argument("--hours", type=int, default=26, help="How far back to fetch news")
    r.add_argument("--stop-after", choices=STAGES, default="all")
    r.add_argument("--fresh", action="store_true", help="Ignore cached stage outputs")
    r.add_argument("--no-publish", action="store_true", help="Skip GitHub release + feed")
    r.add_argument("--no-email", action="store_true", help="Skip email delivery")
    r.set_defaults(func=run)
    f = sub.add_parser("feed", help="Rebuild the podcast feed from GitHub releases")
    f.set_defaults(func=feed)

    args = p.parse_args()
    args.func(args)
