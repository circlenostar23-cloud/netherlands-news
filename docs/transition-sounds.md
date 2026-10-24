# Transition sounds between stories

Built into the pipeline (`src/nlnews/cues.py`) with the set chosen in rounds 11–16 (2026-10-24), on branch `claude/cues-new-set-34ee9a` until David merges it (see Pick up here). `main` still plays the round 10 set.

## Pick up here

**The new set is built in** (branch `claude/cues-new-set-34ee9a`, 2026-10-24) and waiting for David to listen and merge.

**Round 19 (David's notes on round 18):** the sooner story cues and the split before the breath are good; "this format worked for me to review" (clips per transition).
1. "hard-4-short doesn't need to go after hard-4 … it can be in rotation with the other three", and hard-4 for the longer stories; "overall we should just make sure we aren't repeating the same melodic phrases over and over." `hard-4-short` now rotates with `hard-1/2/3` (in the order 1, 3, 2, 4-short, so the two E D B cues sit apart), and `hard-4` plays once, before the hard story with the most airtime if it's 300+ words. Many cues share a cell of the reversed anthem, so each cue's cells are listed in `PHRASES`, and `rotate()` searches (with backtracking) for picks where no two neighbouring breaks share a cell, themes included, and no cue repeats before the rest of its pool has played:

   | Cell | Played by |
   |---|---|
   | D F# G A | `light-1`, the intro theme's opening, the up-first sting, the end of What's on's theme, the outro bed's hook |
   | B C D | `light-2`, the intro theme, the start of What's on's theme |
   | C D E D | `light-3`, What's on's theme |
   | E D B | `hard-3`, `hard-4`, `hard-4-short`, the sombre intro theme |
   | B D E | `hard-1`, the sombre sting |

   Consequences: the light story right after the intro gets `light-3` or `light-4`, and the closer before What's on gets `light-4` (the only light cue sharing nothing with that theme). With five hard stories after the lead, one hard cue plays twice, never in a row. On a sombre day `hard-4` is left out if it would follow the sombre theme. Checked on both days over a week of dates and on 300 random line-ups: no neighbouring clash.
2. "The outro stings sounded a little quieter." Measured over 1.2 s from each downbeat in the mix: the story cues at −21.9 to −23.0 dB, What's on's theme at −25.1 and the button at −23.6. What's on's theme was ducked for the last story's final word too (0.3 s before its downbeat, with a 0.45 s release); it now ducks only for the hosts coming back, plus a 0.5 dB lift (`LIFT`). The button was held 1.7 dB down by the −9 dBFS peak cap, which scaled a whole cue for one bell strike; `_limit()` now brings down only the few ms around a peak (it also let `hard-4-short` and `light-2` up ~1 dB). Now: What's on −22.8, the button −22.6 to −22.8, inside the story cues' range.
3. "Swap back in the one that ended with the bells": round 15's `b no hats, bells` (bed-b without hi-hats, with fuller bells and no shaker). The round 17 button (`b no hats`) is in `assets/cues/round-17/`.

Clips, in `data/transition-samples/round-19-rotation/` in the main checkout (whole episodes there too):

| Clip | Into | At |
|---|---|---|
| `10-23 01 intro` | cold open into the student loan story | 0:00 |
| `10-23 02 hard-1` | Hajar: a plea for help | 2:28 |
| `10-23 03 hard-3` | Dutch embassy in Cairo | 4:20 |
| `10-23 04 hard-2` | Schiphol's new decree | 5:59 |
| `10-23 05 hard-4-short` | Fake-pill webshops | 7:03 |
| `10-23 06 hard-1` | National Slavery Museum | 8:35 |
| `10-23 07 light-1` | A historic night for Dutch football | 9:48 |
| `10-23 08 light-2` | Airbnb hosts | 11:12 |
| `10-23 09 light-4` | The Euromast's mystery whistle | 12:16 |
| `10-23 10 outro` | This weekend in Amsterdam | 13:01 |
| `10-23 11 button` | after the sign-off (bells) | 14:48 |
| `10-24 01 intro` | cold open into the Kushner story | 0:00 |
| `10-24 02 hard-4` | Hajar was killed the day she vanished | 2:41 |
| `10-24 03 hard-2` | Storm Austen | 4:48 |
| `10-24 04 hard-4-short` | PHP flaw | 6:15 |
| `10-24 05 hard-1` | Albert Heijn deliveries | 7:34 |
| `10-24 06 hard-3` | single-use packaging | 8:15 |
| `10-24 07 light-2` | Van Gerwen | 10:04 |
| `10-24 08 light-4` | Sinterklaas's steamboat | 11:27 |
| `10-24 09 outro` | What's on in Amsterdam | 12:51 |
| `10-24 10 button` | after the sign-off (bells) | 14:02 |

On 10-23 no hard story reaches 300 words (Hajar has 280), so it has no `hard-4`.

**Round 18 (David's notes on the round 17 episodes):**
1. "The tones between stories feel a tiny bit delayed." A story cue went in at the next story's start, after the whole pause, so its downbeat came 0.4–1.9 s after the last word (mean 1.3 s). It now lands like the themes: downbeat `STORY_AFTER` (0.6 s) after the last word, swell starting as the host finishes, the next story's first words under its ring-out as before. That's ~0.7 s sooner on average, and the same at every break.
2. "On 10-23 the intro sting came after a breath." A gap in the solver: the split (and the breath fix, `_cut()`) took the quietest moment in the gap, and on 10-23 the stillness between the inhale and "Now…" (−60 dB) was deeper than the one between the first sentence and the inhale (−54 dB), so the split went after the breath. `_before_breath()` now looks for the breath itself (40 ms+ between 45 and 20 dB under the voices, after a quiet) and splits before it: 10-23's split moved from 4.63 s to 4.23 s. `_cut()` uses the same check; no story break on 10-23 or 10-24 had the problem, so none of them moved.
3. "Why are we repeating hard-4 and hard-4-short?" They went to every hard story over the airtime cut-offs (two `hard-4-short` on each day). Now each plays at most once an episode: `hard-4` before the hard story with the most airtime if it's 300+ words, `hard-4-short` before the next if it's 220+. The rest rotate `hard-1/2/3`, which with five hard stories still plays one of them twice (never in a row).
4. "Give me a way to jump between the transitions": samples now come as one short clip per transition (below), numbered in order, as well as the whole episode.

Its clips are in `data/transition-samples/round-18-sooner/`.

| Part | What plays | Where it is |
|---|---|---|
| Intro | The cold open's first sentence dry; the `up-first` sting 0.3 s after its last word, split in the quiet before the next breath (`_before_breath()`); the rest of the cold open over the `up-first` bed; the intro theme 0.3 s after the cold open's last word | `cues._opening()`; split from `first_sentence()` and `_quiet_point()` (round 15's `sentence_ends()` and `quiet_point()`) |
| Sombre intro | The same on the `sombre-pulse` bed with the sombre sting and `sombre-intro` theme, on a day whose `mood` is `sombre` | `mood` in `prompts/select.md` and `StorySelection`; override with `--mood` or the workflows' `mood` input |
| Hard stories | `hard-1`, `hard-3`, `hard-2`, `hard-4-short` in rotation (round 11's minor, minor, sus; round 14); `hard-4` once, before the hard story with the most airtime if 300+ words. Neighbours never share a phrase. Each lands 0.6 s after the last word | `cues.plan()`, `rotate()`, `ORDER`, `PHRASES`, `MAJOR`; `STORY_AFTER` |
| Light stories | `light-1/2/3` (round 10) and `light-4` (round 11) in rotation | `cues.plan()` |
| Outro | Six bars of the `between` loop fade in under the last story's end; What's on's theme 0.3 s after its last word; the hosts start after two of its three bars; the `between` bed from its last bar line under What's on and the sign-off; button `bed-b` without hi-hats, with bells, 0.3 s after the last word | `cues._section()`, `_closing()` (round 15's `closing()`) |

**How it's built:**
- **Rotation:** each kind's rotation starts at the day number mod the pool size, so every cue is heard over a week (before, `hard-1` and `light-1` opened every show and `light-3` was rarely heard). `hard-4` isn't in the rotation and plays once an episode at most.
- **Files:** story cues and themes are WAVs in `assets/cues/`, written by `docs/transition-sounds/render-cues.py` straight from the round scripts' functions. Every cue keeps its 0.65 s lead-in, so the pipeline knows where its downbeat is; `light-1/2/3` were re-rendered from round 9's functions for that (identical to round 10's files once trimmed). The round 10 files replaced are in `assets/cues/round-10/`; move one back up to restore it (it would then play 0.65 s late, since it has no lead-in).
- **Beds as stems:** a bed's bar count and tempo change daily, and CI has no Logic, so `render-cues.py` also writes each bed as one-beat stems (`assets/cues/beds/<bed>/<bar>.<beat>.flac`, 8.3 MB): the last 8 bars by bars left (`near-1` … `near-8`), any earlier bar by its chord (`far-0` … `far-3`), the sting's 2 bars, and the outro's first bar. `_bed()` lays them on the fitted beats. At the beds' own tempo this matches round 13's `bed()` sample for sample (correlation 0.999); at a fitted tempo the hits stay within 2 ms of it (8 ms at a 6% nudge). Stretching whole bars with ffmpeg's `atempo` was tried first: it moved hits by 10–14 ms and smeared them.
- **Fitting:** `_fit()` picks the bar count nearest the bed's own tempo; a nudge of more than 12% (`MAX_NUDGE`, only a very short span) leaves the bed out. On ep-2026-10-24: up-first +1.5%, outro +0.6%, sombre −0.4%. The button and themes play at their own tempo, not the bed's (round 15 rendered the button at the fitted tempo; the difference is under 1% on these days).
- **Level and ducking** follow round 13's `bed_level()`: the bed set to the voices' level, then ducked 17 dB under them while they speak and 9 dB between lines; the sting plays 4 dB up until the hosts start; What's on's theme dips 10 dB under the hosts (only them, not the story's last words). Cues are peak-limited at −9 dBFS over a few ms (`_limit()`), not scaled down whole. Checked against round 15's 10-23 intro demo: same timing, music under the voices within 0.5 dB.
- **Time:** the sting adds time at the split, and each theme from where the voice is cut to where the hosts come back; a bed adds none. `shift()` moves the chapters and transcript to match. Every transcript line on both days was checked against the audio: all within 20 ms.
- **Fallbacks:** without a split (one-sentence cold open, no `chunk00`, Whisper missing), without the stems, or with too big a nudge, the theme still lands 0.3 s after the last word, without the bed. Without a heard What's on start, the button lands alone. If the cues fail outright, the episode is built without them, as before.
- **Fixed on the way:** `shift()` compared each cut (a whole sample) with the heard start exactly, so at about half the breaks not moved for a breath, the story's first transcript line kept its time from before the cue (3–5 s early). That was 6 of 10 breaks on ep-2026-10-23 and 3 of 9 on 10-24. It's its own commit and can go to `main` alone, like the rotation fix.

**Testing on Actions:** only `main` may deploy to `github-pages`, so **Test episode**'s `publish` can't run from a branch. Its new `check` action builds a day the same way, without publishing, and keeps the episode as the `test-episode` artifact. It passed for 10-23 and 10-24 on the branch (runs 40095646383 and 40095857332), with the same bars, cues and length as the local builds and no voice requests. After merging, `publish` (with `mood: sombre` to hear that intro) puts a test episode in the feed.

**Next:** David listens to the round 19 clips and decides whether to merge. `STORY_AFTER` is the one number to change if the story cues should come sooner or later still. Watch for: a cold open whose first sentence is very short (the sting comes in only a few seconds in, as on 10-24); the first `mood: sombre` the selection sets, and its reason in the log.

**Re-rendering the cues** (on this Mac, from the main checkout's `.venv`): `python docs/transition-sounds/render-cues.py assets/cues`. It takes ~10 s and doesn't need `render.swift`.

### Rounds 11–16, as found

**Notes for the build** (kept from before it was built):
- **Split point:**
  - The split goes in the quiet just after the first sentence's last word, so the breath for the next sentence plays after the sting with it (Whisper's word starts land after the breath).
  - `sentence_ends()` matches the script's words to Whisper's and handles misheard names ("DigiD" heard as "digiid").
  - `quiet_point()` searches from 0.3 s before Whisper's sentence end, since its word times can be a few tenths out.
- **Glitches in the voiced audio:** the glitch at "students are furious" on ep-2026-10-23 was in Gemini's audio, not the mix. A separate session is adding a dropout check to `voicecheck.py`.

**Choosing hard-4.** `kind` has no measure of scale, but each story's `airtime` (its word budget, from `prompts/airtime.md`) is the editor's judgment of how much it matters. Story order is too, but the first story gets the intro theme, not a hard cue. A cut-off relative to the day's airtimes would also work; the fixed one is easier to predict.

**Round 13 is built from the run's voiced files** (the `episode-data` artifact) with the pipeline's own placement: `chapters.find()`, `cues.plan()` and `cues._cut()`, which includes the breath fix. Run it as `PYTHONPATH=src python round-13.py <out> data/<day>`. Rounds 11–12 cut their demos from the published episode, which already had round 10's cues in it. Samples for each round are in `data/transition-samples/round-NN/` in the main checkout.

**Joining a bed to a theme on both sides:** a bed has two fixed points: where it starts (the top of the show, or What's on's theme's last bar line) and where its theme lands. `fit()` picks the bar length nearest the bed's own tempo that fits a whole number of bars between them. The outro bed starts at What's on's tempo on its theme's last bar line, so there's no fade-in. On ep-2026-10-24 the music held at −22 to −27 dB across the join, then ducked when the hosts came back in.

**Choosing the sombre intro:** keyword rules or counting hard stories would misfire too often, so the selection step judges it. A single murder story isn't enough; ep-2026-10-24, which led with the Hajar case among others, stays `usual`.

**Landing a theme after the hosts.** David heard "a bit of a lag" between the last word and the theme in round 11's cold-open mixes. It was 1.63 s: the cut followed the transcript's end time, which runs about 0.3–0.6 s past the last word, then came 0.25 s of quiet and the 0.65 s swell. Round 12 finds the last word in the audio (`last_word()`), lands the theme's downbeat 0.3 s after it, and plays the swell under the word. The beds are built backwards from the landing, with their bars counted back so the last one is always D9sus, so the fixed loop never forces a wait.

### The round 10 set (2026-10-23; replaced files in `assets/cues/round-10/`)

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

Run from the main checkout (its `.venv` has numpy). Needs Logic Pro's sound library on this Mac (see "Real instruments without downloads" below). Story cues are defined by `RETRO` / `RETRO_HARM` and `air_pulse()` in `round-9.py`; the themes by `THEMES_SPEC` and `theme()` in `round-10.py`. Round 11 runs the same way (`round-11.py <out-dir> <episode.mp3> <transcript.vtt>`; the episode files, from `gh release download ep-<date> -p episode.mp3 -p transcript.vtt`, give the cold-open demos). Round 10's samples are in `data/transition-samples/round-10-themes/` in the main checkout: one file per tone (`v2 hard-1.mp3`, `theme intro.mp3`, ...) and demo episodes.

**Known issues to tweak next:**
- The three hard cues are hard to tell apart: the same lead-in, register and mostly the same chords. Round 11 gives each its own opening (only the kick, only the swell, a soft hat pickup) and varies register and rhythm.
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
| 11 | After hearing ep-2026-10-24, the first episode with cues. Hard cues: "a little more neutral rather than so positive", in two versions (suspended, minor). light-4. Five sign-off takes. Intro bed in three feels | Notes on round 10: **light-1 and light-3 are favourites** (jazzy chords, more interesting rhythm); **What's on is the favourite theme** (jazzy, the suspended last note); the intro theme is "pretty good"; the button "sounds a little too christmasy". On round 11: minor hard-1, sus hard-2, minor hard-3 and light-4 are good; likes buttons anthem-b and free-b; "really like" the up-first and between beds |
| 12 | The round 11 picks together; the up-first bed under the real cold open into the first story; the between bed under the sign-off, or What's on and the sign-off, into each liked button; themes land 0.3 s after the last word | Hard picks and light-4 confirmed; on the outro: "the What's on version is best" with anthem-b, and asked whether the bed could join the theme instead of fading in. On the intro: try a sting at the top; the cut sounded like it lost a breath; wanted a more serious version for a day after a tragedy |
| 13 | Built from the run's voiced files with the breath fix. Intro: a sting at the top, the up-first bed, the intro theme. A sombre intro for tragedy days. Outro: What's on's theme straight into the between bed, tempo fitted to land anthem-b | Intro "nice": try some of the cold open dry before the sting. Sombre intro "nice": hear a couple of other options; its end sting could also be a hard story cue. Outro: too long a wait for What's on's theme after the story; anthem-b is a little mismatched with the bed |
| 14 | Intro: cold open dry, sting, hello over the bed. Sombre beds `pulse` and `air`; `hard-4` (and `hard-4 short`). Outro: What's on's theme fades in under the story's end, hosts over its last bars; buttons `bed-a/b/c` from the bed | Split intro: the sting comes in too late and covers a breath; try it after a sentence or two. **sombre-pulse**, **hard-4** (for a major story) and **hard-4 short** (a less major one) are great. Outro: **bed-b** is best; wanted a loop fading in under the story's end, not just one bar; try bed-b without hi-hats and with bells |
| 15 | Sting after one or two sentences, split before the breath. Outro loop of six bars under the story's end. bed-b without hi-hats, with glint, with fuller bells. Re-rendered on ep-2026-10-22, and the intro test on ep-2026-10-23 for longer sentences | **The outro is ready**, with bed-b without hi-hats. The sting goes **after two sentences**. Asked about a glitch at "students are furious" (Gemini's) and for a loop fading in before the sting |
| 16 | 2 or 4 bars of the up-first loop fading in under the second sentence, into the sting | "Good to try", but cleaner without: **the sting after the first sentence**, with no loop before it. The set is decided |

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

**More samples on this Mac:** Logic's Drum Kit Designer kits (acoustic, `EXS Factory Samples/Drum Kit Designer Consolidated`) are one long file per drum with the hits end to end; the sampler can't load them, but splitting at the attacks works (`round-9.py` names the hi-hat hits it uses, by start time; `round-11.py` the snare's soft cross-stick hits). The Alchemy bass `Bass/Real Bass/MMBass Mute` follows Logic's naming except "E0", which sounds at E2 (measured), so `round-11.py` leaves it out. Ultrabeat Samples has drum-machine kits; those hats read as fake.

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

1. **Placement** (`plan()`). The script's segments are the cold open, one per story in the briefing's order, What's on if there is one, then the sign-off. The intro theme (or `sombre-intro`, by the day's `mood`) goes at the first story's start (after the hello). Each later story gets a `hard-*` or `light-*` cue by its `kind`, rotating within that kind from a cue that moves on each day; a hard story with enough airtime gets `hard-4` or `hard-4-short` (`MAJOR`). The section theme goes at What's on, and the button after the sign-off. If the segments don't fit that shape, the episode gets no cues.
2. **Only at heard breaks.** `chapters.find()` now also returns each segment's start and whether Whisper heard it (or it's the start of a file) rather than estimating it. A cue at an estimated start is skipped, because an estimate can be seconds off.
3. **Splice** (`splice()`, with `_opening()`, `_section()` and `_closing()` for the themes and beds; see Pick up here). The MP3 is rebuilt from the voiced files in `concat.txt`, with the cues in, and encoded once with the same settings as `tts.py`. Because it always starts from the voiced files, a rerun (e.g. **Test episode**, which deletes `chapters.json`) never adds the cues twice. If the cues fail, the MP3 is rebuilt without them.
4. **Breaths.** Whisper sometimes puts a word's start just after the host's inhale for it, so cutting there plays breath, cue, word. `_cut()` looks back `BREATH_BACK` (0.8 s) for the quietest 40 ms; if that's more than `QUIET` (50 dB) under the voices and something after it is louder than `BREATH` (36 dB under), it cuts at the quiet, and the breath plays under the cue's ring-out with its line. On ep-2026-10-24 and 10-23 this moved 1 of 19 cuts (the 10-24 intro, 0.30 s earlier): breaks at a file start have no breath on either side, and at the others Whisper's start is usually before the breath already. Margins: that breath was 31.5 dB under the voices, the loudest other sound before a break 42 dB under. A false trigger only moves the cut within silence. Before/after clips: `data/transition-samples/breath-cut/` in the main checkout.
5. **Timing.** A story cue's downbeat lands `STORY_AFTER` (0.6 s) after the last word, and the next story starts `UNDER_NEXT` (0.6 s) before the cue ends, under its ring-out; the time added is whatever that needs beyond the pause already there. A theme lands `LAND_AFTER` (0.3 s) after the last word, found in the audio (`_last_word()`), with its swell under the word; the hosts come back `UNDER_NEXT` before its end (the intro) or after `HOST_BARS` of its bars (What's on). `shift()` moves the chapters and transcript to match: a chapter opens at the cut, and the transcript line starts after the cue.
6. **Level.** Each cue is trimmed of silence (a theme keeps its lead-in), set to `CUE_UNDER` (7 dB) under the episode's voices, and capped at `PEAK` (-9 dBFS). The files' own level and padding don't matter. The beds are set and ducked as in Pick up here.

**Swapping tones:** the cue files are `assets/cues/{hard-*,light-*,intro,sombre-intro,section,button}.wav`, 44.1 kHz mono. There can be any number of `hard-*` and `light-*` files, and a missing one is skipped. `light-1/2/3` are the round 10 MP3s converted to WAV; the rest come from `render-cues.py`. A theme's downbeat must be `LEAD` (0.65 s) into its file. Folding to mono didn't change their level (checked on `hard-1` and `section`).

**First run with the round 10 set, ep-2026-10-23** (built locally from that day's run files): 11 cues and 11 chapters, every break heard. The episode went from 14:34 to 15:13 (+39.6 s): ~3 s per story break and ~5.3 s per theme, so more than the ~2 s planned above. Raise `UNDER_NEXT` to let more of each ring-out run under the voices. **Test episode** on Actions (Ubuntu) gave the same result and made no voice requests; the test release was then removed.

**Rebuilding a day locally** (no voice requests): download its run's `episode-data` artifact into `data/`, delete `chapters.json` and `transcript.vtt`, and run `python -m nlnews run --date <day> --stop-after audio` from this checkout's code (in a worktree, set `PYTHONPATH=src` so the main checkout's install isn't used).

Test changes with **Actions → Test episode** (no TTS requests; `check` from a branch, `publish` from `main`). The research behind the editorial choices: [Big Podcast on show sound](https://newsletter.bigpodcast.com/p/the-sound-of-your-show), [NPR's Morning Edition theme variations](https://www.newscaststudio.com/2019/05/06/npr-morning-edition-theme-music/), [MuseHub on podcast sound effects](https://www-cf.musehub.com/learn/podcast-sound-effects).
