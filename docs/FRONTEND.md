# Frontend request of 2026-09-25: Brain Battle

> **Now Brain Run** (decision 51, 2026-09-26): on screen the front is called Brain Run and its fighters are runners
> ("Choose your runners", "Ready to run", "‹ Runners", "N runners"); the home brain's glow pulses. Code ids, file
> names and comments keep the old names. The request and answers below are kept as they were given.

The user's request to rework the live viewer's front, recorded as given, with where the project stood that day and
the questions to settle when it is brainstormed. Decisions go to `DECISIONS.md` once made. Branch: `brain-battle`
(a worktree next to the main checkout, so the session tracking fly2's tracks on `fly2-settle` is not disturbed).

## The request, as given

> Let's modify the live viewer. I want to land on a home page called Brain Battle with a cool fighting-game logo.
> After clicking launch, the user is sent to a character select screen. This screen should be themed like Super
> Smash Bros, where the user can pick between Fly, Jev, Haiku, and GLM Flash. Each has their own pixel art for their
> character. The selection method should be the same as super smash bros.
> So, we have 2 different flies, and 4 different of everything else. Those different variations should be skins,
> like how Super Smash Bros has skins. Except, for this, the skins modify the behavior. Change the color of the icon
> in game / pixel art for each skin. Users can proceed when there is 1-8 players selected. The next screen is the
> game selection screen. This should look like the map selection screen in Super Smash Bros. Right now there is only
> one: Run (the game we built)

Added the same day, while it was being recorded:

> before actually imbedding teh visuals, give me an artifact to approve each screen

## In short

1. **Home page, "Brain Battle".** A fighting-game logo and a Launch button.
2. **Character select, Smash-style.** Four characters (Fly, Jev, Haiku, GLM Flash), each with its own pixel art,
   picked the way Super Smash Bros picks them.
3. **Skins are the variants.** A character's variants are its skins: a skin changes the behaviour (which player
   plays) and the colour of its pixel art, in the select screen and in the tunnel.
4. **One to eight players.** The user can go on once 1 to 8 are selected.
5. **Stage select, Smash-style.** The game select looks like Smash's map select; for now it holds one game, Run.
6. **Approve each screen first.** Every screen (home, character select, stage select) is shown to the user as an
   artifact mock-up and approved before any of it is built into the viewer.

## Where the project stood that day

- The live page (`bakeoff live`, `viewer/index.html`, `viewer/app.js`) opens on the Run tab: the lobby's grid
  (`viewer/lobby.js`, one row per question set, one column per model, the fly and the yardsticks below) picks the
  players and the track, then starts the run. The command sets the port and the ceiling; the page drives the rest
  through `/state`, `/run`, `/cancel`, `/events?run=` behind a token (design
  `docs/superpowers/specs/2026-09-22-page-control-design.md`).
- The roster (`bakeoff/replay.py` `CONTESTANTS`, `bakeoff/players/__init__.py`): flies `fly`, `fly2`; Jev `jev_plain`,
  `jev_step1`, `jev_guided`, `jev_step2`, `jev_map`; Claude Haiku `haiku_plain` and the same four sets; GLM Flash
  `glm_plain` and the same four sets; the free yardsticks `solver`, `random`, `always_jump`.
- The sprites (`viewer/sprites.js`) are our own character grids: the fly, the chat critter, Jev's visor, a grey block.
- The page is the user's brand (dark, one blue for the cursor, `--bad` for deaths), plain JavaScript, no build step,
  nothing loaded from the network.
- Another session is tracking fly2's tracks on `fly2-settle` in the main checkout at the same time: this work must
  not touch that checkout, and must not start a fly process (about 1 GB, one at a time on this Mac) while that
  session may be running one.

## Questions to settle

- The roster: the request says four variants of Jev, Haiku and GLM Flash, and there are five of each (the plain set
  and four more question sets). Which four, or five skins? Are the yardsticks on the select screen?
- One character several times: can two slots pick the same character in different skins (as in Smash), and the
  same skin twice (the same player cannot run twice on one track today)?
- "The same as Smash": a cursor (hand) and tokens dropped on portraits, with player slots below; mouse only or also
  keyboard or gamepad?
- The brand: the page is the user's brand (one blue, dark, restrained). Does Brain Battle keep it, or take a bright
  fighting-game look of its own for these three screens?
- The track (seed): where is it picked now, on the stage select or after it?
- Replays (`bakeoff view`): do they get the same front, or only `bakeoff live`?
- Money: the lobby shows the worst-case cost before a paid run starts; where does that confirmation live now?

Added the same day: "also lets figure out where to put the analysis" — where the Analysis tab's contents (levels,
scoreboard, what is ours, the benchmark) go in the new flow.

## Answers so far (2026-09-25)

- **Skins:** all five variants of each model are skins; the plain set (`jev_plain`, `haiku_plain`, `glm_plain`, the
  one broad question) is the default skin, the four other question sets are the others. The sets are named for this
  screen (decision 44): Plain, Guided, Step 1, Step 2 and Map. The Fly has two skins, `fly` and `fly2`.
- **Yardsticks:** a fifth character, "Bot", whose skins are `solver`, `random` and `always_jump`.
- **Duplicates:** one character can fill several slots in different skins; the same skin twice is refused (one
  player cannot run twice on one track).
- **Analysis:** a results screen after the run (the scoreboard and the benchmark, as Smash shows after a match),
  plus a Records entry on the home page for past runs.
- **Look:** the user's brand everywhere: Smash's layout and energy in the dark palette and the two brand fonts,
  blue still only the cursor.
- **Track:** a screen of its own. (First planned after a stage select; the stage select was dropped the same day, so
  the character select leads straight to it.)
- **Input:** mouse and keyboard. A click on a portrait drops the next token there; a slot's colour dot, or X and Y,
  cycles its skin; the arrow keys move a cursor.
- **Replays:** only `bakeoff live` gets the new front for now; `bakeoff view` still opens on the replay.

## Mock-ups (artifacts, one per screen, approved before anything is built)

- **Home** (https://claude.ai/artifact/SBD24j7sBu9acKV4JK4BTK). The user's changes, 2026-09-25: the logo's two
  words are centred; no slash across them; behind them, a solid pixel brain in blue, fairly opaque (0.7), with a
  pulsing glow, set a little below the text's centre. **This brain is the one use of blue that is not the cursor**
  (the user's call). GLM Flash is an ox, for its preview name Ox Alpha: violet head, amber horns and nose ring.
- **Character select** (https://claude.ai/artifact/LsnzaCSjnujcVmFjVWSixP). Five portraits (Fly, Jev, Haiku, GLM
  Flash, and Bot as a sandbag), eight slots, a "Ready to fight" banner from one fighter on, and a line about the
  skin in focus: what it does, its player name, its price.
  Skin colours, as the user settled them (GLM Flash was the source of truth for red and black, Haiku for green):

  | skin | Jev | Haiku | GLM Flash |
  |---|---|---|---|
  | plain | pale `#B9BEC4` | orange `#D97757` | grey `#9AA0A6` (the ox is greyscale) |
  | guided | green `#5FA35A` | the same | the same |
  | step1 | yellow `#E6B422` | the same | the same |
  | step2 | red `#B8404F` | the same | the same |
  | map | black `#1E2227`, visor lit Zima blue `#7AA2F7` | black, blue eyes | black, blue eyes |

  Fly: Looming is the normal fly (grey wings, red eyes); Sideways (`fly2`) swaps them (red wings, grey eyes).
  Bot, a simple boxy robot (no antenna, no mouth), grey on the select screen: Random greys (its first skin), Solver
  Zima blue `#7AA2F7`, Always jump white. Blue and red are used by skins at the user's call, besides the cursor and
  `--bad`.
- **Track select** (https://claude.ai/artifact/FiSSi5jRBeFZNWe5ic3LTJ). There is no stage select: Run is the only
  game, so the character select leads straight here. The track number with previous, next and Random; a preview of
  the whole track (the mock-up's is made up, the page draws the real one); practice tracks 1000–1019 marked with how
  many of this lineup played each before; tournament seeds locked without `--tournament`; the lineup with each
  fighter's worst-case cost and the total; the button says RUN.
- **Results** (https://claude.ai/artifact/J8cjnoH9ca4L3RCPrsgaih), in place of the Analysis tab; Records on the home
  page opens the same numbers for past runs. A card per fighter ranked by rows survived (place, sprite in its skin,
  rows, how it died, time per row, requests, cost), a bar per fighter against the solver's 150, the warning that one
  track is not a result, and Run again, New track, Fighters, Watch the replay, Records, Home. No "winner" banner.
  **More numbers** opens a table (the cards shrink): rows, death, share of jumps, **wrong moves** (rows where the
  move was worse than the best one, and which was fatal; it replaces "agreed with the solver", which is 97–100% for
  every recorded player and so says nothing), **asked live** and **from cache** as two rows, time per row, tokens,
  cost. Failed or unreadable answers are not a row: a warning line appears only when there were any.
- **Records** (https://claude.ai/artifact/7VpmrDjh6XxKw3ZbNPhsh3), opened from home and from the results. The rest of
  the old Analysis tab. A leaderboard of every player on the v2 practice tracks (mean rows and the 95% interval, the
  yardsticks greyed, a player with under 3 tracks "not ranked", and the warning that overlapping intervals are no
  verdict); head to head, where a pair is picked and shows its difference, its interval around 0, wins / ties /
  losses, tracks needed and the verdict (`bakeoff bench`'s own numbers); the past runs, newest first, with their
  status (a run playing now pulses and offers Watch live), Watch and Results; and "What is ours" as a panel. The
  mock-up's numbers are real (`bakeoff bench` over the v2 practice runs, 2026-09-25).

The mock-ups' sources are kept in `docs/mockups/brain-battle/` (the artifacts' `.dc.html` pages: a design canvas
format, not viewer code). They are the approved look; the build writes the viewer's own plain JavaScript from them.

## Later: the Writeup page (the last step)

Added by the user on 2026-09-25, after the Records mock-up: "a Writeup page that does a scientific analysis of what
we found in my own words, as well as my opinions and thoughts. That can wait to be the final step at the end."

- A page of its own in Brain Battle (reached from home, next to Records), written in the user's words: the
  scientific analysis of the findings, and the user's own opinions and thoughts, kept apart from the analysis.
- It is the **last** step, after Brain Battle is built. It goes with phase 6's write-up (`docs/NEXT.md`, "What the
  write-up must carry"): the tournament's results are what it analyses, and the honesty rules hold on it (what is
  ours is labelled; one track or five is not a result).
- Not in this spec. It gets its own brainstorm when its turn comes; the numbers it cites come from Records.

## Where this stands (2026-09-28) — resume here

- **Brain Battle is built and merged** (PR #9), and so are PRs #8, #10 and #11. PR #11 (`brain-run`) renamed it
  **Brain Run** on screen (decision 51: runners, not fighters; the home brain's glow pulses) and let **Jev play
  without a cap** (decision 50): the track select shows Jev's worst case with "no cap" and does not ask to confirm a
  lineup whose only spending is Jev's. Claude Haiku and GLM Flash keep their cap under `--max-requests`.
- **Branch `card-cached`** (`1dbfa3b`): a results card's Requests read "N live" over "M cached" when some answers
  came from the cache, so a runner that replayed a track shows "0 live / 146 cached" and 0.00 USD.
- **Next:** phase 6 (the tournament and the write-up), awaiting the user's budget go-ahead (`docs/NEXT.md`). The
  write-up page above is its last step.

## Where this stood (2026-09-25)

- **Done:** the request and every answer are recorded above; all five screens are mocked and approved (home,
  character select, track select, results with More numbers, records); decision 44, the rename to plain, guided,
  step1, step2 and map, is built and verified on this branch (`610291e`, `373affa`; 540 fast tests; the cache
  replays under old and new names spend nothing).
- **The spec is approved** (decision 45): `docs/superpowers/specs/2026-09-25-brain-battle-design.md`, all seven of
  its open calls accepted by the user.
- **Plan a, the server and the numbers, is built and reviewed** (`docs/superpowers/plans/2026-09-25-brain-battle-a.md`,
  prototype `proto/bb-a`; commits `fd13ff1..f158a70`, 576 fast tests): the roster, runners in their skins on the Run
  screen (in `bakeoff view` too), `results.py`, `records.py`, the wrong-move columns, and the `/results`, `/records`
  and `/replay` routes. Seven Haiku tasks byte-identical to the prototype; an Opus design review ("ready with fixes":
  Jev · Map's blue visor never lit, the question sets' `about` lines lacked "ours", a broken run could blank Records,
  fly2 is in-sample on 1000–1199); one fix wave, re-reviewed clean. A live smoke with free players passed.
- **Decision 46** (the user, on that review): Records ranks on tracks 1000–1019 only; fly2's rows are marked "tuned
  on these tracks"; the reworded `about` lines stand; one fly smoke covers plans a and b.
- **Plan b, the screens, is built** (`docs/superpowers/plans/2026-09-25-brain-battle-b.md`, prototype `proto/bb-b`;
  commits `912ef4d..c7fa9d8`, 580 fast tests). Nine Haiku tasks, every file byte-identical to the prototype; task 8
  left the old lobby block in `index.html` with every test green, and the byte-compare caught it (the prototype's
  file restored). Looked at in a headless browser against `bakeoff live` on a copy of `runs/`: home, the select,
  the track select, a free Bot run to results that open by themselves, More numbers, Records with the pair chips
  and "What is ours", phone width; no console errors. Not looked at in the browser: the paid confirmation (it needs
  a cap above 0; `trackpick.test.js` pins it, and it was seen on the prototype).
- **The fly smoke for plans a and b passed** (2026-09-25): driven through the page in a headless browser against
  `bakeoff live` on a copy of `runs/`, Fly · Looming and Bot · Solver on v2 track 1001. One brain (peak 797 MB); the
  results opened by themselves (Solver 150 rows, Fly 29, jumped into a gap on row 29); the fly's 28 decisions are
  identical to its recorded run of the same track (`runs/20260925-101614`); no console errors. A worktree has no
  `data/` (git-ignored): link the main checkout's `data/Drosophila_brain_model` and `data/neuron_annotations.tsv`
  into a `data/` folder there before a fly can play. Without them the track select shows the refusal and its reason.
- **PR #9 is open** (2026-09-26, `brain-battle` into `main`). Next: the user's review and merge. PR #8 (`fly2-settle`)
  also edits `docs/NEXT.md`: whichever merges second resolves it by hand.
- **Plan b's design review is done** (Opus, "ready with fixes": 1 Critical, 4 Important, 8 Minor). Fixed in `70f9de4`
  and `a57ae43`, re-reviewed by Opus, checked in a headless browser:
  - a held Enter could walk through RUN's confirmation; it now never confirms;
  - the tabs' and the picker's styles, deleted with the lobby, are back (in `bakeoff view` too);
  - the select's "about" line wraps, so its "…are ours." is never cut off (a change to the approved mock-up);
  - a finish on a result of several tracks is no longer drawn in `--bad`;
  - the run bar and the results that open by themselves follow the run on screen, and watching a past run is
    refused while this session's run is going.
  Left for the user: the moved "what is ours" text says "This run is game v2" where Records has no one run; head to
  head carries no "tuned on these tracks" note for fly2; a `why_not` line on the track select is muted, not
  `--warn` (a colour rule). Subagents run on Opus 5.5 only (the user, 2026-09-25).
- **Open, for the user:**
  - Settled 2026-09-25: the mind panels' tags stay "JEV STEP 1", "HAIKU PLAIN" until Brain Battle, which labels each
    fighter as on the character select, character and skin ("Jev · Step 1") in the skin's colour. The spec says so.
  - Settled 2026-09-25: `docs/COSTS.md`'s tables and `docs/UPDATES.md` item 2 keep the new names (with the note
    that the runs were recorded under the old ones).
  - The four uncommitted edits under `docs/research/2026-09-24-fly/` (`flywire/brain` became `flywire/motg-flywire`)
    are the user's own; this work leaves them for the user to commit.
  - Merging: the other session (fly2's tracks, `fly2-settle`) edits `docs/NEXT.md` too, so whichever branch merges
    second merges that file by hand; that session should hear about decision 44.
