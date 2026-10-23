"""Round 2: variation families built on the marimba and pulse, a hybrid of the two, new timbres,
section-level cues, and a demo of a rotation across one episode's breaks. All in D major."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
OUT = None
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


