"""Short musical cues at the episode's breaks, so a half-listening listener hears that the show has
moved on (docs/transition-sounds.md). A theme after the hosts' hello, a cue before each later story
chosen by its `kind` and rotating within it, a theme opening What's on, and one after the sign-off.

The cues are files in assets/cues: `hard-*.wav` and `light-*.wav` (any number of each), `intro.wav`,
`section.wav` and `button.wav`. Swap or add files to change them; a missing one is skipped. They're
set to sit CUE_UNDER dB under the voices and peak at no more than PEAK dBFS here, so their own level
doesn't matter.

Gemini voices several stories per file, so a cue goes in at the story's start as the chapter step
found it, and only where that start was heard: an estimate can be seconds off, and a cue mid-story
is worse than none. The MP3 is rebuilt from the voiced files each time, so a rerun never adds cues
twice.
"""

import math
import subprocess
from pathlib import Path

import numpy as np

from nlnews.chapters import segment_files

CUES = Path(__file__).resolve().parents[2] / "assets" / "cues"
RATE = 44100
CUE_UNDER = 7  # dB under the voices
PEAK = -9  # dBFS
BEFORE = 0.25  # seconds of quiet added before a cue
UNDER_NEXT = 0.6  # seconds of a cue's ring-out that runs under the next host's first words
BUTTON_AFTER = 0.4  # seconds between the sign-off's last word and the button
BREATH_BACK = 0.8  # seconds before a heard word to look for the host's breath in
QUIET, BREATH = 50, 36  # dB under the voices: the quiet before a breath, and a breath


def plan(segments: list, stories: list, segment_starts: list[tuple[float, bool]]) -> list[tuple[float, str]]:
    """Where each cue goes, as (seconds into the voiced audio, cue name); the button at math.inf, the end.
    `segments` are the script's: cold open, one per story, What's on if there is one, sign-off."""
    extra = segments[1 + len(stories):]
    if not 1 <= len(extra) <= 2 or len(segment_starts) != len(segments):
        print(f"  {len(segments)} segments for {len(stories)} stories; no cues")
        return []
    pools = {k: sorted(p.stem for p in CUES.glob(f"{k}-*.wav")) for k in ("hard", "light")}
    used = {k: 0 for k in pools}
    placed = []
    for i, story in enumerate(stories, start=1):
        start, heard = segment_starts[i]
        if not heard:
            print(f"  no cue before {segments[i].title!r}: its start was estimated")
            continue
        if i == 1:
            placed.append((start, "intro"))
        elif pool := pools[story.kind]:
            placed.append((start, pool[used[story.kind] % len(pool)]))
            used[story.kind] += 1
    if len(extra) == 2:  # What's on, whatever the script calls it, then the sign-off
        start, heard = segment_starts[1 + len(stories)]
        if heard:
            placed.append((start, "section"))
    placed.append((math.inf, "button"))
    return [(t, name) for t, name in placed if (CUES / f"{name}.wav").exists()]


def _decode(*args: str) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", *args, "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def _loud_db(x: np.ndarray) -> float:
    """Level of the sounding parts: RMS over the 50 ms windows within 40 dB of the loudest."""
    win = int(0.05 * RATE)
    rms = np.sqrt(np.mean(x[: len(x) // win * win].reshape(-1, win) ** 2, axis=1))
    loud = rms[rms > rms.max() / 100]
    return 20 * math.log10(np.sqrt(np.mean(loud ** 2)))


def _cue(name: str, voice_db: float) -> np.ndarray:
    x = _decode("-i", str(CUES / f"{name}.wav"))
    sounding = np.nonzero(np.abs(x) > np.abs(x).max() * 10 ** (-55 / 20))[0]
    x = x[sounding[0]: sounding[-1] + 1]
    x *= 10 ** ((voice_db - CUE_UNDER - _loud_db(x)) / 20)
    return x * min(1, 10 ** (PEAK / 20) / np.abs(x).max())


def _cut(voice: np.ndarray, t: float, voice_db: float) -> int:
    """Where a cue before the word heard at `t` cuts the voice: at `t`, or before the breath the host
    takes for that word, so the breath plays after the cue with its line. Whisper puts a word's start
    after the breath, or sometimes at it."""
    c, win, hop = round(t * RATE), int(0.04 * RATE), int(0.01 * RATE)
    starts = list(range(max(0, c - int(BREATH_BACK * RATE)), c - win + 1, hop))
    if not starts:
        return c
    db = [10 * math.log10(np.mean(voice[s: s + win] ** 2) + 1e-12) for s in starts]
    q = int(np.argmin(db))
    if db[q] < voice_db - QUIET and max(db[q:]) > voice_db - BREATH:
        return starts[q] + win // 2
    return c


def splice(out_dir: Path, cues: list[tuple[float, str]], title: str) -> list[tuple[float, float]]:
    """Rebuild episode.mp3 from the voiced files with the cues in. Returns where time was added,
    as (seconds into the voiced audio, seconds added), for shift()."""
    listing = out_dir / "concat.local.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_files(out_dir)))
    voice = _decode("-f", "concat", "-safe", "0", "-i", str(listing))
    voice_db = _loud_db(voice)
    pieces, overlays, added, at, length = [], [], [], 0, 0  # at: in the voice; length: of the output so far
    for t, name in sorted(cues):
        cue = _cue(name, voice_db)
        cut = len(voice) if t == math.inf else min(_cut(voice, t, voice_db), len(voice))
        before, under = (BUTTON_AFTER, 0) if name == "button" else (BEFORE, UNDER_NEXT)
        gap = round(before * RATE) + max(0, len(cue) - round(under * RATE))
        pieces += [voice[at:cut], np.zeros(gap, np.float32)]
        length += cut - at
        overlays.append((length + round(before * RATE), cue))
        length += gap
        added.append((cut / RATE, min(t, len(voice) / RATE), gap / RATE))  # t itself, so shift() matches it exactly
        at = cut
    pieces.append(voice[at:])
    out = np.concatenate(pieces)
    out = np.concatenate([out, np.zeros(max([0] + [s + len(c) - len(out) for s, c in overlays]), np.float32)])
    for s, cue in overlays:
        out[s: s + len(cue)] += cue
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes()
    tmp = out_dir / "episode.cues.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-i", "-",
                    "-b:a", "64k", "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing", str(tmp)],
                   input=pcm, check=True)
    tmp.replace(out_dir / "episode.mp3")
    listing.unlink()
    return added


def shift(t: float, added: list[tuple[float, float, float]], at_break: bool) -> float:
    """Where a moment of the voiced audio is in the episode with the cues in. A moment at a break
    (from its cut to the heard word) is placed before that break's cue if `at_break` (a chapter, so
    it opens with its cue), after it otherwise (a line's first words)."""
    if at_break:
        t = next((cut for cut, heard, _ in added if cut <= t <= heard), t)
    return t + sum(gap for cut, _, gap in added if cut < t or (cut == t and not at_break))
