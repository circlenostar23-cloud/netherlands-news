"""Voice the script with Gemini multi-speaker TTS, then stitch to MP3.

The Gemini TTS free tier allows only 10 requests/day, so segments are packed into
a few larger requests (~4 per episode) rather than one request per segment.
"""

import base64
import logging
import os
import subprocess
import time
from pathlib import Path

from google import genai

from nlnews.config import HOSTS, TTS_MODEL
from nlnews.models import EpisodeScript, Segment

log = logging.getLogger(__name__)
SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM WAV at 24 kHz
MAX_WORDS_PER_REQUEST = 600  # ~4 minutes of audio per request


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
    )
    return base64.b64decode(interaction.output_audio.data)


def _with_retries(fn, attempts: int = 4):
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            if i == attempts - 1:
                raise
            wait = 2 ** (i + 2)
            log.warning("TTS attempt %d failed (%s); retrying in %ds", i + 1, exc, wait)
            time.sleep(wait)


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def synthesize_episode(script: EpisodeScript, out_dir: Path, title: str) -> Path:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(exist_ok=True)

    chunks = _chunk(script.segments)
    wavs = []
    for i, chunk in enumerate(chunks):
        path = seg_dir / f"chunk{i:02d}.wav"
        if not path.exists():  # resumable: reuse audio from an earlier partial run
            print(f"  TTS request {i + 1}/{len(chunks)}: {' / '.join(s.title for s in chunk)}")
            path.write_bytes(_with_retries(lambda: _synthesize(client, chunk)))
        wavs.append(path)

    pause = seg_dir / "pause.wav"
    _ffmpeg("-f", "lavfi", "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", "0.7", "-c:a", "pcm_s16le", str(pause))

    listing = out_dir / "concat.txt"
    entries = []
    for w in wavs:
        entries += [f"file '{w.resolve()}'", f"file '{pause.resolve()}'"]
    listing.write_text("\n".join(entries[:-1]) + "\n")

    mp3 = out_dir / "episode.mp3"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing),
            "-ac", "1", "-ar", "44100", "-b:a", "64k",
            "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing",
            str(mp3))
    return mp3


def duration_seconds(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()))
