"""Turn the briefing into a two-host episode script."""

from nlnews.config import HOSTS, SHOW_TITLE, load_prompt
from nlnews.llm import ask
from nlnews.models import Briefing, EpisodeScript


def write_script(briefing: Briefing, words: tuple[int, int] = (1800, 2200)) -> EpisodeScript:
    host_a, host_b = HOSTS
    system = load_prompt("script").format(
        show=SHOW_TITLE, host_a=host_a, host_b=host_b, words_min=words[0], words_max=words[1],
    )
    script = ask(system, briefing.model_dump_json(indent=2), EpisodeScript, effort="high", max_tokens=32000)
    unknown = {l.speaker for s in script.segments for l in s.lines} - set(HOSTS)
    if unknown:
        raise RuntimeError(f"Script used unknown speakers: {unknown}")
    return script


def word_count(script: EpisodeScript) -> int:
    return sum(len(l.text.split()) for s in script.segments for l in s.lines)


def render_text(script: EpisodeScript) -> str:
    out = [f"# {script.episode_title}", "", script.description, ""]
    for seg in script.segments:
        out += [f"## {seg.title}", ""]
        out += [f"**{l.speaker}:** {l.text}" for l in seg.lines]
        out.append("")
    return "\n".join(out)
