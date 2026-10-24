"""The set decided in rounds 11-16, rendered for the pipeline (src/nlnews/cues.py) into assets/cues.

Story cues and themes are whole files, 44.1 kHz mono WAV. The themes keep their lead-in, so each
one's downbeat is LEAD seconds in, where the pipeline lands it.

The beds can't be whole files: each is fitted to the day's timing, with a bar count and tempo that
change from day to day, and their sounds are Logic's, which CI doesn't have. So each bed is rendered
here as stems, one beat each at the bed's own tempo (everything that starts in that beat, with its
full ring-out and reverb), and the pipeline lays them out on the fitted beats. Within a beat the
timing stays the bed's own: at a 3% nudge that's at most 8 ms off, where stretching the audio (ffmpeg's
atempo) moved hits by up to 14 ms and smeared them. A bar's layers depend only on its chord and on
how many bars are left before the theme (the hook and shaker come in over the last 8), so a bed needs
these bars, as stems `<bar>.<beat>`:

  near-1 ... near-8   the last 8 bars, by bars left (near-1 is the D9sus the theme lands after)
  far-0 ... far-3     any earlier bar, by bars left mod 4 (its chord)
  sting               the up-first and sombre beds' first two bars: the sting, with its swish
  first               the outro bed's first bar (Gmaj9, after What's on's theme)

beds/swish.flac is the swish every bed ends on into its theme. Each stem starts PRE seconds before
its beat. The button plays at What's on's tempo, as the intro theme plays at its own after its bed.

usage: RENDER=<render> python render-cues.py <repo>/assets/cues
"""
import importlib.util, json, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round15", Path(__file__).parent / "round-15.py")
r15 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r15)
r14, r13, r12, r11, r10 = r15.r14, r15.r13, r15.r12, r15.r11, r15.r10
LEAD = r13.LEAD
PRE = 0.7  # seconds of a stem before its bar line, for a swish leading into it
NEAR = 8  # the last bars, each its own stem
BEDS = {"up-first": 4 * r13.BEDS["up-first"]["beat"], "sombre-pulse": 4 * r13.BEDS["sombre-pulse"]["beat"],
        "between": 4 * r13.SECTION_BEAT}  # bar lengths; the outro bed starts at What's on's tempo
OUTRO_FIRST = (r13.GMAJ9, [(0, "G1", 2.5), (2.5, "D2", 1.5)])  # as round 15's closing()


def bar_events(name, bar, left, chord=None, bass=None, hook=True):
    """One bar of r13.bed(), `left` bars before the theme, starting at 0."""
    b = r13.BEDS[name]
    beat = bar / 4
    c, bs = b["bars"][-left % len(b["bars"])]
    chord, bass = chord or c, bass or bs
    events = []
    for k, v in b["kick"]:
        events.append((k * beat, filt(r13.KICK, hi=800) * v))
    for k, v in b["stick"]:
        events.append((k * beat, pan(filt(r13.CROSS_STICK[(left + int(k)) % 4], lo=900) * v, -0.2)))
    if b["hats"] == "eighths" or (b["hats"] == "offbeats" and left <= b.get("hats_from", 99)):
        for k in range(8):
            if b["hats"] == "offbeats" and k % 2 == 0:
                continue
            events.append((k * beat / 2, pan(filt(r13.CLOSED_HATS[(k - left) % 4], lo=2500) * (0.09 if k % 2 else 0.055), 0.35)))
    if left <= b["shaker"]:
        for k in range(16):
            events.append((k * beat / 4, pan(filt(r13.SHAKER[k % 4], lo=1800) * (0.08 if k % 2 else 0.045), -0.45)))
    for k, note, beats in bass:
        events.append((k * beat, filt(r13.BASS.note(note, hold=beats * beat - 0.03, release=0.12, vel=0.55), hi=900)))
    for k, beats, vel in b["comp"]:
        events += r11.rhodes_chord(chord, k * beat, beats * beat - 0.05, vel)
    for k, note in enumerate(b.get("figure", [])):
        events.append((k * beat / 2, pan(RHODES.note(note, hold=beat / 2, release=0.3, vel=0.3), 0.25)))
    if hook and left <= 8 and left % b["hook_every"] == 0:
        for j, (k, note, beats) in enumerate(b["hook"]):
            events.append((k * beat, pan(r11.glint(note, b.get("hook_level", 0.42)), (0.4, 0.25)[j % 2])))
    return events


def sting_events(name, bar):
    """The sting's two bars, as r13.bed() plays them with `sting`, and round 15's swish into them."""
    s = r13.STINGS[name]
    beat = bar / 4
    events = []
    for i, chord in enumerate(s["chords"]):
        events += [(i * bar + t, x) for t, x in bar_events(name, bar, 99, chord, [(0, r13.BASS_ROOT[tuple(chord)], 4)], hook=False)]
    events.append((0, pan(filt(r13.OPEN_HAT, lo=3000) * 0.12, 0.3)))
    for j, (k, note, beats) in enumerate(s["melody"]):
        events.append((k * beat, pan(RHODES.note(note, hold=beats * beat + 0.05, release=0.6, vel=0.62), -0.15)))
        events.append((k * beat, pan(r11.glint(r11.up12(note), 0.45), (0.45, 0.3)[j % 2])))
    swish = (r13.OPEN_HAT[::-1] * np.linspace(0, 1, len(r13.OPEN_HAT))[:, None] ** 3)[-int(LEAD * SR):]
    events.append((-LEAD, filt(swish, lo=2500) * 0.25))
    return events


def beats(events, bar, n_beats=4):
    """Events (in seconds from the bar line) as one stem per beat, each from its beat."""
    beat = bar / 4
    by_beat = {}
    for t, x in events:
        k = min(n_beats - 1, max(0, int(t / beat + 1e-6)))
        by_beat.setdefault(k, []).append((t - k * beat, x))
    return {k: stem(e) for k, e in sorted(by_beat.items())}


def stem(events):
    """Events (from -PRE) as a stem: the bed's filter and reverb, folded to mono, its tail trimmed."""
    y = place([(t + PRE, x) for t, x in events])
    y = reverb(filt(y, lo=40, hi=10000), 0.12).mean(axis=1)
    loud = np.nonzero(np.abs(y) > np.abs(y).max() * 10 ** (-66 / 20))[0]
    return y[: loud[-1] + 1]


def mono(y):
    return y.mean(axis=1)


def write_mono(path, y, fmt="wav"):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = path.with_suffix(".raw")
    raw.write_bytes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", str(raw),
                    *(["-compression_level", "8"] if fmt == "flac" else []), str(path)], check=True)
    raw.unlink()


if __name__ == "__main__":
    out = Path(sys.argv[1])
    story = {
        "hard-1": r11.story(*r11.HARD["minor"]["hard-1"], "hard"),
        "hard-2": r11.story(*r11.HARD["sus"]["hard-2"], "hard"),
        "hard-3": r11.story(*r11.HARD["minor"]["hard-3"], "hard"),
        "light-4": r11.story(*r11.LIGHT_4, "light"),
    }
    for name, sig in story.items():
        write_mono(out / f"{name}.wav", mono(finish(sig, 0.16, 3.6)))
    write_mono(out / "hard-4.wav", mono(finish(r11.button("sombre-intro"), 0.16, 6.5)))
    write_mono(out / "hard-4-short.wav", mono(finish(r11.button("hard-4 short"), 0.16, 6.5)))
    themes = {"intro": r10.theme("intro"), "sombre-intro": r11.button("sombre-intro"), "section": r10.theme("section")}
    for name, sig in themes.items():
        write_mono(out / f"{name}.wav", mono(r13.themed(sig)))
    write_mono(out / "button.wav", mono(r15.bed_button("b no hats", r13.SECTION_BEAT)))

    stems = {}
    for name, bar in BEDS.items():
        parts = {f"near-{d}": beats(bar_events(name, bar, d), bar) for d in range(1, NEAR + 1)}
        parts |= {f"far-{k}": beats(bar_events(name, bar, 4 * NEAR + k), bar) for k in range(4)}
        if name in r13.STINGS:
            parts["sting"] = beats(sting_events(name, bar), bar, 4 * r13.STING_BARS)
        else:
            parts["first"] = beats(bar_events(name, bar, 4 * NEAR, *OUTRO_FIRST), bar)
        stems[name] = {f"{part}.{k}": y for part, by_beat in parts.items() for k, y in by_beat.items()}
    swish = (r13.OPEN_HAT[::-1] * np.linspace(0, 1, len(r13.OPEN_HAT))[:, None] ** 3)[-int(0.6 * SR):]
    stems["swish"] = {"swish": stem([(-0.6, filt(swish, lo=2500) * 0.25)])}
    gain = 0.5 / max(np.abs(y).max() for s in stems.values() for y in s.values())  # one gain keeps their balance
    for name, s in stems.items():
        for part, y in s.items():
            write_mono(out / "beds" / (f"{part}.flac" if name == "swish" else f"{name}/{part}.flac"), y * gain, "flac")
    (out / "beds" / "beds.json").write_text(json.dumps({"pre": PRE, "near": NEAR, "lead": LEAD, "button_bar": 4 * r13.SECTION_BEAT,
                                                       "bars": {k: round(v, 6) for k, v in BEDS.items()}}, indent=2) + "\n")
    print(f"wrote {out}")
