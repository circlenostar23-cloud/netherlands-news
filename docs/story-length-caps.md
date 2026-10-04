# Story length caps per segment type

Parked 2026-10-04 on the branch `claude/story-length-caps`, not merged. David wants more iteration before it ships. Do not call Gemini TTS while iterating; judge by the script text and the offline chunker count.

## Goal

Make story lengths vary on purpose. Follow-ups and light stories should run noticeably shorter than new hard-news stories, instead of every story landing around 250–480 words. Totals should drop back toward the 1,800–2,200 target. Recent published scripts ran 2,980–3,406 words, and follow-ups were as long as new stories.

## What's on this branch

Prompt changes only, with no code change:

- `prompts/script.md`: a block of word caps per segment, plus small edits to items 1, 2 and 4 to point at it. Items 3 and 5 (transitions, host handoffs) are untouched. The caps:
  - cold open ≤80
  - lead (first story, whatever its `kind`) ≤320; no segment over 320
  - other new hard stories 220–260, with stories 2 and 3 at the top of that range
  - follow-ups under 200, typically 120–180, or the lead's 320 if the update is the day's big news
  - light stories 140–180
  - sign-off ≤40
  - total target unchanged at 1,800–2,200, with What's on still on top of it
- `prompts/agenda_segment.md`: a single-day What's on is ≤150 words; the weekend edition is 200–280 (was 200–300).
- `prompts/select_followups.md`: dropped "aim for the top of the story range" when follow-ups are included.

## Test so far (2026-10-03)

The scripts were regenerated from the saved briefings in this folder with `NLNEWS_WRITER=claude-code`, one run each.

| | 10-01 | 10-02 | 10-03 |
|---|---|---|---|
| Total, published → capped | 3,025 → 2,412 | 3,406 → 2,478 | 2,980 → 2,443 |
| Follow-ups | 387, 232 → 200, 170 | 404 → 184 | (none) |
| Lead | 468 → 303 | 361 → 320 | 669 → 343 |
| Other hard stories | 202–437 → 239–258 | 261–482 → 258–286 | 172–378 → 224–291 |
| Light stories | 163 → 160 | 264–341 → 176–201 | 188–275 → 173–186 |

No story break had the same host on both sides, so `_fix_handoffs()` never ran.

`_chunk()` request counts for the capped scripts at each max-words cap:

| Cap (words) | 320 | 350 | 400 | 450 | 500 | 600 (current) |
|---|---|---|---|---|---|---|
| Requests (10-01 / 10-02 / 10-03) | 11/11/11 | 10/11/11 | 9/9/9 | 7/8/8 | 6/7/7 | 6/5/5 |

## Open questions for the next round

- **Total still a little high.** Without What's on, totals are ~2,160–2,320, against a 2,200 ceiling. Hard stories drift ~10% past 260, and the 10-03 lead hit 343 despite the 320 ceiling. The options are tighter caps, fewer stories (the parked plan says 6–7), or a `_fix_lengths()` revision pass beside `_fix_handoffs()` in `src/nlnews/script.py`.
- **Single run per day.** Regenerate each day 2–3 times to see how much lengths vary between runs before trusting the numbers.
- **Listen-through quality.** Read the capped scripts to check that follow-ups still make sense to someone who missed yesterday, and that the shorter light stories still get their moment of fun.
- **Story-sized TTS requests.** One request per story needs 11–12 requests, over Gemini's 10/day. A cap of 450 (7–8 requests, mostly 1–2 stories each) would be a no-cost first listen. `MAX_WORDS_PER_REQUEST` stays at 600 unless David asks. See [shorter-sunday-quality-episodes.md](shorter-sunday-quality-episodes.md).

## Picking it up again

```sh
git fetch origin claude/story-length-caps && git checkout claude/story-length-caps
git merge origin/main   # main has likely moved on
pip install -e .        # needs Python 3.12+
python docs/story-length-caps/measure.py docs/story-length-caps/2026-10-0{1,2,3}
NLNEWS_WRITER=claude-code python docs/story-length-caps/regen.py \
  docs/story-length-caps/2026-10-01/briefing.json docs/story-length-caps/2026-10-01/script.capped2.json
```

`measure.py` prints words per segment (L lead, H hard, F follow-up, Li light) for `script.published.json` and every `script.capped*.json` in a day folder, plus the request counts above. Each day folder holds the saved briefing, the published script and the capped regeneration. The Actions artifacts they came from expire 8–10 October 2026, so this folder is the only copy.

Before merging, move this to **Done** in `ITERATIONS.md`, delete the `docs/story-length-caps/` folder (or keep only this note), and update the "Gemini voices sound worse in packed TTS requests" backlog item.
