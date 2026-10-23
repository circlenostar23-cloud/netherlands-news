"""Round 6: four new families on Wilhelmus fragments (Valerius 1626, in G). No shared lead-in:
every cue starts straight on its own melody, and the six cues use five different fragments.

hard-1   "Wil-hel"            D G          (line 1)
hard-2   "...je heb ik"        G F# D       (line 4)
light-1  "Prin-ce van"         D E D        (line 3)
light-2  "al-tijd ge-"         E F# G       (line 4)
section  "Een prin-ce van O-ran-je"  D E D C B  (line 3)
button   "ge-eerd"             F# G         (the anthem's last two notes)
"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synth import SR, VOICE_DB, lowpass, partials, place, reverb, rng, t

OUT = Path(sys.argv[1])


def note(n, shift=0):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    return 440 * 2 ** ((names[n[0]] + (1 if "#" in n else 0) + 12 * (int(n[-1]) + shift - 4)) / 12)


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def shape(n, attack, release):
    x = np.arange(n) / SR
    return np.minimum(x / attack, 1) * np.minimum((n / SR - x) / release, 1)


# --- instruments: f in Hz, dur in seconds held -------------------------------------------

def lute(f, dur, level=1.0):
    """Plucked gut string (Karplus-Strong) with a little body warmth: the instrument of the 1570s."""
    p, n = int(SR / f), int(max(dur, 0.6) * SR + 0.8 * SR)
    buf = lowpass(rng.standard_normal(p), 4500)
    out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.994 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    body = lowpass(out, 400) * 0.8
    return lowpass(out + body, 3200) * 3 * level


def organ(f, dur, level=1.0):
    """A soft flute stop with breath at the start and a gentle tremulant: Sweelinck's Oude Kerk."""
    n = int((dur + 0.2) * SR)
    x = np.arange(n) / SR
    tone = np.sin(2 * np.pi * f * x) + 0.25 * np.sin(4 * np.pi * f * x) + 0.06 * np.sin(6 * np.pi * f * x)
    chiff = lowpass(rng.standard_normal(n), 3000) * np.exp(-x / 0.03) * 0.15
    trem = 1 - 0.12 * (0.5 + 0.5 * np.sin(2 * np.pi * 4.8 * x))
    return (tone * trem + chiff) * shape(n, 0.06, 0.18) * 0.5 * level


def cello(f, dur, level=1.0):
    """A bowed low string: slow bow, vibrato that blooms after the attack."""
    n = int((dur + 0.35) * SR)
    x = np.arange(n) / SR
    vib = 1 + 0.004 * np.sin(2 * np.pi * 5.3 * x) * np.minimum(x / 0.4, 1)
    phase = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = sum(np.sin(k * phase) / k ** 1.1 for k in range(1, int(5000 / f)))
    bow = lowpass(rng.standard_normal(n), 2500) * 0.04
    return lowpass(tone + bow, 2400) * shape(n, 0.16, 0.35) * 0.4 * level


def music_box(f, dur, level=1.0):
    return partials(f, max(dur, 0.4) + 1.0, [(1, 1, 0.7), (3.0, 0.15, 0.12), (5.4, 0.05, 0.04)], 0.001) * level


def radio(sig, dur):
    """An old shortwave set: band-limited, a slow wow, static under it and a short tuning whistle."""
    n = len(sig)
    x = np.arange(n) / SR
    sig = highpass(lowpass(sig, 2800), 350) * (1 - 0.15 * (0.5 + 0.5 * np.sin(2 * np.pi * 3.1 * x)))
    static = highpass(lowpass(rng.standard_normal(n), 4000), 600) * 0.05 * shape(n, 0.05, 0.4)
    whistle_n = int(0.35 * SR)
    wx = np.arange(whistle_n) / SR
    whistle = np.sin(2 * np.pi * np.cumsum(np.linspace(1900, 600, whistle_n)) / SR) * np.exp(-wx / 0.15) * 0.12
    out = sig + static
    out[:whistle_n] += whistle
    return out


# --- fragments, as (note, beats) ---------------------------------------------------------

FRAGMENTS = {
    "hard-1": [("D4", 1), ("G4", 2)],
    "hard-2": [("G4", 1), ("F#4", 1), ("D4", 2)],
    "light-1": [("D5", 1.5), ("E5", 0.5), ("D5", 2)],
    "light-2": [("E5", 0.5), ("F#5", 0.5), ("G5", 2)],
    "section": [("D5", 1.5), ("E5", 0.5), ("D5", 1.5), ("C5", 0.5), ("B4", 2.5)],
    "button": [("F#4", 1), ("G4", 3)],
}
BASS = {"hard-1": "E2", "hard-2": "D2", "light-1": "G2", "light-2": "C3", "section": "G2", "button": "G2"}  # one low note under each


def render(inst, frag, beat, shift, bass=True, bass_level=0.45):
    events, at = [], 0.0
    notes = FRAGMENTS[frag]
    for i, (n, beats) in enumerate(notes):
        hold = beats * beat * (1.0 if i < len(notes) - 1 else 1.4)
        events.append((at, inst(note(n, shift), hold, 0.85 if i < len(notes) - 1 else 1.0)))
        at += beats * beat
    if bass:
        events.append((0, inst(note(BASS[frag], shift), at + beat, bass_level)))
    return place(events)


FAMILIES = {
    "1-lute (the melody's own era, 1570s)": lambda f: render(lute, f, 0.36, 0, bass_level=0.5),
    "2-church organ, soft flute stop": lambda f: render(organ, f, 0.36, 0, bass_level=0.35),
    "3-bowed cello, low and legato": lambda f: render(cello, f, 0.4, -1, bass=f in ("section", "button"), bass_level=0.4),
    "4-shortwave radio (an old interval signal)": lambda f: radio(np.concatenate([np.zeros(int(0.25 * SR)), render(music_box, f, 0.32, 1, bass=False)]), 0),
}


def level(s):
    loud = s[np.abs(s) > 0.01 * np.max(np.abs(s))]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def finish(s, wet=0.18):
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
plan = [("student loans", "hard"), ("Hajar case", "hard"), ("Cairo embassy", "hard"), ("Schiphol", "hard"),
        ("fake pills", "hard"), ("slavery museum", "hard"), ("football", "light"), ("Airbnb", "light"),
        ("Euromast", "light"), ("What's on", "section"), ("That's it for today.", "button")]
voices = {}
for label, _ in plan:
    tmp = OUT / "_say.aiff"
    OUT.mkdir(parents=True, exist_ok=True)
    subprocess.run(["say", "-v", "Samantha", "-o", str(tmp), label], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.int16) / 32768
    voices[label] = v * 10 ** ((VOICE_DB - level(v)) / 20)
    tmp.unlink()

for fam, make in FAMILIES.items():
    made = {}
    for frag in FRAGMENTS:
        made[frag] = finish(make(frag))
        write(OUT / fam / f"{frag}.mp3", np.concatenate([gap(0.3), made[frag], gap(0.5)]))
        print(f"{fam} {frag}: {len(made[frag]) / SR:.1f}s")
    write(OUT / f"{fam} - six cues.mp3", np.concatenate([gap(0.3)] + [x for s in made.values() for x in (s, gap(1.2))]))
    seen, reel = {}, [gap(0.3)]
    for label, kind in plan:
        pool = [k for k in made if k.startswith(kind)]
        cue = made[pool[seen.get(kind, 0) % len(pool)]]
        seen[kind] = seen.get(kind, 0) + 1
        reel += [voices[label], gap(0.4), cue] if kind == "button" else [cue, gap(0.3), voices[label], gap(1.5)]
    write(OUT / f"{fam} - rotation demo.mp3", np.concatenate(reel + [gap(0.5)]))
