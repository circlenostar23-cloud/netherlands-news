# Iterations log

Ideas and known issues parked so they don't disrupt the working daily pipeline. Newest first. Move an item to **Done** once it ships.

## Backlog

### Story lengths vary on purpose (parked on a branch)
*Logged 2026-10-04*

Work in progress lives on the branch `claude/story-length-caps`, not merged. Start there: `git fetch origin claude/story-length-caps && git checkout claude/story-length-caps`, merge `main` in, then read `docs/story-length-caps.md` on that branch. It has the goal, the caps, test results, open questions, saved test data and how to resume.

Scripts run 2,980–3,406 words against a 1,800–2,200 target, and follow-ups are as long as new stories. The branch adds prompt-only word caps per segment type: lead ≤320, other hard stories 220–260, follow-ups under 200, light stories 140–180. In a first test, totals dropped 18–27% and follow-ups to 170–200 words. Totals are still a little over 2,200, and one lead went to 343. Not shipped yet; David wants more iteration first. When it merges, this item becomes the branch's own backlog entry, which moves to Done.

### OpenRouter as the paid voice provider
*Logged 2026-10-04*

**Why:** Gemini TTS has been slow or stuck on several mornings, and the free tier caps us at 10 requests a day. David has OpenRouter credit, and OpenRouter also offers speech models we never tried because they aren't free. The key is the `OPENROUTER_API_KEY` Actions secret.

**Test (2026-10-04):** `scripts/tts_test.py`, run by hand from `tts-test.yml` (runs 37181889516 and 37182034915). It voices 12 lines (290 words, 1,662 characters) of the 10-04 cleaners' story; the MP3s are in each run's `tts-test` artifact. Total cost about $0.35.
- **Gemini can't voice both hosts in one request on OpenRouter.** The speech endpoint takes one `input` and one `voice`. With Google's `speechConfig.multiSpeakerVoiceConfig` passed as a provider option, the whole excerpt came out in Kore's voice (~140–170 Hz throughout) and the first "Sam:" label was read aloud. The interactions-style `speech_config` got a 400, a request without `voice` is refused, and Gemini only returns `pcm`, not `mp3`.
- **One request per line works with every model tried except Sesame CSM-1B** (a 400 from the provider). Each host keeps their own voice, so a swap like 10-04's can't happen. The catch: the hosts no longer hear each other, so the Gemini back-and-forth (timing, reactions) is gone.

| Model (Maya, Sam) | 290 words took | Full episode (~17,700 characters, 138 lines) |
| - | - | - |
| Gemini 3.8 Flash TTS (Kore, Puck) | 49 s | ~$0.25 |
| Microsoft MAI-Voice 2.1 (Harper, Grant) | 16 s | ~$0.39 |
| MiniMax Speech 2.8 HD | 13 s | ~$1.77 |
| Grok Voice (eve, rex) | 21 s | ~$0.27 |
| Mistral Voxtral (Jane, Paul) | 32 s | ~$0.28 |
| Deepgram Aura-2 (Thalia, Apollo) | 61 s | ~$0.53; Apollo's voice sits high (~150–180 Hz), so the hosts are less distinct |

Times are for requests one after another; an episode's 138 lines can run several at once.

**Decision (2026-10-04):** David listened: Gemini wins, but line by line it's noticeably less natural than the two-host requests. So OpenRouter became the backup, not the main engine (see **Done**).

**Two hosts in one request elsewhere (checked 2026-10-04):** Fish Audio S2.1 Pro does this natively (`<|speaker:0|>` / `<|speaker:1|>` tags, a voice per index), but OpenRouter gives it a single voice and no multiple reference clips, so not there. ElevenLabs Text to Dialogue isn't on OpenRouter. Seed Audio 1.0 on OpenRouter takes up to three reference clips and switches between them (`@Audio1`, `@Audio2`) in one request, but caps each request at 120 s of audio and costs $0.0025/s, ~$2.90 an episode. It would need short Kore and Puck reference clips. Untested; worth one ~$0.25 request only if the line-by-line backup turns out to be used often.

### Gemini repeats a word
*Logged 2026-10-04*

In `ep-2026-10-04`, at ~0:57 in the Centraal story, Maya says "Yesterday — yesterday people were sent to the metro". The script has the word once, so Gemini doubled it (two word-length bursts at 57.1 and 57.8 s in chunk 1; Whisper hears only one). One-off so far; there's no cheap way to catch it short of transcribing every chunk and diffing it against the script. Note it if it comes back.

### Gemini swaps the hosts' voices or drops lines at story breaks
*Logged 2026-10-02, updated 2026-10-03*

**Problem:** in `ep-2026-10-02`, Sam's voice (Puck) said "It's Friday, October second. I'm Maya." and Maya's voice (Kore) said "And I'm Sam." The script attributes the lines correctly, and the request sends `speaker: Maya` / `speaker: Sam` per line, so Gemini slipped at a turn boundary. In `ep-2026-10-03` the intro was fine, but per-line pitch and spectral checks (lines aligned to the audio with faster-whisper) found:
- ~8:37–9:42: the first four lines of the mortgage story in swapped voices (Maya's lines ~117 Hz, Sam's ~150 Hz), back to normal from the fifth line.
- ~6:04–6:56: possibly the end of the inflation/G7 story too; the evidence there is weak.
- ~14:04: Maya's opening line of the Hans Anders story was never voiced. The audio goes straight from the Golden Calf story into Sam's second line.

Both clear failures sit at a story break where the same host speaks the last line of one segment and the first line of the next, inside one TTS request. The scripts had 3–5 such breaks a day (10-01 to 10-03), because Maya both closed and opened stories.

**Change (2026-10-03):** `prompts/script.md` now asks for a host change at every story break, plus a clear one-line topic intro and a closing beat for each story (listeners also found transitions hard to follow). It also bans the stock "Okay, some lighter stuff" gear change. `script.py` checks for same-speaker breaks after writing and asks for one quick rewrite of just those lines if any remain.

**2026-10-04, after the change:** no swap at a story break this time, but one mid-story. In `ep-2026-10-04` (chunk 2, the cleaners' strike story), Maya's line "That doesn't sound terrible. So why did FNV members say no?" at ~3:07 came out in Puck's voice (~111 Hz; Maya's other lines in that chunk sit at 140–158 Hz, Sam's at 102–124 Hz). It follows a long Sam line and Sam answers it, so it sounds like Sam asking himself a question (listener note: "around 3:25 a male voice asked himself a question"). So host changes at breaks don't stop swaps on their own; they can happen at any turn.

**Decision (2026-10-04):** don't build the pitch check yet. Re-requesting chunks could push a slow morning past the job limit. If swaps become a daily issue, first look for what's causing them (chunk size, style hints, line length, how turns are marked) before re-requesting chunks until the voices come out right.

**Trigger:** if a swap or dropped line still turns up at a break that has a host change, consider (a) voicing the cold open as its own small request and checking the "I'm Maya" / "I'm Sam" lines' pitch with a stdlib autocorrelation, re-requesting once on a swap; or (b) a per-line pitch check on every chunk (Kore ~145–290 Hz, Puck ~95–135 Hz) that re-requests a chunk once on a clear mismatch.

### Gemini voices sound worse in packed TTS requests
*Logged 2026-09-29, updated 2026-10-04*

**Problem:** the 2026-09-29 episode (`ep-2026-09-29`, Gemini voices) sounded noticeably worse than Sunday's (`ep-2026-09-27`), which used the same voices. This is a listener report; nobody has yet compared the audio side by side.

**What was checked (CI logs and code):**
- **Same:** model (`gemini-3.8-flash-tts`), voices (Maya = Kore, Sam = Puck), `conversational` mode and per-line style hints. None changed between the two episodes.
- **Different:** Sunday made one TTS call per story segment (7 calls, about 2 minutes of audio each, 2,259-word script, 14m18s). Today's run made 7 calls packed to the 600-word cap by `_chunk()` (about 2.5–4 minutes each, 3,165-word script, 18m36s). Sunday's run predates the packing commit `48fc17c`.
- **Ruled out:** today's episode fell back to neither Microsoft voices (the log says `gemini voices`) nor the later `ep-2026-09-29-ms` rebuild.
- **Not checked:** today's run restored working files from an earlier failed run ("Resume from today's last failed run"). Check whether any reused TTS chunks came from that run.

**Hypothesis:** long single generations drift toward flatter, faster delivery, and Sunday's short calls kept resetting that. Unconfirmed for Gemini TTS.

**Options:**
1. Lower `MAX_WORDS_PER_REQUEST` in `src/nlnews/tts.py` from 600 to about 300 (roughly one call per story). A 3,000-word script then needs 10+ calls, which hits the free tier's 10/day limit and triggers the Microsoft fallback.
2. Enable billing on the Gemini key, which removes the daily cap so small chunks work. TTS is cheap.
3. Split at story boundaries only, with a cap around 400 words.

**Plan:** [docs/shorter-sunday-quality-episodes.md](docs/shorter-sunday-quality-episodes.md). Cut to 6–7 stories and Sunday-sized chunks (~320 words, 8 requests max) so the voices stay inside the free tier. Do not run Gemini TTS to A/B this; that quota is for the next episode. The side-by-side listen (story-sized chunk vs a 600-word chunk, script in the `episode-data` artifact of run 36521945724) stays optional. Related item below: "Test voicing the whole episode in one TTS request" (same drift question, opposite direction).

**Update 2026-10-04:** per-segment word caps from the plan are being tried on the branch `claude/story-length-caps` (backlog item "Story lengths vary on purpose" above). They cut test scripts to ~2,450 words, but one Gemini request per story would still need 11–12 requests, over the 10/day cap. A 600-word cap now gives 5–6 requests. A 450-word cap would give 7–8 requests, mostly 1–2 stories each.

### Set up the 06:00 backup trigger on cron-job.org
*Logged 2026-10-01*

Only the 04:13 job exists, so when that run fails (as on 2026-10-01) nothing retries it. In cron-job.org, copy the 04:13 job and set the time to 06:00 Europe/Amsterdam; everything else (URL, body, headers, token) stays the same. Check that a test run returns `204` and that the workflow's gate job then logs `ep-<date> is already published`. 06:00 leaves room for a 04:13 run that uses the full 65-minute limit; if the first run is still going, the backup waits in the `episode` concurrency queue and then skips at the gate. Afterwards, update the README **Scheduling** section and the comment at the top of `episode.yml`.

### Renew the cron-job.org GitHub token by Monday 28 December 2026
*Logged 2026-09-29*

The fine-grained PAT that cron-job.org uses to start `episode.yml` was created on 2026-09-29 with a 90-day expiry, so it stops working on **2026-12-28**. Once it lapses, the daily trigger (and the backup, once set up) gets `401` and no episode is made, with no error on the GitHub side. Renew it a week or so early: create a new fine-grained PAT (**Actions: read and write** on this repo only), paste it into the `Authorization: Bearer` header of every cron-job.org job, check that a test run returns `204`, then revoke the old token. Setup details are in the README under **Scheduling**.

### Match loudness when an episode mixes Gemini and Microsoft voices
*Logged 2026-09-28*

**Context:** when Gemini TTS fails partway through (daily limit, timeout or the 30-minute budget), the rest of the episode is voiced with Microsoft voices (edge-tts), so one episode can contain both engines. In a test with a stand-in for Gemini (macOS `say`), the two halves came out 1.5 LUFS apart (-16.6 vs -18.1), about the threshold where most listeners notice. The gap with real Gemini audio is unmeasured.

**Proposed fix (tested, not shipped):** add `"-af", "loudnorm=I=-16:TP=-1.5:LRA=11"` to the final ffmpeg call in `tts.synthesize_episode`. That brings every episode to the podcast standard of -16 LUFS and evens out the two engines. It also changes all-Gemini episodes, which is why it was held back.

**Trigger:** ship it if a real mixed episode has an audible volume jump at the switch.

### Test voicing the whole episode in one TTS request
*Logged 2026-09-27*

**Context:** the Gemini TTS free tier allows 10 requests/day (we hit `429 ... limit: 10 requests per day` on 2026-09-27). `src/nlnews/tts.py` now packs segments into ~600-word requests, so an episode takes about 4 requests. One request per episode would be simpler and use 1/day.

**Unknowns:** Google doesn't document the maximum output per TTS request. A 13-minute episode is about 20k audio tokens, and going over the cap may truncate the audio without an error. Long single generations may also let the voices drift in pace and tone, and one failure loses the whole episode.

**Proposed test:** try the full script as one request first. Check that the returned WAV duration is at least ~85% of the expected duration (words ÷ ~160 wpm; observed rates were 148–180 wpm). If it's short, fall back to the ~600-word chunks. Worst case is about 5 requests/day, still under the limit. Also listen for voice drift across the episode.

**Constraint:** run it on a day with spare TTS quota. Don't run it alongside the 04:13 episode.

### Collect headlines through the day (feed coverage)
*Logged 2026-09-27*

**Problem:** most feeds only expose their latest 10–30 items. The 04:13 run keeps items from the last 26 hours, but on a busy weekday the NOS general feed (20 items) may only reach back a few hours, so earlier stories never enter the pool. On 2026-09-27 (a quiet Sunday), 13 feeds gave 87 unique articles; NOS culture returned 0 and DutchNews.nl returned 2.

**Idea:** a lightweight "collect" workflow runs every 3–4 hours. It only fetches and appends new items to a rolling store (e.g. a `data-cache` branch or an Actions cache), with no LLM calls and nothing published. The morning run then picks from the full day's collection instead of a single snapshot.

**Also consider:**
- **More section feeds:** add more of them (NOS regional and tech, NU.nl domestic) so each feed's cap covers a narrower stream.
- **Per-source caps:** today `weight` is only a hint to the model and doesn't limit how many items a source contributes.

### Full text for NU.nl and Het Parool
*The research pass now fills the worst gaps (e.g. missing names) from other sites, but the writer would still do better with the full article.*
*Logged 2026-09-27*

Both are DPG Media sites that redirect to a cookie-consent wall (`myprivacy.dpgmedia.nl`), so the pipeline only gets their RSS summaries. Parool is also paywalled. NOS provides full text, so this is lower priority.

### Evaluate Claude vs Gemini vs NotebookLM
*Logged 2026-09-27*

Four versions of the 2026-09-27 episode to compare:
- **A:** Gemini picks, writes and voices everything. Kept at `compare/A-gemini-local/` and in the podcast feed.
- **A2:** Claude (on the Pro subscription) picks and writes; Gemini TTS voices it. Text only for 2026-09-27, at `compare/A2-claude/`, because the TTS quota was spent. Claude picked 9 stories, including culture and world items that Gemini skipped. The first A2 audio is the 2026-09-28 06:30 episode.
- **B:** NotebookLM Audio Overview built from our English briefing.
- **C:** NotebookLM built from the raw source articles, doing its own translation and synthesis.

Decide the default writer from the results. Claude becomes the default automatically when `CLAUDE_CODE_OAUTH_TOKEN` is set, with Gemini as the fallback.

### Housekeeping
*Logged 2026-09-27*

- **GitHub Actions:** Node 20 deprecation warning; bump `actions/*` versions. The `ubuntu-latest` runner moves to Ubuntu 26 on 2026-10-19.
- **Local Claude CLI:** on the Mac it's v2.1.131 (the `opus` alias → `claude-opus-4-7`). `brew upgrade claude` would match the latest version that CI installs.
- **Gemini API key:** it was pasted into chat; consider rotating it in AI Studio, then rerun `./scripts/sync-secrets.sh`.

### Future: sectioned episodes
*Logged 2026-09-27 (from the original brief)*

Newspaper-style segments: Amsterdam, national politics, arts & culture, business, world news from the Dutch point of view. Feeds are already tagged with a `section` in `sources.yaml`.

## Done

- **2026-10-05** One failed Gemini request no longer costs the rest of the episode, and big requests get a longer timeout. `ep-2026-10-05` was Gemini for the 21-second cold open only and OpenRouter for the other 11 segments. Not the daily limit: run 37254523549 made 4 of its 10 requests. Request 2, the 557-word lead story (close to the 600-word cap), timed out three times, and a failed request used to switch Gemini off for good, though only ~11 of the 30 budgeted minutes were spent and requests 3–8 were ordinary sizes. Now only the failed chunk goes to the backup and Gemini is tried again on the next one. Gemini is still dropped for the rest on the daily limit, when the budget runs out, after two failed chunks in a row, or once Microsoft voices are in use (so the hosts don't change voice and back; without an OpenRouter key the first failure still ends Gemini). The timeout is now 0.5 s per word with the old 180 s as the minimum: 278 s for that lead story, 300 s at the cap. Whether that would have saved it is unknown: the third attempt ran ~295 s before timing out (the first two stopped at exactly 180 s; on 2026-10-04 a third attempt succeeded after ~319 s). Worst case for the job grows by ~2 min (a request that starts just before the budget ends can now run 5 min, not 3), to ~63 of the 65-minute limit. Tested on that day's script with stand-ins for all three engines, so no real requests: failing request 2 keeps 7 of 8 chunks on Gemini; requests 2 and 3 failing sends the rest to OpenRouter; requests 2 and 5 failing keeps 6 chunks; a daily-limit error stops Gemini at once; no key goes to Microsoft for the rest. Watch: retries spend the 10-a-day quota if timed-out requests count (8 chunks plus one chunk's 2 retries is exactly 10), and how Gemini → OpenRouter → Gemini sounds. The long-term fix is shorter lead stories (the parked `story-length-caps` branch).
- **2026-10-04** OpenRouter is the first backup for Gemini TTS, with Microsoft voices last. When a Gemini request fails for good, the remaining segments are voiced line by line with the same voices (Kore, Puck) through OpenRouter's `google/gemini-3.8-flash-tts`, 6 lines at a time, with style hints passed as `speech_metadata`. If any line of a segment fails twice (once on 401/402/403, e.g. out of credit), that whole segment and the rest go to Microsoft voices, so a story never switches voices halfway. The OpenRouter part gets an 8-minute budget (a full episode takes ~2–3 min) and 60 s per line, and the job limit went from 55 to 65 min to keep the worst case (~61 min) inside it. `synthesize_episode()` now returns the engines used, joined by `+` (e.g. `gemini+openrouter`), and the show notes name the backup. Tested with stand-ins for all three engines, so no real requests: no failure gives `gemini`; Gemini failing from chunk 6 gives `gemini+openrouter` (54 line requests); OpenRouter also failing from segment 9 sends segments 9–12 to Microsoft voices; no key goes straight to Microsoft; a 402 on the first segment stops OpenRouter after one try per line. The key is the `OPENROUTER_API_KEY` Actions secret. Watch: the first real switch, and whether OpenRouter hangs when Gemini direct does (it's the same Google backend).
- **2026-10-04** Gemini's TTS budget raised from 20 to 30 min, and the job limit from 45 to 55 min to keep room for it (65 min after the OpenRouter backup, above). `ep-2026-10-04` switched to Microsoft voices at ~11:24 for its last five segments (UvA apology onwards). Not the daily limit: run 37170374188 made 8 of its 10 requests. Gemini was slow (request 1 took 2.5 min, request 2 1.3 min; they're often ~40 s), request 3 timed out twice at 180 s before succeeding (~11.5 min for that chunk), and request 6, started ~2 min before the budget ran out, timed out after it and wasn't retried. The run took 32 min. New worst case: ~11 min before TTS (research can add 4), 30 min of Gemini plus up to 3 min for a request that starts just before the budget ends, ~7 min if Microsoft voices the whole episode, and ~1 min to publish: about 52 min.
- **2026-10-02** Long dead air inside Gemini audio is cut down. `ep-2026-10-02` had 1.8 s of silence and then a breath mid-line, before "Three cases have turned up in Germany and France" at the end of the Ebola story (~2:33). It was in Gemini's own output for chunk 1, not at a chunk boundary. `tts._cap_pauses()` now shortens any silence over 1.0 s (below -55 dBFS, 20 ms windows) in each Gemini chunk to 0.7 s, using only the stdlib (`ffmpeg`'s `silenceremove` in 6.1 left these gaps untouched in testing). On today's 9 chunks it changed only that one gap (chunk 1: 160.04 s to 158.98 s); every other pause, including the normal 0.6–1.0 s ones between lines, is left as is. Microsoft fallback audio isn't touched. Watch: a dramatic pause the model meant to leave would also get trimmed to 0.7 s.
- **2026-10-01** Mixed-voice fallback. When Gemini TTS fails partway, the episode keeps the Gemini chunks already made and only the remaining segments are voiced with Microsoft voices (Ava / Andrew); before, any failure re-voiced the whole episode. Decided on 2026-09-28 in a local chat: David preferred the better Gemini voices for as long as they last over hosts that never change voice. It was built that day on the local branch `tts-partial-fallback`, but the scheduled merge of 2026-09-29 stopped before merging and the branch was never pushed, which is why a cloud session on 2026-10-01 logged it as an open question. Rebased on 2026-10-01 onto the timeout work: a daily-limit error, a request that fails 3 times (180 s timeout each) or the 20-minute `GEMINI_BUDGET` all stop further Gemini requests, and the rest goes to Microsoft. Chunks end on segment boundaries, so the switch falls in the 0.7 s pause between stories. `synthesize_episode()` returns `gemini`, `mixed` or `fallback`; the show notes say "Partly voiced" or "Voiced with backup Microsoft voices because Gemini's voices were unavailable" (the old wording blamed the daily limit, which is wrong for timeouts). Tested on the 09-28 script (5 chunks) with macOS `say` standing in for Gemini, so no real Gemini requests: no failure gives `gemini`; daily limit on chunk 3 gives `mixed` after 3 requests; daily limit on chunk 1 gives `fallback` after 1; connection resets from chunk 3 give `mixed` after 3 tries on that chunk; budget used up after chunk 2 gives `mixed` with no further requests. A rerun over a mixed episode re-voices nothing while Gemini is still down, and replaces the Microsoft part with Gemini once it recovers. Not built: a spoken handoff line at the switch (a cloud-session idea, never requested) and loudness matching (backlog item above). Watch: how the first real mixed episode sounds at the switch, and that an episode can go Gemini, Microsoft, Gemini if a rerun finds later chunks saved.
- **2026-10-01** Gemini TTS requests time out after 3 min. The 04:13 run was cancelled at the 30-minute job limit: Gemini requests hung ~4 min each before failing with "Connection reset by peer" (not the daily quota, which raises at once), and 4 tries per chunk used up the clock. Each request now has a 180 s client timeout and 3 tries, so a stuck chunk gives up in ~9.5 min and the Microsoft fallback voices the episode. All Gemini requests together also get a 20-minute budget (`GEMINI_BUDGET`): a run where every chunk fails twice and then succeeds would otherwise take ~45 min for 6 chunks and still miss the job limit. No Google status page or outage report covered the 02:14–02:43 UTC window; two hours later the same requests took ~40 s each. Job limit raised to 45 min, and `PYTHONUNBUFFERED=1` so the pipeline's progress lines show in the Actions log (they were missing). The 06:00 cron-job.org backup didn't fire because it was never set up (see the open item above); the episode was published by a manual rerun at 04:26 UTC that resumed from the failed run's audio.
- **2026-09-29** Scheduling moved to cron-job.org. GitHub's `schedule` trigger never fired, not once since the repo was created. That included the original `30 4` cron, the `13 2`/`13 3` pair, the same cron re-saved under the account's noreply email, and a bare `*/5` probe workflow. On the same morning, `workflow_dispatch` runs from 05:09 UTC sat queued with no jobs (GitHub reported one as both completed and queued) while githubstatus.com showed no incident. Now cron-job.org POSTs to the dispatches API at 04:13 Amsterdam time (setup in README); the planned 06:00 backup job was not created. The gate skips when today's release already exists, and a `force` input overrides that. The concurrency group was renamed to `daily-episode-v2` while testing the stuck queue; that didn't help. What fixed it was copying the workflow to a new file, `episode.yml`: its runs start straight away, while `daily.yml`'s stuck runs couldn't even be force-cancelled. `daily.yml` is deleted. Watch: whether the 2026-09-30 04:13 run gets a runner.
- **2026-09-29** Follow-ups instead of repeats. The 09-29 episode re-told the Ramallah expulsion and re-ran the same electricity and fuel-tourism figures from 09-28. `previous.py` now loads the last 2 days' published briefings (the `briefing.md` release asset; `data/` doesn't survive between Actions runs), cached as `previous.json`. Articles those episodes already used are dropped before clustering. The selector sees what was covered, and an old story comes back only with a real development (`follow_up_of`). The writer gets the earlier summary and writes just the new part, plus a one-line `previously` recap; the hosts frame it as an update and keep it short. Tested on 09-29's news in the scratchpad: the petrol/electricity rehash was dropped, the Ramallah and budget stories came back as updates (250 and 464 words), and a youth-prisons and an Amsterdam-debt story filled the freed room. Watch: whether "real development" is judged too loosely (the German ICC visit counted as a follow-up), and whether a story from 3+ days ago slips back in.
- **2026-09-28** Fact-check pass. The briefing writer lists each story's `open_questions` (missing facts, or where outlets disagree) instead of hedging in the text; `research.py` looks them up with web search (claude-code WebSearch/WebFetch) before the script is written, one call per story in parallel, and records cited answers as `findings` (shown as **Checked:** lines in `briefing.md`). The unresearched draft is cached as `briefing.draft.json`. Each lookup is capped at 4 min with no Gemini fallback, and a failed lookup keeps the story as written, so research can delay the run by ~4 min at most but never fail it. The script prompt now bans on-air talk about "the write-up"/"our sources" and gets the date spelled out (a test script had said 29 September on the 28th). Tested in `compare/mix-2026-09-28/research-test/`: 13 of 14 questions answered, including the Parool-only Bib Gourmand story and the NOS vs NL Times conflict over the Dutch Gaza-center staff. Watch: answers can vary between runs; some citations are Wikipedia or partisan outlets; scripts ran ~2,300 words. Untested: Gemini's search tool (hit a 429), and the first run in Actions.
- **2026-09-28** Apple Podcasts "can't play on this device" fixed. The feed linked to GitHub release downloads, which redirect to signed URLs that expire (~40 min) and are served as `application/octet-stream` attachments; Apple caches the redirect, so playback failed until a restart. MP3s are now copied to Pages at `<secret>/episodes/<tag>.mp3` and the feed points there. Verified on the phone with a test episode. Manual runs gained a `feed_only` input to rebuild and redeploy the feed without a new episode.
- **2026-09-28** Story mix: each pick is tagged `hard` or `light`, with 2–3 light stories per episode (`NLNEWS_LIGHT_STORIES`, default `2-3`) at the end, and politics capped at ~3. Added NOS sport/offbeat/tech/royals and NU.nl entertainment/science/food feeds; slow feeds look back 72h via a per-source `hours`. Chose the balanced mix (B) over 1 light story (A) and 4–5 (C) after comparing sample scripts in `compare/mix-2026-09-28/`. Open question: no arts story made it in on the sample day, so watch whether culture/arts ever wins a slot over sport and Amsterdam stories.
- **2026-09-27** TTS packed into ~600-word requests (about 4/episode instead of one per segment), to fit Gemini's 10/day free limit.
- **2026-09-27** Briefing must cover every selected story. The Gemini briefing had dropped 3 of 8.
- **2026-09-27** Claude Code subscription writer, with Gemini fallback.
- **2026-09-27** Email made optional; GitHub release notifications recommended as the backup.
- **2026-09-27** Hosts told to use contractions, so the script sounds natural read aloud.
