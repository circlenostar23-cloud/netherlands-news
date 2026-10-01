"""Voice the script with Gemini multi-speaker TTS, then stitch to MP3.

The Gemini TTS free tier allows only 10 requests/day, so segments are packed into
a few larger requests (~4 per episode) rather than one request per segment. If Gemini
still fails (typically that daily limit), the whole episode is voiced line by line with
Microsoft neural voices instead, so the hosts never change voice mid-episode.
"""

import asyncio
import base64
import logging
import os
import subprocess
import time
from pathlib import Path

import edge_tts
from google import genai

from nlnews.config import FALLBACK_VOICES, HOSTS, TTS_MODEL
from nlnews.models import EpisodeScript, Segment

log = logging.getLogger(__name__)
SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM WAV at 24 kHz
MAX_WORDS_PER_REQUEST = 600  # ~4 minutes of audio per request
REQUEST_TIMEOUT = 180  # seconds; a healthy request takes well under this, a stuck one hangs ~4 min
GEMINI_BUDGET = 20 * 60  # seconds for all Gemini requests, leaving room for the fallback in the job limit


def _words(seg: Segment) -> int:
    return sum(len(l.text.split()) for l in seg.lines)


def _chunk(segments: list[Segment]) -> list[list[Segment]]:
    """Group consecutive segments into requests of at most MAX_WORDS_PER_REQUEST words."""
    chunks: list[list[Segment]] = []
    for seg in segments:
        if chunks and sum(map(_words, chunks[-1])) + _words(seg) <= MAX_WORDS_PER_REQUEST:
            chunks[-1].append(seg)
        else:
            chunks.append([seg])
    return chunks


def _synthesize(client: genai.Client, segments: list[Segment]) -> bytes:
    content = []
    for line in (l for seg in segments for l in seg.lines):
        meta = {"type": "speech_metadata", "speaker": line.speaker}
        if line.style:
            meta["style"] = line.style
        content.append({"type": "text", "text": line.text, "annotations": [meta]})
    interaction = client.interactions.create(
        model=TTS_MODEL,
        input=[{"type": "user_input", "content": content}],
        response_format={"type": "audio"},
        generation_config={
            "speech_config": {
                "mode": "conversational",
                "speakers": [{"speaker": name, "voice": voice} for name, voice in HOSTS.items()],
            }
        },
        timeout=REQUEST_TIMEOUT,
    )
    return base64.b64decode(interaction.output_audio.data)


def _with_retries(fn, deadline: float, attempts: int = 3):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if i == attempts - 1 or "per day" in str(exc):  # a daily limit won't clear in seconds
                raise
            if time.monotonic() > deadline:
                raise TimeoutError(f"Gemini TTS budget of {GEMINI_BUDGET // 60} min used up") from exc
            wait = 2 ** (i + 2)
            log.warning("TTS attempt %d failed (%s); retrying in %ds", i + 1, exc, wait)
            time.sleep(wait)


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def _silence(path: Path, seconds: float) -> Path:
    _ffmpeg("-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", str(seconds), "-c:a", "pcm_s16le", str(path))
    return path


def _gemini_wavs(script: EpisodeScript, seg_dir: Path) -> list[Path]:
    """One WAV per request, with a pause between them."""
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    chunks = _chunk(script.segments)
    deadline = time.monotonic() + GEMINI_BUDGET
    wavs = []
    for i, chunk in enumerate(chunks):
        path = seg_dir / f"chunk{i:02d}.wav"
        if not path.exists():  # resumable: reuse audio from an earlier partial run
            if time.monotonic() > deadline:
                raise TimeoutError(f"Gemini TTS budget of {GEMINI_BUDGET // 60} min used up")
            print(f"  TTS request {i + 1}/{len(chunks)}: {' / '.join(s.title for s in chunk)}")
            path.write_bytes(_with_retries(lambda: _synthesize(client, chunk), deadline))
        wavs.append(path)
    pause = _silence(seg_dir / "pause.wav", 0.7)
    return [p for w in wavs for p in (w, pause)][:-1]


async def _edge_line(text: str, voice: str, mp3: Path) -> None:
    for i in range(4):
        try:
            return await edge_tts.Communicate(text, voice).save(str(mp3))
        except Exception as exc:
            if i == 3:
                raise
            log.warning("Fallback TTS attempt %d failed (%s); retrying", i + 1, exc)
            await asyncio.sleep(2 ** (i + 1))


def _fallback_wavs(script: EpisodeScript, seg_dir: Path) -> list[Path]:
    """One WAV per line: a short gap between lines, a longer pause between segments."""
    line_dir = seg_dir / "fallback"
    line_dir.mkdir(exist_ok=True)
    gap, pause = _silence(line_dir / "gap.wav", 0.25), _silence(line_dir / "pause.wav", 0.7)
    out, n = [], 0
    for si, seg in enumerate(script.segments):
        print(f"  fallback TTS {si + 1}/{len(script.segments)}: {seg.title}")
        for li, line in enumerate(seg.lines):
            wav = line_dir / f"{n:03d}.wav"
            if not wav.exists():  # resumable
                mp3 = line_dir / f"{n:03d}.mp3"
                asyncio.run(_edge_line(line.text, FALLBACK_VOICES[line.speaker], mp3))
                _ffmpeg("-i", str(mp3), "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(wav))
            out += [wav, gap if li < len(seg.lines) - 1 else pause]
            n += 1
    return out[:-1]


def synthesize_episode(script: EpisodeScript, out_dir: Path, title: str) -> tuple[Path, str]:
    """Returns the MP3 and which voices were used: "gemini" or "fallback"."""
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(exist_ok=True)
    try:
        parts, voices = _gemini_wavs(script, seg_dir), "gemini"
    except Exception as exc:
        print(f"  Gemini TTS failed ({exc}); falling back to Microsoft voices")
        parts, voices = _fallback_wavs(script, seg_dir), "fallback"

    listing = out_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))

    mp3 = out_dir / "episode.mp3"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing),
            "-ac", "1", "-ar", "44100", "-b:a", "64k",
            "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing",
            str(mp3))
    return mp3, voices


def duration_seconds(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()))
