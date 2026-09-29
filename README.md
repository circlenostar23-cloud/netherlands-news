# Dutch Daily Briefing

A daily ~12-minute, two-host English podcast about news from the Netherlands, built for newcomers.

```
RSS (NOS, NU.nl, Parool, NL Times, DutchNews) → cluster → LLM picks 6–9 stories
  → LLM writes English briefing from full article text (briefing.md — NotebookLM-ready)
  → LLM writes two-host script → Gemini multi-speaker TTS → episode.mp3
  → GitHub Release + private podcast feed (GitHub Pages) + email backup
```

## Local use

```bash
python3.13 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env   # fill in keys
.venv/bin/python -m nlnews run --stop-after briefing   # fetch + curate only (cheap)
.venv/bin/python -m nlnews run --no-publish --no-email # full episode, local MP3 only
```

Output lands in `data/<date>/`: `articles.json`, `selection.json`, `briefing.md`, `script.md`, and `episode.mp3`. Stages are cached per day, so re-running resumes where the last run stopped. Use `--fresh` to rebuild everything.

**NotebookLM comparison:** upload `data/<date>/briefing.md` (also attached to the daily email) to a notebook and click **Audio Overview**.

## One-time setup (GitHub Actions)

1. Create the repo on **circlenostar23-cloud** and push.
2. Go to **Settings → Pages → Source: GitHub Actions**.
3. Fill in the keys in `.env`, then run `./scripts/sync-secrets.sh` to push them as Actions secrets. The full list of **secrets** is:
   - `CLAUDE_CODE_OAUTH_TOKEN`: optional but recommended. Run `claude setup-token`. Claude (Opus, through Claude Code) then writes the briefing and script on your Claude Pro/Max subscription, with no API billing. If it fails, for example because you've hit your usage limit, the run falls back to Gemini.
   - `GEMINI_API_KEY`: from aistudio.google.com/apikey (free tier). Used for the voices, and for writing when there's no Claude token.
   - `ANTHROPIC_API_KEY`: optional, only if you switch the writer to Claude
   - `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO`: optional. If any are missing, email is skipped. A Gmail app password grants full mailbox access, so the recommended backup is instead: on the repo page, **Watch → Custom → Releases**. GitHub then emails you each new episode, with the MP3 and the briefing as downloads.
   - `FEED_SECRET_PATH`: a random string, e.g. the output of `openssl rand -hex 12`
4. Add a **variable** `SITE_BASE_URL` set to `https://circlenostar23-cloud.github.io/netherlands-news`.
5. Go to **Actions → Daily episode → Run workflow** to test it.
6. Subscribe. In Apple Podcasts: **Library → ⋯ → Follow a Show by URL**, then paste `<SITE_BASE_URL>/<FEED_SECRET_PATH>/feed.xml`. Overcast and Pocket Casts support adding a feed by URL too.

**Scheduling:** GitHub's own `schedule` trigger never fired for this repo, so a free [cron-job.org](https://cron-job.org) account starts the workflow instead. Two jobs, both in the Europe/Amsterdam time zone, run daily at **04:13** and at **06:00** as a backup. Each sends a `POST` to `https://api.github.com/repos/circlenostar23-cloud/netherlands-news/actions/workflows/daily.yml/dispatches` with body `{"ref":"main"}` and these headers:
- `Authorization: Bearer <token>`
- `Accept: application/vnd.github+json`
- `X-GitHub-Api-Version: 2022-11-28`
- `Content-Type: application/json`

The token is a fine-grained PAT with **Actions: read and write** on this repo only. It expires, so renew it before then. A successful request returns `204`. The gate job skips any trigger once today's `ep-<date>` release exists, so the backup never spends TTS quota. To rebuild anyway, run the workflow manually with **force** ticked.

**Privacy note:** the feed is *unlisted*, not private. Its URL is unguessable and `itunes:block` keeps it out of directories, but on a public repo the release MP3s are visible to anyone who browses it. It's fine for personal use; don't share it publicly.

## Tuning

- `sources.yaml`: add or remove feeds. `section` tags drive future segmenting.
- `prompts/`: story selection, briefing style, and the hosts' voice and format.
- `src/nlnews/config.py`: host names and voices (`HOSTS`) and the show title. Set `NLNEWS_WRITER=claude` to write with Claude instead of Gemini (the Claude API is paid separately from a Claude Pro subscription, at about $0.10–0.30 per episode).

**Cost:** $0 by default, since both writing (`gemini-3.8-flash`) and voices (`gemini-3.8-flash-tts`) run on the Gemini API free tier. The voices free tier allows 10 requests a day. If Gemini TTS fails (usually that limit), the episode is voiced with free Microsoft neural voices instead (`FALLBACK_VOICES` in `config.py`, via edge-tts) and the show notes say so. On the free tier, Google may use your inputs to improve its products; that's fine here, because the inputs are published news articles.
