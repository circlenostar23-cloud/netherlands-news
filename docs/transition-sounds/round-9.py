"""Round 9: two developments of round 8's approach 5 ("air and pulse"), which is kept as-is in reserve.

1. Same notes, refined instruments. The hi-hats are now a real acoustic kit (Logic's Drum Kit Designer
   "SoCal" kit, sliced out of its sample file) instead of a drum-machine hat; closed hits rotate so no
   two in a row are identical. The bells keep only their shimmer: the low hum and strike are filtered
   out and the ring is cut short, so they sit under the Rhodes as a glint rather than a church bell.
   The kick is unchanged.
2. The anthem backwards. Cues are short cells from the Wilhelmus melody in retrograde, which turns its
   falling lines into rising ones, re-phrased with pickups into a downbeat, over new chords: a borrowed
   F (bVII) and an A-over-G (Lydian) lift alongside C and D, still nothing minor.

usage: RENDER=<path-to-render-binary> python round-9.py <out-dir> [version numbers]
"""
import subprocess, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

KICK = load(LOGIC / "Ultrabeat Samples/Steely Beats/WA_gpark_kick1.aif")
SOCAL_HATS = LOGIC / "EXS Factory Samples/Drum Kit Designer Consolidated/Drum Kit Designer/Stereo/SoCal Kit HiHat_consolidated.caf"


def clip(path, start, dur):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(dur), "-i", str(path),
                          "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return fade(np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64), 0.03)


# The kit's samples sit end to end in one file; these are hits found by their attacks, chosen as the
# darkest (most softly played) closed hats and a soft open hat.
CLOSED_HATS = [clip(SOCAL_HATS, s, 0.3) for s in (228.65, 191.77, 192.63, 212.20)]
OPEN_HAT = clip(SOCAL_HATS, 699.57, 1.0)


def hz(n):
    return 440 * 2 ** ((midi(n) - 69) / 12)


def glint(n, vel):
    """A bell with only its shimmer left: no hum or strike under the note, and a short ring."""
    x = BELLS.note(n)[: int(1.6 * SR)]
    x = filt(x, lo=hz(n) * 0.9, hi=7500)
    return x * np.exp(-np.arange(len(x)) / SR / 0.45)[:, None] * vel


# --- version 1: round 8's fragments and chords ----------------------------------------------------

C9 = ["C3", "G3", "D4", "E4"]          # IV add9
CMAJ7 = ["C3", "G3", "B3", "E4"]       # IV maj7
G9 = ["G2", "D3", "A3", "B3"]          # I add9
G = ["G2", "D3", "B3", "D4"]           # I
D_SUS = ["D3", "A3", "E4"]             # V sus2
F9 = ["F2", "C3", "G3", "A3"]          # bVII add9, borrowed: a confident lift back to G
A_G = ["G2", "A3", "C#4", "E4"]        # A over G: the Lydian brightening of I

ROUND_8 = {
    "hard-1": [("D4", 1), ("G4", 2)],
    "hard-2": [("G4", 1), ("F#4", 1), ("D4", 2)],
    "hard-3": [("A4", 1), ("G4", 2)],
    "light-1": [("D5", 1.5), ("E5", 0.5), ("D5", 2)],
    "light-2": [("E5", 0.5), ("F#5", 0.5), ("G5", 2)],
    "light-3": [("D5", 1), ("G5", 1), ("G5", 2)],
    "section": [("D5", 1.5), ("E5", 0.5), ("D5", 1.5), ("C5", 0.5), ("B4", 2.5)],
    "button": [("F#4", 1), ("G4", 3)],
}
ROUND_8_HARM = {
    "hard-1": [(0, C9), (1, G9)],
    "hard-2": [(0, CMAJ7), (1, D_SUS), (2, G9)],
    "hard-3": [(0, D_SUS), (1, G9)],
    "light-1": [(0, G9), (1.5, C9), (2, G9)],
    "light-2": [(0, C9), (0.5, D_SUS), (1, G9)],
    "light-3": [(0, G9), (1, C9), (2, G9)],
    "section": [(0, G9), (2, CMAJ7), (4, G)],
    "button": [(0, D_SUS), (1, G9 + ["G4"])],
}

# --- version 2: the Wilhelmus in retrograde ------------------------------------------------------
# The melody (Valerius, in G; notes from the score on nl.wikipedia), each phrase read backwards:
#   phrase 1 reversed: G A G A B C B A B A C B A G G D
#   phrase 2 reversed: A G A B C B A B C D E D C B
#   phrase 3 reversed: G F# G G F# E D F# G A B A G F# G D
# Cells taken from those, mostly rising now, re-phrased with a pickup into the downbeat.

RETRO = {
    "hard-1": [("D4", 0.5), ("F#4", 0.5), ("G4", 2)],                  # phrase 3: D F# G
    "hard-2": [("G4", 1), ("A4", 1), ("B4", 2)],                       # phrase 1: G A B
    "hard-3": [("G4", 1), ("F#4", 0.5), ("G4", 2)],                    # phrase 3: G F# G
    "light-1": [("D5", 0.5), ("F#5", 0.5), ("G5", 0.5), ("A5", 1.5)],  # phrase 3: D F# G A
    "light-2": [("B4", 0.5), ("C5", 0.5), ("D5", 2)],                  # phrase 2: B C D
    "light-3": [("C5", 0.5), ("D5", 0.5), ("E5", 0.5), ("D5", 1.5)],   # phrase 2: C D E D
    "section": [("B4", 0.5), ("C5", 0.5), ("D5", 1.5), ("E5", 0.5), ("D5", 2.5)],  # phrase 2: B C D E D
    "button": [("A4", 0.5), ("B4", 0.5), ("G4", 3)],                   # phrase 1: A B, home to G
}
RETRO_HARM = {
    "hard-1": [(0, C9), (1, G9)],                   # F# over C: a Lydian glow, then home
    "hard-2": [(0, C9), (2, G9)],                   # B over C is its major 7th
    "hard-3": [(0, G9), (1, D_SUS), (1.5, G9)],
    "light-1": [(0, D_SUS), (1.5, A_G)],            # ends floating on A over A/G
    "light-2": [(0, CMAJ7), (1, G9)],
    "light-3": [(0, F9), (1.5, G9)],                # bVII to I
    "section": [(0, G9), (1, F9), (2.5, C9), (3, G9)],
    "button": [(0, D_SUS), (1, G9 + ["G4"])],
}


def hard(frag):
    return frag.startswith("hard")


def air_pulse(fragments, harmony):
    """Round 8's approach 5: a reversed open-hat swell and a soft kick lead in, Rhodes and a bell glint
    play the melody together over Rhodes chords; light cues keep time with a closed hat."""
    def make(frag):
        beat = 0.36 if hard(frag) else 0.3
        lead = 0.65
        at, notes = 0.0, []
        for n, b in fragments[frag]:
            notes.append((at, n, b * beat))
            at += b * beat
        end = at
        swish = OPEN_HAT[::-1] * np.linspace(0, 1, len(OPEN_HAT))[:, None] ** 3
        swish = swish[-int(0.6 * SR):]
        events = [(lead - len(swish) / SR, filt(swish, lo=2500) * (0.16 if hard(frag) else 0.22)),
                  (lead, filt(KICK, hi=900) * (0.5 if hard(frag) else 0.65))]
        if not hard(frag):
            events += [(lead + k * beat, pan(filt(CLOSED_HATS[k % 4], lo=2000) * 0.1, (-0.35, 0.35)[k % 2]))
                       for k in range(1, int(end / beat) + 1)]
        for i, (s, n, h) in enumerate(notes):
            events.append((lead + s, pan(RHODES.note(n, hold=h + 0.05, release=0.5, vel=0.68), -0.15)))
            events.append((lead + s, pan(glint(up12(n), 0.38 if hard(frag) else 0.48), (0.45, 0.3)[i % 2])))
        harm = harmony[frag]
        for k, (b, voicing) in enumerate(harm):
            until = harm[k + 1][0] * beat if k + 1 < len(harm) else end + 0.6
            for j, n in enumerate(voicing):
                p = 0.4 * (2 * j / max(1, len(voicing) - 1) - 1)
                events.append((lead + b * beat + 0.012 * j,
                               pan(RHODES.note(n, hold=until - b * beat, release=0.5, vel=0.32 if hard(frag) else 0.38), p)))
        return filt(place(events), lo=40, hi=6000 if hard(frag) else 9000)
    return make


def up12(n):
    return n[:-1] + str(int(n[-1]) + 1)


VERSIONS = {
    "1-air and pulse, real hats, bell glint": (air_pulse(ROUND_8, ROUND_8_HARM), 0.16, ROUND_8),
    "2-the anthem backwards": (air_pulse(RETRO, RETRO_HARM), 0.16, RETRO),
}

if __name__ == "__main__":
    out, only = Path(sys.argv[1]), sys.argv[2:]
    for name, (make, wet, frags) in VERSIONS.items():
        if not only or name.split("-")[0] in only:
            demo(out, {name: (make, wet)}, frags, prefix=f"v{name.split('-')[0]} ")
