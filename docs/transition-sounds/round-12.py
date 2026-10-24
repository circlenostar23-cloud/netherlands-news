"""Round 12: David's picks from round 11, and beds at both ends of the show.

Picks: the hard cues are minor hard-1, sus hard-2 and minor hard-3; light-4 joins the rotation; the
sign-off is anthem-b or free-b. The up-first bed plays under the cold open; the between bed plays under
the sign-off (or all of What's on and the sign-off) and lands the button.

Tighter landings. In round 11 the theme's swell started only after the hosts' last word (0.25 s of quiet
plus 0.65 s of swell), so the theme came in about a second late. The beds are built backwards from the
landing, so it can go anywhere: now the downbeat lands LAND_AFTER seconds after the last word as heard
(not the transcript's end time, which runs long), and the swell plays under the last word. The bed's
bars are also counted back from the landing, so its last bar is always D9sus, the V going home.

usage: RENDER=<path-to-render-binary> python round-12.py <out-dir> <episode.mp3> <transcript.vtt>
(ep-2026-10-24: its What's on and sign-off times are below)
"""
import importlib.util, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round11", Path(__file__).parent / "round-11.py")
r11 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r11)
r9, r10 = r11.r9, r11.r10

HARD = {"hard-1": r11.HARD["minor"]["hard-1"], "hard-2": r11.HARD["sus"]["hard-2"], "hard-3": r11.HARD["minor"]["hard-3"]}
BUTTONS = ("anthem-b", "free-b")
LAND_AFTER = 0.3  # seconds from the last word to the theme's downbeat
LEAD = 0.65  # a theme's swell, before its downbeat

# ep-2026-10-24, from its chapters and transcript: What's on's first words, the sign-off's, and the
# sign-off's last line's end
WHATS_ON, SIGN_OFF, END = 792.4, 848.94, 858.85


def bed(name, length):
    """r11.bed() with its bars counted back from the end, so the last bar is the loop's last chord."""
    b = r11.BEDS[name]
    n = int(np.ceil(length / (4 * b["beat"]))) + 1  # as r11.bed() counts them
    k = -n % len(b["bars"])
    r11.BEDS[f"{name} aligned"] = dict(b, bars=b["bars"][k:] + b["bars"][:k])
    return r11.bed(f"{name} aligned", length)


def last_word(voice, floor_db=-35):
    """Where the speech stops: the last 10 ms that comes within `floor_db` of the loudest."""
    m = np.abs(voice).max(axis=1)
    win = int(0.01 * SR)
    env = np.sqrt(np.mean(m[: len(m) // win * win].reshape(-1, win) ** 2, axis=1))
    return (np.nonzero(env > env.max() * 10 ** (floor_db / 20))[0][-1] + 1) * win / SR


def under(voice, bed_name, theme, bed_from=0.0, fade_in=1.5, after=None):
    """`voice` with a bed from `bed_from` seconds and `theme` landing LAND_AFTER after its last word, then
    `after` (the next story's first words) with the theme's ring-out under them as in the episode."""
    v = voice * 10 ** ((VOICE_DB - level(voice)) / 20)
    land = last_word(v) + LAND_AFTER
    music = bed(bed_name, land - bed_from)
    music = reverb(music, 0.12)[: len(music)]
    n = min(len(music), int(fade_in * SR))
    music[:n] *= np.linspace(0, 1, n)[:, None] ** 2
    music *= 10 ** ((VOICE_DB - level(music)) / 20)
    music = r11.duck(music, np.concatenate([v[int(bed_from * SR):], secs(1)])[: len(music)])
    events = [(0, v), (bed_from, music), (land - LEAD, theme)]
    if after is not None:
        a = after * 10 ** ((VOICE_DB - level(after)) / 20)
        events.append((land - LEAD + len(theme) / SR - 0.6, a))  # cues.UNDER_NEXT
    return place(events)


def piece(episode, start, end):
    return episode[int(start * SR): int(end * SR)]


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    episode = load(Path(sys.argv[2]))
    voice = r11.cold_open(Path(sys.argv[2]), Path(sys.argv[3]))
    intro = finish(r10.theme("intro"), 0.16, 6.5)
    first_story = piece(episode, 28.0, 36.0)  # its first line, after round 10's intro theme in the episode
    first_story[: int(0.05 * SR)] *= np.linspace(0, 1, int(0.05 * SR))[:, None]
    write(out / "intro - up-first bed under the cold open.mp3",
          np.concatenate([under(voice, "up-first", intro, after=fade(first_story, 1.0)), secs(0.5)]))

    for b in BUTTONS:
        theme = finish(r11.button(b), 0.16, 6.5)
        # the bed under the sign-off only: from the end of What's on's last line
        tail = piece(episode, SIGN_OFF - 6, END + 0.1)
        write(out / f"outro - between bed under the sign-off, button {b}.mp3",
              np.concatenate([under(tail, "between", theme, bed_from=6.0 - 0.3), secs(0.5)]))
        # the bed under What's on and the sign-off, after the section theme (already in the episode)
        whole = piece(episode, WHATS_ON - 5.2, END + 0.1)
        write(out / f"outro - between bed under What's on and the sign-off, button {b}.mp3",
              np.concatenate([under(whole, "between", theme, bed_from=5.2, fade_in=3.0), secs(0.5)]))
        print(f"outro {b}")

    # the picked story cues in rotation, with light-4
    def make(frag):
        if frag in HARD:
            return r11.story(*HARD[frag], "hard")
        if frag == "light-4":
            return r11.story(*r11.LIGHT_4, "light")
        if frag == "button":
            return r11.button(BUTTONS[0])
        return r10.theme(frag) if frag in THEMES else r9.air_pulse(r9.RETRO, r9.RETRO_HARM)(frag)
    frags = list(HARD) + ["light-1", "light-4", "light-3", "light-2", "intro", "section", "button"]
    demo(out, {"picks": (make, 0.16)}, frags, prefix="picks ", longest=r10.longest)
    for f in frags:
        (out / f"picks {f}.mp3").unlink()
    (out / "picks demo episode.mp3").rename(out / "story cues - the picks in rotation.mp3")
