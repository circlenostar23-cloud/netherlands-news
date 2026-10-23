"""Round 8: the same Wilhelmus fragments, re-harmonised for calm-but-present energy, on bells and Rhodes.

Round 7's instruments landed (glass bells, Rhodes) but its harmony was too sad: hard cues sat on low
minor chords. Here nothing is minor. Every fragment moves IV -> I or V -> I in open add9 / sus2
voicings in the middle register, so each cue settles rather than sighs. Hard and light now differ by
energy (sparser, slower, warmer vs brighter, quicker, a sparkle on top), not by mode.

Five approaches:
1. Open chords      Rhodes plays the fragment over the new IV -> I voicings. The plain re-harmonisation.
2. Pulse            a soft muted Rhodes pulse starts a beat or two early and carries the bells in.
3. Scattered        the fragment's notes thrown across octaves and stereo, each with a dotted echo,
                    over a high open-fifth pad: the motif deconstructed into a pattern.
4. Call and answer  Rhodes states the fragment; bells answer an octave up, turned upward, so every
                    cue ends lifting forward rather than falling.
5. Air and pulse    a brushed hi-hat swell and a soft kick lead in; bells and Rhodes in unison on top.

usage: RENDER=<path-to-render-binary> python round-8.py <out-dir> [approach numbers]
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

ULTRABEAT = LOGIC / "Ultrabeat Samples"
KICK = load(ULTRABEAT / "Steely Beats/WA_gpark_kick1.aif")
HAT = load(ULTRABEAT / "Indie Disco/SS_Kit04_Pedal_Hat_1.aif")
OPEN_HAT = load(ULTRABEAT / "Indie Disco/SS_Kit04_Open_Hat_1.aif")

FRAGMENTS = {
    "hard-1": [("D4", 1), ("G4", 2)],                       # "Wil-hel"
    "hard-2": [("G4", 1), ("F#4", 1), ("D4", 2)],            # "...je heb ik"
    "hard-3": [("A4", 1), ("G4", 2)],                        # "...schen bloed"
    "light-1": [("D5", 1.5), ("E5", 0.5), ("D5", 2)],        # "Prin-ce van"
    "light-2": [("E5", 0.5), ("F#5", 0.5), ("G5", 2)],       # "al-tijd ge-"
    "light-3": [("D5", 1), ("G5", 1), ("G5", 2)],            # "Wil-hel-mus"
    "section": [("D5", 1.5), ("E5", 0.5), ("D5", 1.5), ("C5", 0.5), ("B4", 2.5)],  # "Een prin-ce van O-ran-je"
    "button": [("F#4", 1), ("G4", 3)],                       # "ge-eerd"
}

# Chords as (beat, voicing). Only I, IV and V, in open add9 / sus2 / maj7 shapes.
C9 = ["C3", "G3", "D4", "E4"]          # IV add9
CMAJ7 = ["C3", "G3", "B3", "E4"]       # IV maj7
G9 = ["G2", "D3", "A3", "B3"]          # I add9
G = ["G2", "D3", "B3", "D4"]           # I
D_SUS = ["D3", "A3", "E4"]             # V sus2: no third, so it leans forward without tension
HARM = {
    "hard-1": [(0, C9), (1, G9)],
    "hard-2": [(0, CMAJ7), (1, D_SUS), (2, G9)],
    "hard-3": [(0, D_SUS), (1, G9)],
    "light-1": [(0, G9), (1.5, C9), (2, G9)],
    "light-2": [(0, C9), (0.5, D_SUS), (1, G9)],
    "light-3": [(0, G9), (1, C9), (2, G9)],
    "section": [(0, G9), (2, CMAJ7), (4, G)],
    "button": [(0, D_SUS), (1, G9 + ["G4"])],
}


def hard(frag):
    return frag.startswith("hard")


def tempo(frag):
    return 0.36 if hard(frag) else 0.3


def melody(frag, beat, octave=0):
    at, out = 0.0, []
    for n, b in FRAGMENTS[frag]:
        out.append((at, n[:-1] + str(int(n[-1]) + octave), b * beat))
        at += b * beat
    return out, at


def up(n, semis):
    """The note `semis` semitones above n, as a name."""
    m = midi(n) + semis
    name = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"][m % 12]
    return f"{name}{m // 12 - 1}"


def chords(frag, beat, bank, vel, spread=0.4, start=0.0, ring=0.6):
    harm = HARM[frag]
    _, end = melody(frag, beat)
    events = []
    for k, (b, voicing) in enumerate(harm):
        until = harm[k + 1][0] * beat if k + 1 < len(harm) else end + ring
        for j, n in enumerate(voicing):
            p = spread * (2 * j / max(1, len(voicing) - 1) - 1)
            events.append((start + b * beat + 0.012 * j, pan(bank.note(n, hold=until - b * beat, release=0.5, vel=vel), p)))
    return events


def sparkle(at, n, vel=0.18):
    return (at, pan(BELLS.note(up(n, 12), vel=vel)[: int(1.4 * SR)], 0.5))


# --- the five approaches ---------------------------------------------------------------------------

def open_chords(frag):
    beat = tempo(frag)
    notes, _ = melody(frag, beat)
    mel = [(s, pan(RHODES.note(n, hold=h + 0.05, release=0.6, vel=0.8 if i < len(notes) - 1 else 0.9), 0.15))
           for i, (s, n, h) in enumerate(notes)]
    events = chords(frag, beat, RHODES, 0.4 if hard(frag) else 0.48) + mel
    if not hard(frag):
        events.append(sparkle(notes[-1][0], notes[-1][1]))
    return wow(filt(place(events), lo=90, hi=4200 if hard(frag) else 6500), depth=0.0012)


def pulse(frag):
    beat = tempo(frag)
    pre = 2 if hard(frag) else 4                      # pulses before the melody lands
    step = beat if hard(frag) else beat / 2           # quarters before hard stories, eighths before light
    notes, end = melody(frag, beat)
    t0 = pre * step
    harm = HARM[frag]
    events, t = [], 0.0
    while t < t0 + end - 0.01:
        b = (t - t0) / beat
        voicing = harm[0][1] if b < 0 else [v for hb, v in harm if hb <= b + 1e-6][-1]
        lo, hi = voicing[0], voicing[1]
        fade_in = min(1, 0.45 + 0.55 * t / max(t0, 1e-6))
        for n, p in ((lo, -0.35), (hi, 0.35)):
            events.append((t, pan(RHODES.note(up(n, 12), hold=step * 0.45, release=0.08, vel=0.32 * fade_in), p)))
        t += step
    events += [(t0 + s, pan(BELLS.note(n, vel=0.9), 0.1)) for s, n, _ in notes]
    events += chords(frag, beat, SKY, 0.22, spread=0.7, start=t0)
    return filt(place(events), lo=110, hi=5000 if hard(frag) else 8000)


def scattered(frag):
    beat = tempo(frag) * 1.1
    notes, end = melody(frag, beat)
    leap = 12 if hard(frag) else -12          # every other note jumps an octave: up from low, down from high
    events = []
    for i, (s, n, _) in enumerate(notes):
        n2 = up(n, leap * (i % 2))
        p = (-0.6, 0.6)[i % 2]
        hit = BELLS.note(n2, vel=0.85)[: int(2.2 * SR)]
        events.append((s, pan(hit, p)))
        events.append((s + beat * 0.75, pan(filt(hit, lo=400, hi=5000), -p) * 0.3))   # dotted echo, other side
    root_fifth = ["G4", "D5"] if HARM[frag][-1][1][0].startswith("G") else ["C4", "G4"]
    events += [(0, pan(SKY.note(n, hold=end + 0.4, release=0.9, vel=0.22), p)) for n, p in zip(root_fifth, (-0.5, 0.5))]
    sig = place(events)
    first = place(events[:1])
    return np.concatenate([inhale(first, 0.45) * 0.8, filt(sig, lo=150, hi=6000 if hard(frag) else 9000)])


def call_answer(frag):
    beat = tempo(frag)
    notes, end = melody(frag, beat)
    events = chords(frag, beat, RHODES, 0.38 if hard(frag) else 0.45, ring=0.9)
    events += [(s, pan(RHODES.note(n, hold=h + 0.05, release=0.5, vel=0.78), 0.15)) for s, n, h in notes]
    # the answer: the last note, then a step up (to the 2nd or 6th): an open, forward-leaning ending
    last = notes[-1][1]
    step = {"G": 2, "D": 2, "B": 3, "A": 2}.get(last[0], 2)
    a0 = notes[-1][0] + beat * (1.0 if hard(frag) else 0.75)
    for k, (n, v) in enumerate(((up(last, 12), 0.5), (up(last, 12 + step), 0.62))):
        events.append((a0 + k * beat * 0.5, pan(BELLS.note(n, vel=v)[: int(2 * SR)], (0.45, -0.25)[k])))
    return filt(place(events), lo=90, hi=5000 if hard(frag) else 8000)


def air_pulse(frag):
    beat = tempo(frag)
    notes, end = melody(frag, beat)
    lead = 0.65
    # a closed hi-hat swell, reversed, brushing up into a soft low kick on the downbeat
    swish = OPEN_HAT[: int(0.6 * SR)][::-1]
    swish = swish * np.linspace(0, 1, len(swish))[:, None] ** 2
    kick = filt(KICK, hi=900) * (0.5 if hard(frag) else 0.65)
    events = [(lead - len(swish) / SR, filt(swish, lo=3000) * (0.12 if hard(frag) else 0.18)), (lead, kick)]
    if not hard(frag):
        events += [(lead + k * beat, pan(filt(HAT, lo=4000) * 0.12, (-0.4, 0.4)[k % 2])) for k in range(1, int(end / beat) + 1)]
    for s, n, h in notes:
        events.append((lead + s, pan(BELLS.note(n, vel=0.7), 0.25)))
        events.append((lead + s, pan(RHODES.note(n, hold=h + 0.05, release=0.5, vel=0.6), -0.2)))
    events += chords(frag, beat, RHODES, 0.32 if hard(frag) else 0.38, start=lead)
    return filt(place(events), lo=40, hi=5500 if hard(frag) else 8500)


FAMILIES = {
    "1-open chords (Rhodes)": (open_chords, 0.18),
    "2-pulse (Rhodes pulse, bells)": (pulse, 0.18),
    "3-scattered (bells, deconstructed)": (scattered, 0.22),
    "4-call and answer (Rhodes, bells)": (call_answer, 0.18),
    "5-air and pulse (hat, kick, bells + Rhodes)": (air_pulse, 0.16),
}

demo(Path(sys.argv[1]), FAMILIES, FRAGMENTS, sys.argv[2:])
