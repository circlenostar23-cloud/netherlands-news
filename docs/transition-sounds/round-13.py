"""Round 13: the beds as the pipeline would play them, built on the run's own voiced files.

Round 12 cut its demos out of the published episode, which already had round 10's cues in it, placed
before the breath fix. This round starts from the voiced files, as `cues.splice()` does, and uses the
pipeline's own placement: `chapters.find()` for the heard starts, and `cues._cut()`, which cuts before
the host's breath (main, 310a36e), so the breath plays after the cue with its line.

  intro    a sting at the top, then the up-first bed under the hosts, landing the intro theme
           LAND_AFTER the cold open's last word, then the first story
  sombre   the same shape for a day after a tragedy: a slower, sparser bed in E minor with no backbeat,
           its own sting, and its own theme in place of the intro theme
  outro    What's on's theme runs straight into the between bed, which starts on the theme's last bar
           line at its tempo, with no fade-in. The tempo is nudged (a few percent at most) so a whole
           number of bars reaches the button's downbeat, and the button is anthem-b

Tempo nudging: a bed has two fixed points, where it starts (the top of the show, or What's on's
theme) and where its theme lands (just after the last word). Neither moves, so the bar length is
chosen to fit a whole number of bars between them, close to the bed's own tempo.

usage: PYTHONPATH=src RENDER=<render> python round-13.py <out-dir> <run dir, e.g. data/2026-10-24>
(the run dir is the run's episode-data artifact: script.json, briefing.json, concat.txt, segments/)
"""
import importlib.util, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round12", Path(__file__).parent / "round-12.py")
r12 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r12)
r11, r10 = r12.r11, r12.r10
KICK, CLOSED_HATS, OPEN_HAT, SHAKER, CROSS_STICK, BASS = r11.KICK, r11.CLOSED_HATS, r11.OPEN_HAT, r11.SHAKER, r11.CROSS_STICK, r11.BASS
EM9, CMAJ9, AM9, BM7, GMAJ9, D9SUS = r11.EM9, r11.CMAJ9, r11.AM9, r11.BM7, r11.GMAJ9, r11.D9SUS

LAND_AFTER, LEAD = r12.LAND_AFTER, r12.LEAD
STING_BARS = 2  # the sting's length; the hosts start after it
STING_UP = 4  # dB the sting plays above the bed's level between lines
SECTION_BEATS, SECTION_BEAT = 12, 0.28  # What's on's theme (round 10)

BEDS = dict(r11.BEDS, sombre=dict(
    beat=0.36,
    bars=[(EM9, [(0, "E1", 4)]), (CMAJ9, [(0, "C2", 4)]), (AM9, [(0, "A1", 4)]), (BM7, [(0, "B1", 4)])],
    kick=[(0, 0.35)], stick=[], comp=[(0, 4, 0.2)],
    hats="none", shaker=0, hook_every=4, hook=[(0, "B5", 2), (2, "G5", 2)], hook_level=0.28,
))
STINGS = {  # melody over the first bars, as (beat, note, beats), and those bars' chords
    "up-first": dict(melody=[(0, "D5", 0.5), (0.5, "F#5", 0.5), (1, "G5", 0.5), (1.5, "A5", 2.5)], chords=[GMAJ9, D9SUS]),
    "sombre": dict(melody=[(0, "B4", 1), (1, "D5", 1), (2, "E5", 4)], chords=[CMAJ9, EM9]),
}
# the sombre day's theme after the hello, in place of the intro theme: falling, ending open on Em9
r11.BUTTONS["sombre-intro"] = dict(
    beat=0.36, beats=8, glint=0.3,
    melody=[(0, "E5", 1), (1, "D5", 0.5), (1.5, "B4", 2.5), (4, "A4", 1), (5, "B4", 3)],
    chords=[(0, CMAJ9), (1.5, EM9), (4, D9SUS), (5, EM9)],
    bass=[(0, "C2", 1.5), (1.5, "E1", 2.5), (4, "D2", 1), (5, "E1", 3)],
    kick=[(0, 0.4), (5, 0.3)], hats=(0, 0), shaker=(0, 0), end_hat=None,
)


def bed(name, n, bar, sting=None, first=None):
    """`n` bars of bed at `bar` seconds a bar, counted back from the end so the last bar is the loop's
    last chord. `sting` plays its melody over the first bars; `first` replaces bar 0's chord."""
    b = BEDS[name]
    beat = bar / 4
    events = []
    for i in range(n):
        left, at = n - i, i * bar
        chord, bass = b["bars"][(i - n) % len(b["bars"])]
        if sting and i < len(sting["chords"]):
            chord = sting["chords"][i]
            bass = [(0, BASS_ROOT[tuple(chord)], 4)]
        elif i == 0 and first:
            chord, bass = first
        for k, v in b["kick"]:
            events.append((at + k * beat, filt(KICK, hi=800) * v))
        for k, v in b["stick"]:
            events.append((at + k * beat, pan(filt(CROSS_STICK[(i + int(k)) % 4], lo=900) * v, -0.2)))
        if b["hats"] == "eighths" or (b["hats"] == "offbeats" and left <= b.get("hats_from", 99)):
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
            events += r11.rhodes_chord(chord, at + k * beat, beats * beat - 0.05, vel)
        for k, note in enumerate(b.get("figure", [])):
            events.append((at + k * beat / 2, pan(RHODES.note(note, hold=beat / 2, release=0.3, vel=0.3), 0.25)))
        if left <= 8 and left % b["hook_every"] == 0 and not (sting and i < len(sting["chords"])):
            for j, (k, note, beats) in enumerate(b["hook"]):
                events.append((at + k * beat, pan(r11.glint(note, b.get("hook_level", 0.42)), (0.4, 0.25)[j % 2])))
    if sting:
        events.append((0, pan(filt(OPEN_HAT, lo=3000) * 0.12, 0.3)))
        for j, (k, note, beats) in enumerate(sting["melody"]):
            events.append((k * beat, pan(RHODES.note(note, hold=beats * beat + 0.05, release=0.6, vel=0.62), -0.15)))
            events.append((k * beat, pan(r11.glint(r11.up12(note), 0.45), (0.45, 0.3)[j % 2])))
    swish = (OPEN_HAT[::-1] * np.linspace(0, 1, len(OPEN_HAT))[:, None] ** 3)[-int(0.6 * SR):]
    events.append((n * bar - 0.6, filt(swish, lo=2500) * 0.25))
    y = place(events)[: int((n * bar + 0.1) * SR)]
    return filt(fade(y, 0.15), lo=40, hi=10000)


BASS_ROOT = {tuple(GMAJ9): "G1", tuple(D9SUS): "D2", tuple(CMAJ9): "C2", tuple(EM9): "E1"}


def fit(span, bar):
    """Bars and bar length for `span` seconds, as near `bar` as a whole number of bars allows."""
    n = max(1, round(span / bar))
    return n, span / n


def themed(sig):
    """A theme levelled as the episode levels cues, keeping its lead-in so the downbeat stays at LEAD."""
    s = ring_out(reverb(sig / np.abs(sig).max(), 0.16), longest=6.5)
    s = s * 10 ** ((VOICE_DB - 7 - level(s)) / 20)
    return s * min(1, 10 ** (-9 / 20) / np.abs(s).max())


def bed_level(music, voice_track, sting_end=None):
    """The bed set to the voices and ducked under them; the sting louder until the hosts start."""
    music = reverb(music, 0.12)[: len(music)]
    music *= 10 ** ((VOICE_DB - level(music)) / 20)
    track = np.concatenate([voice_track, secs(max(0, (len(music) - len(voice_track)) / SR))])[: len(music)]
    music = r11.duck(music, track)
    if sting_end:
        up = np.full(len(music), 1.0)
        e = int(sting_end * SR)
        r = int(0.5 * SR)
        up[:e - r] = 10 ** (STING_UP / 20)
        up[e - r:e] = 10 ** (np.linspace(STING_UP, 0, r) / 20)
        music *= up[:, None]
    return music


def stereo(x):
    return np.stack([x, x], axis=1).astype(np.float64)


def load_run(d):
    from nlnews import chapters, cues
    from nlnews.models import Briefing, EpisodeScript
    script = EpisodeScript.model_validate_json((d / "script.json").read_text())
    briefing = Briefing.model_validate_json((d / "briefing.json").read_text())
    for w in (d / "segments").glob("*.words.json"):  # an artifact keeps no mtimes; the transcripts are current
        w.touch()
    _, _, starts = chapters.find(script, d)
    placed = cues.plan(script.segments, briefing.stories, starts)
    voice = cues._decode("-f", "concat", "-safe", "0", "-i", str(listing(d)))
    voice_db = cues._loud_db(voice)
    cuts = {name: cues._cut(voice, t, voice_db) / cues.RATE for t, name in placed if t != float("inf")}
    voice = stereo(voice)
    return voice * 10 ** ((VOICE_DB - level(voice)) / 20), cuts


def listing(d):
    from nlnews.chapters import segment_files
    p = d / "concat.local.txt"
    p.write_text("".join(f"file '{f.resolve()}'\n" for f in segment_files(d)))
    return p


def opening(voice, cut, bed_name, theme, follow=9.0):
    """Sting, the cold open over the bed, the theme LAND_AFTER its last word, then `follow` seconds
    of the first story with the theme's ring-out under its first words."""
    cold = voice[: int(cut * SR)]
    words = r12.last_word(cold) + LAND_AFTER
    b = BEDS[bed_name]
    n, bar = fit(words, 4 * b["beat"])  # the bars under the hosts; the sting adds its own
    n += STING_BARS
    start = STING_BARS * bar
    music = bed(bed_name, n, bar, sting=STINGS[bed_name])
    music = bed_level(music, np.concatenate([secs(start), cold]), sting_end=start)
    land = n * bar
    theme_at = land - LEAD
    story = voice[int(cut * SR): int((cut + follow) * SR)]
    print(f"  {bed_name}: {n} bars of {bar:.3f} s (its own {4 * b['beat']:.3f}), theme lands {land - start - r12.last_word(cold):.2f} s after the last word")
    return place([(start, cold), (0, music), (theme_at, theme), (theme_at + len(theme) / SR - 0.6, fade(story, 1.0))])


def closing(voice, cut, button, before=6.0):
    """The end of the last story, What's on's theme straight into the between bed, the rest of the
    show over it, and the button LAND_AFTER the sign-off's last word."""
    section = themed(r10.theme("section"))
    tail = voice[int(cut * SR):]
    out_cut = before
    sec_at = out_cut + 0.25  # cues.BEFORE
    resume = sec_at + len(section) / SR - 0.6  # cues.UNDER_NEXT
    bed_from = sec_at + LEAD + SECTION_BEATS * SECTION_BEAT  # What's on's theme's last bar line
    land = resume + r12.last_word(tail) + LAND_AFTER
    n, bar = fit(land - bed_from, 4 * SECTION_BEAT)
    print(f"  outro: {n} bars of {bar:.3f} s (What's on's theme: {4 * SECTION_BEAT:.3f}), {land - bed_from:.1f} s of bed")
    music = bed("between", n, bar, first=(GMAJ9, [(0, "G1", 2.5), (2.5, "D2", 1.5)]))
    voice_track = np.concatenate([secs(resume - bed_from), tail])
    music = bed_level(music, voice_track)
    return place([(0, voice[int((cut - before) * SR): int(cut * SR)]), (sec_at, section), (resume, tail),
                  (bed_from, music), (land - LEAD, button)])


if __name__ == "__main__":
    out, run = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    voice, cuts = load_run(run)
    print("  cuts:", {k: round(v, 2) for k, v in cuts.items()})
    intro_cut = next(t for name, t in cuts.items() if name == "intro")
    write(out / "intro - sting, up-first bed, intro theme.mp3",
          np.concatenate([opening(voice, intro_cut, "up-first", themed(r10.theme("intro"))), secs(0.5)]))
    write(out / "sombre intro - sting, bed, sombre theme.mp3",
          np.concatenate([opening(voice, intro_cut, "sombre", themed(r11.button("sombre-intro"))), secs(0.5)]))
    write(out / "outro - What's on theme into the between bed, button anthem-b.mp3",
          np.concatenate([closing(voice, cuts["section"], themed(r11.button("anthem-b"))), secs(0.5)]))
