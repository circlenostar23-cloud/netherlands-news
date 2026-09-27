# Iterations log

Ideas and known issues parked so they don't disrupt the working daily pipeline. Newest first. Move an item to **Done** once it ships.

## Backlog

### Test voicing the whole episode in one TTS request
*Logged 2026-09-27*

**Context:** the Gemini TTS free tier allows 10 requests/day (we hit `429 ... limit: 10 requests per day` on 2026-09-27). `src/nlnews/tts.py` now packs segments into ~600-word requests, so an episode takes about 4 requests. One request per episode would be simpler and use 1/day.

**Unknowns:** Google doesn't document the maximum output per TTS request. A 13-minute episode is about 20k audio tokens, and going over the cap may truncate the audio without an error. Long single generations may also let the voices drift in pace and tone, and one failure loses the whole episode.

**Proposed test:** try the full script as one request first. Check that the returned WAV duration is at least ~85% of the expected duration (words ÷ ~160 wpm; observed rates were 148–180 wpm). If it's short, fall back to the ~600-word chunks. Worst case is about 5 requests/day, still under the limit. Also listen for voice drift across the episode.

**Constraint:** run it on a day with spare TTS quota. Don't run it alongside the 06:30 episode.

### Collect headlines through the day (feed coverage)
*Logged 2026-09-27*

**Problem:** most feeds only expose their latest 10–30 items. The 06:30 run keeps items from the last 26 hours, but on a busy weekday the NOS general feed (20 items) may only reach back a few hours, so earlier stories never enter the pool. On 2026-09-27 (a quiet Sunday), 13 feeds gave 87 unique articles; NOS culture returned 0 and DutchNews.nl returned 2.

**Idea:** a lightweight "collect" workflow runs every 3–4 hours. It only fetches and appends new items to a rolling store (e.g. a `data-cache` branch or an Actions cache), with no LLM calls and nothing published. The morning run then picks from the full day's collection instead of a single snapshot.

**Also consider:**
- **More section feeds:** add more of them (NOS regional and tech, NU.nl domestic) so each feed's cap covers a narrower stream.
- **Per-source caps:** today `weight` is only a hint to the model and doesn't limit how many items a source contributes.

### Full text for NU.nl and Het Parool
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

- **2026-09-27** TTS packed into ~600-word requests (about 4/episode instead of one per segment), to fit Gemini's 10/day free limit.
- **2026-09-27** Briefing must cover every selected story. The Gemini briefing had dropped 3 of 8.
- **2026-09-27** Claude Code subscription writer, with Gemini fallback.
- **2026-09-27** Email made optional; GitHub release notifications recommended as the backup.
- **2026-09-27** Hosts told to use contractions, so the script sounds natural read aloud.
