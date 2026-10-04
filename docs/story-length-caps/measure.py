"""Words per segment, labelled from the briefing: L=lead, H=hard, F=follow-up, Li=light."""
import json, sys
from nlnews.models import Briefing, EpisodeScript
from nlnews import tts
def labels(b):
    out = []
    for i, s in enumerate(b.stories):
        out.append("L" if i == 0 else "F" if s.previously else "Li" if s.kind == "light" else "H")
    return out
def report(bpath, spath, name):
    b = Briefing.model_validate_json(open(bpath).read()); sc = EpisodeScript.model_validate_json(open(spath).read())
    w = [tts._words(s) for s in sc.segments]; lab = labels(b)
    n = len(sc.segments); extra = n - 2 - len(lab)  # cold open, stories, [agenda], sign-off
    tags = ["open"] + lab + (["agenda"] if extra >= 1 else []) + ["close"]
    tags = tags[:n] + ["?"] * (n - len(tags))
    print(f"{name}: {sum(w)} words, {n} segs")
    print("   " + ", ".join(f"{t}:{x}" for t, x in zip(tags, w)))
    for cap in (600, 320):
        tts.MAX_WORDS_PER_REQUEST = cap
        ch = tts._chunk(sc.segments)
        print(f"   chunks@{cap}: {len(ch)} requests {[sum(map(tts._words, c)) for c in ch]}")
    print(f"   one-per-segment: {n} requests; over 320: {[t+':'+str(x) for t,x in zip(tags,w) if x>320]}")
for d in sys.argv[1:]:
    p = d
    report(f"{p}/briefing.json", f"{p}/script.published.json", "published")
    import glob
    for s in sorted(glob.glob(f"{p}/script.capped*.json")):
        report(f"{p}/briefing.json", s, s.split('/')[-1])
