# Dutch Daily Briefing

A daily ~12-minute, two-host English podcast about news from the Netherlands, built for newcomers.

```
RSS (NOS, NU.nl, Parool, NL Times, DutchNews) → cluster → Claude picks 6–9 stories
  → Claude writes English briefing from full article text (briefing.md — NotebookLM-ready)
  → Claude writes two-host script → Gemini multi-speaker TTS → episode.mp3
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
3. Go to **Settings → Secrets and variables → Actions** and add these **secrets**:
   - `ANTHROPIC_API_KEY`: from console.anthropic.com
   - `GEMINI_API_KEY`: from aistudio.google.com/apikey
   - `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `EMAIL_TO`: create an app password at myaccount.google.com/apppasswords (2FA required)
   - `FEED_SECRET_PATH`: a random string, e.g. the output of `openssl rand -hex 12`
4. Add a **variable** `SITE_BASE_URL` set to `https://circlenostar23-cloud.github.io/netherlands-news`.
5. Go to **Actions → Daily episode → Run workflow** to test it.
6. Subscribe. In Apple Podcasts: **Library → ⋯ → Follow a Show by URL**, then paste `<SITE_BASE_URL>/<FEED_SECRET_PATH>/feed.xml`. Overcast and Pocket Casts support adding a feed by URL too.

The workflow runs daily at 04:30 UTC, which is 06:30 Amsterdam time in summer and 05:30 in winter.

**Privacy note:** the feed is *unlisted*, not private. Its URL is unguessable and `itunes:block` keeps it out of directories, but on a public repo the release MP3s are visible to anyone who browses it. It's fine for personal use; don't share it publicly.

## Tuning

- `sources.yaml`: add or remove feeds. `section` tags drive future segmenting.
- `prompts/`: story selection, briefing style, and the hosts' voice and format.
- `src/nlnews/config.py`: host names and voices (`HOSTS`) and the show title. Set `NLNEWS_MODEL` or `NLNEWS_TTS_MODEL` to swap models.

Estimated cost is about $0.10–0.30 per episode (Claude Sonnet 5 plus Gemini TTS).
