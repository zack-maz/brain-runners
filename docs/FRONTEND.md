# Frontend request of 2026-09-25: Brain Battle

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
- The roster (`bakeoff/replay.py` `CONTESTANTS`, `bakeoff/players/__init__.py`): flies `fly`, `fly2`; Jev `jev`,
  `jev_composed`, `jev_choice`, `jev_two_step`, `jev_reader`; Claude Haiku `haiku` and the same four sets; GLM Flash
  `glm` and the same four sets; the free yardsticks `solver`, `random`, `always_jump`.
- The sprites (`viewer/sprites.js`) are our own character grids: the fly, the chat critter, Jev's visor, a grey block.
- The page is the user's brand (dark, one blue for the cursor, `--bad` for deaths), plain JavaScript, no build step,
  nothing loaded from the network.
- Another session is tracking fly2's tracks on `fly2-settle` in the main checkout at the same time: this work must
  not touch that checkout, and must not start a fly process (about 1 GB, one at a time on this Mac) while that
  session may be running one.

## Questions to settle

- The roster: the request says four variants of Jev, Haiku and GLM Flash, and there are five of each (the one-shot
  and four question sets). Which four, or five skins? Are the yardsticks on the select screen?
- One character several times: can two slots pick the same character in different skins (as in Smash), and the
  same skin twice (the same player cannot run twice on one track today)?
- "The same as Smash": a cursor (hand) and tokens dropped on portraits, with player slots below; mouse only or also
  keyboard or gamepad?
- The brand: the page is the user's brand (one blue, dark, restrained). Does Brain Battle keep it, or take a bright
  fighting-game look of its own for these three screens?
- The track (seed): where is it picked now, on the stage select or after it?
- Replays (`bakeoff view`): do they get the same front, or only `bakeoff live`?
- Money: the lobby shows the worst-case cost before a paid run starts; where does that confirmation live now?
