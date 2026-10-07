"""Health check for one day's published episode.

Checks the workflow run and its log (retries, backup voices, writer fallbacks, unanswered
research questions), the release, the live feed and its MP3, and the audio itself (length,
pace, long silences, loudness). With --voices it also downloads the run's working files and
checks every script line: that it's in the audio, and that it's in the right host's voice.

    .venv/bin/python scripts/health_check.py              # today's episode
    .venv/bin/python scripts/health_check.py 2026-10-07 --voices

--voices needs `pip install -e '.[check]'` (faster-whisper and numpy) and takes a few minutes.
The working files are kept for 7 days after the run; pass --data to use a local copy instead.
Exits 1 if any check fails; warnings alone exit 0.
"""

import argparse
import difflib
import json
import re
import statistics
import subprocess
import sys
import tempfile
import urllib.request
import wave
import xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

from nlnews import publish
from nlnews.config import DATA_DIR, HOSTS, TZ
from nlnews.models import EpisodeScript
from nlnews.tts import _chunk

WORKFLOW = "episode.yml"
SLOW_RUN = 18 * 60  # seconds; a clean run takes 12-13 min, a TTS timeout adds 3-10
WPM = (140, 185)  # observed pace is 148-180 words a minute; slower or faster suggests lost or repeated audio
LONG_SILENCE = 1.5  # seconds; pauses are capped at 1.0 when the audio is built
MIN_MATCHED = 0.5  # share of a line's words found in the transcript; numbers are heard as digits and lower it
ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"

results: list[str] = []
seen: dict[str, int] = {}  # numbers one check reads for a later one


def report(level: str, text: str) -> None:
    results.append(level)
    print(f"  {level:<4} {text}")


def _run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _gh_json(*args: str):
    return json.loads(_run("gh", *args).stdout)


def _clock(seconds: float) -> str:
    return f"{int(seconds) // 60}:{int(seconds) % 60:02d}"


def check_run(day: date) -> int | None:
    """Report on the day's run that built the episode. Returns its id."""
    print("Workflow run")
    runs = _gh_json("run", "list", "--workflow", WORKFLOW, "-L", "30",
                    "--json", "databaseId,conclusion,status,createdAt,updatedAt")
    stamp = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    todays = [r for r in runs if stamp(r["createdAt"]).astimezone(TZ).date() == day]
    if not todays:
        report("FAIL", f"no {WORKFLOW} run started on {day} (Amsterdam time)")
        return None
    for r in todays:
        if r["conclusion"] in ("failure", "cancelled", "timed_out"):
            report("warn", f"run {r['databaseId']} ended as {r['conclusion']}")
    # later triggers skip at the gate once the episode is out, so the builder is the run whose log has an audio line
    for r in todays:
        if r["status"] != "completed":
            report("warn", f"run {r['databaseId']} is still {r['status']}")
            continue
        log = [l.split("\t", 2)[-1][29:] for l in _run("gh", "run", "view", str(r["databaseId"]), "--log", check=False).stdout.splitlines()]
        audio = next((l for l in log if l.startswith("  audio: ")), None)
        if not audio:
            continue
        took = (stamp(r["updatedAt"]) - stamp(r["createdAt"])).total_seconds()
        started = stamp(r["createdAt"]).astimezone(TZ).strftime("%H:%M")
        report("warn" if took > SLOW_RUN else "ok", f"run {r['databaseId']} succeeded: started {started}, took {_clock(took)}")
        check_log(log, audio)
        return r["databaseId"]
    report("FAIL", f"none of the {len(todays)} run(s) on {day} produced audio")
    return None


def check_log(log: list[str], audio: str) -> None:
    empty = [l.split()[1] for l in log if re.search(r"\s0 items$", l)]
    articles = next((l.strip() for l in log if re.fullmatch(r"\s+\d+ articles", l)), "? articles")
    report("warn" if empty else "ok", articles + (f"; no items from {', '.join(empty)}" if empty else ""))

    fallbacks = [l.strip() for l in log if "falling back to Gemini" in l]
    report("warn" if fallbacks else "ok", f"writer fell back to Gemini {len(fallbacks)} time(s)" if fallbacks else "writer: no fallback to Gemini")
    for l in log:
        if re.search(r"research failed|agenda failed|handoff rewrite|story breaks still", l):
            report("warn", l.strip()[:160])

    answered, unanswered = (sum(l.startswith(f"    {mark} ") for l in log) for mark in "✓?")
    if answered + unanswered:
        report("ok", f"research: {answered} of {answered + unanswered} open questions answered")
    script = next((l.strip() for l in log if l.startswith("  script: ")), None)
    if script:
        report("ok", script)
        seen["words"] = int(script.split()[1])

    retries = [l for l in log if l.startswith("TTS attempt")]
    if retries:
        report("warn", f"{len(retries)} Gemini TTS attempt(s) failed and were retried: {retries[0].split('(')[1][:60]}")
    for l in log:
        if "Gemini TTS failed" in l or "OpenRouter TTS failed" in l:
            report("warn", l.strip()[:160])
    voices = re.search(r", ([\w+ ]+) voices\)", audio)
    voices = voices.group(1) if voices else "unknown"
    report("ok" if voices == "gemini" else "warn", f"voices: {voices}")


def check_release(day: date) -> dict | None:
    print("Release")
    tag = f"ep-{day}"
    try:
        rel = _gh_json("release", "view", tag, "--json", "name,body,assets,isDraft")
    except subprocess.CalledProcessError:
        report("FAIL", f"no release {tag}")
        return None
    sizes = {a["name"]: a["size"] for a in rel["assets"]}
    report("FAIL" if rel["isDraft"] else "ok", f"{tag}: {rel['name']}" + (" (still a draft)" if rel["isDraft"] else ""))
    for name in ("episode.mp3", "briefing.md"):
        report("ok" if sizes.get(name) else "FAIL", f"{name}: {sizes[name] / 1e3:,.0f} kB" if sizes.get(name) else f"{name} is missing")
    meta = publish.META.search(rel["body"] or "")
    return {"mp3_size": sizes.get("episode.mp3"), "duration": json.loads(meta.group(1))["duration"] if meta else None}


def check_feed(day: date, release: dict | None) -> str | None:
    """Check the live feed's entry for the day. Returns the MP3's URL."""
    print("Feed")
    url = publish.feed_url()
    if not url:
        report("warn", "skipped: SITE_BASE_URL and FEED_SECRET_PATH aren't set in .env")
        return None
    try:
        channel = ET.fromstring(urllib.request.urlopen(url, timeout=30).read()).find("channel")
    except Exception as exc:
        report("FAIL", f"feed didn't load: {exc}")
        return None
    items = channel.findall("item")
    item = next((i for i in items if f"ep-{day}" in i.find("enclosure").get("url")), None)
    if item is None:
        report("FAIL", f"feed has {len(items)} episodes but not ep-{day}")
        return None
    stale = day == datetime.now(TZ).date() and item is not items[0]
    report("warn" if stale else "ok", item.findtext("title")[:70] + (" (not the newest item)" if stale else ""))
    enclosure = item.find("enclosure")
    try:
        head = urllib.request.urlopen(urllib.request.Request(enclosure.get("url"), method="HEAD"), timeout=30)
        served = int(head.headers["Content-Length"])
    except Exception as exc:
        report("FAIL", f"MP3 link didn't load: {exc}")
        return None
    sizes = {served, int(enclosure.get("length"))} | ({release["mp3_size"]} if release and release["mp3_size"] else set())
    report("ok" if len(sizes) == 1 else "FAIL", f"MP3 link works, {served / 1e6:.1f} MB" + ("" if len(sizes) == 1 else f"; sizes disagree across feed, link and release: {sorted(sizes)}"))
    if release and release["duration"] and str(release["duration"]) != item.findtext(f"{ITUNES}duration"):
        report("warn", f"feed duration {item.findtext(f'{ITUNES}duration')} s differs from the release's {release['duration']} s")
    return enclosure.get("url")


def check_audio(mp3: str, words: int | None) -> None:
    """mp3 is a path or URL; ffmpeg reads either."""
    print("Audio")
    duration = float(_run("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3).stdout)
    out = _run("ffmpeg", "-hide_banner", "-nostats", "-i", mp3,
               "-af", f"silencedetect=noise=-40dB:d={LONG_SILENCE},ebur128=peak=true", "-f", "null", "-").stderr
    if words:
        wpm = words / duration * 60
        report("ok" if WPM[0] <= wpm <= WPM[1] else "warn", f"{_clock(duration)} long, {words} words, {wpm:.0f} words a minute")
    else:
        report("ok", f"{_clock(duration)} long")
    silences = [(float(s), float(d)) for s, d in re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", out)]
    report("warn" if silences else "ok", f"{len(silences)} silence(s) of {LONG_SILENCE} s or longer"
           + "".join(f"; {d:.1f} s ending at {_clock(end)}" for end, d in silences[:5]))
    summary = out[out.rfind("Summary:"):]
    loudness, peak = re.search(r"I:\s+(-?[\d.]+) LUFS", summary), re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    if loudness and peak:
        report("ok", f"loudness {loudness.group(1)} LUFS, peak {peak.group(1)} dBFS")


# --- voices: is each line in the audio, and in the right host's voice? ---

_norm = lambda w: re.sub(r"[^a-z0-9]", "", w.lower())


def _pitch(x, sr: int) -> float:
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


def _timbre(x, sr: int):
    """Mean of 19 mel cepstral coefficients over the loud frames: the voice's colour, apart from its pitch."""
    import numpy as np
    n, hop, mels = 1024, 256, 40
    if len(x) < n + 8 * hop:
        return None
    mel, hz = lambda f: 2595 * np.log10(1 + f / 700), lambda m: 700 * (10 ** (m / 2595) - 1)
    b = np.floor((n + 1) * hz(np.linspace(mel(60), mel(8000), mels + 2)) / sr).astype(int)
    bank = np.zeros((mels, n // 2 + 1))
    for j in range(mels):
        bank[j, b[j]:b[j + 1]] = np.linspace(0, 1, b[j + 1] - b[j], endpoint=False)
        bank[j, b[j + 1]:b[j + 2]] = np.linspace(1, 0, b[j + 2] - b[j + 1], endpoint=False)
    dct = np.cos(np.pi * np.outer(np.arange(1, 20), np.arange(mels) + .5) / mels)
    frames = x[np.arange(0, len(x) - n, hop)[:, None] + np.arange(n)] * np.hanning(n)
    loud = np.sqrt((frames ** 2).mean(1)) > 0.03
    if loud.sum() < 8:
        return None
    return (np.log(np.abs(np.fft.rfft(frames[loud])) ** 2 @ bank.T + 1e-9) @ dct.T).mean(0)


def _other_host_scores(feats, labels):
    """Score each line against a two-voice model fitted on all the other lines (labels from the
    script). Positive means it sounds like the second host. A swapped line scores on the wrong side."""
    import numpy as np
    X, y, scores = np.array(feats), np.array(labels), []
    for i in range(len(X)):
        keep = np.arange(len(X)) != i
        Xt, yt = X[keep], y[keep]
        m0, m1 = Xt[yt == 0].mean(0), Xt[yt == 1].mean(0)
        within = np.cov(Xt[yt == 0].T) + np.cov(Xt[yt == 1].T) + 1e-3 * np.eye(X.shape[1])
        w = np.linalg.solve(within, m1 - m0)
        scores.append(float((X[i] - (m0 + m1) / 2) @ w / ((Xt - (m0 + m1) / 2) @ w).std()))
    return scores


def fetch_working_files(day: date, run_id: int | None, tmp: Path) -> Path | None:
    local = DATA_DIR / day.isoformat()
    if (local / "script.json").exists() and any((local / "segments").glob("chunk*.wav")):
        return local
    if not run_id:
        return None
    got = _run("gh", "run", "download", str(run_id), "-n", "episode-data", "-D", str(tmp), check=False)
    return tmp / day.isoformat() if got.returncode == 0 and (tmp / day.isoformat() / "script.json").exists() else None


def check_voices(data: Path, model_name: str) -> None:
    print("Voices")
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        report("FAIL", "needs faster-whisper and numpy: pip install -e '.[check]'")
        return
    script = EpisodeScript.model_validate_json((data / "script.json").read_text())
    hosts = list(HOSTS)
    # where each audio file starts in the episode, from the list the MP3 was built from
    starts, at = {}, 0.0
    for name in re.findall(r"segments/([^']+)'", (data / "concat.txt").read_text()):
        starts.setdefault(name, at)
        with wave.open(str(data / "segments" / name)) as w:
            at += w.getnframes() / w.getframerate()

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    lines, skipped = [], 0  # (episode time, speaker, text, share of words matched, pitch, timbre)
    for ci, chunk in enumerate(_chunk(script.segments)):
        path = data / "segments" / f"chunk{ci:02d}.wav"
        if path.name not in starts:  # voiced line by line by a backup, so each line had its own request
            skipped += sum(len(s.lines) for s in chunk)
            continue
        with wave.open(str(path)) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ar", "16000", "-ac", "1", "-f", "s16le", "-"],
                             capture_output=True, check=True).stdout
        heard_segments, _ = model.transcribe(np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768,
                                             language="en", word_timestamps=True, condition_on_previous_text=False)
        heard = [(_norm(w.word), w.start, w.end) for s in heard_segments for w in s.words if _norm(w.word)]
        chunk_lines = [l for s in chunk for l in s.lines]
        words, owner = [], []
        for k, l in enumerate(chunk_lines):
            for t in filter(None, map(_norm, l.text.split())):
                words.append(t)
                owner.append(k)
        spans: dict[int, list] = {}
        for a, b, n in difflib.SequenceMatcher(None, words, [h[0] for h in heard], autojunk=False).get_matching_blocks():
            for j in range(n):
                spans.setdefault(owner[a + j], []).append(heard[b + j])
        for k, l in enumerate(chunk_lines):
            found = spans.get(k, [])
            if not found:
                lines.append((None, l.speaker, l.text, 0.0, 0.0, None))
                continue
            clip = x[int(found[0][1] * sr):int(found[-1][2] * sr)]
            lines.append((starts[path.name] + found[0][1], l.speaker, l.text, len(found) / owner.count(k), _pitch(clip, sr), _timbre(clip, sr)))
    if not lines:
        report("warn", "skipped: no Gemini-voiced chunks to check")
        return
    if skipped:
        report("warn", f"{skipped} lines were voiced one request each by a backup and weren't checked")

    missing = [l for l in lines if l[0] is None]
    partial = [l for l in lines if l[0] is not None and l[3] < MIN_MATCHED]
    report("FAIL" if missing else "ok", f"{len(lines) - len(missing)} of {len(lines)} lines found in the audio")
    for l in missing:
        print(f"         not heard: {l[1]}: {l[2][:90]}")
    for l in partial:
        report("warn", f"{_clock(l[0])} {l[1]}: only {l[3]:.0%} of the words matched: {l[2][:70]}")

    by_host = {h: [l[4] for l in lines if l[1] == h and l[4]] for h in hosts}
    if all(by_host.values()):
        medians = {h: statistics.median(v) for h, v in by_host.items()}
        print("         pitch: " + ", ".join(f"{h} {m:.0f} Hz" for h, m in medians.items()))
    for l in lines:
        if l[0] is not None and re.search(rf"\bI'm ({'|'.join(hosts)})\b", l[2]):
            print(f"         host names at {_clock(l[0])}: \"{l[2][:60]}\" by {l[1]}, {l[4]:.0f} Hz")

    scored = [l for l in lines if l[5] is not None]
    counts = [sum(l[1] == h for l in scored) for h in hosts]
    if min(counts) < 15:
        report("warn", f"too few lines to model the two voices ({counts[0]} and {counts[1]}); voice check skipped")
        return
    scores = _other_host_scores([l[5] for l in scored], [hosts.index(l[1]) for l in scored])
    swapped = [(l, s) for l, s in zip(scored, scores) if (s > 0) != (l[1] == hosts[1])]
    report("FAIL" if swapped else "ok", f"{len(scored) - len(swapped)} of {len(scored)} lines are in the voice the script gives them")
    for l, s in swapped:
        print(f"         {_clock(l[0])} script says {l[1]}, sounds like {hosts[1 - hosts.index(l[1])]} ({l[4]:.0f} Hz): {l[2][:70]}")
    closest = min(zip(scored, scores), key=lambda p: abs(p[1]))
    if not swapped:
        print(f"         closest call: {_clock(closest[0][0])} {closest[0][1]}: {closest[0][2][:60]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("day", nargs="?", type=date.fromisoformat, default=datetime.now(TZ).date(), help="YYYY-MM-DD, default today")
    ap.add_argument("--voices", action="store_true", help="also check each line is in the audio and in the right voice")
    ap.add_argument("--data", type=Path, help="the day's working files, instead of downloading them from the run")
    ap.add_argument("--model", default="small", help="faster-whisper model for --voices (default: small)")
    args = ap.parse_args()

    print(f"Episode {args.day}")
    run_id = check_run(args.day)
    release = check_release(args.day)
    mp3 = check_feed(args.day, release)
    with tempfile.TemporaryDirectory() as tmp:
        data = args.data
        if args.voices and not data:
            data = fetch_working_files(args.day, run_id, Path(tmp))
        words = seen.get("words")
        if data and (data / "script.json").exists():
            script = EpisodeScript.model_validate_json((data / "script.json").read_text())
            words = sum(len(l.text.split()) for s in script.segments for l in s.lines)
        if data and (data / "episode.mp3").exists():
            mp3 = mp3 or str(data / "episode.mp3")
        if mp3:
            check_audio(mp3, words)
        if args.voices:
            if data:
                check_voices(data, args.model)
            else:
                print("Voices")
                report("FAIL", "no working files: the run's episode-data artifact is gone (kept 7 days); pass --data")

    fails, warns = results.count("FAIL"), results.count("warn")
    print(f"\n{'FAILED' if fails else 'Healthy'}: {fails} failed, {warns} warning(s), {results.count('ok')} ok")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
