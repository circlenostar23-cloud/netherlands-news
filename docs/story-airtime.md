# Story airtime

Shipped 2026-10-06. Each story's length comes from how much it has to say, not from its kind or position.

## How it works

`script.plan_airtime()` runs just before the script is written. A short call (`prompts/airtime.md`, low effort) reads the researched briefing and splits a fixed pool of story words across the stories, with a one-line reason for each. The pool is the middle of the episode target minus ~120 words for the cold open and sign-off: 1,880 words for 1,800–2,200. Light stories aren't automatically short, hard news isn't automatically long, and a follow-up usually needs less because the background's been given. The test it applies is "what would the listener lose if this ran 100 words shorter?"

`_fit()` then scales the asked-for numbers so they add up to the pool, keeps each story between 90 and 340 words, and rounds to tens. The budgets are saved in `briefing.json` as each story's `airtime` and `airtime_reason`. The script prompt asks the writer to stay within about 10% of each and to use the reason as a pointer to the story's angle. After writing, the log prints `story words vs airtime` for each story.

What's on in Amsterdam is still on top of the target: 150 words at most for a single day, 200–280 for a weekend.

## Why not fixed caps per kind

The first try on this branch, 2026-10-04, gave each kind of story a word range: lead ≤320, hard 220–260, follow-ups 120–180, light 140–180. That cut totals, but it made every light story the shortest, even when it was the most interesting story of the day. David asked for lengths that follow the material instead.

## Test (2026-10-06)

Scripts were regenerated from the saved 10-01, 10-02 and 10-03 briefings with `NLNEWS_WRITER=claude-code`, twice per day. Totals include What's on:

| | 10-01 | 10-02 | 10-03 |
|---|---|---|---|
| Published | 3,025 | 3,406 | 2,980 |
| Fixed caps | 2,412 | 2,478 | 2,443 |
| Airtime, run 1 / run 2 | 2,414 / 2,319 | 2,268 / 2,355 | 2,283 / 2,190 |
| Story budgets | 90–300 | 120–300 | 110–340 |
| Story words vs budget, mean | +10% / +6% | +10% / +13% | +10% / +4% |

- **Lengths follow the material.** On 10-03, "Dutch TV turns 75" (light) got 180–230 for its pillarisation back-story, and the Hans Anders camera-glasses story got 170–220. "Amsterdam drops the Utrechtsestraat one-way plan" (hard) got 110–130. On 10-01, the Cornelisse obituary (light, the lead) got 300, while the Van Gogh auction and the Fabel Friet follow-up, one fact each, got 90–120.
- **Plans are stable between runs.** Most stories moved 10–40 words between the two plans; the most was 50.
- **Scripts land just over budget.** Stories came in 4–13% over on average, never more than 18%. The longest segment was 386 words, the 10-03 lead with a 340 budget. Totals without What's on are ~2,050–2,140, inside the target.
- **Short stories still sound complete.** The 91-word Van Gogh story keeps its joke, and the 96-word Fabel Friet follow-up keeps its caveat and its punchline.
- No story break had the same host on both sides.

The saved briefings, published scripts, the fixed-caps and airtime regenerations, and the `measure.py` / `regen.py` helpers are in commit `7d84847` on the branch `claude/story-length-caps`, under `docs/story-length-caps/`.

## Watch

- **Whether the plan undervalues light stories with an old back-story but little news.** One run gave the Batavia replica 120 words because there was "little new beyond the move itself", despite the mutiny history.
- **The steady ~10% overshoot.** If totals creep up, lower the pool in `plan_airtime()` rather than tightening the script prompt.
- **TTS requests.** At the 600-word cap these scripts pack into 5–6 Gemini requests. The longest story is now ~390 words, so story-sized chunks (450 cap: 6–8 requests) are within reach; see [shorter-sunday-quality-episodes.md](shorter-sunday-quality-episodes.md).
