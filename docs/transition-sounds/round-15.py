"""Round 15: David's notes on round 14.

  intro    one more try at splitting the cold open: the sting after the first sentence, or the first
           two, instead of after the whole hook (too late). The split goes in the quiet just after the
           sentence's last word, so the breath for the next sentence plays after the sting with it
           (round 14 cut at Whisper's word start, which left the breath to be covered by the sting)
  outro    a loop of the between bed fades in under the last story's final bars and leads into What's
           on's theme on its downbeat; the rest as round 14 (hosts over the theme's last bars)
  button   bed-b, David's pick, in versions: without the hi-hats, with the bell glint, and with fuller
           bells, each heard at the end of the outro

usage: PYTHONPATH=src RENDER=<render> python round-15.py <out-dir> <run dir, e.g. data/2026-10-24>
"""
import difflib, importlib.util, re, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round14", Path(__file__).parent / "round-14.py")
r14 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r14)
r13, r12, r11, r10 = r14.r13, r14.r12, r14.r11, r14.r10
LAND_AFTER, LEAD, SECTION_BEAT, SECTION_BEATS = r14.LAND_AFTER, r14.LEAD, r14.SECTION_BEAT, r14.SECTION_BEATS
PRE_BARS = 6  # bars of loop fading in under the last story before What's on's theme
PRE_FADE = 4  # of which the fade-in takes this many

BUTTON_VERSIONS = {  # bed-b with: hi-hats (closed and open), shaker, glint level, fuller bells level
    "b no hats": dict(hats=(0, 0), end_hat=None),
    "b no hats, glint": dict(hats=(0, 0), end_hat=None, shaker=(0, 0), glint=0.42),
    "b no hats, bells": dict(hats=(0, 0), end_hat=None, shaker=(0, 0), bells=0.3),
    "b hats, glint": dict(glint=0.42),
}


def bells(n, vel):
    """The bell itself, an octave up, its hum filtered out but more of its ring kept than the glint."""
    x = BELLS.note(r11.up12(n))[: int(2.4 * SR)]
    x = filt(x, lo=r11.r9.hz(r11.up12(n)) * 0.6, hi=8000)
    return x * np.exp(-np.arange(len(x)) / SR / 1.1)[:, None] * vel


def bed_button(version, beat):
    spec = dict(r14.BED_BUTTONS["bed-b"], beat=beat, **{k: v for k, v in BUTTON_VERSIONS[version].items() if k != "bells"})
    r11.BUTTONS[version] = spec
    y = r11.button(version)
    if level := BUTTON_VERSIONS[version].get("bells"):
        events = [(0, y)] + [(LEAD + b * beat, pan(bells(n, level), (0.4, 0.25)[i % 2])) for i, (b, n, _) in enumerate(spec["melody"])]
        y = place(events)
    return r13.themed(y)


def sentence_ends(d, voice):
    """Where each of the cold open's first line's sentences ends, as (its last word's end, the next
    word's start), in seconds, from Whisper's words for the first chunk."""
    from nlnews import voicecheck
    from nlnews.chapters import _norm
    from nlnews.models import EpisodeScript
    line = EpisodeScript.model_validate_json((d / "script.json").read_text()).segments[0].lines[0].text
    heard = voicecheck.heard(d / "segments" / "chunk00.wav")
    sentences = re.findall(r"[^.?!]+[.?!]", line)
    tokens = lambda text: re.findall(r"[\w']+", text)  # "son-in-law" is three words to Whisper
    words = [_norm(w) for w in tokens(line)]
    match = {}
    for a, b, n in difflib.SequenceMatcher(None, words, [h[0] for h in heard], autojunk=False).get_matching_blocks():
        for j in range(n):
            match[a + j] = b + j
    ends, k = [], 0
    for s in sentences[:-1]:
        k += len(tokens(s))
        if k - 1 in match and match[k - 1] + 1 < len(heard):  # the next word as heard, even if misheard
            ends.append((heard[match[k - 1]][2], heard[match[k - 1] + 1][1]))
    return ends


def quiet_point(voice, a, b):
    """The quietest 40 ms around the gap Whisper puts between `a` and `b` seconds (its word times can be
    a few tenths out, so the search starts 0.3 s early): the gap before the next breath."""
    m = voice[:, 0]
    win, hop = int(0.04 * SR), int(0.005 * SR)
    lo, hi = int((a - 0.3) * SR), int((b + 0.1) * SR) - win
    starts = range(lo, max(lo + 1, hi), hop)
    return (min(starts, key=lambda s: np.mean(m[s: s + win] ** 2)) + win // 2) / SR


def split_opening(voice, split, cut, bed_name="up-first", follow=9.0):
    """r14.split_opening() at any split: the voice up to `split` dry, the sting LAND_AFTER its last word,
    the rest of the cold open over the bed, the intro theme, then the first story."""
    hook, rest = voice[: int(split * SR)], voice[int(split * SR): int(cut * SR)]
    sting_at = r12.last_word(hook) + LAND_AFTER
    words = r12.last_word(rest) + LAND_AFTER
    b = r13.BEDS[bed_name]
    n, bar = r13.fit(words, 4 * b["beat"])
    n += r13.STING_BARS
    rest_at = sting_at + r13.STING_BARS * bar
    swish = (r13.OPEN_HAT[::-1] * np.linspace(0, 1, len(r13.OPEN_HAT))[:, None] ** 3)[-int(LEAD * SR):]
    music = place([(0, filt(swish, lo=2500) * 0.25), (LEAD, r13.bed(bed_name, n, bar, sting=r13.STINGS[bed_name]))])
    music = r13.bed_level(music, np.concatenate([secs(rest_at - sting_at + LEAD), rest]), sting_end=rest_at - sting_at + LEAD)
    theme = r13.themed(r10.theme("intro"))
    land = sting_at + n * bar
    story = voice[int(cut * SR): int((cut + follow) * SR)]
    print(f"  split at {split:.2f} s: sting {sting_at:.2f} s, {n} bars of {bar:.3f} s, {len(rest) / SR:.1f} s of voice over the bed")
    return place([(0, hook), (sting_at - LEAD, music), (rest_at, rest),
                  (land - LEAD, theme), (land - LEAD + len(theme) / SR - 0.6, fade(story, 1.0))])


def closing(voice, cut, button, host_bars=2, before=12.0):
    """r14.closing(), with PRE_BARS of the between bed fading in under the last story in place of its
    single bar, leading into What's on's theme on the downbeat."""
    start = cut - before
    story = voice[int(start * SR): int(cut * SR)]
    tail = voice[int(cut * SR):]
    sec_bar = 4 * SECTION_BEAT
    down = r12.last_word(story) + LAND_AFTER
    resume = down + host_bars * sec_bar
    bed_from = down + SECTION_BEATS * SECTION_BEAT
    land = resume + r12.last_word(tail) + LAND_AFTER
    voices = place([(0, story), (resume, tail)])
    # the loop under the story, built back from the theme's downbeat so its last bar is D9sus
    pre_at = down - PRE_BARS * sec_bar
    pre = r13.bed("between", PRE_BARS, sec_bar)
    ramp = np.ones(len(pre))
    nf = int(PRE_FADE * sec_bar * SR)
    ramp[:nf] = 10 ** (np.linspace(-30, 0, nf) / 20)
    pre = r13.bed_level(pre * ramp[:, None], voices[int(pre_at * SR):])
    theme = r13.themed(r10.theme("section"))
    theme_at = down - LEAD
    track = np.concatenate([voices, secs(len(theme) / SR)])[int(theme_at * SR):][: len(theme)]
    theme = r11.duck(theme, track, under=10, gaps=0)
    n, bar = r13.fit(land - bed_from, sec_bar)
    music = r13.bed("between", n, bar, first=(r13.GMAJ9, [(0, "G1", 2.5), (2.5, "D2", 1.5)]))
    music = r13.bed_level(music, voices[int(bed_from * SR):])
    print(f"  outro ({button[0]}): loop from {pre_at - r12.last_word(story) + 0:.1f} s before the story's last word, {n} bars of {bar:.3f} s")
    return place([(0, voices), (pre_at, pre), (theme_at, theme), (bed_from, music), (land - LEAD, button[1](bar / 4))])


if __name__ == "__main__":
    out, run = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    voice, cuts = r14.load_run(run)
    ends = sentence_ends(run, voice)
    print("  sentence ends:", [(round(a, 2), round(b, 2)) for a, b in ends])
    for k, label in ((0, "one sentence"), (1, "two sentences")):
        split = quiet_point(voice, *ends[k])
        write(out / f"intro - sting after {label}.mp3",
              np.concatenate([split_opening(voice, split, cuts["intro"]), secs(0.5)]))
    for i, version in enumerate(BUTTON_VERSIONS):
        y = closing(voice, cuts["section"], (version, lambda beat, v=version: bed_button(v, beat)))
        if i == 0:
            write(out / f"outro - loop under the story, button {version}.mp3", np.concatenate([y, secs(0.5)]))
        write(out / f"end - button {version}.mp3", np.concatenate([y[-int(16 * SR):], secs(0.5)]))
