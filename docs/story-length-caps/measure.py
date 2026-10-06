"""Words per segment, labelled from the briefing: L=lead, H=hard, F=follow-up, Li=light.
For script.airtime*.json, also shows each story's planned airtime (words/airtime)."""
import glob, json, os, sys
from nlnews.models import Briefing, EpisodeScript
from nlnews import tts
def labels(b):
    return ["L" if i == 0 else "F" if s.previously else "Li" if s.kind == "light" else "H" for i, s in enumerate(b.stories)]
def report(bpath, spath, name):
    b = Briefing.model_validate_json(open(bpath).read()); sc = EpisodeScript.model_validate_json(open(spath).read())
    plan = spath.replace(".json", ".plan.json")
    air = [s.airtime for s in Briefing.model_validate_json(open(plan).read()).stories] if os.path.exists(plan) else []
    w = [tts._words(s) for s in sc.segments]; lab = labels(b)
    n = len(sc.segments); extra = n - 2 - len(lab)  # cold open, stories, [agenda], sign-off
    tags = ["open"] + lab + (["agenda"] if extra >= 1 else []) + ["close"]
    tags = tags[:n] + ["?"] * (n - len(tags))
    budget = [""] + [f"/{a}" for a in air] + [""] * n
    print(f"{name}: {sum(w)} words, {n} segs")
    print("   " + ", ".join(f"{t}:{x}{a}" for t, x, a in zip(tags, w, budget)))
    if air:
        off = [x / a - 1 for x, a in zip(w[1:], air)]
        print(f"   vs airtime: {min(off):+.0%} to {max(off):+.0%}, mean {sum(off) / len(off):+.0%}")
    for cap in (600, 450):
        tts.MAX_WORDS_PER_REQUEST = cap
        ch = tts._chunk(sc.segments)
        print(f"   chunks@{cap}: {len(ch)} requests {[sum(map(tts._words, c)) for c in ch]}")
for d in sys.argv[1:]:
    report(f"{d}/briefing.json", f"{d}/script.published.json", "published")
    for s in sorted(glob.glob(f"{d}/script.capped*.json") + glob.glob(f"{d}/script.airtime*.json")):
        if not s.endswith(".plan.json"):
            report(f"{d}/briefing.json", s, s.split('/')[-1])
