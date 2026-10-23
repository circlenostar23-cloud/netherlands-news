# Transition sounds between stories

Not shipped. Discovery paused 2026-10-23 after six rounds of samples; this is the handoff for picking it back up.

**Goal:** a short sound at each story break so a half-listening listener hears that the show has moved on. The script's spoken transitions stay; the sound marks the break and the hosts' first line says what's next.

## Where things are

- **Samples:** `data/transition-samples/` in the main checkout (gitignored, not in the repo). One folder per round; every round's folder also has the script that made it.
- **Scripts:** `docs/transition-sounds/` here. `round-1.py` also shows how to splice cues into a real episode at its chapter starts. `round-3.py` to `round-6.py` import `synth.py`. They need `numpy` and `ffmpeg`; run with a downloaded `episode.mp3` (`gh release download ep-<date> -p episode.mp3`) for round 1.

## Decided

**Flow and placement** (David: "heading in the right editorial direction"):
- **A family, not one sound.** One idea, in one key, varied by job, so ten breaks an episode don't play the same thing ten times.
- **Chosen by the next story's `kind`.** Before a `hard` story: lower, softer, sparser. Before a `light` one: a little higher and brighter. Rotate within each group so no two breaks in a row repeat. This also does what `prompts/script.md` asks of the hosts: the tone shift is signalled without being announced.
- **Bigger moments get bigger cues.** A longer phrase opens What's on in Amsterdam; a short resolving "button" follows the sign-off. No cue between the cold open and the first story, where the hello already does the job.
- **Short and under the voices.** About 1.5 s of notes, ~7 dB under the speech, peaks capped at -9 dB. The ring-out can run under the next host's first words, so a break costs ~2 s, not 3.

**Theme:** build the family from fragments of the **Wilhelmus** (David's idea). Use different parts of the song, not just the opening; few notes, unhurried. Only the What's on cue should be plainly recognisable; the story cues just hint at it, so the anthem never sounds ceremonial before a sad story.

Fragments used (melody as in Valerius 1626, notated in G on [nl.wikipedia](https://nl.wikipedia.org/wiki/Wilhelmus)):

| Cue | Fragment | Notes |
|---|---|---|
| hard | "Wil-hel" (line 1) | D G |
| hard | "...je heb ik" (line 4) | G F# D |
| hard | "...schen bloed" (line 1) | A G |
| light | "Prin-ce van" (line 3) | D E D |
| light | "al-tijd ge-" (line 4) | E F# G |
| light | "Wil-hel-mus" (line 1) | D G G |
| What's on | "Een prin-ce van O-ran-je" (line 3) | D E D C B |
| button | "ge-eerd", the anthem's last two notes | F# G |

A different low note under each (E under the hard cues gives a sober, minor colour) helps cues that share notes sound different. The melody is from the 1570s, so it should be public domain; that's an inference, not checked.

## What David thought of each round

| Round | Tried | Verdict |
|---|---|---|
| 1 | Soft chime, carillon, marimba, pulse, tick, spliced into ep-2026-10-23 | Liked **marimba** and **pulse** |
| 2 | Variations on those two, a marimba+pulse hybrid, kalimba, vibes, e-piano, felt piano, guitar; first rotation demo | Liked the family and kind-based rotation; open to other sounds |
| 3 | Seven families: celesta, pizzicato strings, analog synth, handpan, jazz trio, **news ticker** (woodblock into a tone), lo-fi piano | All built on the same D-major chord, which was a fair complaint |
| 4 | Wilhelmus fragments on six instruments | Too many notes too fast: "erratic" |
| 5 | Slower fragments from across the song, on the news ticker | "Ok", but repetitive: every cue opened with the same three woodblock ticks |
| 6 | No shared lead-in: lute, church organ, cello, shortwave radio | Direction fine, but **"still sound pretty robotic"** |

## Lessons

- **The synthesis is the bottleneck.** Every sound so far is made from sine waves, plucked-string and filtered-noise recipes in numpy. That's fine for a quick sketch and for electronic or bell-like sounds, but real instruments (lute, cello, organ, piano) come out robotic. The next round needs real recorded or generated instruments.
- **Repetition comes from shared openings**, not from reusing the motif. Any lead-in common to every cue (the ticker's ticks) makes ten breaks sound identical.
- **Few notes, slow.** Two or three notes at ~0.35 s each worked; four or more quick notes sounded erratic.
- **Always share a rotation demo**, not just single cues: a cue that's nice once can be grating at the tenth break. The demos voice placeholder story names with macOS `say`.

## Next: tools to try

Pick something that renders the same fragments with real instrument sounds. In rough order of effort:

1. **SoundFont rendering (free, local, deterministic).** Write the fragments as MIDI and render them with `fluidsynth` (`brew install fluid-synth`) and a free General MIDI SoundFont (e.g. MuseScore General or FluidR3). Real sampled instruments, exact notes, seconds to render, and small enough to run in the pipeline or to pre-render once. Probably the best first try, since the notes are already decided.
2. **Free recorded-instrument libraries.** VSCO 2 Community Edition (orchestral, CC0), the University of Iowa instrument recordings, CC0 sounds on Freesound. More work to map notes to files, but the most natural sound.
3. **AI music generation**, for a texture or bed rather than exact notes:
   - **MusicGen (Meta)** can loosely follow a given melody. The code is MIT, but the weights are reportedly non-commercial (CC-BY-NC). That's fine for a personal feed; check before anything public. Runs locally, slowly on CPU.
   - **Stable Audio Open** is reportedly good at short sound design and ambient textures, weaker on structured melody. License not checked.
   - **Google Lyria (Gemini API)** reportedly has no free tier: about $0.04 per 30-second clip (third-party pricing, check ai.google.dev). Cheap for a one-off, since the cues would be rendered once and committed.

Whatever renders them, the cues should be made once and committed as files (`assets/cues/*.wav`), not generated per episode.

## Building it into the pipeline (once the sounds are picked)

Mostly simple, with one catch: Gemini voices several stories per request, so there's no file per story to put a cue between. The chapter step already finds where each story starts (Whisper, snapped to a pause), so:

1. After `chapters.find()` in `cli.py`, cut the episode at each chapter start and insert the chosen cue (by the next story's `kind`, rotating; the What's on cue before the agenda; the button after the sign-off; nothing before the first story).
2. Shift the chapter starts and the transcript's cue times by the time inserted before them, then embed the chapters.
3. Skip a break's cue when its chapter start was estimated, not heard: an estimate can be a few seconds off, and a cue mid-story is worse than none.

About 50–80 lines across `tts.py`/`chapters.py`/`cli.py`. Test with **Actions → Test episode** (no TTS requests). The research behind the editorial choices: [Big Podcast on show sound](https://newsletter.bigpodcast.com/p/the-sound-of-your-show), [NPR's Morning Edition theme variations](https://www.newscaststudio.com/2019/05/06/npr-morning-edition-theme-music/), [MuseHub on podcast sound effects](https://www-cf.musehub.com/learn/podcast-sound-effects).
