"""Round 11: David's notes on the round 10 set as heard in ep-2026-10-24.

  hard cues  too positive: two variants to choose from, suspended (never quite lands) and warm minor
             (m9 colour, middle register, so pensive rather than sad). Each cue also gets its own
             opening (only the kick, only the swell, a soft hat pickup) so the three are easier to tell apart.
  light-4    one more in the style of light-1 and light-3 (his favourites): syncopated, borrowed chords.
  button     "a little too christmasy": takes from the anthem's cells and free ones, all resolving home,
             mostly without the bell glint.
  intro bed  new: music under the whole cold open that lands the intro theme after the hello, as NPR's
             Up First or NYT's The Daily do. Three feels: up-first (bright, punchy), the-daily (a pulsing
             repeated figure that builds) and between (a groove in the set's jazzy Rhodes colour).
             Each is also mixed under ep-2026-10-24's real cold open.

light-1/2/3, the intro theme and What's on are unchanged (round 10).

usage: RENDER=<path-to-render-binary> python round-11.py <out-dir> [episode.mp3 transcript.vtt]
"""
import importlib.util, re, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()


def _round(n):
    spec = importlib.util.spec_from_file_location(f"round{n}", Path(__file__).parent / f"round-{n}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


r9, r10 = _round(9), _round(10)
from_r9 = ("KICK", "CLOSED_HATS", "OPEN_HAT", "glint", "up12", "clip", "C9", "CMAJ7", "G9", "D_SUS", "F9", "A_G")
KICK, CLOSED_HATS, OPEN_HAT, glint, up12, clip, C9, CMAJ7, G9, D_SUS, F9, A_G = (getattr(r9, k) for k in from_r9)
SHAKER = r10.SHAKER

SNARE_FILE = LOGIC / "EXS Factory Samples/Drum Kit Designer Consolidated/Drum Kit Designer/Stereo/SoCal Kit Snare_consolidated.caf"
CROSS_STICK = [clip(SNARE_FILE, s, 0.25) for s in (110.62, 111.87, 113.12, 114.38)]  # the kit's softest, brightest hits
BASS = Bank(ALCHEMY / "Bass/Real Bass/MMBass Mute")
BASS.roots.pop(midi("E1"))  # "E0" sounds at E2, not E1 (measured); low notes come from C2 instead

# New voicings, beside round 9's
CSUS2 = ["C3", "G3", "D4"]
GSUS2 = ["G2", "D3", "A3"]
GSUS4 = ["G2", "D3", "C4"]
DSUS4 = ["D3", "G3", "A3"]
EM9 = ["E3", "G3", "D4", "F#4"]
AM9 = ["A2", "G3", "B3", "C4"]
BM7 = ["B2", "F#3", "A3", "D4"]
D9SUS = ["D3", "G3", "C4", "E4"]
CMAJ9 = ["C3", "G3", "B3", "D4"]
GMAJ9 = ["G2", "F#3", "A3", "B3"]
G69 = ["G2", "D3", "A3", "B3", "E4"]

# --- story cues ----------------------------------------------------------------------------------
# (melody as (note, beats), chords as (beat, voicing), opening)

HARD = {
    "sus": {  # every melody ends on a 2nd or 4th, over a chord that doesn't settle
        "hard-1": ([("D4", 0.5), ("E4", 0.5), ("A4", 2)], [(0, CSUS2), (1, GSUS2)], "kick"),
        "hard-2": ([("G4", 1), ("A4", 1), ("C5", 2)], [(0, DSUS4), (2, GSUS4)], "swell"),
        "hard-3": ([("A3", 1), ("G3", 0.5), ("A3", 2)], [(0, CSUS2), (1.5, GSUS2)], "hats"),
    },
    "minor": {  # E minor, warm: m9 and maj7 colour, nothing low
        "hard-1": ([("B3", 0.5), ("D4", 0.5), ("E4", 2)], [(0, CMAJ7), (1, EM9)], "kick"),
        "hard-2": ([("E4", 1), ("F#4", 1), ("G4", 2)], [(0, AM9), (2, EM9)], "swell"),
        "hard-3": ([("E4", 0.5), ("D4", 0.5), ("B3", 2)], [(0, AM9), (1, BM7)], "hats"),
    },
}
LIGHT_4 = ([("A4", 0.5), ("C5", 1), ("E5", 0.5), ("F#5", 1.5)], [(0, AM9), (1.5, GMAJ9)], "swell+kick")


def story(notes, harm, opening, kind):
    """Round 9's air_pulse() with a choice of opening: 'kick' (no swell), 'swell' (no kick), 'hats' (a
    soft closed-hat pickup), or 'swell+kick' as before."""
    hard = kind == "hard"
    beat, lead = (0.36 if hard else 0.3), 0.65
    at, placed = 0.0, []
    for n, b in notes:
        placed.append((at, n, b * beat))
        at += b * beat
    end = at
    events = []
    if "swell" in opening:
        swish = OPEN_HAT[::-1] * np.linspace(0, 1, len(OPEN_HAT))[:, None] ** 3
        swish = swish[-int(0.6 * SR):]
        events.append((lead - len(swish) / SR, filt(swish, lo=2500) * (0.2 if hard else 0.22)))
    if "kick" in opening:
        events.append((lead, filt(KICK, hi=900) * (0.5 if hard else 0.65)))
    if opening == "hats":
        events += [(lead - k * beat / 2, pan(filt(CLOSED_HATS[k], lo=2000) * 0.08, (-0.35, 0.35)[k % 2])) for k in (2, 1)]
        events.append((lead, filt(KICK, hi=700) * 0.3))
    if not hard:
        events += [(lead + k * beat, pan(filt(CLOSED_HATS[k % 4], lo=2000) * 0.1, (-0.35, 0.35)[k % 2]))
                   for k in range(1, int(end / beat) + 1)]
    for i, (s, n, h) in enumerate(placed):
        events.append((lead + s, pan(RHODES.note(n, hold=h + 0.05, release=0.5, vel=0.68), -0.15)))
        events.append((lead + s, pan(glint(up12(n), 0.38 if hard else 0.48), (0.45, 0.3)[i % 2])))
    for k, (b, voicing) in enumerate(harm):
        until = harm[k + 1][0] * beat if k + 1 < len(harm) else end + 0.6
        for j, n in enumerate(voicing):
            p = 0.4 * (2 * j / max(1, len(voicing) - 1) - 1)
            events.append((lead + b * beat + 0.012 * j,
                           pan(RHODES.note(n, hold=until - b * beat, release=0.5, vel=0.32 if hard else 0.38), p)))
    return filt(place(events), lo=40, hi=6000 if hard else 9000)


# --- buttons -------------------------------------------------------------------------------------
# round 10's theme() spec, plus: glint (its level, 0 for none) and bass as (beat, note, beats)

BUTTONS = {
    "anthem-a": dict(  # phrase 3 reversed: G F# E D, then F# G home
        beat=0.34, beats=8, glint=0,
        melody=[(0, "G4", 1), (1, "F#4", 1), (2, "E4", 0.5), (2.5, "D4", 1.5), (4, "F#4", 1), (5, "G4", 3)],
        chords=[(0, CMAJ7), (2.5, D_SUS), (4, D9SUS), (5, G69)],
        kick=[(0, 0.5), (2.5, 0.3), (5, 0.45)], hats=(0, 4), shaker=(0, 0), end_hat=None,
    ),
    "anthem-b": dict(  # phrase 2 reversed: C D E D C, settling on B, the 3rd
        beat=0.34, beats=8, glint=0,
        melody=[(0, "C5", 0.5), (0.5, "D5", 0.5), (1, "E5", 1), (2, "D5", 1), (3, "C5", 1), (4, "B4", 4)],
        chords=[(0, AM9), (2, D9SUS), (4, GMAJ9)],
        bass=[(0, "A1", 2), (2, "D2", 2), (4, "G1", 4)],
        kick=[(0, 0.5), (2, 0.3), (4, 0.45)], hats=(0, 4), shaker=(0, 2), end_hat=None,
    ),
    "free-a": dict(  # a rising answer, twice, landing on the root up top
        beat=0.32, beats=8, glint=0,
        melody=[(0, "D5", 0.5), (0.5, "E5", 1.5), (2, "B4", 0.5), (2.5, "D5", 1.5), (4, "E5", 0.5), (4.5, "G5", 3.5)],
        chords=[(0, CMAJ9), (2, EM9), (4, AM9), (4.5, G69)],
        kick=[(0, 0.55), (2, 0.3), (4.5, 0.45)], hats=(0, 4.5), shaker=(0, 4), end_hat=4.5,
    ),
    "free-b": dict(  # What's on's ending (D F# G A over A/G), then the suspension resolved: C to B over G
        beat=0.3, beats=10, glint=0.4,
        melody=[(0, "D5", 0.5), (0.5, "F#5", 0.5), (1, "G5", 0.5), (1.5, "A5", 2.5), (4, "C5", 1), (5, "B4", 5)],
        chords=[(0, D_SUS), (1.5, A_G), (4, GSUS4), (5, G9)],
        kick=[(0, 0.55), (1.5, 0.3), (4, 0.45), (5, 0.4)], hats=(0, 4), shaker=(0, 4), end_hat=5,
    ),
    "free-c": dict(  # ii - V - I in G: Am9, D9sus, Gmaj9, with the bass under it and the kit dropping out
        beat=0.34, beats=8, glint=0,
        melody=[(0, "C5", 0.5), (0.5, "E5", 1.5), (2, "D5", 0.5), (2.5, "C5", 1.5), (4, "B4", 0.5), (4.5, "D5", 3.5)],
        chords=[(0, AM9), (2, D9SUS), (4, GMAJ9)],
        bass=[(0, "A1", 2), (2, "D2", 2), (4, "G1", 4)],
        kick=[(0, 0.5), (4, 0.4)], hats=(0, 2), shaker=(0, 0), end_hat=None,
    ),
}


def rhodes_chord(voicing, at, length, vel, spread=0.4):
    return [(at + 0.012 * j, pan(RHODES.note(n, hold=length, release=0.5, vel=vel),
                                 spread * (2 * j / max(1, len(voicing) - 1) - 1))) for j, n in enumerate(voicing)]


def button(name):
    """Round 10's theme(), with an optional glint and bass line."""
    t = BUTTONS[name]
    beat, lead = t["beat"], 0.65
    swish = OPEN_HAT[::-1] * np.linspace(0, 1, len(OPEN_HAT))[:, None] ** 3
    events = [(lead - 0.6, filt(swish[-int(0.6 * SR):], lo=2500) * 0.22)]
    events += [(lead + b * beat, filt(KICK, hi=900) * v) for b, v in t["kick"]]
    h0, h1 = t["hats"]
    for k in range(int(h0 * 2), int(h1 * 2)):
        events.append((lead + k * beat / 2, pan(filt(CLOSED_HATS[k % 4], lo=2000) * (0.11 if k % 2 else 0.07), 0.35)))
    s0, s1 = t["shaker"]
    for k in range(int(s0 * 4), int(s1 * 4)):
        events.append((lead + k * beat / 4, pan(filt(SHAKER[k % 4], lo=1500) * (0.1 if k % 2 else 0.06), -0.45)))
    if t["end_hat"] is not None:
        events.append((lead + t["end_hat"] * beat, pan(filt(OPEN_HAT, lo=3000) * 0.12, 0.3)))
    for i, (b, n, length) in enumerate(t["melody"]):
        events.append((lead + b * beat, pan(RHODES.note(n, hold=length * beat + 0.05, release=0.5, vel=0.68), -0.15)))
        if t["glint"]:
            events.append((lead + b * beat, pan(glint(up12(n), t["glint"]), (0.45, 0.3)[i % 2])))
    for b, n, length in t.get("bass", []):
        events.append((lead + b * beat, filt(BASS.note(n, hold=length * beat, release=0.4, vel=0.5), hi=1200)))
    chords = t["chords"]
    for k, (b, voicing) in enumerate(chords):
        until = (chords[k + 1][0] if k + 1 < len(chords) else t["beats"]) * beat + (0 if k + 1 < len(chords) else 0.6)
        events += rhodes_chord(voicing, lead + b * beat, until - b * beat, 0.36)
    return filt(place(events), lo=40, hi=9000)


# --- intro beds ----------------------------------------------------------------------------------
# A bar of four beats repeats under the cold open. Beds are built backwards from the moment the intro
# theme lands (its downbeat), so the last bar always ends there whatever the cold open's length; layers
# enter by how many bars are left, which makes each bed build towards the theme.
# Each bar: (chord voicing, bass notes as (beat, note, beats)).

BEDS = {
    "up-first": dict(
        beat=0.27,
        bars=[(GMAJ9, [(0, "G1", 1.5), (1.5, "D2", 1), (3, "G1", 0.5), (3.5, "A1", 0.5)]),
              (AM9, [(0, "A1", 1.5), (1.5, "E2", 1), (3, "A1", 0.5), (3.5, "B1", 0.5)]),
              (CMAJ9, [(0, "C2", 1.5), (1.5, "G1", 1), (3, "C2", 1)]),
              (D9SUS, [(0, "D2", 1.5), (1.5, "A1", 1), (3, "D2", 0.5), (3.5, "F#1", 0.5)])],
        kick=[(0, 0.6), (1.5, 0.45), (2, 0.5)], stick=[(1, 0.16), (3, 0.18)],
        comp=[(0, 0.5, 0.24), (1.5, 0.5, 0.2), (2.5, 1.5, 0.22)],  # (beat, beats, velocity): stabs
        hats="eighths", shaker=99, hook_every=2,
        hook=[(0, "D5", 0.5), (0.5, "E5", 0.5), (1, "G5", 1.5), (3, "A5", 1)],
    ),
    "the-daily": dict(
        beat=0.3,
        bars=[(EM9, [(0, "E1", 4)]), (CMAJ9, [(0, "C2", 4)]), (EM9, [(0, "E1", 4)]), (D9SUS, [(0, "D2", 4)])],
        kick=[(0, 0.45), (1, 0.3), (2, 0.4), (3, 0.3)], stick=[],
        figure=["E4", "B4", "G4", "B4", "D5", "B4", "G4", "B4"],  # a repeating eighth-note Rhodes figure
        comp=[(0, 4, 0.16)],
        hats="offbeats", hats_from=8, shaker=4, hook_every=4,
        hook=[(0, "B5", 2), (2, "A5", 2)],
    ),
    "between": dict(
        beat=0.3,
        bars=[(GMAJ9, [(0, "G1", 2.5), (2.5, "D2", 1), (3.5, "F#1", 0.5)]),
              (EM9, [(0, "E1", 2.5), (2.5, "B1", 1.5)]),
              (CMAJ9, [(0, "C2", 2.5), (2.5, "G1", 1.5)]),
              (D9SUS, [(0, "D2", 2.5), (2.5, "A1", 1), (3.5, "C2", 0.5)])],
        kick=[(0, 0.55), (2.5, 0.35)], stick=[(1, 0.13), (3, 0.15)],
        comp=[(0, 1.5, 0.26), (1.5, 2.5, 0.22)],
        hats="eighths", shaker=8, hook_every=4,
        hook=[(0, "D5", 0.5), (0.5, "F#5", 0.5), (1, "G5", 0.5), (1.5, "A5", 2.5)],  # the intro theme's opening cell
    ),
}


def bed(name, length):
    """`length` seconds of bed, ending on a bar line at its last sample (where the theme's downbeat goes)."""
    b = BEDS[name]
    beat = b["beat"]
    bar = 4 * beat
    n = int(np.ceil(length / bar)) + 1
    t0 = length - n * bar  # where bar 0 starts; usually before 0, so the bed opens mid-bar
    events = []
    for i in range(n):
        left = n - i  # bars until the theme
        at = t0 + i * bar
        chord, bass = b["bars"][i % len(b["bars"])]
        for k, v in b["kick"]:
            events.append((at + k * beat, filt(KICK, hi=800) * v))
        for k, v in b["stick"]:
            events.append((at + k * beat, pan(filt(CROSS_STICK[(i + int(k)) % 4], lo=900) * v, -0.2)))
        if b["hats"] == "eighths" or left <= b.get("hats_from", 99):
            for k in range(8):
                if b["hats"] == "offbeats" and k % 2 == 0:
                    continue
                events.append((at + k * beat / 2, pan(filt(CLOSED_HATS[(i + k) % 4], lo=2500) * (0.09 if k % 2 else 0.055), 0.35)))
        if left <= b["shaker"]:
            for k in range(16):
                events.append((at + k * beat / 4, pan(filt(SHAKER[k % 4], lo=1800) * (0.08 if k % 2 else 0.045), -0.45)))
        for k, note, beats in bass:
            events.append((at + k * beat, filt(BASS.note(note, hold=beats * beat - 0.03, release=0.12, vel=0.55), hi=900)))
        for k, beats, vel in b["comp"]:
            events += rhodes_chord(chord, at + k * beat, beats * beat - 0.05, vel)
        for k, note in enumerate(b.get("figure", [])):
            events.append((at + k * beat / 2, pan(RHODES.note(note, hold=beat / 2, release=0.3, vel=0.3), 0.25)))
        if left <= 8 and left % b["hook_every"] == 0:
            for j, (k, note, beats) in enumerate(b["hook"]):
                events.append((at + k * beat, pan(glint(note, 0.42), (0.4, 0.25)[j % 2])))
    events.append((length - 0.6, filt((OPEN_HAT[::-1] * np.linspace(0, 1, len(OPEN_HAT))[:, None] ** 3)[-int(0.6 * SR):], lo=2500) * 0.25))
    events = [(s - t0, x) for s, x in events if s + len(x) / SR > 0]  # shift so the earliest sound is in range
    y = place([(s, x) for s, x in events])
    y = y[int(-t0 * SR):][: int(length * SR)]
    y = filt(y, lo=40, hi=10000)
    fade_in = min(len(y), int(1.5 * SR))
    y[:fade_in] *= np.linspace(0, 1, fade_in)[:, None] ** 2
    return y


def duck(music, voice, under=17, gaps=9):
    """Sidechain: the bed sits `under` dB below the voice while it speaks and `gaps` dB below it between
    lines, with a quick dip and a slow return."""
    m = np.abs(voice).max(axis=1)
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(win) / win, mode="same"))
    speaking = (env > env.max() * 10 ** (-30 / 20)).astype(float)
    # attack 40 ms, release 450 ms, one sample at a time on a 10 ms grid
    step = int(0.01 * SR)
    coarse = speaking[::step]
    g = np.zeros_like(coarse)
    for i in range(1, len(coarse)):
        rate = 0.25 if coarse[i] > g[i - 1] else 0.022
        g[i] = g[i - 1] + (coarse[i] - g[i - 1]) * rate
    g = np.interp(np.arange(len(m)), np.arange(len(coarse)) * step, g)
    db = -gaps - (under - gaps) * g
    n = min(len(music), len(db))
    out = music.copy()
    out[:n] *= 10 ** (db[:n] / 20)[:, None]
    out[n:] *= 10 ** (-gaps / 20)
    return out


def cold_open(episode, vtt):
    """The cold open's voices from a cue-free stretch of an episode: up to the end of the last line before
    the first story (the first gap of more than 2 s in the transcript, where the intro theme sits)."""
    cues = [(secs_of(a), secs_of(b)) for a, b in re.findall(r"(\d+:\d+:[\d.]+) --> (\d+:\d+:[\d.]+)", vtt.read_text())]
    end = next(b for (_, b), (a, _) in zip(cues, cues[1:]) if a - b > 2)
    return load(episode)[: int((end + 0.1) * SR)]


def secs_of(stamp):
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def bed_demo(name, voice):
    """The bed under `voice`, then the intro theme as the episode plays it after the hello."""
    v = voice * 10 ** ((VOICE_DB - level(voice)) / 20)
    intro = finish(r10.theme("intro"), 0.16, 6.5)
    gap = 0.25  # cues.BEFORE
    lead = 0.65  # the theme's downbeat, after its own swell
    land = len(v) / SR + gap + lead
    music = bed(name, land)
    music = reverb(music, 0.12)[: len(music)]
    music *= 10 ** ((VOICE_DB - level(music)) / 20)
    music = duck(music, np.concatenate([v, secs(land - len(v) / SR)]))
    return place([(0, v), (0, music), (len(v) / SR + gap, intro)])


def bed_alone(name, length=24.0):
    music = reverb(bed(name, length), 0.12)
    music *= 10 ** ((VOICE_DB - 9 - level(music)) / 20)
    intro = finish(r10.theme("intro"), 0.16, 6.5)
    return place([(0, music[: int(length * SR)]), (length - 0.65, intro)])


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    lights = {f: v for f, v in r9.RETRO.items() if f.startswith("light")}
    for variant, cues in HARD.items():
        def make(frag, cues=cues):
            if frag in cues:
                return story(*cues[frag], "hard")
            if frag == "light-4":
                return story(*LIGHT_4, "light")
            if frag == "button":
                return button("free-b")
            return r10.theme(frag) if frag in THEMES else r9.air_pulse(r9.RETRO, r9.RETRO_HARM)(frag)
        # the new light-4 goes second so the demo's three light breaks play it
        frags = list(cues) + ["light-1", "light-4", "light-3", "light-2", "intro", "section", "button"]
        demo(out, {variant: (make, 0.16)}, frags, prefix=f"{variant} ", longest=r10.longest)
        for f in frags:
            p = out / f"{variant} {f}.mp3"
            if f == "light-4" and variant == "sus":
                p.rename(out / "light-4.mp3")
            elif not f.startswith("hard"):
                p.unlink()
        (out / f"{variant} demo episode.mp3").rename(out / f"{variant} hard - demo episode.mp3")
    for name in BUTTONS:
        s = finish(button(name), 0.16, 6.5)
        write(out / f"button {name}.mp3", np.concatenate([secs(0.3), s, secs(0.5)]))
        print(f"button {name}: {len(s) / SR:.1f}s")
    for name in BEDS:
        write(out / f"intro bed {name}.mp3", np.concatenate([bed_alone(name), secs(0.5)]))
        print(f"intro bed {name}")
    if len(sys.argv) > 3:
        voice = cold_open(Path(sys.argv[2]), Path(sys.argv[3]))
        for name in BEDS:
            write(out / f"intro bed {name} - cold open.mp3", np.concatenate([bed_demo(name, voice), secs(0.5)]))
