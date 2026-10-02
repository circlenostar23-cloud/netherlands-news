"""Voice the script with Gemini multi-speaker TTS, then stitch to MP3.

The Gemini TTS free tier allows only 10 requests/day, so segments are packed into
a few larger requests (~4 per episode) rather than one request per segment. If Gemini
fails partway (that daily limit, a request that times out, or the GEMINI_BUDGET running
out), the remaining segments are voiced line by line with Microsoft neural voices, so the
episode keeps Gemini's voices for as long as it can.
"""

import array
import asyncio
import base64
import io
import logging
import os
import subprocess
import time
import wave
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


def _cap_pauses(wav: bytes, longest: float = 1.0, keep: float = 0.7, floor_db: float = -55) -> bytes:
    """Shorten silences longer than `longest` seconds to `keep` seconds. Gemini sometimes leaves
    ~2 s of dead air mid-line (2026-10-02, before the last sentence of the Ebola story)."""
    with wave.open(io.BytesIO(wav)) as w:
        params, samples = w.getparams(), array.array("h", w.readframes(w.getnframes()))
    win = params.framerate // 50  # 20 ms
    floor = (32768 * 10 ** (floor_db / 20)) ** 2 * win
    quiet = [sum(s * s for s in samples[i:i + win]) < floor for i in range(0, len(samples), win)]
    out, start, run = array.array("h"), 0, 0  # run = consecutive quiet windows
    for i, q in enumerate(quiet + [False]):
        if q:
            run += 1
            continue
        if run * win > longest * params.framerate:  # cut the middle of the silence, keep its edges
            a, b = (i - run) * win, i * win
            half = int(keep * params.framerate) // 2
            out += samples[start:a + half]
            start = b - half
        run = 0
    out += samples[start:]
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setparams(params)
        w.writeframes(out.tobytes())
    return buf.getvalue()


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


async def _edge_line(text: str, voice: str, mp3: Path) -> None:
    for i in range(4):
        try:
            return await edge_tts.Communicate(text, voice).save(str(mp3))
        except Exception as exc:
            if i == 3:
                raise
            log.warning("Fallback TTS attempt %d failed (%s); retrying", i + 1, exc)
            await asyncio.sleep(2 ** (i + 1))


def _fallback_wavs(segments: list[tuple[int, Segment]], line_dir: Path, gap: Path, pause: Path) -> list[Path]:
    """One WAV per line: a short gap between lines, a longer pause between segments."""
    out = []
    for si, seg in segments:
        print(f"  fallback TTS: {seg.title}")
        for li, line in enumerate(seg.lines):
            wav = line_dir / f"{si:02d}-{li:03d}.wav"
            if not wav.exists():  # resumable
                mp3 = wav.with_suffix(".mp3")
                asyncio.run(_edge_line(line.text, FALLBACK_VOICES[line.speaker], mp3))
                _ffmpeg("-i", str(mp3), "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(wav))
            out += [wav, gap if li < len(seg.lines) - 1 else pause]
    return out[:-1]


def synthesize_episode(script: EpisodeScript, out_dir: Path, title: str) -> tuple[Path, str]:
    """Voice each chunk with Gemini until a request fails for good, then voice the rest line by line
    with Microsoft voices. Chunks end on segment boundaries, so any switch falls in the pause
    between stories. Returns the MP3 and which voices were used: "gemini", "mixed" or "fallback"."""
    seg_dir = out_dir / "segments"
    line_dir = seg_dir / "fallback"
    line_dir.mkdir(parents=True, exist_ok=True)
    gap, pause = _silence(seg_dir / "gap.wav", 0.25), _silence(seg_dir / "pause.wav", 0.7)

    client, gemini_ok, used, parts, si = None, True, set(), [], 0
    chunks = _chunk(script.segments)
    deadline = time.monotonic() + GEMINI_BUDGET
    for i, chunk in enumerate(chunks):
        path = seg_dir / f"chunk{i:02d}.wav"
        if gemini_ok and not path.exists():  # resumable: reuse audio from an earlier partial run
            try:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Gemini TTS budget of {GEMINI_BUDGET // 60} min used up")
                print(f"  TTS request {i + 1}/{len(chunks)}: {' / '.join(s.title for s in chunk)}")
                client = client or genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
                path.write_bytes(_cap_pauses(_with_retries(lambda: _synthesize(client, chunk), deadline)))
            except Exception as exc:
                print(f"  Gemini TTS failed ({exc}); voicing the rest with Microsoft voices")
                gemini_ok = False
        if path.exists():
            parts.append(path)
            used.add("gemini")
        else:
            parts += _fallback_wavs(list(enumerate(chunk, si)), line_dir, gap, pause)
            used.add("fallback")
        parts.append(pause)
        si += len(chunk)

    listing = out_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts[:-1]))

    mp3 = out_dir / "episode.mp3"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing),
            "-ac", "1", "-ar", "44100", "-b:a", "64k",
            "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing",
            str(mp3))
    return mp3, "mixed" if len(used) > 1 else used.pop()


def duration_seconds(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()))
