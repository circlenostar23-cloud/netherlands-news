"""Cheap same-language near-duplicate grouping, to shrink what Claude has to read.

Cross-language merging (e.g. NOS in Dutch + NL Times in English on the same story)
is left to the curation model, which is much better at it.
"""

import re

from nlnews.models import Article

_WORD = re.compile(r"\w{4,}")
STOP = {"deze", "wordt", "worden", "heeft", "hebben", "naar", "over", "door", "voor", "niet",
        "with", "after", "from", "that", "have", "will", "their", "about", "over"}


def _tokens(a: Article) -> set[str]:
    return {w for w in _WORD.findall(f"{a.title} {a.summary[:200]}".lower()) if w not in STOP}


def cluster(articles: list[Article], threshold: float = 0.35) -> list[list[Article]]:
    """Greedy single-pass clustering on Jaccard similarity of title+lede tokens."""
    groups: list[tuple[set[str], list[Article]]] = []
    for a in sorted(articles, key=lambda a: -a.weight):
        toks = _tokens(a)
        for gtoks, members in groups:
            if members[0].lang == a.lang and toks and len(toks & gtoks) / len(toks | gtoks) >= threshold:
                members.append(a)
                gtoks |= toks
                break
        else:
            groups.append((toks, [a]))
    return [members for _, members in groups]
