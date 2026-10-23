"""Round 5: news-ticker cues (woodblock ticks into a soft tone) on slow, short fragments from
across the Wilhelmus (Valerius 1626, in G). At most three pitched notes per story cue, unhurried.

Line 1  d | g g a-b c-a b a-b c b | a-g a g.     Wil-hel-mus van Nas-sou-we ... van Duit-schen bloed
Line 3  b-c | d. e d. c | b a-b c b a g | a.    Een prin-ce van O-ran-je ben ik, vrij on-ver-veerd
Line 4  d | g-f# g a b a. g | f# d e-f# g g f# g.  De ko-ning van His-pan-je heb ik al-tijd ge-eerd
"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synth import SR, VOICE_DB, lowpass, partials, place, reverb

OUT = Path(sys.argv[1])
TICK = 0.15  # seconds between ticks
BEAT = 0.34  # seconds per quarter note in the tones: slow on purpose


def note(n):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    return 440 * 2 ** ((names[n[0]] + (1 if "#" in n else 0) + 12 * (int(n[-1]) - 4)) / 12)


def woodblock(level=1.0, f=880):
    return partials(f, 0.15, [(1, 1, 0.035), (2.7, 0.4, 0.015)], 0.0005) * level


def tone(n, level=1.0, decay=0.4):
    return partials(note(n), 1.6, [(1, 0.5, decay), (2, 0.1, decay / 2.5), (3, 0.03, decay / 5)], 0.004) * level


def low(n, level=0.35):  # a soft low note under the tones, for colour
    return lowpass(partials(note(n), 1.8, [(1, 1, 0.7), (2, 0.3, 0.3)], 0.02), 600) * level


def cue(ticks, tones, under=(), soft=False):
    """ticks: 'x.x' at TICK spacing; tones: [(note, beats)], starting one tick after the last tick."""
    events = [(i * TICK, woodblock(0.7 if soft else (1 if i == 0 else 0.6))) for i, c in enumerate(ticks) if c == "x"]
    at = len(ticks) * TICK
    start = at
    for i, (n, beats) in enumerate(tones):
        events.append((at, tone(n, 1.0 if i == len(tones) - 1 else 0.85, 0.5 if i == len(tones) - 1 else 0.35)))
        at += beats * BEAT
    events += [(start + s, u) for s, u in under]
    return place(events)


CUES = {
    # before a serious story: two or three falling or bare notes, a soft low E or D underneath
    "hard-1 'Wil-hel' (D up to G, line 1)": lambda: cue("x.x", [("D4", 1), ("G4", 2)], [(0, low("E2"))], soft=True),
    "hard-2 'heb ik' (G F# D, line 4)": lambda: cue("x.x", [("G4", 1), ("F#4", 1), ("D4", 2)], [(0, low("D2"))], soft=True),
    "hard-3 'Duit-schen bloed' (A to G, line 1)": lambda: cue("x.x", [("A4", 1), ("G4", 2)], [(0, low("E2"))], soft=True),
    # before a light story: a little higher, the ticks a touch busier
    "light-1 'Prin-ce van' (D E D, line 3)": lambda: cue("xx.x", [("D5", 1.5), ("E5", 0.5), ("D5", 1.5)]),
    "light-2 'Wil-hel-mus' (D G G, line 1)": lambda: cue("xx.x", [("D5", 1), ("G5", 1), ("G5", 1.5)]),
    "light-3 'van Nas-sou' (B C B, line 1)": lambda: cue("xx.x", [("B4", 1), ("C5", 1), ("B4", 1.5)]),
    # opening What's on: the 'O-ran-je' line, the only fully recognisable phrase
    "section 'Een prin-ce van O-ran-je' (line 3)": lambda: cue("x.xx.x.x", [("D5", 1.5), ("E5", 0.5), ("D5", 1.5), ("C5", 0.5), ("B4", 2)], [(0, low("G2", 0.25))]),
    # after the sign-off: the anthem's own ending, resolving home to G
    "button 'ge-eerd' (F# to G, the anthem's last notes)": lambda: cue("xx.x", [("F#4", 1), ("G4", 3)], [(BEAT, low("G2", 0.4))]),
}


def level(s):
    loud = s[np.abs(s) > 0.01 * np.max(np.abs(s))]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def finish(s):
    s = reverb(s / np.max(np.abs(s)), 0.15)
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
made = {}
for name, fn in CUES.items():
    made[name] = finish(fn())
    write(OUT / "cues" / f"{name}.mp3", np.concatenate([gap(0.3), made[name], gap(0.5)]))
    print(f"{name}: {len(made[name]) / SR:.1f}s")

write(OUT / "1-all eight cues.mp3", np.concatenate([x for s in made.values() for x in (s, gap(1.3))]))

# today's breaks in order: cue by the next story's kind, rotating within each group; `say` stands in for the hosts
plan = [("student loans", "hard"), ("Hajar case", "hard"), ("Cairo embassy", "hard"), ("Schiphol", "hard"),
        ("fake pills", "hard"), ("slavery museum", "hard"), ("football", "light"), ("Airbnb", "light"),
        ("Euromast", "light"), ("What's on", "section"), ("That's it for today.", "button")]
seen, reel, tmp = {}, [gap(0.3)], OUT / "_say.aiff"
for label, kind in plan:
    pool = [k for k in made if k.startswith(kind)]
    name = pool[seen.get(kind, 0) % len(pool)]
    seen[kind] = seen.get(kind, 0) + 1
    subprocess.run(["say", "-v", "Samantha", "-o", str(tmp), label], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.int16) / 32768
    voice = voice * 10 ** ((VOICE_DB - level(voice)) / 20)
    reel += [voice, gap(0.4), made[name]] if kind == "button" else [made[name], gap(0.4), voice, gap(1.5)]
tmp.unlink()
write(OUT / "2-rotation demo (today's breaks in order).mp3", np.concatenate(reel + [gap(0.5)]))
