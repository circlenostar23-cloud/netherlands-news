"""Round 14: David's notes on round 13.

  intro    the cold open's top line and hook stay dry; the sting comes in after them, then the hello
           over the up-first bed, and the intro theme lands after it (cold open, theme, then welcome,
           the order many news podcasts use)
  sombre   two more beds for a day after a tragedy, both with round 13's sombre sting and theme:
           `pulse`, a quiet repeating Rhodes figure over a heartbeat kick, and `air`, a pad with no
           drums. Round 13's sombre theme also as a story cue, `hard-4`, and a shorter `hard-4 short`
  outro    What's on's theme no longer waits for the story to end: a bar of D9sus fades in under its
           last words, the theme lands LAND_AFTER the last word, and the hosts start over its last
           bars (after 2 bars, or after 1) with the bed carrying on underneath. Three buttons made
           from the bed itself, at its tempo, in place of anthem-b

usage: PYTHONPATH=src RENDER=<render> python round-14.py <out-dir> <run dir, e.g. data/2026-10-24>
"""
import importlib.util, re, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round13", Path(__file__).parent / "round-13.py")
r13 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r13)
r12, r11, r10 = r13.r12, r13.r11, r13.r10
EM9, CMAJ9, AM9, BM7, GMAJ9, D9SUS = r13.EM9, r13.CMAJ9, r13.AM9, r13.BM7, r13.GMAJ9, r13.D9SUS
LAND_AFTER, LEAD, SECTION_BEAT, SECTION_BEATS = r13.LAND_AFTER, r13.LEAD, r13.SECTION_BEAT, r13.SECTION_BEATS
WEEKDAYS = r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b"

# --- sombre beds ---------------------------------------------------------------------------------
SOMBRE_BARS = [(EM9, [(0, "E1", 4)]), (CMAJ9, [(0, "C2", 4)]), (AM9, [(0, "A1", 4)]), (BM7, [(0, "B1", 4)])]
r13.BEDS["sombre-pulse"] = dict(
    beat=0.36, bars=SOMBRE_BARS,
    kick=[(0, 0.32), (0.5, 0.16)], stick=[], comp=[(0, 4, 0.1)],
    figure=["E4", "B4", "D5", "B4", "E4", "B4", "D5", "B4"],  # quiet eighths, the same over every chord
    hats="none", shaker=0, hook_every=4, hook=[(0, "B5", 2), (2, "G5", 2)], hook_level=0.22,
)
r13.BEDS["sombre-air"] = dict(
    beat=0.36, bars=SOMBRE_BARS,
    kick=[], stick=[], comp=[], pad=0.5,  # chords on a pad instead of the Rhodes
    hats="none", shaker=0, hook_every=2, hook=[(0, "B5", 4)], hook_level=0.3,
)
for name in ("sombre-pulse", "sombre-air"):
    r13.STINGS[name] = r13.STINGS["sombre"]

_bed = r13.bed


def bed_with_pad(name, n, bar, sting=None, first=None):
    """r13.bed(), plus a pad holding each bar's chord when the bed has one."""
    y = _bed(name, n, bar, sting=sting, first=first)
    b = r13.BEDS[name]
    if not b.get("pad"):
        return y
    events = []
    for i in range(n):
        chord = b["bars"][(i - n) % len(b["bars"])][0]
        if sting and i < len(sting["chords"]):
            chord = sting["chords"][i]
        for j, note in enumerate(chord):
            events.append((i * bar, pan(SKY.note(note, hold=bar, release=0.8, vel=b["pad"]), 0.5 * (2 * j / (len(chord) - 1) - 1))))
    pad = filt(place(events), lo=60, hi=6000)[: len(y)]
    return y + np.concatenate([pad, np.zeros((len(y) - len(pad), 2))])


r13.bed = bed_with_pad  # r13.opening() uses it

# the sombre theme as a story cue, and a shorter one: E D B over Cmaj9 to Em9, held
r11.BUTTONS["hard-4 short"] = dict(
    beat=0.36, beats=5, glint=0.3,
    melody=[(0, "E5", 1), (1, "D5", 0.5), (1.5, "B4", 3.5)],
    chords=[(0, CMAJ9), (1.5, EM9)], bass=[(0, "C2", 1.5), (1.5, "E1", 3.5)],
    kick=[(0, 0.4)], hats=(0, 0), shaker=(0, 0), end_hat=None,
)

# --- buttons from the outro bed: its chords, its hook, its kit, at its tempo ----------------------
BED_BUTTONS = {
    "bed-a": dict(  # the bed's hook (D F# G A), turning down to G
        beats=8, glint=0.42,
        melody=[(0, "D5", 0.5), (0.5, "F#5", 0.5), (1, "G5", 0.5), (1.5, "A5", 1), (2.5, "F#5", 0.5), (3, "G5", 5)],
        chords=[(0, CMAJ9), (1.5, D9SUS), (3, GMAJ9)],
        bass=[(0, "C2", 1.5), (1.5, "D2", 1.5), (3, "G1", 5)],
        kick=[(0, 0.55), (1.5, 0.35), (3, 0.5)], hats=(0, 3), shaker=(0, 3), end_hat=3,
    ),
    "bed-b": dict(  # the bed's loop in half the time, Em9 Cmaj9 D9sus, landing on Gmaj9
        beats=9, glint=0,
        melody=[(0, "G5", 1), (1, "E5", 1), (2, "D5", 1), (3, "C5", 1), (4, "B4", 0.5), (4.5, "D5", 4.5)],
        chords=[(0, EM9), (2, CMAJ9), (3, D9SUS), (4, GMAJ9)],
        bass=[(0, "E1", 2), (2, "C2", 1), (3, "D2", 1), (4, "G1", 5)],
        kick=[(0, 0.5), (2, 0.3), (3, 0.35), (4, 0.5)], hats=(0, 4), shaker=(0, 4), end_hat=4,
    ),
    "bed-c": dict(  # What's on's floating A, brought down home over the bed's chords
        beats=9, glint=0.3,
        melody=[(0, "A5", 1), (1, "G5", 0.5), (1.5, "F#5", 0.5), (2, "E5", 1), (3, "D5", 1), (4, "G5", 5)],
        chords=[(0, CMAJ9), (2, D9SUS), (4, GMAJ9)],
        bass=[(0, "C2", 2), (2, "D2", 2), (4, "G1", 5)],
        kick=[(0, 0.5), (2, 0.35), (4, 0.5)], hats=(0, 4), shaker=(0, 2), end_hat=4,
    ),
}


def bed_button(name, beat):
    r11.BUTTONS[name] = dict(BED_BUTTONS[name], beat=beat)
    return r13.themed(r11.button(name))


# --- the run ---------------------------------------------------------------------------------------

def load_run(d):
    """r13.load_run(), plus where the hello starts (the cold open's line with the weekday in it)."""
    from nlnews import chapters, cues
    from nlnews.models import EpisodeScript
    voice, cuts = r13.load_run(d)
    script = EpisodeScript.model_validate_json((d / "script.json").read_text())
    _, timed, _ = chapters.find(script, d)
    cold = script.segments[0].lines
    hello = next(start for line, start, _ in timed[: len(cold)] if re.search(WEEKDAYS, line.text))
    mono = voice[:, 0].astype(np.float32)
    cuts["hello"] = cues._cut(mono, hello, cues._loud_db(mono)) / cues.RATE
    return voice, cuts


def split_opening(voice, hello, cut, bed_name="up-first", follow=9.0):
    """The top line and hook dry, the sting LAND_AFTER their last word (its swell under it), the hello
    over the bed, the intro theme LAND_AFTER the hello's last word, then the first story."""
    hook, hi = voice[: int(hello * SR)], voice[int(hello * SR): int(cut * SR)]
    sting_at = r12.last_word(hook) + LAND_AFTER
    words = r12.last_word(hi) + LAND_AFTER
    b = r13.BEDS[bed_name]
    n, bar = r13.fit(words, 4 * b["beat"])
    n += r13.STING_BARS
    hello_at = sting_at + r13.STING_BARS * bar
    swish = (r13.OPEN_HAT[::-1] * np.linspace(0, 1, len(r13.OPEN_HAT))[:, None] ** 3)[-int(LEAD * SR):]
    music = place([(0, filt(swish, lo=2500) * 0.25), (LEAD, r13.bed(bed_name, n, bar, sting=r13.STINGS[bed_name]))])
    music = r13.bed_level(music, np.concatenate([secs(hello_at - sting_at + LEAD), hi]), sting_end=hello_at - sting_at + LEAD)
    theme = r13.themed(r10.theme("intro"))
    land = sting_at + n * bar
    story = voice[int(cut * SR): int((cut + follow) * SR)]
    print(f"  split intro: sting {sting_at - r12.last_word(hook):.2f} s after the hook, {n} bars of {bar:.3f} s")
    return place([(0, hook), (sting_at - LEAD, music), (hello_at, hi),
                  (land - LEAD, theme), (land - LEAD + len(theme) / SR - 0.6, fade(story, 1.0))])


def closing(voice, cut, button_name, host_bars=2, before=8.0):
    """The end of the last story with a bar of D9sus fading in under it, What's on's theme LAND_AFTER
    its last word, the hosts in after `host_bars` bars of it, the bed from the theme's last bar line
    under the rest of the show, and a button made from the bed LAND_AFTER the sign-off's last word."""
    start = cut - before
    story = voice[int(start * SR): int(cut * SR)]
    tail = voice[int(cut * SR):]
    down = r12.last_word(story) + LAND_AFTER  # What's on's theme's downbeat
    sec_bar = 4 * SECTION_BEAT
    resume = down + host_bars * sec_bar
    bed_from = down + SECTION_BEATS * SECTION_BEAT
    land = resume + r12.last_word(tail) + LAND_AFTER
    n, bar = r13.fit(land - bed_from, sec_bar)
    # the theme and the bar fading in before it play at cue level, dipping 10 dB under the voices
    pre = r11.rhodes_chord(D9SUS, 0, sec_bar + LEAD, 0.24)
    pre = filt(place(pre), lo=60, hi=7000)
    pre *= np.linspace(0, 1, len(pre))[:, None] ** 1.5
    theme = place([(0, pre * 0.5), (sec_bar, r10.theme("section"))])  # theme() leads in by LEAD itself
    theme = r13.themed(theme)
    theme_at = down - sec_bar - LEAD
    voices = place([(0, story), (resume, tail)])
    track = np.concatenate([voices, secs(len(theme) / SR)])[int(theme_at * SR):][: len(theme)]
    theme = r11.duck(theme, track, under=10, gaps=0)
    music = r13.bed("between", n, bar, first=(GMAJ9, [(0, "G1", 2.5), (2.5, "D2", 1.5)]))
    music = r13.bed_level(music, voices[int(bed_from * SR):])
    button = bed_button(button_name, bar / 4)
    print(f"  outro {button_name}, hosts after {host_bars} bars: story to hosts {resume - r12.last_word(story):.2f} s; {n} bars of {bar:.3f} s")
    return place([(0, voices), (theme_at, theme), (bed_from, music), (land - LEAD, button)])


if __name__ == "__main__":
    out, run = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    voice, cuts = load_run(run)
    write(out / "intro - cold open, sting, hello over the bed.mp3",
          np.concatenate([split_opening(voice, cuts["hello"], cuts["intro"]), secs(0.5)]))
    sombre = r13.themed(r11.button("sombre-intro"))
    for name in ("sombre-pulse", "sombre-air"):
        write(out / f"sombre intro - {name.split('-')[1]}.mp3",
              np.concatenate([r13.opening(voice, cuts["intro"], name, sombre), secs(0.5)]))
    for name in ("sombre-intro", "hard-4 short"):
        s = finish(r11.button(name), 0.16, 6.5)
        write(out / f"{'hard-4' if name == 'sombre-intro' else name}.mp3", np.concatenate([secs(0.3), s, secs(0.5)]))
    for b in BED_BUTTONS:
        write(out / f"outro - {b}, hosts after 2 bars.mp3", np.concatenate([closing(voice, cuts["section"], b), secs(0.5)]))
    write(out / "outro - bed-a, hosts after 1 bar.mp3", np.concatenate([closing(voice, cuts["section"], "bed-a", 1), secs(0.5)]))
