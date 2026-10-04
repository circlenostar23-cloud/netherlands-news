"""One-off OpenRouter TTS test: voice a short two-host excerpt with several models.

Checks whether Gemini 3.8 Flash TTS on OpenRouter can voice both hosts in one request
(OpenRouter's speech endpoint takes a single `input` and `voice`, and forwards unknown
Google options as generation config), and voices the same excerpt line by line with other
speech models to compare. Writes one MP3 per variant and results.md to the output folder.

    OPENROUTER_API_KEY=... python scripts/tts_test.py out/ [only]
"""

import io
import json
import os
import subprocess
import sys
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx

API = "https://openrouter.ai/api/v1"
SAMPLE_RATE = 24000

# 2026-10-04, cleaners' strike story. Line 8 came out in Sam's voice in that episode.
LINES = [
    ("Sam", "While we're on stations, the cleaners who struck there last month are getting ready to strike again."),
    ("Maya", "The union FNV says there'll be new strikes, because employers won't come back to the table. And Sam, this is really a story about two unions."),
    ("Sam", "Right. Most Dutch sectors run on a cao, a collective labour agreement. It sets wages and conditions for the whole industry, whether you're in a union or not. And there are several unions. FNV is the biggest, and it leans left. CNV is smaller, with Christian roots."),
    ("Maya", "And the employers signed with CNV."),
    ("Sam", "On the first of September. The employers' association, Schoonmakend Nederland, did a deal with CNV that runs until mid-2028, and FNV was left out. Now the employers say a finished cao isn't a starting point for new talks."),
    ("Maya", "So what's actually in it?"),
    ("Sam", "Pay goes up 3.1 percent this coming January and 3 percent the January after. The starting wage becomes sixteen euros an hour. And about 85,000 cleaners who never got a travel allowance will now get one."),
    ("Maya", "That doesn't sound terrible. So why did FNV members say no?"),
    ("Sam", "More than 80 percent of them voted it down. A big reason is sick pay: the deal cuts it for people with less than six years in the sector. FNV wants no loss of income when you're ill, automatic inflation adjustment, a bigger raise, and the same allowances for hotel cleaners."),
    ("Maya", "And they've already tried striking."),
    ("Sam", "In mid-September they held a five-day strike at Schiphol, train stations and universities. About 800 cleaners took part, and hundreds rallied outside the Utrecht head office of the cleaning company Asito. But Schiphol and NS reported little disruption, and the employers didn't budge."),
    ("Maya", "So when's the next one?"),
]
DIALOGUE = "\n".join(f"{who}: {text}" for who, text in LINES)

GEMINI = "google/gemini-3.8-flash-tts"
SPEAKERS_A = {"speech_config": {"mode": "conversational", "speakers": [
    {"speaker": "Maya", "voice": "Kore"}, {"speaker": "Sam", "voice": "Puck"}]}}
SPEAKERS_B = {"speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
    {"speaker": "Maya", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}},
    {"speaker": "Sam", "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Puck"}}}]}}}

# Whole excerpt in one request: does Gemini on OpenRouter give each host their own voice?
ONE_REQUEST = {
    "gemini-multi-a": {"voice": "Kore", "options": SPEAKERS_A},
    "gemini-multi-a-novoice": {"voice": None, "options": SPEAKERS_A},
    "gemini-multi-b": {"voice": "Kore", "options": SPEAKERS_B},
    "gemini-multi-b-novoice": {"voice": None, "options": SPEAKERS_B},
}

# One request per line: model -> (Maya's voice, Sam's voice)
PER_LINE = {
    GEMINI: ("Kore", "Puck"),
    "microsoft/mai-voice-2.1": ("en-US-Harper:MAI-Voice-2.1", "en-US-Grant:MAI-Voice-2.1"),
    "minimax/speech-2.8-hd": ("English_Upbeat_Woman", "English_Trustworth_Man"),
    "deepgram/aura-2": ("aura-2-thalia-en", "aura-2-apollo-en"),
    "x-ai/grok-voice-tts-1.0": ("eve", "rex"),
    "mistralai/voxtral-mini-tts-2603": ("gb_jane_neutral", "en_paul_neutral"),
    "sesame/csm-1b": ("conversational_a", "conversational_b"),
}


def speak(client: httpx.Client, model: str, text: str, voice: str | None, options: dict | None = None) -> tuple[bytes, str]:
    """Returns the audio as 24 kHz 16-bit mono PCM, and the generation id."""
    body = {"model": model, "input": text, "response_format": "pcm" if model.startswith("google/") else "mp3"}
    if voice:
        body["voice"] = voice
    if options:
        body["provider"] = {"options": {"google-ai-studio": options}}
    r = client.post(f"{API}/audio/speech", json=body)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    audio = r.content if "pcm" in r.headers.get("content-type", "") else to_pcm(r.content)  # pcm: 24 kHz 16-bit mono
    return audio, r.headers.get("x-generation-id", "")


def to_pcm(mp3: bytes) -> bytes:
    out = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ac", "1",
                          "-ar", str(SAMPLE_RATE), "pipe:1"], input=mp3, capture_output=True, check=True)
    return out.stdout


def save_mp3(pcm: bytes, path: Path) -> float:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "wav", "-i", "pipe:0", "-b:a", "96k", str(path)],
                   input=buf.getvalue(), check=True)
    return len(pcm) / 2 / SAMPLE_RATE


def cost(client: httpx.Client, gen_ids: list[str]) -> float | None:
    total = 0.0
    for gid in filter(None, gen_ids):
        for _ in range(5):  # generation stats can take a moment to appear
            r = client.get(f"{API}/generation", params={"id": gid})
            if r.status_code == 200:
                total += r.json()["data"].get("total_cost") or 0
                break
            time.sleep(2)
        else:
            return None
    return total


def run(client: httpx.Client, name: str, out: Path) -> dict:
    start, gen_ids = time.monotonic(), []
    try:
        if name in ONE_REQUEST:
            v = ONE_REQUEST[name]
            pcm, gid = speak(client, GEMINI, DIALOGUE, v["voice"], v["options"])
            gen_ids.append(gid)
        else:
            gap, pcm = b"\0\0" * int(0.25 * SAMPLE_RATE), b""
            for who, text in LINES:
                audio, gid = speak(client, name, text, PER_LINE[name][who != "Maya"])
                gen_ids.append(gid)
                pcm += audio + gap
        seconds = save_mp3(pcm, out / f"{name.replace('/', '_')}.mp3")
        return {"name": name, "ok": True, "wall": time.monotonic() - start, "audio": seconds,
                "cost": cost(client, gen_ids)}
    except Exception as exc:
        return {"name": name, "ok": False, "wall": time.monotonic() - start, "error": str(exc)}


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "tts-test")
    only = sys.argv[2] if len(sys.argv) > 2 else ""  # e.g. "gemini" runs only variants with that in the name
    out.mkdir(parents=True, exist_ok=True)
    headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
    with httpx.Client(headers=headers, timeout=180) as client, ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda n: run(client, n, out), [n for n in [*ONE_REQUEST, *PER_LINE] if only in n]))
    words = sum(len(t.split()) for _, t in LINES)
    rows = [f"Excerpt: {len(LINES)} lines, {words} words.\n",
            "| Variant | Result | Wall time | Audio | Cost |", "| - | - | - | - | - |"]
    for r in results:
        if r["ok"]:
            c = "?" if r["cost"] is None else f"${r['cost']:.4f}"
            rows.append(f"| {r['name']} | ok | {r['wall']:.0f} s | {r['audio']:.0f} s | {c} |")
        else:
            rows.append(f"| {r['name']} | failed: {r['error'][:200].replace('|', '/')} | {r['wall']:.0f} s | | |")
    report = "\n".join(rows) + "\n"
    (out / "results.md").write_text(report)
    (out / "results.json").write_text(json.dumps(results, indent=2))
    print(report)


if __name__ == "__main__":
    main()
