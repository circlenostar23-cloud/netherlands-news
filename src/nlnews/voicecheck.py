"""Does each Gemini chunk say what the script says, in the right voices?

Gemini sometimes drops or garbles a line, repeats one, or voices a line in the other host's
voice (ep-2026-10-19: Maya broke off her Albert Heijn line and repeated Sam's). Right after a
chunk is voiced, Whisper transcribes it and each line is matched against the script. A chunk
with a problem is voiced once more, if the day's request quota and the Gemini budget leave room
for it, and the take with fewer problems is kept.

NLNEWS_VOICE_CHECK (an Actions variable) sets how far this goes:
- `retry` (default): check every chunk and voice a failing one once more.
- `log`: check and report in the log and voicecheck.txt, but never spend a request on it.
- `off`: no check, as before 2026-10-19. Chapters still transcribe the audio for their timings.

The transcripts are kept next to each chunk (chunkNN.words.json), so the chapters step reuses
them instead of transcribing the episode a second time.
"""

import difflib
import json
import os
import re
import subprocess
import wave
from pathlib import Path

from nlnews.config import HOSTS
from nlnews.models import Line

MODE = os.environ.get("NLNEWS_VOICE_CHECK", "retry").strip().lower() or "retry"
WHISPER_MODEL = "tiny.en"
MIN_MATCHED = 0.5  # share of a line's words Whisper must hear; Dutch names alone cost ~40% on 10-19
MIN_LINE_WORDS = 5  # shorter lines ("Eighty-three?") are too easy for Whisper to miss
MAX_EXTRA_WORDS = 10  # heard words in a row that match no script word: a repeat or a made-up line
MIN_PITCH_WORDS = 8  # matched words a line needs before its pitch counts
# The lowest median pitch a line in each voice should have: Maya's lines voiced by Puck sat at
# 111-117 Hz (10-04, 10-06), her own at 140-170. Puck has no floor or ceiling here: Sam's questions
# and excited lines reached 150-200 Hz in the episodes of 10-13 to 10-19, as high as Kore.
LOWEST_PITCH = {"Kore": 130}

_model = False  # not loaded yet; None once loading failed


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def _whisper():
    global _model
    if _model is False:
        try:
            from faster_whisper import WhisperModel
            _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        except Exception as exc:
            print(f"  Whisper unavailable ({exc})")
            _model = None
    return _model


def words_file(wav: Path) -> Path:
    return wav.with_suffix(".words.json")


def heard(wav: Path) -> list[tuple[str, float, float]] | None:
    """The words Whisper hears in a chunk (normalised, start, end), or None without Whisper.
    Cached next to the chunk, and redone when the chunk is newer than its transcript."""
    cache = words_file(wav)
    if cache.exists() and cache.stat().st_mtime >= wav.stat().st_mtime:
        return [tuple(w) for w in json.loads(cache.read_text())]
    if (model := _whisper()) is None:
        return None
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    found, _ = model.transcribe(np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768,
                                language="en", word_timestamps=True, condition_on_previous_text=False)
    words = [(_norm(w.word), round(w.start, 2), round(w.end, 2)) for s in found for w in s.words if _norm(w.word)]
    cache.write_text(json.dumps(words))
    return words


def pitch(x, sr: int) -> float:
    """Median pitch in Hz over the voiced 40 ms frames, by autocorrelation between 70 and 350 Hz."""
    import numpy as np
    n, hop, lo, hi, found = int(.04 * sr), int(.02 * sr), sr // 350, sr // 70, []
    for i in range(0, len(x) - n, hop):
        f = x[i:i + n] - x[i:i + n].mean()
        if (f ** 2).mean() < 0.02 ** 2:
            continue
        ac = np.correlate(f, f, "full")[n - 1:]
        ac = ac / ac[0]
        k = lo + int(np.argmax(ac[lo:hi]))
        if ac[k] > 0.5:
            found.append(sr / k)
    return float(np.median(found)) if len(found) >= 10 else 0.0


def check(wav: Path, lines: list[Line]) -> list[str] | None:
    """What's wrong with a chunk, one entry per problem; None if it couldn't be checked."""
    import numpy as np
    try:
        words_heard = heard(wav)
    except Exception as exc:
        print(f"  voice check failed on {wav.name} ({exc})")
        return None
    if words_heard is None:
        return None
    words, owner = [], []
    for k, line in enumerate(lines):
        for t in filter(None, map(_norm, line.text.split())):
            words.append(t)
            owner.append(k)
    spans: dict[int, list] = {}
    matched = [False] * len(words_heard)
    for a, b, n in difflib.SequenceMatcher(None, words, [h[0] for h in words_heard], autojunk=False).get_matching_blocks():
        for j in range(n):
            spans.setdefault(owner[a + j], []).append(words_heard[b + j])
            matched[b + j] = True

    with wave.open(str(wav)) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    problems = []
    for k, line in enumerate(lines):
        n, found = owner.count(k), spans.get(k, [])
        if n >= MIN_LINE_WORDS and len(found) / n < MIN_MATCHED:
            problems.append(f"{line.speaker} line {'missing' if not found else f'garbled ({len(found) / n:.0%} heard)'}: {line.text[:60]}")
            continue
        if len(found) >= MIN_PITCH_WORDS and (low := LOWEST_PITCH.get(HOSTS.get(line.speaker, ""))):
            p = pitch(x[int(found[0][1] * sr):int(found[-1][2] * sr)], sr)
            if p and p < low:
                problems.append(f"{line.speaker} line in the other voice ({p:.0f} Hz): {line.text[:60]}")
    run, at = 0, 0.0
    for (_, start, _), ok in zip(words_heard + [("", 0.0, 0.0)], matched + [True]):
        if not ok:
            run, at = run + 1, at if run else start
            continue
        if run >= MAX_EXTRA_WORDS:
            problems.append(f"{run} unscripted words at {at:.0f}s (a repeat?)")
        run = 0
    return problems
