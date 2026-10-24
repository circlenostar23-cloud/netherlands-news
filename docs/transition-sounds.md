# Transition sounds between stories

Built into the pipeline (`src/nlnews/cues.py`) with the round 10 set; the tones are still being refined and any of them may be swapped. Ten rounds of samples on 2026-10-23; the direction is chosen (round 9 version 2 plus the round 10 themes).

## Pick up here

**The chosen set: "version 2", the anthem backwards, with its themes.** In David's words, round 9's version 2 is "more dynamic", and he'll keep building on it and the round 10 themes, refining with smaller tweaks before it goes into episodes. Round 8's approach 5 (same production, the anthem's original fragments) is kept in reserve.

| Cue | Plays | Notes | Chords |
|---|---|---|---|
| `hard-1` | before a hard story | D F# G | C → G |
| `hard-2` | before a hard story | G A B | C → G |
| `hard-3` | before a hard story | G F# G | G → D → G |
| `light-1` | before a light story | D F# G A | D → A/G |
| `light-2` | before a light story | B C D | Cmaj7 → G |
| `light-3` | before a light story | C D E D | F → G |
| `theme intro` | after the hosts' hello, before the first story | D F# G A, B C D, E D (3 bars) | D, A/G, C, G |
| `theme section` | opens What's on | B C D E D, C D E D, D F# G A (3 bars) | G, C, F, G, D, A/G |
| `theme button` | after the sign-off | A B C B, A G (2 bars) | F, C, D, G |

All cells come from the Wilhelmus read backwards (phrases written out in `round-9.py`), so the anthem is no longer recognisable, only its intervals. Nothing is minor: minor read as sad (round 7).

**The sound:** Rhodes (Logic's EPiano Mrk II) plays the melody and the chords, with a "glint" an octave up: a Logic bell with its hum and strike filtered out and a short ring. Each cue leads in with a real open hi-hat played backwards into a soft kick; light cues add real closed hats on the beat, and the themes add closed hats on the eighths and a soft shaker. Hard cues are slower (0.36 s a beat), quieter and darker than light ones (0.30 s).

**Render it:** `round-10.py` makes the whole set (and re-renders round 9's two versions for reference):

```bash
swiftc -O docs/transition-sounds/render.swift -o /tmp/render
RENDER=/tmp/render .venv/bin/python docs/transition-sounds/round-10.py data/transition-samples/round-11
```

Run from the main checkout (its `.venv` has numpy). Needs Logic Pro's sound library on this Mac (see "Real instruments without downloads" below). Story cues are defined by `RETRO` / `RETRO_HARM` and `air_pulse()` in `round-9.py`; the themes by `THEMES_SPEC` and `theme()` in `round-10.py`. The latest samples are in `data/transition-samples/round-10-themes/` in the main checkout: one file per tone (`v2 hard-1.mp3`, `theme intro.mp3`, ...) and demo episodes.

**Known issues to tweak next:**
- The three hard cues are hard to tell apart: the same lead-in, register and mostly the same chords. Give each its own opening (only the kick, only the swell, a soft hat pickup) and vary register and rhythm.
- The themes haven't had feedback yet.
- The demo episodes voice placeholder lines with macOS `say`. To hear a tone in a real episode, swap its file and rebuild a day locally (see "How the pipeline plays them").

**How David reviews:** one file per tone, named by version and cue, listed in a table (tone, where it plays, file) so feedback can name a tone; demos play each cue once. Share samples before any pipeline work.

**In the pipeline:** see "How the pipeline plays them" at the end of this doc. To swap a tone, replace its file in `assets/cues/`.

**Goal:** a short sound at each story break so a half-listening listener hears that the show has moved on. The script's spoken transitions stay; the sound marks the break and the hosts' first line says what's next.

## Where things are

- **Samples:** `data/transition-samples/` in the main checkout (gitignored, not in the repo). One folder per round; every round's folder also has the script that made it.
- **Scripts:** `docs/transition-sounds/` here. `round-1.py` also shows how to splice cues into a real episode at its chapter starts. `round-3.py` to `round-6.py` import `synth.py`; `round-7.py` and up import `logic.py` (Logic Pro samples, see below). They need `numpy` and `ffmpeg`; run with a downloaded `episode.mp3` (`gh release download ep-<date> -p episode.mp3`) for round 1.

## Decided

**Flow and placement** (David: "heading in the right editorial direction"):
- **A family, not one sound.** One idea, in one key, varied by job, so ten breaks an episode don't play the same thing ten times.
- **Chosen by the next story's `kind`.** Before a `hard` story: lower, softer, sparser. Before a `light` one: a little higher and brighter. Rotate within each group so no two breaks in a row repeat. This also does what `prompts/script.md` asks of the hosts: the tone shift is signalled without being announced.
- **Bigger moments get bigger cues.** Short themes (a few bars, ~5 s, with light percussion) play after the hosts' hello before the first story, at the start of What's on in Amsterdam, and after the sign-off. (Earlier plan had no cue after the hello; David wants one, 2026-10-23.)
- **Short and under the voices.** About 1.5 s of notes, ~7 dB under the speech, peaks capped at -9 dB. The ring-out can run under the next host's first words, so a break costs ~2 s, not 3.

**Theme:** build the family from fragments of the **Wilhelmus** (David's idea). Use different parts of the song, not just the opening; few notes, unhurried; the anthem should never sound ceremonial before a sad story. Rounds 4–8 used fragments as written (below); from round 9 the chosen set uses the melody backwards (see Pick up here).

Fragments used in rounds 4–8 (melody as in Valerius 1626, notated in G on [nl.wikipedia](https://nl.wikipedia.org/wiki/Wilhelmus)):

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
| 7 | Real recorded instruments in stereo: glass bells with a reverse-reverb inhale and echoes, flute/clarinet over strings, a singer humming the fragment, Rhodes on tape. Eight cues (three hard, three light) | Liked **glass bells** and **Rhodes**; harmony "too sad and low-key". Wants calm yet present, at ease but focused |
| 8 | No minor chords: IV→I / V→I in open add9, sus2 and maj7 voicings; hard vs light by energy, not mode. Five approaches on bells and Rhodes: open chords, a Rhodes pulse leading in, the motif scattered across octaves with echoes, call and answer ending on an upward step, a hi-hat swell and soft kick lead-in | **Approach 5 (air and pulse) is the closest yet**, kept in reserve. Its hats sounded fake (drum-machine), the bells too heavy, "like church bells"; the kick was nice. Also wants to loosen the fixed melodic sequence |
| 9 | Two developments of approach 5. (1) Real acoustic hats sliced from Logic's Drum Kit Designer kit, and a "glint" bell: hum and strike filtered out, ring cut short, an octave above the Rhodes. (2) The same production on cells from the anthem played backwards (rising lines, pickups into the downbeat) over new chords including a borrowed F (bVII→I) and A-over-G (Lydian) | **Version 2 is more dynamic**; glad of the rethink. The three hard cues were hard to tell apart (same opening, register and chords) |
| 10 | Longer themes (3 bars, ~5 s) in version 2's language with a fuller kit (kick, closed hats on eighths, soft shaker): **intro** after the hello, **What's on**, **sign-off**. Demos now play each cue once, hard and light alternating; every tone is its own file, named by version and cue | "Getting somewhere solid": **version 2 plus these themes is the set to refine** |

## Lessons

- **The synthesis is the bottleneck.** Every sound so far is made from sine waves, plucked-string and filtered-noise recipes in numpy. That's fine for a quick sketch and for electronic or bell-like sounds, but real instruments (lute, cello, organ, piano) come out robotic. The next round needs real recorded or generated instruments.
- **Repetition comes from shared openings**, not from reusing the motif. Any lead-in common to every cue (the ticker's ticks) makes ten breaks sound identical.
- **Few notes, slow.** Two or three notes at ~0.35 s each worked; four or more quick notes sounded erratic.
- **Minor reads as sad.** Round 7 put hard cues on low minor chords (Em, Bm, Am) to sound sober; David heard it as sad. Round 8 keeps hard cues sparser, slower and warmer instead, in the same major harmony.
- **Present samples as one file per tone**, named by version and cue (`v2 hard-1`), in a table, so feedback can be tone-specific. Demos play each cue once.
- **Always share a rotation demo**, not just single cues: a cue that's nice once can be grating at the tenth break. The demos voice placeholder story names with macOS `say`.

## Real instruments without downloads (round 7)

This Mac has Logic Pro's sound library, so round 7 needed no new tools:

- **Sampler instruments** (`/Library/Application Support/Logic/Sampler Instruments/09 Orchestral`: flute, clarinet, strings, horn, brass) load into macOS's `AVAudioUnitSampler`, which `render.swift` drives offline from a JSON score. The newer "consolidated" instruments (Steinway, guitars) don't load that way.
- **Alchemy samples** (`.../Logic/Alchemy Samples`: bells, Rhodes, pads, sung vowels) are plain WAVs, one per note; `round-7.py` pitches each note from the nearest one. Logic names them with C3 as middle C, so they sound an octave above their names, and the Bell Attack Pad set is recorded about 42 cents flat. Both measured.
- Apple's licence lets you use this content in your own productions; it isn't redistributable as samples, so commit rendered cues, not the source WAVs.

The options below are still the fallback if this library isn't available (CI, another machine).

**More samples on this Mac:** Logic's Drum Kit Designer kits (acoustic, `EXS Factory Samples/Drum Kit Designer Consolidated`) are one long file per drum with the hits end to end; the sampler can't load them, but splitting at the attacks works (`round-9.py` names the hi-hat hits it uses, by start time). Ultrabeat Samples has drum-machine kits; those hats read as fake.

## Next: tools to try

Pick something that renders the same fragments with real instrument sounds. In rough order of effort:

1. **SoundFont rendering (free, local, deterministic).** Write the fragments as MIDI and render them with `fluidsynth` (`brew install fluid-synth`) and a free General MIDI SoundFont (e.g. MuseScore General or FluidR3). Real sampled instruments, exact notes, seconds to render, and small enough to run in the pipeline or to pre-render once. Probably the best first try, since the notes are already decided.
2. **Free recorded-instrument libraries.** VSCO 2 Community Edition (orchestral, CC0), the University of Iowa instrument recordings, CC0 sounds on Freesound. More work to map notes to files, but the most natural sound.
3. **AI music generation**, for a texture or bed rather than exact notes:
   - **MusicGen (Meta)** can loosely follow a given melody. The code is MIT, but the weights are reportedly non-commercial (CC-BY-NC). That's fine for a personal feed; check before anything public. Runs locally, slowly on CPU.
   - **Stable Audio Open** is reportedly good at short sound design and ambient textures, weaker on structured melody. License not checked.
   - **Google Lyria (Gemini API)** reportedly has no free tier: about $0.04 per 30-second clip (third-party pricing, check ai.google.dev). Cheap for a one-off, since the cues would be rendered once and committed.

Whatever renders them, the cues should be made once and committed as files (`assets/cues/*.wav`), not generated per episode.

## How the pipeline plays them

`src/nlnews/cues.py`, called from `cli.py` right after `chapters.find()`:

1. **Placement** (`plan()`). The script's segments are the cold open, one per story in the briefing's order, What's on if there is one, then the sign-off. The intro theme goes at the first story's start (after the hello). Each later story gets a `hard-*` or `light-*` cue by its `kind`, rotating within that kind. The section theme goes at What's on, and the button after the sign-off's last word. If the segments don't fit that shape, the episode gets no cues.
2. **Only at heard breaks.** `chapters.find()` now also returns each segment's start and whether Whisper heard it (or it's the start of a file) rather than estimating it. A cue at an estimated start is skipped, because an estimate can be seconds off.
3. **Splice** (`splice()`). The MP3 is rebuilt from the voiced files in `concat.txt`, with the cues in, and encoded once with the same settings as `tts.py`. Because it always starts from the voiced files, a rerun (e.g. **Test episode**, which deletes `chapters.json`) never adds the cues twice. If the cues fail, the MP3 is rebuilt without them.
4. **Breaths.** Whisper sometimes puts a word's start just after the host's inhale for it, so cutting there plays breath, cue, word. `_cut()` looks back `BREATH_BACK` (0.8 s) for the quietest 40 ms; if that's more than `QUIET` (50 dB) under the voices and something after it is louder than `BREATH` (36 dB under), it cuts at the quiet, and the breath plays under the cue's ring-out with its line. On ep-2026-10-24 and 10-23 this moved 1 of 19 cuts (the 10-24 intro, 0.30 s earlier): breaks at a file start have no breath on either side, and at the others Whisper's start is usually before the breath already. Margins: that breath was 31.5 dB under the voices, the loudest other sound before a break 42 dB under. A false trigger only moves the cut within silence. Before/after clips: `data/transition-samples/breath-cut/` in the main checkout.
5. **Timing.** Each break adds `BEFORE` (0.25 s) of quiet plus the cue, minus the `UNDER_NEXT` (0.6 s) of ring-out that plays under the next host's first words, as in the demos. `shift()` moves the chapters and transcript to match: a chapter opens on its cue (at the cut), and the transcript line starts after it.
6. **Level.** Each cue is trimmed of silence, set to `CUE_UNDER` (7 dB) under the episode's voices, and capped at `PEAK` (-9 dBFS). The files' own level and padding don't matter.

**Swapping tones:** the cue files are `assets/cues/{hard-*,light-*,intro,section,button}.wav`, 44.1 kHz mono. There can be any number of `hard-*` and `light-*` files, and a missing one is skipped. The current files are the round 10 MP3s (`v2 *.mp3`, `theme *.mp3`) converted to WAV; for refined versions, export WAV straight from the render script. Folding to mono didn't change their level (checked on `hard-1` and `section`).

**First run, ep-2026-10-23** (built locally from that day's run files): 11 cues and 11 chapters, every break heard. The episode went from 14:34 to 15:13 (+39.6 s): ~3 s per story break and ~5.3 s per theme, so more than the ~2 s planned above. Raise `UNDER_NEXT` to let more of each ring-out run under the voices. **Test episode** on Actions (Ubuntu) gave the same result and made no voice requests; the test release was then removed.

**Next:** listen to ep-2026-10-24, the first daily episode with cues, and check its log for `N cues` and any "no cue before" lines (estimated starts). Then carry on refining tones ("Known issues" above), swapping files in `assets/cues/`.

**Rebuilding a day locally** (no voice requests): download its run's `episode-data` artifact into `data/`, delete `chapters.json` and `transcript.vtt`, and run `python -m nlnews run --date <day> --stop-after audio` from this checkout's code (in a worktree, set `PYTHONPATH=src` so the main checkout's install isn't used).

Test changes with **Actions → Test episode** (no TTS requests). The research behind the editorial choices: [Big Podcast on show sound](https://newsletter.bigpodcast.com/p/the-sound-of-your-show), [NPR's Morning Edition theme variations](https://www.newscaststudio.com/2019/05/06/npr-morning-edition-theme-music/), [MuseHub on podcast sound effects](https://www-cf.musehub.com/learn/podcast-sound-effects).
