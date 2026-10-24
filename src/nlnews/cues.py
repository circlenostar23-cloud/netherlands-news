"""Short musical cues at the episode's breaks, so a half-listening listener hears that the show has
moved on (docs/transition-sounds.md).

  intro    the cold open's first sentence dry, a sting LAND_AFTER its last word, the rest of the cold
           open over a bed, and the intro theme LAND_AFTER the cold open's last word. On a sombre day
           (the selection's `mood`) the bed, sting and theme are the sombre ones
  stories  a cue before each later story, chosen by its `kind` and rotating within it; a major hard
           story (by its airtime) gets hard-4 or hard-4-short
  outro    the between loop fades in under the last story's end, What's on's theme lands after its
           last word, the hosts start over the theme's last bars, the between bed runs on under
           What's on and the sign-off, and the button lands LAND_AFTER the last word

The cues are files in assets/cues: `hard-*.wav` and `light-*.wav` (any number of each), and the
themes `intro.wav`, `sombre-intro.wav`, `section.wav` and `button.wav`, whose downbeat is LEAD
seconds in. A missing one is skipped. They're set to sit CUE_UNDER dB under the voices and peak at no
more than PEAK dBFS here, so their own level doesn't matter.

The beds are fitted to the day: built back from where their theme lands, with the bar length nearest
their own tempo that fits a whole number of bars. They're assembled from stems in assets/cues/beds,
one beat each, rendered on a Mac with Logic's sounds (docs/transition-sounds/render-cues.py), and
laid on the fitted beats. A bed inserts no time; the sting and the themes do.

Gemini voices several stories per file, so a cue goes in at the story's start as the chapter step
found it, and only where that start was heard: an estimate can be seconds off, and a cue mid-story
is worse than none. The MP3 is rebuilt from the voiced files each time, so a rerun never adds cues
twice.
"""

import difflib
import json
import math
import re
import subprocess
import wave
from datetime import date
from pathlib import Path

import numpy as np

from nlnews.chapters import _norm, segment_files

CUES = Path(__file__).resolve().parents[2] / "assets" / "cues"
BEDS = CUES / "beds"
RATE = 44100
CUE_UNDER = 7  # dB under the voices
PEAK = -9  # dBFS
BEFORE = 0.25  # seconds of quiet added before a story cue
UNDER_NEXT = 0.6  # seconds of a cue's ring-out that runs under the next host's first words
BREATH_BACK = 0.8  # seconds before a heard word to look for the host's breath in
QUIET, BREATH = 50, 36  # dB under the voices: the quiet before a breath, and a breath
LAND_AFTER = 0.3  # seconds from the last word to a theme's downbeat
LEAD = 0.65  # seconds of a theme's swell before its downbeat
MAJOR = {"hard-4": 300, "hard-4-short": 220}  # a hard story with at least this many words of airtime gets it
MOODS = {"usual": ("intro", "up-first"), "sombre": ("sombre-intro", "sombre-pulse")}  # theme, bed
STING_BARS, STING_UP = 2, 4  # the sting's bars, and the dB it plays over the bed until the hosts start
SECTION_BAR, SECTION_BARS, HOST_BARS = 1.12, 3, 2  # What's on's theme: bar, bars, and bars before the hosts
PRE_BARS, PRE_FADE = 6, 4  # bars of the between loop under the last story, and of its fade-in
MAX_NUDGE = 0.12  # the most a bed's tempo is changed to fit; more and it's left out


def plan(segments: list, stories: list, segment_starts: list[tuple[float, bool]], day: date,
         mood: str = "usual") -> list[tuple[float, str]]:
    """Where each cue goes, as (seconds into the voiced audio, cue name); the button at math.inf, the end.
    `segments` are the script's: cold open, one per story, What's on if there is one, sign-off. Each
    kind's rotation starts at a cue that moves on by one each day, so every cue gets heard over a week,
    not only the first one or two. A cue never plays before two stories of a kind in a row."""
    extra = segments[1 + len(stories):]
    if not 1 <= len(extra) <= 2 or len(segment_starts) != len(segments):
        print(f"  {len(segments)} segments for {len(stories)} stories; no cues")
        return []
    pools = {k: sorted(p.stem for p in CUES.glob(f"{k}-*.wav") if p.stem not in MAJOR) for k in ("hard", "light")}
    used = {k: day.toordinal() for k in pools}
    last = {}  # the cue before the last story of each kind
    placed = []
    for i, story in enumerate(stories, start=1):
        start, heard = segment_starts[i]
        if not heard:
            print(f"  no cue before {segments[i].title!r}: its start was estimated")
            continue
        if i == 1:
            placed.append((start, MOODS[mood][0]))
            continue
        name = next((m for m, words in MAJOR.items() if story.kind == "hard" and story.airtime >= words), None)
        if name is None or name == last.get(story.kind) or not (CUES / f"{name}.wav").exists():
            if not (pool := pools[story.kind]):
                continue
            name = pool[used[story.kind] % len(pool)]
            used[story.kind] += 1
        placed.append((start, name))
        last[story.kind] = name
    if len(extra) == 2:  # What's on, whatever the script calls it, then the sign-off
        start, heard = segment_starts[1 + len(stories)]
        if heard:
            placed.append((start, "section"))
    placed.append((math.inf, "button"))
    return [(t, name) for t, name in placed if (CUES / f"{name}.wav").exists()]


def first_sentence(script, out_dir: Path) -> tuple[float, float] | None:
    """Where the cold open's first sentence ends, as (its last word's end, the next word's start) in
    seconds into the voiced audio, from Whisper's words for the first chunk; None if not heard."""
    from nlnews import voicecheck
    at = 0.0
    for path in segment_files(out_dir):
        if path.name == "chunk00.wav":
            break
        with wave.open(str(path)) as w:
            at += w.getnframes() / w.getframerate()
    else:
        return None
    heard = voicecheck.heard(path)
    text = " ".join(l.text for l in script.segments[0].lines)
    sentences = re.findall(r"[^.?!]+[.?!]", text)
    if not heard or len(sentences) < 2:
        return None
    tokens = lambda s: re.findall(r"[\w']+", s)  # "son-in-law" is three words to Whisper
    match = {}
    blocks = difflib.SequenceMatcher(None, [_norm(w) for w in tokens(text)], [h[0] for h in heard], autojunk=False)
    for a, b, n in blocks.get_matching_blocks():
        for j in range(n):
            match[a + j] = b + j
    k = len(tokens(sentences[0])) - 1
    if k not in match or match[k] + 1 >= len(heard):  # the next word as heard, even if misheard
        return None
    return at + heard[match[k]][2], at + heard[match[k] + 1][1]


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


def _level(x: np.ndarray) -> float:
    """RMS of the samples within 40 dB of the peak: how the beds were set against the voices."""
    loud = x[np.abs(x) > np.abs(x).max() / 100]
    return 20 * math.log10(np.sqrt(np.mean(loud.astype(np.float64) ** 2)))


def _cue(name: str, voice_db: float, keep_lead: bool = False) -> np.ndarray:
    """A cue set to the voices, its silence trimmed; a theme keeps its lead-in, so its downbeat stays LEAD in."""
    x = _decode("-i", str(CUES / f"{name}.wav"))
    sounding = np.nonzero(np.abs(x) > np.abs(x).max() * 10 ** (-55 / 20))[0]
    x = x[0 if keep_lead else sounding[0]: sounding[-1] + 1]
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


def _last_word(x: np.ndarray, floor_db: float = -35) -> int:
    """Where the speech in `x` stops, in samples: the end of the last 10 ms within `floor_db` of its loudest.
    Whisper's and the transcript's end times run a few tenths late."""
    win = int(0.01 * RATE)
    env = np.sqrt(np.mean(x[: len(x) // win * win].reshape(-1, win).astype(np.float64) ** 2, axis=1))
    loud = np.nonzero(env > env.max() * 10 ** (floor_db / 20))[0]
    return (loud[-1] + 1) * win if len(loud) and env.max() > 0 else len(x)


def _quiet_point(voice: np.ndarray, a: float, b: float) -> int:
    """The quietest 40 ms around the gap Whisper puts between `a` and `b` seconds (its word times can be
    a few tenths out, so the search starts 0.3 s early): the gap before the next breath."""
    win, hop = int(0.04 * RATE), int(0.005 * RATE)
    lo, hi = int((a - 0.3) * RATE), int((b + 0.1) * RATE) - win
    return min(range(lo, max(lo + 1, hi), hop), key=lambda s: np.mean(voice[s: s + win] ** 2)) + win // 2


def _beds() -> dict:
    return json.loads((BEDS / "beds.json").read_text())


def _has_bed(name: str) -> bool:
    return (BEDS / name / "near-1.0.flac").exists()


def _fit(span: int, bar: float) -> tuple[int, float] | None:
    """Bars and bar length (seconds) for `span` samples, as near `bar` as a whole number of bars allows."""
    n = max(1, round(span / RATE / bar))
    fitted = span / RATE / n
    return (n, fitted) if abs(fitted / bar - 1) <= MAX_NUDGE else None


def _bed(name: str, n: int, bar: float, head: str | None = None) -> tuple[np.ndarray, int]:
    """`n` bars of a bed at `bar` seconds a bar, ending where its theme lands, and how many samples of
    it come before its first bar line. `head` plays first: the sting (2 bars) or the outro's first bar.
    Each stem is a beat, laid on the fitted beats; within a beat the timing is the bed's own."""
    spec = _beds()
    near, pre = spec["near"], round(spec["pre"] * RATE)
    stems = {p.stem: _decode("-i", str(p)) for p in (BEDS / name).glob("*.flac")}
    beat = bar / 4 * RATE
    h = {"sting": STING_BARS, "first": 1}.get(head, 0)
    names = [f"{head}.{k}" for k in range(4 * h)]  # the head's beats run on across its bars
    names += [f"{'near' if n - i <= near else 'far'}-{n - i if n - i <= near else (n - i) % 4}.{k}"
              for i in range(h, n) for k in range(4)]
    parts = [(round(j * beat), stems[name]) for j, name in enumerate(names) if name in stems]
    end = pre + round(n * bar * RATE)  # where the theme lands
    y = np.zeros(max([end + int(0.1 * RATE)] + [s + len(x) for s, x in parts]), np.float32)
    for s, x in parts:
        y[s: s + len(x)] += x
    swish = _decode("-i", str(BEDS / "swish.flac"))
    y[end - pre: end - pre + len(swish)] += swish[: len(y) - (end - pre)]
    y = y[: end + int(0.1 * RATE)]
    y[-int(0.15 * RATE):] *= np.linspace(1, 0, int(0.15 * RATE)) ** 2
    return y, pre


def _duck(music: np.ndarray, voices: np.ndarray, under: float = 17, gaps: float = 9) -> np.ndarray:
    """Sidechain: the music `under` dB below its level while the hosts speak and `gaps` dB below
    between lines, with a quick dip and a slow return. `voices` is what plays with it, sample for sample."""
    win, step = int(0.05 * RATE), int(0.01 * RATE)
    power = np.concatenate([[0], np.cumsum(voices.astype(np.float64) ** 2)])
    i = np.arange(len(voices))
    lo, hi = np.clip(i - win // 2, 0, len(voices)), np.clip(i + win // 2, 0, len(voices))
    env = np.sqrt((power[hi] - power[lo]) / win)
    coarse = (env > env.max() * 10 ** (-30 / 20)).astype(float)[::step] if env.max() > 0 else np.zeros(len(i[::step]))
    g = np.zeros_like(coarse)
    for k in range(1, len(coarse)):  # attack 40 ms, release 450 ms
        g[k] = g[k - 1] + (coarse[k] - g[k - 1]) * (0.25 if coarse[k] > g[k - 1] else 0.022)
    db = -gaps - (under - gaps) * np.interp(i, i[::step], g)
    return music * (10 ** (db / 20)).astype(np.float32)


def _bed_level(voice_level: float, sting_end: int | None = None):
    """A bed set to the voices and ducked under them; with `sting_end`, louder until then (the sting)."""
    def level(music: np.ndarray, voices: np.ndarray) -> np.ndarray:
        music = _duck(music * 10 ** ((voice_level - _level(music)) / 20), voices)
        if sting_end:
            up = np.ones(len(music), np.float32)
            ramp = int(0.5 * RATE)
            up[: sting_end - ramp] = 10 ** (STING_UP / 20)
            up[sting_end - ramp: sting_end] = 10 ** (np.linspace(STING_UP, 0, ramp) / 20)
            music = music * up
        return music
    return level


class _Mix:
    """The episode as it's built: the voice cut at the breaks with time added for the cues, and the
    music laid over it."""

    def __init__(self, voice: np.ndarray):
        self.voice, self.pieces, self.at, self.length = voice, [], 0, 0  # at: in the voice; length: of the output so far
        self.added, self.layers, self.outro = [], [], None

    def out(self, i: int) -> int:
        """Where sample `i` of the voice (not before the last break) is in the output, before any time added at it."""
        return self.length + i - self.at

    def insert(self, cut: int, heard: float, gap: int) -> None:
        self.pieces += [self.voice[self.at: cut], np.zeros(gap, np.float32)]
        self.length += cut - self.at + gap
        self.added.append((cut / RATE, heard, gap / RATE))
        self.at = cut

    def lay(self, at: int, x: np.ndarray, mix=None) -> None:
        """`x` over the output from sample `at`; `mix(x, voices)` sets it against the voices it plays with."""
        self.layers.append((at, x, mix))

    def build(self) -> np.ndarray:
        voices = np.concatenate(self.pieces + [self.voice[self.at:]])
        out = np.zeros(max([len(voices)] + [at + len(x) for at, x, _ in self.layers]), np.float32)
        out[: len(voices)] = voices
        voices = out.copy()
        for at, x, mix in self.layers:
            if mix:
                x = mix(x, voices[max(0, at): at + len(x)] if at >= 0 else np.concatenate([np.zeros(-at, np.float32), voices[: at + len(x)]]))
            if at < 0:
                x, at = x[-at:], 0
            out[at: at + len(x)] += x
        return out


def _before(voice: np.ndarray, mix: _Mix, cut: int) -> int:
    """The last word before `cut`, in the voice."""
    start = max(mix.at, cut - 10 * RATE)
    return start + _last_word(voice[start: cut])


def _opening(mix: _Mix, t: float, theme_name: str, voice_db: float, voice_level: float, split) -> None:
    voice = mix.voice
    theme = _cue(theme_name, voice_db, keep_lead=True)
    lead, after = round(LEAD * RATE), round(LAND_AFTER * RATE)
    cut = min(_cut(voice, t, voice_db), len(voice))
    bed_name = next(b for th, b in MOODS.values() if th == theme_name)
    land = None
    if split and _has_bed(bed_name) and 0 < (s := _quiet_point(voice, *split)) < cut:
        rest = _last_word(voice[s: cut]) + after
        if fitted := _fit(rest, _beds()["bars"][bed_name]):
            n, bar = fitted
            sting = mix.out(_last_word(voice[:s])) + after  # its downbeat
            hosts = sting + round(STING_BARS * bar * RATE)
            mix.insert(s, s / RATE, hosts - mix.out(s))
            music, off = _bed(bed_name, n + STING_BARS, bar, "sting")
            land = sting + round((n + STING_BARS) * bar * RATE)
            start = sting - off

            def under(music, voices, quiet=hosts - start, level=_bed_level(voice_level, hosts - start)):
                voices = voices.copy()
                voices[:quiet] = 0  # the first sentence plays before the sting, not under it
                return level(music, voices)
            mix.lay(start, music, under)
            print(f"  {bed_name} bed: sting {mix.added[-1][2]:.2f} s in at {s / RATE:.2f} s, "
                  f"{n} bars of {bar:.3f} s under the cold open")
    if land is None:
        land = mix.out(_before(voice, mix, cut)) + after
    resume = land - lead + len(theme) - round(UNDER_NEXT * RATE)
    mix.lay(land - lead, theme)
    mix.insert(cut, min(t, len(voice) / RATE), max(0, resume - mix.out(cut)))


def _section(mix: _Mix, t: float, voice_db: float, voice_level: float) -> None:
    voice = mix.voice
    theme = _cue("section", voice_db, keep_lead=True)
    lead, bar = round(LEAD * RATE), round(SECTION_BAR * RATE)
    cut = min(_cut(voice, t, voice_db), len(voice))
    down = mix.out(_before(voice, mix, cut)) + round(LAND_AFTER * RATE)
    if _has_bed("between"):
        music, off = _bed("between", PRE_BARS, SECTION_BAR)
        ramp = np.ones(len(music), np.float32)
        fade = PRE_FADE * bar
        ramp[:off] = 10 ** (-30 / 20)
        ramp[off: off + fade] = 10 ** (np.linspace(-30, 0, fade) / 20)
        mix.lay(down - PRE_BARS * bar - off, music * ramp, _bed_level(voice_level))
    mix.lay(down - lead, theme, lambda x, voices: _duck(x, voices, under=10, gaps=0))
    mix.insert(cut, min(t, len(voice) / RATE), max(0, down + HOST_BARS * bar - mix.out(cut)))
    mix.outro = down + SECTION_BARS * bar  # where the between bed starts, on the theme's last bar line


def _closing(mix: _Mix, voice_db: float, voice_level: float) -> None:
    voice = mix.voice
    button = _cue("button", voice_db, keep_lead=True)
    land = mix.out(_before(voice, mix, len(voice))) + round(LAND_AFTER * RATE)
    bar = SECTION_BAR
    if mix.outro and _has_bed("between") and land > mix.outro and (fitted := _fit(land - mix.outro, SECTION_BAR)):
        n, bar = fitted
        music, off = _bed("between", n, bar, "first")
        mix.lay(mix.outro - off, music, _bed_level(voice_level))
        print(f"  outro bed: {n} bars of {bar:.3f} s ({bar / SECTION_BAR - 1:+.1%})")
    mix.lay(land - round(LEAD * RATE), button)  # at What's on's tempo, as the intro theme is at its own


def splice(out_dir: Path, cues: list[tuple[float, str]], title: str,
           split: tuple[float, float] | None = None) -> list[tuple[float, float, float]]:
    """Rebuild episode.mp3 from the voiced files with the cues in. `split` is where the cold open's
    first sentence ends (first_sentence()). Returns where time was added, as (the cut, the heard
    start it's for, seconds added), in the voiced audio, for shift()."""
    listing = out_dir / "concat.local.txt"
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_files(out_dir)))
    voice = _decode("-f", "concat", "-safe", "0", "-i", str(listing))
    voice_db, voice_level = _loud_db(voice), _level(voice)
    mix = _Mix(voice)
    for t, name in sorted(cues):
        if name in (theme for theme, _ in MOODS.values()):
            _opening(mix, t, name, voice_db, voice_level, split)
        elif name == "section":
            _section(mix, t, voice_db, voice_level)
        elif name == "button":
            _closing(mix, voice_db, voice_level)
        else:
            cue = _cue(name, voice_db)
            cut = min(_cut(voice, t, voice_db), len(voice))
            mix.lay(mix.out(cut) + round(BEFORE * RATE), cue)
            mix.insert(cut, min(t, len(voice) / RATE), round(BEFORE * RATE) + max(0, len(cue) - round(UNDER_NEXT * RATE)))
    out = mix.build()
    pcm = (np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes()
    tmp = out_dir / "episode.cues.mp3"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ac", "1", "-ar", str(RATE), "-i", "-",
                    "-b:a", "64k", "-metadata", f"title={title}", "-metadata", "artist=Dutch Daily Briefing", str(tmp)],
                   input=pcm, check=True)
    tmp.replace(out_dir / "episode.mp3")
    listing.unlink()
    return mix.added


def shift(t: float, added: list[tuple[float, float, float]], at_break: bool) -> float:
    """Where a moment of the voiced audio is in the episode with the cues in. A moment at a break
    (from its cut to the heard word) is placed before that break's cue if `at_break` (a chapter, so
    it opens with its cue), after it otherwise (a line's first words). A cut is a whole sample, so
    "at" a cut is within half a sample of it."""
    near = 0.5 / RATE
    if at_break:
        t = next((cut for cut, heard, _ in added if cut - near <= t <= heard + near), t)
    return t + sum(gap for cut, _, gap in added if cut < t - near or (abs(cut - t) <= near and not at_break))
