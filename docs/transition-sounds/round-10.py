"""Round 10: longer themes for the show's three big moments, in round 9 version 2's language.

  intro     after the hosts' hello, before the first story (new: there was no cue there before)
  section   opens What's on in Amsterdam
  button    after the sign-off

Each is three bars (about 5 s with its ring-out) instead of one gesture: cells from the Wilhelmus in
retrograde, over the same chords (C, D, F, A-over-G, G; nothing minor), played by Rhodes with a bell
glint, with a fuller kit than the story cues: kick, real closed hats on the eighths and a soft shaker.
The intro rises and stays up in the air (it leads into the news), What's on is the lightest and
busiest, and the sign-off thins out and comes home.

Also re-renders round 9's two versions so every file is named by version and cue, and the demo
episode plays each cue once.

usage: RENDER=<path-to-render-binary> python round-10.py <out-dir>
"""
import importlib.util, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round9", Path(__file__).parent / "round-9.py")
r9 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r9)

SHAKER_FILE = LOGIC / "EXS Factory Samples/Drum Kit Designer Consolidated/Drum Kit Designer Shaker/AP v1 Shaker_consolidated.caf"
SHAKER = [r9.clip(SHAKER_FILE, s, 0.12) for s in (20.65, 20.79, 20.93, 21.21)]  # a softly played run

# Each theme: beat length, melody as (beat, note, beats), chords as (beat, voicing), and the kit:
# kick beats (with level), whether hats and shaker play (and until which beat), and the total beats.
THEMES_SPEC = {
    "intro": dict(  # phrase 3 reversed (D F# G A), phrase 2 reversed (B C D), then E D: ends on the 5th, open
        beat=0.3, beats=12,
        melody=[(0, "D4", 0.5), (0.5, "F#4", 0.5), (1, "G4", 0.5), (1.5, "A4", 2.5),
                (4, "B4", 0.5), (4.5, "C5", 0.5), (5, "D5", 3), (8, "E5", 0.5), (8.5, "D5", 3.5)],
        chords=[(0, r9.D_SUS), (1.5, r9.A_G), (4, r9.C9), (5, r9.G9), (8, r9.C9), (8.5, r9.G9)],
        kick=[(0, 0.65), (2.5, 0.3), (4, 0.6), (6.5, 0.3), (8, 0.6)],
        hats=(0, 8), shaker=(4, 8), end_hat=8,
    ),
    "section": dict(  # phrase 2 reversed twice, then phrase 3 reversed an octave up, floating on A over G
        beat=0.28, beats=12,
        melody=[(0, "B4", 0.5), (0.5, "C5", 0.5), (1, "D5", 1), (2, "E5", 0.5), (2.5, "D5", 1.5),
                (4, "C5", 0.5), (4.5, "D5", 0.5), (5, "E5", 0.5), (5.5, "D5", 2.5),
                (8, "D5", 0.5), (8.5, "F#5", 0.5), (9, "G5", 0.5), (9.5, "A5", 2.5)],
        chords=[(0, r9.G9), (2, r9.C9), (4, r9.F9), (5.5, r9.G9), (8, r9.D_SUS), (9.5, r9.A_G)],
        kick=[(0, 0.6), (2.5, 0.3), (4, 0.55), (6.5, 0.3), (8, 0.55), (9.5, 0.3)],
        hats=(0, 10), shaker=(0, 10), end_hat=9.5,
    ),
    "button": dict(  # phrase 1 reversed (A B C B), then A home to G: F -> C -> D -> G, the kit dropping out
        beat=0.34, beats=8,
        melody=[(0, "A4", 0.5), (0.5, "B4", 0.5), (1, "C5", 1), (2, "B4", 2),
                (4, "A4", 1), (5, "G4", 3)],
        chords=[(0, r9.F9), (2, r9.C9), (4, r9.D_SUS), (5, r9.G9 + ["G4"])],
        kick=[(0, 0.55), (4, 0.45), (5, 0.5)],
        hats=(0, 4), shaker=(0, 2), end_hat=5,
    ),
}


def theme(name):
    t = THEMES_SPEC[name]
    beat, lead = t["beat"], 0.65
    swish = r9.OPEN_HAT[::-1] * np.linspace(0, 1, len(r9.OPEN_HAT))[:, None] ** 3
    swish = swish[-int(0.6 * SR):]
    events = [(lead - len(swish) / SR, filt(swish, lo=2500) * 0.22)]
    events += [(lead + b * beat, filt(r9.KICK, hi=900) * v) for b, v in t["kick"]]
    h0, h1 = t["hats"]
    for k in range(int(h0 * 2), int(h1 * 2)):  # eighths, offbeats a touch louder
        events.append((lead + k * beat / 2, pan(filt(r9.CLOSED_HATS[k % 4], lo=2000) * (0.11 if k % 2 else 0.07), 0.35)))
    s0, s1 = t["shaker"]
    for k in range(int(s0 * 4), int(s1 * 4)):  # sixteenths, very soft, on the other side
        events.append((lead + k * beat / 4, pan(filt(SHAKER[k % 4], lo=1500) * (0.1 if k % 2 else 0.06), -0.45)))
    events.append((lead + t["end_hat"] * beat, pan(filt(r9.OPEN_HAT, lo=3000) * 0.12, 0.3)))
    end = t["beats"] * beat
    for i, (b, n, length) in enumerate(t["melody"]):
        events.append((lead + b * beat, pan(RHODES.note(n, hold=length * beat + 0.05, release=0.5, vel=0.68), -0.15)))
        events.append((lead + b * beat, pan(r9.glint(r9.up12(n), 0.48), (0.45, 0.3)[i % 2])))
    chords = t["chords"]
    for k, (b, voicing) in enumerate(chords):
        until = (chords[k + 1][0] if k + 1 < len(chords) else t["beats"]) * beat + (0 if k + 1 < len(chords) else 0.6)
        for j, n in enumerate(voicing):
            p = 0.4 * (2 * j / max(1, len(voicing) - 1) - 1)
            events.append((lead + b * beat + 0.012 * j, pan(RHODES.note(n, hold=until - b * beat, release=0.5, vel=0.36), p)))
    return filt(place(events), lo=40, hi=9000)


def longest(frag):
    return 6.5 if frag in THEMES else 3.6


out = Path(sys.argv[1])
cues = {k: v for k, v in r9.RETRO.items() if k not in ("section", "button")}
make_v2 = r9.air_pulse(r9.RETRO, r9.RETRO_HARM)

# version 2's story cues with the new themes: the full set as an episode would use it
demo(out, {"themes": (lambda f: theme(f) if f in THEMES else make_v2(f), 0.16)},
     list(cues) + list(THEMES), prefix="v2+themes ", longest=longest)
# round 9's versions as they were, for reference by name
for name, (make, wet, frags) in r9.VERSIONS.items():
    demo(out, {name: (make, wet)}, frags, prefix=f"v{name.split('-')[0]} ")

# the v2 story cues are already there under "v2"; keep only the themes under their own names
for f in cues:
    (out / f"v2+themes {f}.mp3").unlink()
for f in THEMES:
    (out / f"v2+themes {f}.mp3").rename(out / f"theme {f}.mp3")
(out / "v2+themes demo episode.mp3").rename(out / "v2 with themes - demo episode.mp3")
for v in ("v1", "v2"):
    (out / f"{v} demo episode.mp3").rename(out / f"{v} - demo episode.mp3")
