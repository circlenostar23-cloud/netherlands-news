"""Voice the script with Gemini multi-speaker TTS, then stitch to MP3.

The Gemini TTS free tier allows only 10 requests/day, so segments are packed into
a few larger requests (~4 per episode) rather than one request per segment. If a request
fails for good (it times out, say), its segments are voiced line by line with the same Gemini
voices through OpenRouter (paid, and it can't do two speakers in one request), and Gemini
carries on with the next request. Gemini is dropped for the rest of the episode on the daily
limit, when the GEMINI_BUDGET runs out, or after two failed requests in a row. If OpenRouter
fails too, or isn't set up, the rest is voiced line by line with Microsoft neural voices.
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
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import edge_tts
import httpx
from google import genai

from nlnews.config import FALLBACK_VOICES, HOSTS, OPENROUTER_TTS_MODEL, TTS_MODEL
from nlnews.models import EpisodeScript, Segment

log = logging.getLogger(__name__)
SAMPLE_RATE = 24000  # Gemini TTS returns 16-bit mono PCM WAV at 24 kHz
MAX_WORDS_PER_REQUEST = 600  # ~4 minutes of audio per request
REQUEST_TIMEOUT = 180  # seconds, at least; a healthy request takes ~30 s, a stuck one hangs ~4 min
TIMEOUT_PER_WORD = 0.5  # seconds; on a slow morning a 557-word request outran 180 s (2026-10-05)
GEMINI_BUDGET = 30 * 60  # seconds for all Gemini requests, leaving room for the fallback in the job limit
OPENROUTER_BUDGET = 8 * 60  # seconds for the OpenRouter backup; a full episode takes ~2-3 min
OPENROUTER_TIMEOUT = 60  # seconds per line; a line takes ~4 s
OPENROUTER_PARALLEL = 6  # lines voiced at once


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


def _timeout(segments: list[Segment]) -> float:
    """Bigger requests get longer: 180 s up to 360 words, 300 s at the 600-word cap."""
    return max(REQUEST_TIMEOUT, TIMEOUT_PER_WORD * sum(map(_words, segments)))


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
        timeout=_timeout(segments),
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


def _edge_wavs(si: int, seg: Segment, line_dir: Path) -> list[Path]:
    """One WAV per line, voiced with Microsoft voices."""
    print(f"  Microsoft TTS: {seg.title}")
    wavs = []
    for li, line in enumerate(seg.lines):
        wav = line_dir / f"{si:02d}-{li:03d}.wav"
        if not wav.exists():  # resumable
            mp3 = wav.with_suffix(".mp3")
            asyncio.run(_edge_line(line.text, FALLBACK_VOICES[line.speaker], mp3))
            _ffmpeg("-i", str(mp3), "-ar", str(SAMPLE_RATE), "-ac", "1", "-c:a", "pcm_s16le", str(wav))
        wavs.append(wav)
    return wavs


def _openrouter_line(client: httpx.Client, line, wav: Path, deadline: float) -> None:
    """Voice one line with the host's Gemini voice through OpenRouter; two tries."""
    body = {"model": OPENROUTER_TTS_MODEL, "input": line.text, "voice": HOSTS[line.speaker], "response_format": "pcm"}
    if line.style:
        body["provider"] = {"options": {"google-ai-studio": {"speech_metadata": {"style": line.style}}}}
    for i in range(2):
        if time.monotonic() > deadline:
            raise TimeoutError(f"OpenRouter TTS budget of {OPENROUTER_BUDGET // 60} min used up")
        try:
            r = client.post("https://openrouter.ai/api/v1/audio/speech", json=body)
            if r.status_code == 200 and r.content:
                tmp = wav.with_suffix(".part")  # never leave a half-written WAV for a rerun to reuse
                with wave.open(str(tmp), "wb") as w:  # 24 kHz 16-bit mono PCM, like Gemini direct
                    w.setnchannels(1), w.setsampwidth(2), w.setframerate(SAMPLE_RATE)
                    w.writeframes(r.content)
                tmp.replace(wav)
                return
            err = RuntimeError(f"HTTP {r.status_code}: {r.text[:200]}")
            if r.status_code in (401, 402, 403):  # bad key or out of credit: retrying won't help
                raise err
        except httpx.HTTPError as exc:
            err = exc
        if i == 0:
            log.warning("OpenRouter TTS line failed (%s); retrying", err)
            time.sleep(2)
    raise err


def _openrouter_wavs(client: httpx.Client, si: int, seg: Segment, line_dir: Path, deadline: float) -> list[Path]:
    """One WAV per line, several lines at once. Raises if any line fails, so the whole segment
    can go to Microsoft voices instead of switching voices mid-story."""
    print(f"  OpenRouter TTS: {seg.title}")
    wavs = [line_dir / f"{si:02d}-{li:03d}.wav" for li in range(len(seg.lines))]
    todo = [(line, wav) for line, wav in zip(seg.lines, wavs) if not wav.exists()]  # resumable
    with ThreadPoolExecutor(OPENROUTER_PARALLEL) as pool:
        for f in [pool.submit(_openrouter_line, client, line, wav, deadline) for line, wav in todo]:
            f.result()
    return wavs


def synthesize_episode(script: EpisodeScript, out_dir: Path, title: str) -> tuple[Path, str]:
    """Voice each chunk with Gemini. A chunk whose request fails for good is voiced line by line,
    a segment at a time: through OpenRouter (same Gemini voices) until that fails, then with
    Microsoft voices. Gemini is tried again on the next chunk, unless it hit the daily limit, ran
    out of budget or failed two chunks in a row. Switches fall in the pause between stories, and
    once Microsoft voices are in use Gemini isn't tried again. Returns the MP3 and which
    engines were used, e.g. "gemini", "gemini+openrouter" or "gemini+openrouter+microsoft"."""
    seg_dir = out_dir / "segments"
    or_dir, ms_dir = seg_dir / "openrouter", seg_dir / "fallback"
    for d in (or_dir, ms_dir):
        d.mkdir(parents=True, exist_ok=True)
    gap, pause = _silence(seg_dir / "gap.wav", 0.25), _silence(seg_dir / "pause.wav", 0.7)

    client, gemini_ok, failed, used, parts, si = None, True, 0, set(), [], 0
    or_key = os.environ.get("OPENROUTER_API_KEY")
    or_client, or_deadline = None, None
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
                failed = 0
            except Exception as exc:
                failed += 1
                # without OpenRouter the backup is Microsoft voices, and the hosts shouldn't change back
                gemini_ok = bool(or_key) and failed < 2 and "per day" not in str(exc) and time.monotonic() < deadline
                backup = "OpenRouter" if or_key else "Microsoft voices"
                print(f"  Gemini TTS failed ({exc}); voicing {'this part' if gemini_ok else 'the rest'} line by line with {backup}")
        if path.exists():
            parts += [path, pause]
            used.add("gemini")
            si += len(chunk)
            continue
        for seg in chunk:
            wavs = None
            if or_key:
                try:
                    if or_client is None:
                        or_client = httpx.Client(headers={"Authorization": f"Bearer {or_key}"}, timeout=OPENROUTER_TIMEOUT)
                        or_deadline = time.monotonic() + OPENROUTER_BUDGET
                    wavs = _openrouter_wavs(or_client, si, seg, or_dir, or_deadline)
                    used.add("openrouter")
                except Exception as exc:
                    print(f"  OpenRouter TTS failed ({exc}); voicing the rest with Microsoft voices")
                    or_key, gemini_ok = None, False
            if wavs is None:
                wavs = _edge_wavs(si, seg, ms_dir)
                used.add("microsoft")
            for wav in wavs:
                parts += [wav, gap]
            parts[-1] = pause
            si += 1
    if or_client:
        or_client.close()

    listing = out_dir / "concat.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts[:-1]))

    mp3 = out_dir / "episode.mp3"
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(listing),
            "-ac", "1", "-ar", "44100", "-b:a", "64k",
            "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing",
            str(mp3))
    return mp3, "+".join(e for e in ("gemini", "openrouter", "microsoft") if e in used)


def duration_seconds(path: Path) -> int:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    )
    return round(float(out.stdout.strip()))
