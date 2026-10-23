"""Synthesize candidate story-transition stings and splice them into excerpts of a real episode."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
OUT = Path(sys.argv[1])
EP = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(7)


def t(sec):
    return np.arange(int(sec * SR)) / SR


def note(f):  # semitone name -> Hz
    names = {"C": -9, "D": -7, "E": -5, "F": -4, "G": -2, "A": 0, "B": 2}
    n, acc, octv = f[0], f[1:-1], int(f[-1])
    semis = names[n] + (1 if acc == "#" else -1 if acc == "b" else 0) + 12 * (octv - 4)
    return 440 * 2 ** (semis / 12)


def env(n, attack=0.004, decay=0.5):
    x = np.arange(n) / SR
    return np.minimum(x / attack, 1) * np.exp(-x / decay)


def partials(freq, dur, spec, attack=0.004):
    """spec: list of (ratio, amp, decay)."""
    x = t(dur)
    out = np.zeros_like(x)
    for r, a, d in spec:
        out += a * np.sin(2 * np.pi * freq * r * x + rng.uniform(0, 6.28)) * env(len(x), attack, d)
    return out


def place(events, dur):
    out = np.zeros(int(dur * SR))
    for start, sig in events:
        i = int(start * SR)
        n = min(len(sig), len(out) - i)
        out[i:i + n] += sig[:n]
    return out


def reverb(x, wet=0.18, length=1.2, decay=0.35):
    ir = rng.standard_normal(int(length * SR)) * np.exp(-t(length) / decay)
    ir = np.convolve(ir, np.ones(40) / 40, mode="same")  # darken the tail
    ir /= np.sqrt(np.sum(ir ** 2))
    n = len(x) + len(ir)
    tail = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)
    y = np.concatenate([x, np.zeros(len(ir))]) * (1 - wet) + tail * wet
    return trim(y)


def trim(y, floor=1e-3):
    idx = np.nonzero(np.abs(y) > floor * np.max(np.abs(y)) * 10)[0]
    y = y[: idx[-1] + 1]
    fade = min(len(y), int(0.08 * SR))
    y[-fade:] *= np.linspace(1, 0, fade)
    return y


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = 0.0
    for i, v in enumerate(x):  # one-pole; fine for short stings
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


# --- the candidates -------------------------------------------------------------------

def soft_chime():
    """Two soft bell tones a fifth apart: the neutral public-radio 'ding-dong'."""
    bell = [(1, 1, 0.7), (2.0, 0.25, 0.35), (2.76, 0.12, 0.2), (5.4, 0.05, 0.08)]
    return reverb(place([(0, partials(note("E5"), 1.6, bell)), (0.16, partials(note("B5"), 1.6, bell) * 0.8)], 1.8))


def carillon():
    """Three carillon-bell strikes (with the bell's minor-third partial) - a nod to Dutch church towers."""
    bell = [(0.5, 0.35, 1.2), (1, 1, 0.8), (1.19, 0.45, 0.6), (1.5, 0.2, 0.45), (2, 0.35, 0.4), (2.5, 0.08, 0.2), (3.0, 0.06, 0.12)]
    hits = [("G5", 0), ("E5", 0.22), ("C5", 0.44)]
    return reverb(place([(s, partials(note(n), 2.0, bell, 0.002) * (1 - 0.1 * k)) for k, (n, s) in enumerate(hits)], 2.4), wet=0.25)


def marimba():
    """Three rising marimba notes: warm, a little friendly, very short."""
    bar = [(1, 1, 0.28), (3.93, 0.25, 0.06), (9.2, 0.06, 0.02)]
    hits = [("D5", 0), ("F#5", 0.11), ("A5", 0.22)]
    return reverb(place([(s, partials(note(n), 0.9, bar, 0.002)) for n, s in hits], 1.2), wet=0.12)


def pulse():
    """Soft low thump, a filtered air swell and a single high glint: modern, music-free 'news' texture."""
    dur = 1.3
    x = t(dur)
    swell_n = int(0.45 * SR)
    noise = lowpass(rng.standard_normal(swell_n), 1800) * np.linspace(0, 1, swell_n) ** 2 * 0.5
    thump_f = 70 + 40 * np.exp(-x / 0.05)
    thump = np.sin(2 * np.pi * np.cumsum(thump_f) / SR) * env(len(x), 0.003, 0.18) * 0.9
    glint = partials(note("A6"), 1.0, [(1, 0.18, 0.35), (2.01, 0.05, 0.15)])
    return reverb(place([(0, noise), (0.45, thump), (0.45, glint)], dur), wet=0.2)


def tick():
    """One soft, short tone - the least you can do."""
    return reverb(partials(note("A5"), 0.7, [(1, 1, 0.25), (2, 0.15, 0.1)], 0.006), wet=0.15)


CANDIDATES = {"1-soft-chime": soft_chime, "2-carillon": carillon, "3-marimba": marimba, "4-pulse": pulse, "5-tick": tick}


def read_mp3(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path),
                          "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float64) / 32768


def write(path, y):
    y = np.clip(y, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SR)
        w.writeframes((y * 32767).astype(np.int16).tobytes())
    mp3 = path.with_suffix(".mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-b:a", "128k", str(mp3)], check=True)
    path.unlink()
    return mp3


def rms_db(y):
    loud = y[np.abs(y) > 0.01]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)) + 1e-9)


# voice level: speech in the middle of the episode
voice_db = rms_db(read_mp3(EP, 300, 60))
stings = {}
for name, fn in CANDIDATES.items():
    s = fn()
    s *= 10 ** ((voice_db - 7 - rms_db(s)) / 20)  # sit ~7 dB under the voices
    stings[name] = s
    write(OUT / f"sting-{name}.wav", np.concatenate([np.zeros(int(0.3 * SR)), s, np.zeros(int(0.5 * SR))]))

# (label, chapter start, silence start, silence end) - absolute seconds in the episode
breaks = [
    ("A-hard-to-hard (Cairo embassy -> Schiphol)", 354.0, 353.036, 354.323),
    ("B-hard-to-light (slavery museum -> football)", 575.9, 574.963, 575.921),
    ("C-into-whats-on (Euromast -> What's on)", 771.06, 770.109, 771.199),
]
PRE, POST, KEEP = 0.35, 0.45, 0.2  # silence before/after the sting; voice-pause edges kept from the original

for name, s in stings.items():
    reel = []
    for label, ch, s0, s1 in breaks:
        before = read_mp3(EP, ch - 12, 12 - (ch - s0) + KEEP)
        after = read_mp3(EP, s1 - KEEP, 9)
        clip = np.concatenate([before, np.zeros(int(PRE * SR)), s, np.zeros(int(POST * SR)), after])
        fade = int(0.3 * SR)
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
        reel += [clip, np.zeros(int(1.2 * SR))]
    write(OUT / f"in-context-{name}.wav", np.concatenate(reel))

# the same three breaks with no sting, for comparison
reel = []
for label, ch, s0, s1 in breaks:
    clip = read_mp3(EP, ch - 12, 21)
    fade = int(0.3 * SR)
    clip[:fade] *= np.linspace(0, 1, fade)
    clip[-fade:] *= np.linspace(1, 0, fade)
    reel += [clip, np.zeros(int(1.2 * SR))]
write(OUT / "in-context-0-as-today.wav", np.concatenate(reel))
print("voice", round(voice_db, 1), "dB;", sorted(p.name for p in OUT.iterdir()))
