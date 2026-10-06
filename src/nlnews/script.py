"""Turn the briefing into a two-host episode script."""

from datetime import date

from nlnews.config import HOSTS, SHOW_TITLE, load_prompt
from nlnews.llm import ask
from nlnews.models import AirtimePlan, Briefing, EpisodeScript

# Words per story, whatever its kind. The cold open and sign-off take ~120 of the episode's target.
AIRTIME_FLOOR, AIRTIME_CEILING, OPEN_AND_CLOSE = 90, 340, 120


def plan_airtime(briefing: Briefing, words: tuple[int, int] = (1800, 2200)) -> Briefing:
    """Split the episode's story words across the stories by how much each one has to say."""
    pool = sum(words) // 2 - OPEN_AND_CLOSE
    system = load_prompt("airtime").format(pool=pool, floor=AIRTIME_FLOOR, ceiling=AIRTIME_CEILING)
    plan = ask(system, briefing.model_dump_json(indent=2, exclude={"agenda"}), AirtimePlan, effort="low")
    if len(plan.stories) != len(briefing.stories):
        raise RuntimeError(f"Airtime plan has {len(plan.stories)} entries for {len(briefing.stories)} stories")
    budgets = _fit(pool, [a.words for a in plan.stories])
    stories = [s.model_copy(update={"airtime": w, "airtime_reason": a.reason})
               for s, a, w in zip(briefing.stories, plan.stories, budgets)]
    for s in stories:
        print(f"  airtime {s.airtime:>3}  {s.headline[:60]}  ({s.airtime_reason})")
    return briefing.model_copy(update={"stories": stories})


def _fit(pool: int, asked: list[int]) -> list[int]:
    """Scale the asked-for counts to add up to about `pool`, within the floor and ceiling, in steps of 10."""
    fit = lambda k: [min(max(w * k, AIRTIME_FLOOR), AIRTIME_CEILING) for w in asked]
    lo, hi = 0.0, 10.0
    for _ in range(40):  # the clamped total grows with k, so bisect for the scale that hits the pool
        k = (lo + hi) / 2
        lo, hi = (k, hi) if sum(fit(k)) < pool else (lo, k)
    return [int(round(w / 10) * 10) for w in fit((lo + hi) / 2)]


def write_script(briefing: Briefing, words: tuple[int, int] = (1800, 2200)) -> EpisodeScript:
    if not all(s.airtime for s in briefing.stories):
        briefing = plan_airtime(briefing, words)
    host_a, host_b = HOSTS
    system = load_prompt("script").format(
        show=SHOW_TITLE, host_a=host_a, host_b=host_b, words_min=words[0], words_max=words[1],
        today=date.fromisoformat(briefing.date).strftime("%A %-d %B %Y"),
    )
    if briefing.agenda:
        system += load_prompt("agenda_segment")
    script = ask(system, briefing.model_dump_json(indent=2), EpisodeScript, effort="high", max_tokens=32000)
    unknown = {l.speaker for s in script.segments for l in s.lines} - set(HOSTS)
    if unknown:
        raise RuntimeError(f"Script used unknown speakers: {unknown}")
    _report_lengths(briefing, script)
    return _fix_handoffs(script)


def _report_lengths(briefing: Briefing, script: EpisodeScript) -> None:
    """Print each story's words against its airtime, assuming one segment per story after the cold open."""
    segs = script.segments[1:1 + len(briefing.stories)]
    print("  story words vs airtime: " + ", ".join(
        f"{sum(len(l.text.split()) for l in seg.lines)}/{s.airtime}" for s, seg in zip(briefing.stories, segs)))


def same_speaker_breaks(script: EpisodeScript) -> list[int]:
    """Indexes of segments whose first speaker also spoke the previous segment's last line."""
    segs = script.segments
    return [i for i in range(1, len(segs)) if segs[i - 1].lines[-1].speaker == segs[i].lines[0].speaker]


def _fix_handoffs(script: EpisodeScript) -> EpisodeScript:
    """Ask for one rewrite of the story breaks where a host speaks twice in a row; Gemini TTS tends to
    swap the voices or drop a line there. Keeps the original if the rewrite fails or changes too much."""
    breaks = same_speaker_breaks(script)
    if not breaks:
        return script
    print(f"  {len(breaks)} story breaks without a host change; rewriting them")
    listed = "\n".join(f"- {i}: {script.segments[i].title}" for i in breaks)
    try:
        fixed = ask(load_prompt("script_handoffs").format(breaks=listed), script.model_dump_json(indent=2),
                    EpisodeScript, effort="low", max_tokens=32000, fallback=False)
    except Exception as exc:  # the unfixed script still voices fine most of the time
        print(f"  handoff rewrite failed ({exc}); keeping the original script")
        return script
    if (len(fixed.segments) != len(script.segments)
            or {l.speaker for s in fixed.segments for l in s.lines} - set(HOSTS)
            or not 0.95 <= word_count(fixed) / word_count(script) <= 1.1):
        print("  handoff rewrite changed the script too much; keeping the original")
        return script
    left = same_speaker_breaks(fixed)
    if left:
        print(f"  {len(left)} story breaks still without a host change: {left}")
    return fixed


def word_count(script: EpisodeScript) -> int:
    return sum(len(l.text.split()) for s in script.segments for l in s.lines)


def render_text(script: EpisodeScript) -> str:
    out = [f"# {script.episode_title}", "", script.description, ""]
    for seg in script.segments:
        out += [f"## {seg.title}", ""]
        out += [f"**{l.speaker}:** {l.text}" for l in seg.lines]
        out.append("")
    return "\n".join(out)
