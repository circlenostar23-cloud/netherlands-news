"""Turn the briefing into a two-host episode script."""

from datetime import date

from nlnews.config import HOSTS, SHOW_TITLE, load_prompt
from nlnews.llm import ask
from nlnews.models import Briefing, EpisodeScript


def write_script(briefing: Briefing, words: tuple[int, int] = (1800, 2200)) -> EpisodeScript:
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
    return _fix_handoffs(script)


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
