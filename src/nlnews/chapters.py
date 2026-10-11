"""Chapter markers: where each story starts in the episode. They're embedded in the MP3 as ID3
chapters, which Apple Podcasts, Overcast and Pocket Casts show, and listed in the show notes.

Gemini voices several stories in one request, so where a story starts inside a chunk isn't
known. Whisper (tiny.en, ~1.5 min for an episode on 4 cores) finds each story's first words.
Without it, or if it fails, the start is estimated from the share of the chunk's words before
it, which was up to 5 s off on ep-2026-10-11 because serious stories are read more slowly.
Either way the start then moves to the nearest pause, so a chapter never begins mid-word.
Stories voiced line by line by a backup have a file each, so their starts are exact.
"""

import array
import difflib
import re
import subprocess
import wave
from pathlib import Path

from nlnews.models import Chapter, EpisodeScript, Segment
from nlnews.tts import _chunk, _ffmpeg, _quiet, _words

WHISPER_MODEL = "tiny.en"
LEAD_IN = 0.2  # seconds of the pause kept before a story's first word


def _norm(word: str) -> str:
    return re.sub(r"[^a-z0-9]", "", word.lower())


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


def _heard_starts(model, wav: Path, segments: list[Segment]) -> list[float | None]:
    """When Whisper hears each segment's first words, or None if it doesn't recognise them."""
    import numpy as np
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    found, _ = model.transcribe(np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768,
                                language="en", word_timestamps=True, condition_on_previous_text=False)
    heard = [(_norm(w.word), w.start) for s in found for w in s.words if _norm(w.word)]
    words, firsts = [], []
    for seg in segments:
        firsts.append(len(words))
        words += [t for l in seg.lines for t in map(_norm, l.text.split()) if t]
    at = {}
    for a, b, n in difflib.SequenceMatcher(None, words, [h[0] for h in heard], autojunk=False).get_matching_blocks():
        for j in range(n):
            at[a + j] = heard[b + j][1]
    # a story's first word or one of the two after it; later than that and the start is a guess
    return [next((at[i] for i in range(f, f + 3) if i in at), None) for f in firsts]


def _chunk_starts(model, wav: Path, segments: list[Segment]) -> list[float]:
    """Where each segment starts inside one Gemini chunk, in seconds."""
    length, pauses = _pause_ends(wav)
    heard = [None] * len(segments)
    if model is not None:
        try:
            heard = _heard_starts(model, wav, segments)
        except Exception as exc:
            print(f"  Whisper failed on {wav.name} ({exc}); estimating its chapter starts")
    total, before, starts = sum(map(_words, segments)), 0, []
    for seg, t in zip(segments, heard):
        guess, within = (t, 0.6) if t is not None else (length * before / total, 10.0)
        near = [p for p in pauses if abs(p - guess) <= within]
        start = min(near, key=lambda p: abs(p - guess)) - LEAD_IN if near else guess
        starts.append(max(0.0, start) if before else 0.0)
        before += _words(seg)
    return starts


def _whisper():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    except Exception as exc:
        print(f"  Whisper unavailable ({exc}); estimating chapter starts from word counts")
        return None


def find(script: EpisodeScript, out_dir: Path) -> list[Chapter]:
    """Each segment's start in episode.mp3, read back from the list of files it was built from."""
    by_name, at = {}, 0.0  # file name -> (path, where it starts)
    for rel in re.findall(r"segments/(.+)'$", (out_dir / "concat.txt").read_text(), re.M):
        path = out_dir / "segments" / rel  # relative, so a run restored on another machine still works
        by_name.setdefault(path.name, (path, at))
        with wave.open(str(path)) as w:
            at += w.getnframes() / w.getframerate()

    model, chapters, si = False, [], 0
    for ci, chunk in enumerate(_chunk(script.segments)):
        if (name := f"chunk{ci:02d}.wav") in by_name:
            path, t0 = by_name[name]
            model = _whisper() if model is False else model
            offsets = _chunk_starts(model, path, chunk)
            chapters += [Chapter(title=s.title, start=t0 + o) for s, o in zip(chunk, offsets)]
        else:  # voiced line by line: each segment's first line is its own file
            chapters += [Chapter(title=s.title, start=by_name[f"{si + k:02d}-000.wav"][1]) for k, s in enumerate(chunk)]
        si += len(chunk)
    return _tidy(chapters)


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


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"
