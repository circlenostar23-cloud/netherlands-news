"""Round 16: the split intro with a loop fading in before the sting, as the outro does before What's on.

David picked the sting after the cold open's first two sentences (round 15, ep-2026-10-23). Now a few
bars of the up-first loop fade in under those sentences and lead into the sting on its downbeat. It's
shorter than the outro's six bars, since it only ever runs under two sentences: PRE_BARS of 2 or 4.

usage: PYTHONPATH=src RENDER=<render> python round-16.py <out-dir> <run dir, e.g. data/2026-10-23>
"""
import importlib.util, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from logic import *  # noqa: F401,F403 -- samples, effects, finish() and demo()

spec = importlib.util.spec_from_file_location("round15", Path(__file__).parent / "round-15.py")
r15 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r15)
r14, r13, r12, r11, r10 = r15.r14, r15.r13, r15.r12, r15.r11, r15.r10
LAND_AFTER, LEAD = r15.LAND_AFTER, r15.LEAD
SENTENCES = 2  # the sting comes in after this many of the cold open's sentences


def split_opening(voice, split, cut, pre_bars, bed_name="up-first", follow=9.0):
    """r15.split_opening() with `pre_bars` of the loop fading in under the voice before the sting:
    built back from the sting's downbeat, at the bed's (fitted) tempo, so its last bar leads into it."""
    hook, rest = voice[: int(split * SR)], voice[int(split * SR): int(cut * SR)]
    sting_at = r12.last_word(hook) + LAND_AFTER
    words = r12.last_word(rest) + LAND_AFTER
    b = r13.BEDS[bed_name]
    n, bar = r13.fit(words, 4 * b["beat"])
    n += r13.STING_BARS
    rest_at = sting_at + r13.STING_BARS * bar
    pre_at = sting_at - pre_bars * bar
    pre = r13.bed(bed_name, pre_bars, bar)  # ends with its own swell into the sting
    ramp = 10 ** (np.linspace(-30, 0, len(pre)) / 20)  # fades in over all of it
    pre = r13.bed_level(pre * ramp[:, None], np.concatenate([voice, secs(1)])[int(pre_at * SR):])
    music = r13.bed(bed_name, n, bar, sting=r13.STINGS[bed_name])
    music = r13.bed_level(music, np.concatenate([secs(rest_at - sting_at), rest]), sting_end=rest_at - sting_at)
    theme = r13.themed(r10.theme("intro"))
    land = sting_at + n * bar
    story = voice[int(cut * SR): int((cut + follow) * SR)]
    print(f"  {pre_bars} bars ({pre_bars * bar:.1f} s) of loop before the sting at {sting_at:.2f} s")
    return place([(0, hook), (pre_at, pre), (sting_at, music), (rest_at, rest),
                  (land - LEAD, theme), (land - LEAD + len(theme) / SR - 0.6, fade(story, 1.0))])


if __name__ == "__main__":
    out, run = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    voice, cuts = r14.load_run(run)
    split = r15.quiet_point(voice, *r15.sentence_ends(run, voice)[SENTENCES - 1])
    for pre_bars in (2, 4):
        write(out / f"intro - {pre_bars}-bar loop, sting after two sentences.mp3",
              np.concatenate([split_opening(voice, split, cuts["intro"], pre_bars), secs(0.5)]))
