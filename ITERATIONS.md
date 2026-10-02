# Iterations log

Ideas and known issues parked so they don't disrupt the working daily pipeline. Newest first. Move an item to **Done** once it ships.

## Backlog

### Gemini swapped the hosts' voices in the 2026-10-02 intro
*Logged 2026-10-02*

**Problem:** in `ep-2026-10-02`, Sam's voice (Puck) said "It's Friday, October second. I'm Maya." and Maya's voice (Kore) said "And I'm Sam." The script attributes the lines correctly, and the request sends `speaker: Maya` / `speaker: Sam` per line, so Gemini slipped at a turn boundary. Pitch per line (Kore ~160–290 Hz, Puck ~80–140 Hz) shows the rest of that chunk was voiced correctly from "This is Dutch Daily Briefing" on. The 09-30 and 10-01 intros were checked the same way and were correct.

**Decision:** no code change for a first occurrence. A cheap guard doesn't exist: re-voicing a chunk costs a request from the 10/day free tier (today used 9), and a pitch check per line needs a speech model in CI.

**Trigger:** if it happens again, consider (a) voicing the cold open as its own small request and checking the "I'm Maya" / "I'm Sam" lines' pitch with a stdlib autocorrelation, re-requesting once on a swap; or (b) writing the intro so each host's self-introduction is a longer line rather than a 3-word one.

### Gemini voices sound worse in packed TTS requests
*Logged 2026-09-29*

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

### Set up the 06:00 backup trigger on cron-job.org
*Logged 2026-10-01*

Only the 04:13 job exists, so when that run fails (as on 2026-10-01) nothing retries it. In cron-job.org, copy the 04:13 job and set the time to 06:00 Europe/Amsterdam; everything else (URL, body, headers, token) stays the same. Check that a test run returns `204` and that the workflow's gate job then logs `ep-<date> is already published`. 06:00 leaves room for a 04:13 run that uses the full 45-minute limit; if the first run is still going, the backup waits in the `episode` concurrency queue and then skips at the gate. Afterwards, update the README **Scheduling** section and the comment at the top of `episode.yml`.

### Renew the cron-job.org GitHub token by Monday 28 December 2026
*Logged 2026-09-29*

The fine-grained PAT that cron-job.org uses to start `episode.yml` was created on 2026-09-29 with a 90-day expiry, so it stops working on **2026-12-28**. Once it lapses, the daily trigger (and the backup, once set up) gets `401` and no episode is made, with no error on the GitHub side. Renew it a week or so early: create a new fine-grained PAT (**Actions: read and write** on this repo only), paste it into the `Authorization: Bearer` header of every cron-job.org job, check that a test run returns `204`, then revoke the old token. Setup details are in the README under **Scheduling**.

### Match loudness when an episode mixes Gemini and Microsoft voices
*Logged 2026-09-28*

**Context:** when Gemini TTS fails partway through (daily limit, timeout or the 20-minute budget), the rest of the episode is voiced with Microsoft voices (edge-tts), so one episode can contain both engines. In a test with a stand-in for Gemini (macOS `say`), the two halves came out 1.5 LUFS apart (-16.6 vs -18.1), about the threshold where most listeners notice. The gap with real Gemini audio is unmeasured.

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
