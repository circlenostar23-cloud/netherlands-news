"""When each script line is heard in the episode. From that come the chapters (where each story
starts), embedded in the MP3 as ID3 chapters and listed in the show notes, and the transcript,
a WebVTT file the feed points to with a `podcast:transcript` tag.

Gemini voices several stories in one request, so where a line starts inside a chunk isn't
known. Whisper (tiny.en, ~1.5 min for an episode on 4 cores) finds each line's first words.
Lines it doesn't recognise, and every line when Whisper is missing or fails, are placed by
their share of the words between the nearest known starts. On ep-2026-10-11 that estimate was
up to 5 s off for story starts when only the chunk's ends were known, because serious stories
are read more slowly. Either way a start then moves to the nearest pause, so it never falls
mid-word. Lines voiced one by one by a backup have a file each, so their starts are exact.
"""

import array
import difflib
import re
import subprocess
import wave
from pathlib import Path

from nlnews.models import Chapter, EpisodeScript, Line
from nlnews.tts import _chunk, _ffmpeg, _quiet

WHISPER_MODEL = "tiny.en"
LEAD_IN = 0.2  # seconds of the pause kept before a line's first word


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


def _n(line: Line) -> int:
    return len(line.text.split())


def _pause_ends(wav: Path, min_pause: float = 0.3, floor_db: float = -45) -> tuple[float, list[float]]:
    """The file's length and where each pause of at least `min_pause` seconds ends, in seconds."""
    with wave.open(str(wav)) as w:
        rate, samples = w.getframerate(), array.array("h", w.readframes(w.getnframes()))
    win, quiet = _quiet(samples, rate, floor_db)
    ends, run = [], 0
    for i, q in enumerate(quiet + [False]):
        if q:
            run += 1
            continue
        if run * win >= min_pause * rate:
            ends.append(i * win / rate)
        run = 0
    return len(samples) / rate, ends


def _heard_starts(model, wav: Path, lines: list[Line]) -> list[float | None]:
    """When Whisper hears each line's first words, or None if it doesn't recognise them."""
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    found, _ = model.transcribe(np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768,
                                language="en", word_timestamps=True, condition_on_previous_text=False)
    heard = [(_norm(w.word), w.start) for s in found for w in s.words if _norm(w.word)]
    words, firsts = [], []
    for line in lines:
        firsts.append(len(words))
        words += [t for t in map(_norm, line.text.split()) if t]
    at = {}
    for a, b, n in difflib.SequenceMatcher(None, words, [h[0] for h in heard], autojunk=False).get_matching_blocks():
        for j in range(n):
            at[a + j] = heard[b + j][1]
    # a line's first word or one of the two after it; later than that and the start is a guess
    return [next((at[i] for i in range(f, f + 3) if i in at), None) for f in firsts]


def _chunk_starts(model, wav: Path, lines: list[Line]) -> list[float]:
    """Where each line starts inside one Gemini chunk, in seconds."""
    length, pauses = _pause_ends(wav)
    heard = [None] * len(lines)
    if model is not None:
        try:
            heard = _heard_starts(model, wav, lines)
        except Exception as exc:
            print(f"  Whisper failed on {wav.name} ({exc}); estimating its line starts")
    heard[0] = 0.0
    # a heard start earlier than one before it is a mismatch
    for i in range(1, len(heard)):
        if heard[i] is not None and heard[i] <= max((h for h in heard[:i] if h is not None), default=0.0):
            heard[i] = None
    words = [0]
    for line in lines:
        words.append(words[-1] + _n(line))
    known = [(i, t) for i, t in enumerate(heard) if t is not None] + [(len(lines), length)]
    starts = []
    for i, t in enumerate(heard):
        if i == 0:
            starts.append(0.0)
            continue
        if t is not None:
            guess, within = t, 0.6
        else:  # between the nearest known starts, by share of words
            (a, ta), (b, tb) = max(k for k in known if k[0] < i), min(k for k in known if k[0] > i)
            guess, within = ta + (tb - ta) * (words[i] - words[a]) / max(1, words[b] - words[a]), 2.0
        near = [p for p in pauses if abs(p - guess) <= within]
        start = min(near, key=lambda p: abs(p - guess)) - LEAD_IN if near else guess
        starts.append(max(start, starts[-1]))
    return starts


def _whisper():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    except Exception as exc:
        print(f"  Whisper unavailable ({exc}); estimating line starts from word counts")
        return None


def find(script: EpisodeScript, out_dir: Path) -> tuple[list[Chapter], list[tuple[Line, float, float]]]:
    """The chapters, and each line with its start and end in episode.mp3, read back from the
    list of files the MP3 was built from."""
    by_name, at = {}, 0.0  # file name -> (path, where it starts)
    for rel in re.findall(r"segments/(.+)'$", (out_dir / "concat.txt").read_text(), re.M):
        path = out_dir / "segments" / rel  # relative, so a run restored on another machine still works
        with wave.open(str(path)) as w:
            length = w.getnframes() / w.getframerate()
        by_name.setdefault(path.name, (path, at, length))
        at += length

    model, chapters, timed, si = False, [], [], 0
    for ci, chunk in enumerate(_chunk(script.segments)):
        lines = [l for s in chunk for l in s.lines]
        if (name := f"chunk{ci:02d}.wav") in by_name:
            path, t0, length = by_name[name]
            model = _whisper() if model is False else model
            starts = [t0 + o for o in _chunk_starts(model, path, lines)]
            ends = [*starts[1:], t0 + length]
        else:  # voiced line by line: each line is its own file
            files = [by_name[f"{si + k:02d}-{li:03d}.wav"] for k, s in enumerate(chunk) for li in range(len(s.lines))]
            starts, ends = [f[1] for f in files], [f[1] + f[2] for f in files]
        k = 0
        for seg in chunk:
            chapters.append(Chapter(title=seg.title, start=starts[k]))
            k += len(seg.lines)
        timed += list(zip(lines, starts, ends))
        si += len(chunk)
    return _tidy(chapters), timed


def _tidy(chapters: list[Chapter]) -> list[Chapter]:
    """Listener-facing titles: the cold open becomes the headlines, and the sign-off, a few
    seconds long, stays part of the chapter before it."""
    if chapters and re.search(r"cold open|intro", chapters[0].title, re.I):
        chapters[0].title = "Today's headlines"
    if len(chapters) > 1 and re.search(r"sign.?off|outro|goodbye", chapters[-1].title, re.I):
        chapters.pop()
    if chapters:
        chapters[0].start = 0.0
    return chapters


def _escape(text: str) -> str:
    return re.sub(r"([=;#\\\n])", r"\\\1", text)


def embed(mp3: Path, chapters: list[Chapter]) -> None:
    """Write the chapters into the MP3 as ID3 CHAP frames, replacing any already there."""
    duration = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                     str(mp3)], capture_output=True, text=True, check=True).stdout)
    meta = mp3.with_name("chapters.txt")
    lines = [";FFMETADATA1"]
    for c, nxt in zip(chapters, [*(c.start for c in chapters[1:]), duration]):
        lines += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={round(c.start * 1000)}",
                  f"END={round(nxt * 1000)}", f"title={_escape(c.title)}"]
    meta.write_text("\n".join(lines) + "\n")
    tmp = mp3.with_suffix(".chapters.mp3")
    _ffmpeg("-i", str(mp3), "-f", "ffmetadata", "-i", str(meta), "-map", "0:a", "-map_metadata", "0",
            "-map_chapters", "1", "-c", "copy", "-id3v2_version", "3", str(tmp))
    tmp.replace(mp3)


def _vtt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def vtt(timed: list[tuple[Line, float, float]]) -> str:
    """The transcript as WebVTT: one cue per script line, with the host as the cue's voice."""
    out = ["WEBVTT", ""]
    for line, start, end in timed:
        text = line.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out += [f"{_vtt_time(start)} --> {_vtt_time(max(end, start + 0.5))}", f"<v {line.speaker}>{text}", ""]
    return "\n".join(out)


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
