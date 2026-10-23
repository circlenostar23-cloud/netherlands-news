"""Shared by rounds 7 and up: Logic Pro's recorded instruments, stereo production, and the demo reel.

Every note is a recording: Logic's sampler instruments (flute, clarinet, strings, horn) rendered
offline through macOS's AVAudioUnitSampler (render.swift), and Logic's Alchemy samples (bells, Rhodes,
pads, sung vowels) pitched from the nearest recorded note. Numpy only does the production.

Needs Logic Pro's sound library (/Library/Application Support/Logic), ffmpeg, numpy, and render.swift
compiled (swiftc -O docs/transition-sounds/render.swift -o <dir>/render) with RENDER set to its path.
"""
import json, os, re, subprocess, tempfile, wave
from pathlib import Path
import numpy as np

SR = 44100
VOICE_DB = -16.7  # speech level measured in ep-2026-10-23
RENDER = os.environ.get("RENDER", "render")  # the compiled render.swift
LOGIC = Path("/Library/Application Support/Logic")
EXS = LOGIC / "Sampler Instruments/09 Orchestral"
ALCHEMY = LOGIC / "Alchemy Samples"
rng = np.random.default_rng(7)

NAMES = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(n):
    m = re.fullmatch(r"([A-G])(#?)(-?\d)", n)
    return 12 * (int(m[3]) + 1) + NAMES[m[1]] + (1 if m[2] else 0)


def secs(s):
    return np.zeros((int(s * SR), 2))


def load(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)


def place(events):
    """events: (start_s, stereo signal) -> one stereo signal."""
    end = max(int(s * SR) + len(x) for s, x in events)
    out = np.zeros((end, 2))
    for s, x in events:
        i = int(s * SR)
        out[i:i + len(x)] += x
    return out


def pan(x, p):
    """p from -1 (left) to 1 (right), equal power."""
    a = (p + 1) * np.pi / 4
    return x * np.array([np.cos(a), np.sin(a)]) * np.sqrt(2)


def filt(x, lo=None, hi=None):
    """Gentle (2nd-order-shaped) low/high-pass in the frequency domain."""
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if hi:
        g /= np.sqrt(1 + (f / hi) ** 4)
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1)) ** 4)
    return np.fft.irfft(np.fft.rfft(x, axis=0) * g[:, None], len(x), axis=0)


def conv(x, ir):
    n = len(x) + len(ir)
    return np.fft.irfft(np.fft.rfft(x, n, axis=0) * np.fft.rfft(ir, n, axis=0), n, axis=0)


def room(length=2.2, decay=0.55, bright=5000):
    """A stereo hall: decorrelated noise per side, darkening as it decays, 18 ms pre-delay."""
    n = int(length * SR)
    x = np.arange(n) / SR
    ir = rng.standard_normal((n, 2)) * np.exp(-x / decay)[:, None]
    ir = filt(ir, lo=150, hi=bright) * 0.5 + filt(ir, hi=bright / 3) * np.linspace(0.2, 1, n)[:, None]
    ir = np.concatenate([np.zeros((int(0.018 * SR), 2)), ir])
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


HALL = room()
PLATE = room(1.4, 0.35, 7000)


def reverb(x, wet=0.25, ir=HALL):
    tail = conv(x, ir)
    return np.concatenate([x, np.zeros((len(tail) - len(x), 2))]) * (1 - wet) + tail * wet


def inhale(note_sig, length=0.55):
    """A reversed reverb tail of the first note: the sound breathes in to it."""
    tail = conv(note_sig[: int(0.4 * SR)], HALL)[: int(length * SR)][::-1]
    return tail * np.linspace(0, 1, len(tail))[:, None] ** 1.5 * 0.5


def pingpong(x, delay, repeats=4, feedback=0.42):
    events = [(0, x)]
    for k in range(1, repeats + 1):
        events.append((k * delay, pan(filt(x, lo=300, hi=6000 - 900 * k), -0.85 if k % 2 else 0.85) * feedback ** k))
    return place(events)


def wow(x, depth=0.0018, rate=0.55):
    """Tape wow: a slow wobble in playback speed."""
    t = np.arange(len(x)) / SR
    read = (t + depth / (2 * np.pi * rate) * np.sin(2 * np.pi * rate * t)) * SR
    return np.stack([np.interp(read, np.arange(len(x)), x[:, c]) for c in range(2)], axis=1)


def fade(x, release):
    n = min(len(x), int(release * SR))
    x = x.copy()
    x[-n:] *= np.linspace(1, 0, n)[:, None] ** 2
    return x


# --- sample banks: Alchemy single-note recordings, pitched from the nearest root ---------------

class Bank:
    def __init__(self, folder, pattern="*.wav", octave=1, cents=0.0):
        """octave: Logic names samples with C3 as middle C, one octave below the usual C4.
        cents: how far the recording is from concert pitch."""
        self.roots, self.offset = {}, 12 * octave + cents / 100
        for p in sorted(Path(folder).glob(pattern)):
            m = re.search(r"([A-G]#?\d)\.wav$", p.name)
            if m:
                self.roots.setdefault(midi(m[1]) + self.offset, p)
        self.cache = {}

    def note(self, n, hold=None, release=0.35, vel=1.0):
        m = midi(n) if isinstance(n, str) else n
        root = min(self.roots, key=lambda r: (abs(r - m), r < m))  # prefer pitching down
        if root not in self.cache:
            self.cache[root] = load(self.roots[root])
        src = self.cache[root]
        ratio = 2 ** ((m - root) / 12)
        idx = np.arange(0, len(src) - 1, ratio)
        x = np.stack([np.interp(idx, np.arange(len(src)), src[:, c]) for c in range(2)], axis=1)
        if hold is not None:
            x = fade(x[: int((hold + release) * SR)], release)
        return x * vel


BELLS = Bank(ALCHEMY / "Mallets/Metal Mallets/Bell Attack Pad", octave=0, cents=-42)  # measured
RHODES = Bank(ALCHEMY / "Keys/Electric Pianos/EPiano Mrk II")
SKY = Bank(ALCHEMY / "Pads/Digital/Beautiful Sky")
AMANDA = Bank(ALCHEMY / "Vocals/Solo Vocals/Sustain/Amanda Sustain/Amanda Aa", "Amanda Aa 1 *.wav")
TOM = Bank(ALCHEMY / "Vocals/Solo Vocals/Sustain/Tom Sustain/Solo Tom Oh")
BELL_TREE = load(ALCHEMY / "Soundscapes/Single Samples/The Bell Tree.wav")


def exs(instrument, notes, seconds):
    """notes: (start_s, note, dur_s, velocity 1-127), rendered through the macOS sampler."""
    with tempfile.TemporaryDirectory() as d:
        score = Path(d) / "s.json"
        score.write_text(json.dumps({"instrument": str(instrument), "seconds": seconds,
                                     "notes": [[s, midi(n), dur, v] for s, n, dur, v in notes]}))
        subprocess.run([RENDER, str(score), f"{d}/o.wav"], check=True, capture_output=True)
        return load(f"{d}/o.wav")


FLUTE = EXS / "01 Woodwinds/Flute Solo+.exs"
CLARINET = EXS / "01 Woodwinds/Clarinet Solo+.exs"
STRINGS = EXS / "09 Strings/String Ensemble.exs"
HORN = EXS / "02 Brass/French Horn Solo+.exs"


def level(s):
    m = np.abs(s).max(axis=1)
    loud = s[m > 0.01 * m.max()]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def trim(y, floor_db=-55):
    m = np.abs(y).max(axis=1)
    idx = np.nonzero(m > m.max() * 10 ** (floor_db / 20))[0]
    return fade(y[idx[0]: idx[-1] + 1], 0.15)


def ring_out(s, floor_db=-32, longest=3.6):
    """Cut the tail where it has faded well under the voices (or at `longest` seconds)."""
    m = np.abs(s).max(axis=1)
    win = int(0.05 * SR)
    env = np.sqrt(np.convolve(m ** 2, np.ones(win) / win, mode="same"))
    loud = np.nonzero(env > env.max() * 10 ** (floor_db / 20))[0]
    return fade(s[: min(loud[-1] + win, int(longest * SR))], 0.5)


def finish(s, wet, longest):
    s = ring_out(trim(reverb(s / np.abs(s).max(), wet)), longest=longest)
    s = s * 10 ** ((VOICE_DB - 7 - level(s)) / 20)
    return s * min(1, 10 ** (-9 / 20) / np.abs(s).max())


def write(path, y):
    path.parent.mkdir(parents=True, exist_ok=True)
    wav = path.with_suffix(".wav")
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(2), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-b:a", "160k", str(path)], check=True)
    wav.unlink()


# The demo episode: each cue plays once, before the story it introduces; the button follows the sign-off.
# Stories alternate hard and light so neighbouring cues can be compared. A cue type a family doesn't
# have (round 9 has no intro) is skipped.
REEL = [("say", "Good morning. It's Friday, and this is the news from the Netherlands."), ("cue", "intro"),
        ("say", "student loans"), ("cue", "hard"), ("say", "Hajar case"), ("cue", "light"), ("say", "football"),
        ("cue", "hard"), ("say", "Cairo embassy"), ("cue", "light"), ("say", "Airbnb"), ("cue", "hard"),
        ("say", "fake pills"), ("cue", "light"), ("say", "Euromast"), ("cue", "section"), ("say", "What's on"),
        ("say", "That's it for today."), ("cue", "button")]
THEMES = ("intro", "section", "button")


def longest_default(frag):
    return 4.8 if frag == "section" else 3.6


def demo(out, families, fragments, only=(), prefix="", longest=longest_default):
    """Render each family's cues (one file per cue, named `prefix` + cue, or in a folder per family) and a demo episode over REEL.
    families: {name: (make(frag) -> signal, reverb wet)}; only: family numbers to render."""
    out.mkdir(parents=True, exist_ok=True)
    spoken = {}
    for kind, text in REEL:
        if kind == "say":
            tmp = out / "_say.aiff"
            subprocess.run(["say", "-v", "Samantha", "-o", str(tmp), text], check=True)
            v = load(tmp)
            spoken[text] = v * 10 ** ((VOICE_DB - level(v)) / 20)
            tmp.unlink()
    for fam, (make, wet) in families.items():
        if only and fam.split("-")[0] not in only:
            continue
        made = {frag: finish(make(frag), wet, longest(frag)) for frag in fragments}
        tag = prefix or f"{fam}/"  # several families in one run each get a folder
        for frag, s in made.items():
            write(out / f"{tag}{frag}.mp3", np.concatenate([secs(0.3), s, secs(0.5)]))
            print(f"{tag}{frag}: {len(s) / SR:.1f}s")
        events, at, seen = [], 0.3, {}
        for kind, what in REEL:
            if kind == "say":
                events.append((at, spoken[what]))
                at += len(spoken[what]) / SR + 0.45
                continue
            pool = [k for k in made if k.startswith(what)]
            if not pool:
                continue
            cue = made[pool[seen.get(what, 0) % len(pool)]]
            seen[what] = seen.get(what, 0) + 1
            events.append((at, cue))
            # the ring-out runs under the next line, as it would in the episode
            at += len(cue) / SR - (0 if what == "button" else 0.6)
        write(out / f"{tag}demo episode.mp3", np.concatenate([place(events), secs(0.5)]))
