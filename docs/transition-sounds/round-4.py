"""Round 4: a cue family built from fragments of the Wilhelmus (melody as in Valerius 1626, in G).

    d | g g a-b c-a b a-b c b | a-g a g.
    Wil-hel-mus van Nas-sou-we ben ik van Duit-schen bloed

hard    "Wil-hel"      D -> G, the bare rising fourth, low and slow over a soft E (minor colour)
light   "Wil-hel-mus van"  D G G A-B, quick, left open on B so it leans into the story
section "Wil-hel-mus van Nas-sou-we"  the first half-line, the only fully recognisable statement
button  "Duit-schen bloed"  B A-G A G., the cadence every line of the anthem ends on
"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synth import SR, VOICE_DB, lowpass, marimba, partials, place, reverb, rng, swell, t, thump

OUT = Path(sys.argv[1])


def note(n, shift=0):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    name, acc, octv = n[0], n[1:-1], int(n[-1]) + shift
    return 440 * 2 ** ((names[name] + (1 if acc == "#" else 0) + 12 * (octv - 4)) / 12)


# --- instruments, each taking a frequency ---------------------------------------------

def carillon(f, level=1.0):
    spec = [(0.5, 0.35, 1.2), (1, 1, 0.8), (1.19, 0.45, 0.6), (1.5, 0.2, 0.45), (2, 0.35, 0.4), (2.5, 0.08, 0.2), (3.0, 0.06, 0.12)]
    return partials(f, 2.2, spec, 0.002) * level


def handpan(f, level=1.0):
    out = 0
    for r, a, d in [(1, 1, 1.3), (2, 0.45, 0.8), (3, 0.2, 0.5)]:
        for beat in (0, 0.0015):
            out = out + partials(f * (1 + beat), 2.0, [(r, a / 2, d)], 0.01)
    return out * level


def celesta(f, level=1.0):
    s = partials(f, 1.6, [(1, 1, 0.6), (4, 0.3, 0.15), (2, 0.1, 0.3), (7.1, 0.04, 0.04)], 0.001)
    s[:120] += rng.standard_normal(120) * np.linspace(0.15, 0, 120)
    return s * level


def analog(f, level=1.0, decay=0.35):
    x, out = t(1.4), 0
    for k in range(1, int(9000 / f)):
        out = out + np.sin(2 * np.pi * f * k * x) / k * np.exp(-x / (decay / (1 + 0.5 * k)))
    return (out + 0.5 * np.sin(np.pi * f * x) * np.exp(-x / decay)) * np.minimum(x / 0.003, 1) * level


def mallet(f, level=1.0):  # the round-2 marimba, by frequency
    spec = [(1, 1, 0.3), (3.93, 0.25, 0.06), (9.2, 0.06, 0.02)]
    return partials(f, 1.0, spec, 0.002) * level


def soft_mallet(f, level=1.0):
    return partials(f, 1.2, [(1, 1, 0.35), (3.93, 0.08, 0.06)], 0.006) * level


def drone(f, dur, level=0.35):
    x = t(dur)
    shape = np.minimum(x / 0.3, 1) * np.minimum((dur - x) / 0.6, 1)
    return lowpass((np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * shape, 800) * level


# --- the four cues, as (note, beats) -------------------------------------------------

HARD = [("D4", 1), ("G4", 2)]
LIGHT = [("D4", 0.5), ("G4", 0.5), ("G4", 0.5), ("A4", 0.25), ("B4", 0.75)]
SECTION = [("D4", 1), ("G4", 1), ("G4", 1), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 1.5)]
BUTTON = [("B4", 1), ("A4", 0.5), ("G4", 0.5), ("A4", 1), ("G4", 2)]


def phrase(inst, notes, beat, shift=0, accent_first=True):
    events, at = [], 0.0
    for i, (n, beats) in enumerate(notes):
        events.append((at, inst(note(n, shift), 1.0 if (i == 0 and accent_first) or i == len(notes) - 1 else 0.8)))
        at += beats * beat
    return place(events), at


def family(inst, shift, beat, extra=None):
    """The four cues for one instrument; `extra` adds the instrument's own texture under each."""
    def cue(notes, b, sh, under=()):
        mel, length = phrase(inst, notes, b, sh)
        layers = [(0, mel)] + [(s, u) for s, u in under]
        return place(layers + (extra(length) if extra else []))
    return {
        "hard": lambda: cue(HARD, beat * 1.5, shift - 1, [(0, drone(note("E2", shift), 1.8))]),
        "light": lambda: cue(LIGHT, beat, shift),
        "section": lambda: cue(SECTION, beat * 1.1, shift),
        "button": lambda: cue(BUTTON, beat * 1.2, shift, [(beat * 1.2 * 3, inst(note("G3", shift), 0.6))]),
    }


def pulse_under(length):  # the round-2 pulse texture: an air swell into a thump on the first note
    return [(0, thump(depth=0.7))]


FAMILIES = {
    "1-carillon (Dutch church towers play the Wilhelmus)": family(carillon, 1, 0.2),
    "2-marimba with the pulse thump": family(mallet, 1, 0.13, pulse_under),
    "3-handpan": family(handpan, 0, 0.17),
    "4-celesta": family(celesta, 1, 0.14),
    "5-analog synth": family(analog, 0, 0.13),
    "6-soft felt mallets (the most understated)": family(soft_mallet, 0, 0.16),
}


def level(s):
    loud = s[np.abs(s) > 0.01 * np.max(np.abs(s))]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def finish(s, wet):
    s = reverb(s / np.max(np.abs(s)), wet)
    s = s * 10 ** ((VOICE_DB - 7 - level(s)) / 20)
    return s * min(1, 10 ** (-9 / 20) / np.max(np.abs(s)))


def write(path, y):
    path.parent.mkdir(parents=True, exist_ok=True)
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "128k", str(path)], check=True)
    wav.unlink()


gap = lambda s: np.zeros(int(s * SR))
for fam, roles in FAMILIES.items():
    reel = [gap(0.3)]
    for role, fn in roles.items():
        s = finish(fn(), 0.25 if fam.startswith("1-") else 0.18)
        write(OUT / fam / f"{role}.mp3", np.concatenate([gap(0.3), s, gap(0.5)]))
        reel += [s, gap(1.2)]
        print(f"{fam} {role}: {len(s) / SR:.1f}s")
    write(OUT / f"{fam}.mp3", np.concatenate(reel))

# the source, plainly: the first line of the anthem on a felt mallet, for reference
line1 = [("D4", 1), ("G4", 1), ("G4", 1), ("A4", 0.5), ("B4", 0.5), ("C5", 0.5), ("A4", 0.5), ("B4", 1),
         ("A4", 0.5), ("B4", 0.5), ("C5", 1), ("B4", 1), ("A4", 0.5), ("G4", 0.5), ("A4", 1), ("G4", 3)]
ref, _ = phrase(soft_mallet, line1, 0.42)
write(OUT / "0-reference - first line of the Wilhelmus.mp3", np.concatenate([gap(0.3), finish(ref, 0.15), gap(0.5)]))
