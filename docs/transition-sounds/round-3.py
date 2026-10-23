"""Round 3: seven new sound families, each with the four roles the show needs:
hard (before a serious story), light (before a light one), section (opens What's on) and button (after the sign-off)."""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from synth import SR, VOICE_DB, env, lowpass, motif, note, partials, place, pluck, reverb, rng, t, vibraphone

OUT = Path(sys.argv[1])


# --- instruments ----------------------------------------------------------------------

def celesta(n, level=1.0):
    s = partials(note(n), 1.6, [(1, 1, 0.6), (4, 0.3, 0.15), (2, 0.1, 0.3), (7.1, 0.04, 0.04)], 0.001)
    s[:120] += rng.standard_normal(120) * np.linspace(0.15, 0, 120)
    return s * level


def pizz(n, level=1.0):
    return lowpass(pluck(n, 0.7, 0.985), 2600) * 3 * level


def pad(notes, dur=1.6, attack=0.35):
    x, out = t(dur), np.zeros(int(dur * SR))
    for n in notes:
        for detune in (-0.004, 0.004):
            f = note(n) * (1 + detune)
            for k in range(1, int(4000 / f)):
                out += np.sin(2 * np.pi * f * k * x) / k ** 1.3
    shape = np.minimum(x / attack, 1) * np.minimum((dur - x) / 0.5, 1)
    return lowpass(out * shape, 1400) / len(notes)


def analog(n, decay=0.35, bright=1.0):
    """Saw with a closing filter: higher harmonics die first."""
    f, x, out = note(n), t(1.4), 0
    for k in range(1, int(9000 / f)):
        out = out + np.sin(2 * np.pi * f * k * x) / k * np.exp(-x / (decay / (1 + 0.5 * k / bright)))
    return (out + 0.5 * np.sin(np.pi * f * x) * np.exp(-x / decay)) * np.minimum(x / 0.003, 1)


def handpan(n, level=1.0):
    out = 0
    for r, a, d in [(1, 1, 1.3), (2, 0.45, 0.8), (3, 0.2, 0.5)]:
        for beat in (0, 0.0015):  # two slightly detuned copies give the shimmer
            out = out + partials(note(n) * (1 + beat), 2.0, [(r, a / 2, d)], 0.01)
    return out * level


def bass(n, level=1.0):
    return lowpass(pluck(n, 1.2, 0.997), 900) * 4 * level


def brush(dur=0.3, level=0.25):
    n = int(dur * SR)
    x = np.arange(n) / SR
    return lowpass(rng.standard_normal(n), 6000) * np.minimum(x / 0.06, 1) * np.exp(-x / 0.1) * level


def woodblock(level=1.0, f=880):
    return partials(f, 0.15, [(1, 1, 0.035), (2.7, 0.4, 0.015)], 0.0005) * level


def ticks(pattern, step=0.136):
    """pattern like 'x.xx' - x a tick, . a rest - at 16ths of ~110 BPM."""
    return place([(i * step, woodblock(1 if i == 0 else 0.6)) for i, c in enumerate(pattern) if c == "x"])


def lofi_piano(n, level=1.0):
    x, f = t(2.0), note(n)
    wobble = 1 + 0.004 * np.sin(2 * np.pi * 0.7 * x)  # tape wow
    phase = 2 * np.pi * np.cumsum(f * wobble) / SR
    out = sum(np.sin(k * phase) / k ** 1.6 * np.exp(-x / (0.9 / k ** 0.6)) for k in range(1, 7))
    return lowpass(out * np.minimum(x / 0.01, 1), 1600) * level


def crackle(dur):
    n = int(dur * SR)
    out = rng.standard_normal(n) * 0.006
    pops = rng.random(n) < 12 / SR
    out[pops] += rng.choice([-1, 1], pops.sum()) * rng.uniform(0.05, 0.25, pops.sum())
    return lowpass(out, 5000)


def lofi(events, dur):
    return place(events + [(0, crackle(dur))])


# --- the families: hard, light, section, button ----------------------------------------

FAMILIES = {
    "1-celesta (music box, delicate)": {
        "hard": lambda: motif(lambda n: celesta(n, 0.8), ["A5", "D5"], 0.22),
        "light": lambda: motif(celesta, ["D6", "F#6", "A6"], 0.1),
        "section": lambda: motif(celesta, ["D6", "E6", "F#6", "A6", "D7"], 0.11),
        "button": lambda: place([(0, motif(celesta, ["A6", "F#6", "E6"], 0.12)), (0.36, celesta("D6") + celesta("D5", 0.6))]),
    },
    "2-strings (pizzicato over a soft pad)": {
        "hard": lambda: place([(0, pad(["D3", "A3"], 1.5)), (0.3, motif(lambda n: pizz(n, 0.8), ["D4", "A3"], 0.25))]),
        "light": lambda: motif(pizz, ["D4", "F#4", "A4", "D5"], 0.1),
        "section": lambda: place([(0, pad(["D4", "F#4", "A4"], 2.0)), (0.3, motif(pizz, ["D4", "F#4", "A4", "D5", "A4", "D5"], 0.1))]),
        "button": lambda: place([(0, motif(pizz, ["A4", "F#4", "E4"], 0.12)), (0.36, pizz("D4") + pizz("D3")), (0.36, pad(["D3", "A3", "F#4"], 1.4, 0.05))]),
    },
    "3-analog synth (warm, modern newsroom)": {
        "hard": lambda: motif(lambda n: analog(n, 0.3, 0.5), ["D3", "A3"], 0.2),
        "light": lambda: motif(analog, ["D4", "F#4", "A4", "D5"], 0.09),
        "section": lambda: place([(0, motif(analog, ["D4", "F#4", "A4", "D5", "F#5"], 0.09)), (0.45, analog("D3", 0.8, 0.6))]),
        "button": lambda: place([(0, motif(analog, ["A4", "F#4", "E4"], 0.12)), (0.36, analog("D4", 0.7) + analog("D3", 0.7, 0.5))]),
    },
    "4-handpan (warm, organic, round)": {
        "hard": lambda: motif(lambda n: handpan(n, 0.9), ["D3", "A3"], 0.3),
        "light": lambda: motif(handpan, ["A3", "D4", "F#4"], 0.13),
        "section": lambda: motif(handpan, ["D3", "A3", "D4", "E4", "F#4", "A4"], 0.13),
        "button": lambda: place([(0, motif(handpan, ["A4", "F#4", "E4"], 0.14)), (0.42, handpan("D4") + handpan("D3", 0.7))]),
    },
    "5-jazz trio (upright bass, brushes, vibes)": {
        "hard": lambda: place([(0, bass("D2")), (0.25, bass("A1", 0.8)), (0, brush())]),
        "light": lambda: place([(0, brush()), (0, bass("D2")), (0.05, motif(vibraphone, ["D5", "F#5", "A5"], 0.11))]),
        "section": lambda: place([(i * 0.2, bass(n)) for i, n in enumerate(["D2", "F#2", "A2", "D3"])] + [(i * 0.2, brush(level=0.18)) for i in range(4)] + [(0.8, vibraphone("D5") + vibraphone("F#5") + vibraphone("A5"))]),
        "button": lambda: place([(0, vibraphone("A5") * 0.8), (0.15, vibraphone("E5") * 0.8), (0.3, vibraphone("D5") + vibraphone("F#5")), (0.3, bass("D2")), (0.3, brush())]),
    },
    "6-news ticker (woodblock rhythm into a tone)": {
        "hard": lambda: place([(0, ticks("x.x")), (0.27, partials(note("D4"), 1.0, [(1, 0.5, 0.35), (2, 0.1, 0.15)]))]),
        "light": lambda: place([(0, ticks("xxx.x")), (0.54, partials(note("A5"), 1.0, [(1, 0.4, 0.3), (2, 0.1, 0.12)]))]),
        "section": lambda: place([(0, ticks("x.xxx.x.xx")), (1.22, partials(note("D5"), 1.4, [(1, 0.4, 0.45), (2, 0.1, 0.2)]) + partials(note("A5"), 1.4, [(1, 0.25, 0.4)]))]),
        "button": lambda: place([(0, ticks("xx.x")), (0.41, partials(note("D4"), 1.4, [(1, 0.5, 0.5), (2, 0.08, 0.2)]))]),
    },
    "7-lo-fi piano (tape wobble, vinyl crackle)": {
        "hard": lambda: lofi([(0.1, motif(lofi_piano, ["A3", "D3"], 0.28))], 1.6),
        "light": lambda: lofi([(0.1, motif(lofi_piano, ["D4", "F#4", "A4"], 0.12))], 1.4),
        "section": lambda: lofi([(0.1, motif(lofi_piano, ["D4", "A4", "F#4", "A4", "D5"], 0.15)), (0.85, lofi_piano("D3", 0.8))], 2.2),
        "button": lambda: lofi([(0.1, motif(lofi_piano, ["A4", "F#4", "E4"], 0.15)), (0.55, lofi_piano("D4") + lofi_piano("D3", 0.7))], 2.0),
    },
}


def level(s):
    loud = s[np.abs(s) > 0.01 * np.max(np.abs(s))]
    return 20 * np.log10(np.sqrt(np.mean(loud ** 2)))


def finish(s, wet):
    s = reverb(s / np.max(np.abs(s)), wet)
    s = s * 10 ** ((VOICE_DB - 7 - level(s)) / 20)
    return s * min(1, 10 ** (-9 / 20) / np.max(np.abs(s)))  # clicky cues: cap the peak so transients don't poke out


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
        s = finish(fn(), 0.2 if role in ("section", "button") else 0.15)
        write(OUT / fam / f"{role}.mp3", np.concatenate([gap(0.3), s, gap(0.5)]))
        reel += [s, gap(1.2)]
        print(f"{fam} {role}: {len(s) / SR:.1f}s, peak {20 * np.log10(np.max(np.abs(s))):.1f} dB")
    write(OUT / f"{fam}.mp3", np.concatenate(reel))
