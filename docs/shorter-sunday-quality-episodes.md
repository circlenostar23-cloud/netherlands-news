# Shorter episodes for Sunday-quality voices

Parked 2026-09-29. **2026-10-06:** fixed word caps per kind of story, as under *Cuts*, were tried and dropped; story lengths now come from an airtime plan instead (see [story-airtime.md](story-airtime.md)). Main is already up to date with the iterations note. Do not call Gemini TTS while implementing this: that quota is for tomorrow's episode.

Shrink the episode so Gemini voices stay in Sunday-sized chunks (about 320 words, one request per story) and still finish in 8 requests, under the 10/day free-tier cap.

Today's Gemini episode (`ep-2026-09-29`, 3,165 words, 7 packed ~600-word calls, 18m36s) sounded worse than Sunday (`ep-2026-09-27`, 2,259 words, 7 calls of about 2 minutes, 14m18s). Same model and voices. The difference that lines up with the listener report is chunk length.

## Budget

Gemini free tier is 10 TTS requests/day. One failed request still falls through to Microsoft for the **whole** episode ([`src/nlnews/tts.py`](../src/nlnews/tts.py) wraps `_gemini_wavs` in a single try). Stay at **8 requests** so one retry does not spend the cap.

Sunday-sized audio is about **320 words per request** (2,259 words / 7 calls). A 3,165-word script at that size needs 10 requests, so the script has to get shorter. Shortening alone is not enough if each story stays its own request: today's shape is cold open + 9 stories + What's on + sign-off = 12 segments, and most stories are already too long to pair inside 320 words.

## Cuts

- **Stories: 6–7**, down from 6–9 in [`src/nlnews/curate.py`](../src/nlnews/curate.py) and [`prompts/select.md`](../prompts/select.md). Light stories stay 2–3. In [`prompts/select_followups.md`](../prompts/select_followups.md), stop telling the editor to aim for the top of the range; a follow-up is shorter, it does not add a slot.
- **Script: 1,900–2,200 words including What's on** (today the agenda is extra, on top of 1,800–2,200, and the model ignored the cap). In [`prompts/script.md`](../prompts/script.md) and [`prompts/agenda_segment.md`](../prompts/agenda_segment.md):
  - Cold open is the opening of the first story segment; sign-off is the end of the last. They are not their own segments, so they do not burn a request.
  - No story segment over **320 words**. Lead up to 320; other new hard stories about 220–260; follow-ups under 200; light stories about 140–180.
  - Weekday What's on stays about 150 words; weekend edition capped at 280 so it is one request.
- **7 stories + What's on = 8 segments.** At one request per segment that is exactly the cap. Six stories lands on 7, matching Sunday.

## TTS

In [`src/nlnews/tts.py`](../src/nlnews/tts.py):

- `MAX_WORDS_PER_REQUEST = 320`. Still split only on segment boundaries (never mid-story).
- `MAX_REQUESTS = 8`. If `_chunk()` would need more, raise **before** any Gemini call so quota is untouched and the existing Microsoft fallback still produces an episode.
- Update the module docstring and the README line that says voices are packed to stay under 10/day (it should say Sunday-sized chunks, 8 requests, Microsoft if the script does not fit).

## Writer guard

[`src/nlnews/script.py`](../src/nlnews/script.py) already asks for a word range and the published script still came out at 3,165 words. After the first draft, if the total is over 2,200, any segment is over 320, or the TTS chunker would need more than 8 requests, make **one** revision call (Claude/Gemini text, not TTS) that names the overrun. If it is still over, keep the script and let TTS skip Gemini.

No `synthesize` / Gemini audio in this change. Check the chunker locally against the saved scripts in `data/2026-09-27`, `data/2026-09-28`, and `data/2026-09-29` (those locals are not the published episodes, but they show request counts). A tiny unit test around `_chunk` is enough; there is no project test suite yet.

## When it ships

Move **Gemini voices sound worse in packed TTS requests** in [`ITERATIONS.md`](../ITERATIONS.md) to Done with this decision: 320-word segment chunks, 6–7 stories, 8-request ceiling, no A/B listen because that would spend the daily quota. Point the older "one TTS request for the whole episode" item at this: long generations are the suspected cause, so that test waits.
