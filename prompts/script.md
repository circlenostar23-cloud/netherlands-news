Today is {today}. Write the script for today's episode of "{show}", a daily ~12-minute two-host English podcast about news from the Netherlands. The audience is English-speaking internationals living in the Netherlands, especially newcomers.

Hosts:
- {host_a}: the anchor. She's warm and crisp, keeps things moving, and frames each story.
- {host_b}: the explainer. He's curious, a little wry, and asks the questions a newcomer would ask ("wait, who's that?"), then answers with context.

Style: like NPR's Up First or The Daily, delivered by a well-matched pair. Keep it conversational but substantive, with natural back-and-forth and short sentences written for the ear. Use contractions the way people actually talk ("it's", "we're", "let's"). Avoid lists of numbers, URLs, and markdown. Say Dutch names naturally and gloss them the first time ("the Tweede Kamer, the Dutch House of Representatives"). No invented facts: everything must come from the briefing. Never talk about the briefing, the write-up, or "our sources". If something is still unknown, say it the way a reporter would ("the names haven't been released yet", "it's not yet clear how many people are affected"). If outlets still disagree after the research, say who reported what. Keep any humor light, and never make light of tragedies.

Structure:
1. A short cold open: the top line, a hook, and a hello with the date.
2. One segment per story, in the briefing's order. Give the top 2–3 stories the most room.
3. Tone follows each story's `kind`, not its position. Light stories (`kind: light`) are looser and more playful: the hosts react, riff a little, and connect it to life here. Keep them shorter than the big stories, but give each a real moment of fun or curiosity, not just a headline. Let the story itself set the new tone; never announce it. No "Okay, some lighter stuff", "On a lighter note", "Time for something fun" or similar. A playful first line does the job ("{host_b}, have you got a spare 180 million dollars?"). Coming back to hard news after a light story, just start the story plainly.
4. Stories with a `previously` line are follow-ups to something the show covered in the last day or two. Frame them as updates: one quick line of recap for anyone who missed it ("Yesterday we told you Israel was stripping Dutch diplomats in Ramallah of their status. Now…"), then straight to what's new. Don't re-explain people, parties or background you already gave; a few words of gloss is enough. Keep a follow-up shorter than a new story of similar weight, unless the development itself is the day's big news. Spend the time you save on the new stories.
5. Transitions between stories have to be clear to someone half-listening while cooking or cycling, without sounding like a radio jingle:
   - End each story on a short closing beat: what happens next, what it means for listeners, or a host's one-line reaction. Don't summarise the story, and don't trail off mid-explanation into the next one.
   - Open each story with a short first line that names the new topic in plain words before any detail ("Now, mortgages, and some bad news if you're over fifty."). Keep it to one sentence. The detail starts on the next line.
   - Link stories when there's a real connection (same place, same people, same wallet). Otherwise a plain "Next," or just the topic is fine. Vary the wording; don't open every story with "Next".
   - Hand over at every boundary: the host who speaks a story's last line never speaks the next story's first line. {host_b} can open a story, or {host_a} can end one by handing over to {host_b}'s reaction. This also applies to the cold open, the What's on in Amsterdam segment and the sign-off. The voice engine mixes up the hosts when one of them speaks twice in a row across a story break.
6. The last story is always a light closer. It leads naturally into a quick sign-off, or into the What's on in Amsterdam segment when there is one.

Aim for {words_min}–{words_max} words total. Each `segment` is one story (or the intro/outro). Use exactly the speaker names {host_a} and {host_b}. `style` is an optional short delivery note for the voice actor (e.g. "serious", "amused").
