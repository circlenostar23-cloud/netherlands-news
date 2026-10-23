"""Round 2: variation families built on the marimba and pulse, a hybrid of the two, new timbres,
section-level cues, and a demo of a rotation across one episode's breaks. All in D major."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
OUT = Path(sys.argv[1])
rng = np.random.default_rng(11)
VOICE_DB = -16.7  # speech level measured in ep-2026-10-23


def t(sec):
    return np.arange(int(sec * SR)) / SR


def note(f):
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    n, acc, octv = f[0], f[1:-1], int(f[-1])
    return 440 * 2 ** ((names[n] + (1 if acc == "#" else -1 if acc == "b" else 0) + 12 * (octv - 4)) / 12)


def env(n, attack=0.004, decay=0.5):
    x = np.arange(n) / SR
    return np.minimum(x / attack, 1) * np.exp(-x / decay)


def partials(freq, dur, spec, attack=0.004):
    x = t(dur)
    out = np.zeros_like(x)
    for r, a, d in spec:
        out += a * np.sin(2 * np.pi * freq * r * x + rng.uniform(0, 6.28)) * env(len(x), attack, d)
    return out


def place(events, dur=None):
    end = max(s + len(sig) / SR for s, sig in events)
    out = np.zeros(int((dur or end) * SR) + 1)
    for start, sig in events:
        i = int(start * SR)
        n = min(len(sig), len(out) - i)
        out[i:i + n] += sig[:n]
    return out


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y, acc = np.zeros_like(x), 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def trim(y, floor_db=-50):
    idx = np.nonzero(np.abs(y) > np.max(np.abs(y)) * 10 ** (floor_db / 20))[0]
    y = y[: idx[-1] + 1].copy()
    fade = min(len(y), int(0.08 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def reverb(x, wet=0.15, length=1.2, decay=0.3):
    ir = rng.standard_normal(int(length * SR)) * np.exp(-t(length) / decay)
    ir = np.convolve(ir, np.ones(40) / 40, mode="same")
    ir /= np.sqrt(np.sum(ir ** 2))
    n = len(x) + len(ir)
    tail = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    return trim(np.concatenate([x, np.zeros(len(ir))]) * (1 - wet) + tail * wet)


# --- instruments: each takes a note name and returns one strike -----------------------

def marimba(n, soft=False):
    spec = [(1, 1, 0.3), (3.93, 0.08 if soft else 0.25, 0.06), (9.2, 0.0 if soft else 0.06, 0.02)]
    return partials(note(n), 1.0, spec, 0.006 if soft else 0.002)


def kalimba(n):
    s = partials(note(n), 1.4, [(1, 1, 0.55), (5.4, 0.18, 0.05), (2.0, 0.06, 0.2)], 0.001)
    s[:200] += rng.standard_normal(200) * np.linspace(0.3, 0, 200)  # tine click
    return s


def vibraphone(n):
    x = t(2.0)
    return partials(note(n), 2.0, [(1, 1, 0.9), (4.0, 0.12, 0.25), (10.0, 0.03, 0.05)], 0.003) * (1 - 0.3 * (0.5 + 0.5 * np.sin(2 * np.pi * 5.5 * x)))


def epiano(n):
    f, x = note(n), t(1.8)
    index = 0.4 + 1.6 * np.exp(-x / 0.12)  # bright attack mellowing into a sine: Rhodes-ish FM
    tone = np.sin(2 * np.pi * f * x + index * np.sin(2 * np.pi * f * x))
    return tone * env(len(x), 0.004, 0.7) + partials(f, 1.8, [(14.0, 0.04, 0.03)])


def felt_piano(n):
    spec = [(k, 1 / k ** 1.6, 0.9 / k ** 0.6) for k in range(1, 7)]
    return lowpass(partials(note(n), 1.8, spec, 0.008), 2500)


def pluck(n, dur=1.0, damp=0.996):
    p = int(SR / note(n))
    buf = lowpass(rng.standard_normal(p), 3000)
    out = np.zeros(int(dur * SR))
    for i in range(len(out)):  # Karplus-Strong
        out[i] = buf[i % p]
        buf[i % p] = damp * 0.5 * (buf[i % p] + buf[(i + 1) % p])
    return lowpass(out, 2200)


def thump(dur=0.6, depth=1.0):
    x = t(dur)
    f = 70 + 40 * np.exp(-x / 0.05)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(x), 0.003, 0.18) * 0.9 * depth


def swell(dur=0.45, cutoff=1800):
    n = int(dur * SR)
    return lowpass(rng.standard_normal(n), cutoff) * np.linspace(0, 1, n) ** 2 * 0.5


def glint(n="A6", level=0.18):
    return partials(note(n), 1.0, [(1, level, 0.35), (2.01, level / 3.6, 0.15)])


def motif(inst, notes, step):
    return place([(i * step, inst(n)) for i, n in enumerate(notes)])


def pulse_with(*hits, swell_dur=0.45):
    """The pulse texture (air swell into a thump) with any hits laid on the downbeat."""
    return place([(0, swell(swell_dur)), (swell_dur, thump())] + [(swell_dur + s, h) for s, h in hits])


SOUNDS = {
    # marimba family: same mallet, same key, different shapes
    "a-marimba/1-rising (original)": lambda: motif(marimba, ["D5", "F#5", "A5"], 0.11),
    "a-marimba/2-falling": lambda: motif(marimba, ["A5", "F#5", "D5"], 0.11),
    "a-marimba/3-two-note": lambda: motif(marimba, ["D5", "A5"], 0.14),
    "a-marimba/4-four-note run": lambda: motif(marimba, ["D5", "E5", "F#5", "A5"], 0.09),
    "a-marimba/5-low soft mallets (for serious stories)": lambda: motif(lambda n: marimba(n, soft=True), ["D4", "A4"], 0.16),
    # pulse family: same thump-and-air texture, different tops
    "b-pulse/1-original": lambda: pulse_with((0, glint("A6"))),
    "b-pulse/2-two glints": lambda: pulse_with((0, glint("A6")), (0.12, glint("D7", 0.12))),
    "b-pulse/3-low glint": lambda: pulse_with((0, glint("D6", 0.22))),
    "b-pulse/4-air only, no thump": lambda: place([(0, swell(0.6, 2400)), (0.6, glint("F#6", 0.15))]),
    "b-pulse/5-short swell, tight": lambda: pulse_with((0, glint("A6")), swell_dur=0.22),
    # hybrid: the pulse's thump with the marimba's notes on top
    "c-hybrid/1-thump plus marimba rise": lambda: pulse_with((0, motif(marimba, ["D5", "F#5", "A5"], 0.11) * 0.8)),
    "c-hybrid/2-thump plus marimba two-note": lambda: pulse_with((0, motif(marimba, ["A5", "D5"], 0.14) * 0.8), swell_dur=0.3),
    "c-hybrid/3-thump plus soft low marimba": lambda: pulse_with((0, motif(lambda n: marimba(n, soft=True), ["D4", "A4"], 0.16))),
    # new timbres, same D-major cell
    "d-new/1-kalimba": lambda: motif(kalimba, ["D5", "F#5", "A5"], 0.12),
    "d-new/2-vibraphone": lambda: motif(vibraphone, ["D5", "A5"], 0.18),
    "d-new/3-electric piano chord": lambda: place([(0, epiano("D4")), (0.02, epiano("F#4")), (0.04, epiano("A4")), (0.06, epiano("E5") * 0.6)]),
    "d-new/4-felt piano": lambda: motif(felt_piano, ["A4", "D5"], 0.2),
    "d-new/5-muted guitar pluck": lambda: motif(pluck, ["D4", "A4", "D5"], 0.1),
}

# Section cues: longer members of the hybrid family, for the bigger structural moments
SECTIONS = {
    "e-sections/1-whats-on (longer phrase, opens the section)": lambda: pulse_with(
        (0, motif(marimba, ["D5", "F#5", "A5", "D6"], 0.13) * 0.8), (0.55, glint("F#6", 0.12)), (0.7, thump(depth=0.5)), swell_dur=0.55),
    "e-sections/2-sign-off button (resolves down)": lambda: place([(0, motif(marimba, ["A5", "F#5", "E5", "D5"], 0.13)), (0.39, thump(depth=0.6)), (0.39, motif(lambda n: marimba(n, soft=True), ["D4"], 0)), (0.39, glint("D6", 0.1))]),
}


def level(s):
    loud = s[np.abs(s) > 0.01 * np.max(np.abs(s))]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def finish(s, wet=0.15):
    s = reverb(s / np.max(np.abs(s)), wet)
    return s * 10 ** ((VOICE_DB - 7 - level(s)) / 20)


def write(path, y):
    path.parent.mkdir(parents=True, exist_ok=True)
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "128k", str(path)], check=True)
    wav.unlink()


pad = lambda s, a=0.3, b=0.5: np.concatenate([np.zeros(int(a * SR)), s, np.zeros(int(b * SR))])
made = {}
for name, fn in {**SOUNDS, **SECTIONS}.items():
    made[name] = finish(fn(), 0.2 if name.startswith("e-") else 0.15)
    write(OUT / f"{name}.mp3", pad(made[name]))
    print(f"{name}: {len(made[name]) / SR:.1f}s")

# Rotation demo: today's ten breaks in order, the cue chosen by the next story's kind and rotated
# so no two in a row repeat. Spoken labels stand in for the stories (macOS `say`).
plan = [("student loans", "hard"), ("Hajar case", "hard"), ("Cairo embassy", "hard"), ("Schiphol", "hard"),
        ("fake pills", "hard"), ("slavery museum", "hard"), ("football", "light"), ("Airbnb", "light"),
        ("Euromast", "light"), ("What's on", "section"), ("sign-off", "end")]
pools = {"hard": ["c-hybrid/3-thump plus soft low marimba", "a-marimba/5-low soft mallets (for serious stories)", "b-pulse/3-low glint"],
         "light": ["c-hybrid/1-thump plus marimba rise", "a-marimba/4-four-note run", "c-hybrid/2-thump plus marimba two-note"],
         "section": ["e-sections/1-whats-on (longer phrase, opens the section)"], "end": ["e-sections/2-sign-off button (resolves down)"]}
tmp = OUT / "_say.aiff"
reel, seen = [], {}
for label, kind in plan:
    cue = pools[kind][seen.get(kind, 0) % len(pools[kind])]
    seen[kind] = seen.get(kind, 0) + 1
    subprocess.run(["say", "-v", "Samantha", "-o", str(tmp), label], check=True)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(tmp), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    voice = np.frombuffer(raw, np.int16) / 32768
    voice *= 10 ** ((VOICE_DB - level(voice)) / 20)
    gap = np.zeros(int(0.4 * SR))
    reel += ([voice, gap, made[cue]] if kind == "end" else [made[cue], gap, voice, np.zeros(int(1.5 * SR))])
tmp.unlink()
write(OUT / "f-rotation demo (kind-aware, across one episode).mp3", pad(np.concatenate(reel)))
