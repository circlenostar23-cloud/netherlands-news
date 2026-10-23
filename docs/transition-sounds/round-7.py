"""Round 7: the Wilhelmus fragments on real recorded instruments, in stereo, with modern production.

Round 6 sounded robotic because every instrument was synthesized in numpy. Here every note is a
recording: Logic Pro's sampler instruments (flute, clarinet, strings, horn) rendered offline through
macOS's AVAudioUnitSampler (render.swift), and Logic's Alchemy samples (bells, Rhodes, pads, sung
vowels) pitched from the nearest recorded note. Numpy only does the production: stereo reverb, a
reverse-reverb "inhale" into the first note, ping-pong echoes, gentle tape wow.

Needs Logic Pro's sound library installed (/Library/Application Support/Logic), ffmpeg, numpy, and
render.swift compiled: swiftc -O docs/transition-sounds/render.swift -o <dir>/render

usage: RENDER=<path-to-render-binary> python round-7.py <out-dir> [family numbers]
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

# --- fragments (Valerius 1626, in G) as (note, beats), and a quiet chord under each ----------------

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
CHORD = {"hard-1": ["E3", "B3"], "hard-2": ["B2", "F#3"], "hard-3": ["A2", "E3"],
         "light-1": ["G3", "D4"], "light-2": ["C3", "G3"], "light-3": ["G3", "D4"],
         "section": ["G2", "D3", "B3"], "button": ["G2", "D3"]}


def shift(n, octaves):
    return n[:-1] + str(int(n[-1]) + octaves)


def timeline(frag, beat, octave=0):
    """-> [(start_s, note, hold_s)] and total length in seconds."""
    at, out = 0.0, []
    for n, b in FRAGMENTS[frag]:
        out.append((at, shift(n, octave), b * beat))
        at += b * beat
    return out, at


def hard(frag):
    return frag.startswith("hard")


# --- families -------------------------------------------------------------------------------------

def glass(frag):
    """Real bells, breathing in through a reversed reverb, the last note echoing left and right.
    Hard cues an octave down and darker; light cues bright with a bell-tree shimmer."""
    beat = 0.38 if hard(frag) else 0.32
    notes, end = timeline(frag, beat)
    hits = [(s, pan(BELLS.note(n, vel=0.9 if i < len(notes) - 1 else 1), (-0.3, 0.3)[i % 2])) for i, (s, n, _) in enumerate(notes)]
    last_s, last_n, _ = notes[-1]
    echo = pingpong(BELLS.note(shift(last_n, 1), vel=0.22)[: int(1.2 * SR)], beat * 0.75, 3, 0.5)
    under = [(0, SKY.note(c, hold=end + 0.6, release=0.9, vel=0.35)) for c in CHORD[frag]]
    events = hits + under + [(last_s + beat * 0.75, echo)]
    if not hard(frag):
        events.append((last_s, filt(BELL_TREE[: int(1.6 * SR)], lo=3000) * 0.1 * np.linspace(1, 0, int(1.6 * SR))[:, None]))
    sig = place(events)
    sig = filt(sig, hi=3500 if hard(frag) else 9000)
    return np.concatenate([inhale(place(hits[:1])), sig])


def winds(frag):
    """Flute (light) or clarinet (hard) over a string chord that blooms in; horn joins What's on."""
    beat = 0.42 if hard(frag) else 0.36
    notes, end = timeline(frag, beat, -1 if hard(frag) else 0)
    lead = CLARINET if hard(frag) else FLUTE
    melody = exs(lead, [(0.15 + s, n, h * 0.95, 70 if i < len(notes) - 1 else 78) for i, (s, n, h) in enumerate(notes)], end + 2.5)
    strings = exs(STRINGS, [(0, c, end + 0.5, 48) for c in CHORD[frag]], end + 2.5)
    events = [(0, pan(melody, 0.15)), (0, pan(strings, -0.2) * 0.8)]
    if frag == "section":
        events.append((0, pan(exs(HORN, [(0, "G3", end + 0.4, 52), (0, "D3", end + 0.4, 46)], end + 2.5), -0.4) * 0.6))
    return place(events)


def voices(frag):
    """A real singer hums the fragment: a low male 'oh' before hard stories, a female 'ah' before light."""
    beat = 0.42 if hard(frag) else 0.36
    singer = TOM if hard(frag) else AMANDA
    notes, end = timeline(frag, beat, -1 if hard(frag) else 0)
    sung = [(s, pan(singer.note(n, hold=h * 1.05 if i < len(notes) - 1 else h + 0.3, release=0.35 if i < len(notes) - 1 else 0.8,
                                vel=0.9), 0.1)) for i, (s, n, h) in enumerate(notes)]
    under = [(0, pan(SKY.note(c, hold=end + 0.5, release=1.0, vel=0.3), p)) for c, p in zip(CHORD[frag], (-0.5, 0.5, 0))]
    out = place(sung + under)
    if frag in ("section", "button"):  # the second singer joins a third below / in unison
        partner = AMANDA if singer is TOM else TOM
        harm = [(s, pan(partner.note(n, hold=h + (0.3 if i == len(notes) - 1 else 0), release=0.5, vel=0.55), -0.35))
                for i, (s, n, h) in enumerate(timeline(frag, beat, -1)[0])]
        out = place([(0, out)] + harm)
    return out


def rhodes(frag):
    """Rhodes electric piano on a slightly wobbly tape, soft chord first, melody answering."""
    beat = 0.38 if hard(frag) else 0.33
    notes, end = timeline(frag, beat)
    chord = [(0, pan(RHODES.note(c, hold=end + 0.4, release=0.8, vel=0.45), p)) for c, p in zip(CHORD[frag], (-0.4, 0.4, 0))]
    mel = [(0.06 + s, pan(RHODES.note(n, hold=h + (0.5 if i == len(notes) - 1 else 0.05), release=0.6, vel=0.85), 0.2))
           for i, (s, n, h) in enumerate(notes)]
    sig = place(chord + mel)
    if not hard(frag):
        last_s, last_n, _ = notes[-1]
        sig = place([(0, sig), (0.06 + last_s + beat, pingpong(RHODES.note(shift(last_n, 1), hold=0.3, vel=0.18), beat, 3, 0.45))])
    return wow(filt(sig, lo=90, hi=5000))


FAMILIES = {
    "1-glass bells (inhale, echo)": (glass, 0.2),
    "2-flute and clarinet over strings": (winds, 0.22),
    "3-a singer hums it": (voices, 0.24),
    "4-Rhodes on tape": (rhodes, 0.16),
}


demo(Path(sys.argv[1]), FAMILIES, FRAGMENTS, sys.argv[2:])
