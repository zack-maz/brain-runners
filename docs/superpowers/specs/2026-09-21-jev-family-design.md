# Update 2a: the Jev family and its LLM twins: design

Date: 2026-09-21 · Status: choices made by the user in chat (decisions 25 and 26 of `docs/DECISIONS.md`); the user
said "don't need my approval here, just go" for design sections · Item 2 of `docs/UPDATES.md` · Builds on game v2
(`docs/superpowers/specs/2026-09-21-game-v2-design.md`) · The fly (item 1) is update 2b, its own spec.

## Goal

Find the best cost/performance way to ask Jev, and make the LLM comparison fair: every question set is played twice,
once by Jev and once by Claude Haiku, with the same questions and the same rule, so the model is the only
difference.

## What the numbers say (free, perfect answers, v2 practice seeds 1000–1199)

| rule | mean rows | finished |
| --- | --- | --- |
| composed Jev today: the move least likely to land on a gap (one step) | 112.1 | 26% |
| two-step: also avoid landings from which every next move lands on a gap | 140.1 | 74% |
| reader: read every visible tile, then plan like the solver | 149.0 | 97% |

These are ceilings of the rules, not of Jev: a wrong answer can only lower them.

## The question sets (`bakeoff/players/question_sets.py`, new)

A question set is: the questions (built from the game's rules, since the reader's depend on the vision), and the
rule that turns the answers into a move. All wording and every rule are **ours**, not TypeSafe's or Anthropic's,
and are labelled so on the page and in the write-up.

| set | questions per row | rule |
| --- | --- | --- |
| `composed` | the composed Jev's four Nouls `gap_<action>`, byte for byte (so its cache keeps replaying) | lowest P(gap) after rounding to 2 decimals, ties stay, left, right, jump |
| `choice` | one Choice `action` over the four moves; its instructions state where each move lands (spike 02: the one-shot Choice failed because it could not map a move to its landing tile) | the chosen move |
| `two_step` | the four `gap_<action>` Nouls plus four `trapped_<action>` Nouls: "after this move, would every next move land on a gap?" | lowest risk = P(gap) + (1 − P(gap)) · P(trapped), then lowest P(gap), both rounded to 2 decimals, ties in the same order |
| `reader` | one Noul `tile_r<row>_<side><n>` per visible tile (6 rows × 7 lanes = 42 on v2): "does `ahead[row-1].gaps_relative` contain this offset?" | tiles with P(gap) > 0.5 are gaps; the reference solver's search over that picture picks the move |

Noul ids name what they ask, so their truth can be read from any record's senses: `bakeoff.senses.truth_of(senses,
noul_id)` answers `gap_<action>`, `trapped_<action>` and `tile_r<r>_<l|c|r><n>` (and returns None for anything
else). The report scores every Noul with it.

## Players

- `jev_choice`, `jev_two_step`, `jev_reader`: `JevSetPlayer` (one class, the set as a parameter), built on
  `PaidPlayer` (same cache, cap, error and fallback rules). Questions are built at `reset` from the game's rules. The
  `composed` set is played by the existing `jev_composed`, unchanged.
- `llm_composed`, `llm_choice`, `llm_two_step`, `llm_reader`: `LlmSetPlayer`, the same sets asked of Claude Haiku
  4.5 in one Messages request per row. System prompt: the shared briefing (`briefing.RULES`, unchanged) plus one
  line saying how to answer, plus the numbered questions with their ids. Structured output: one property per
  question id, a number for a Noul (the model's stated probability that the answer is yes), one of the four moves
  for the Choice. The answers are logged in Jev's shape (`{"noul": p}`, `{"choice": a}`) plus the raw text and stop
  reason, so the report and the page treat both models alike. A number outside [0, 1], a missing id or a move that
  is not one of the four makes the decision invalid (the runner runs `stay`). The stated probabilities are the
  model's words, not calibrated probabilities; the write-up says so.
- The one-shot `jev` and `llm` stay as they are.
- `PAID` gains all seven: the caps, the cache, `--tournament` and the `--window` guard cover them.

## Report and page

- Report: one new column `brier_all`, the Brier score over every logged Noul whose truth `truth_of` knows. The
  existing Brier columns stay.
- Page: short tags and one-line descriptions for the seven players; one generic mind panel for set players (each
  Noul as a bar, the reader's 42 answers drawn as a probability grid over the senses picture, the Choice as the
  chosen move), with the set's rule named as ours. The demo's default three are unchanged. The page layout work is
  update 4/8.

## Paid runs (controller only, after the code is merged into the branch)

1. One capped track first: v2 practice seed 1000, every paid player (the 7 new ones plus `jev_composed` and `llm`
   as v2 baselines). Measure cost and latency per request per player.
2. Then seeds 1001–1004 with caps sized so that Claude Haiku stays within **5.00 USD in total** for this update
   (decision 26), counting step 1. Jev is capped at 150 requests per seed per player.
3. The fly on the same five seeds (free, one process, about a second a row).
4. Results into `docs/COSTS.md` (time, cost, rows, Brier per player) and `docs/DECISIONS.md`. Five tracks are an
   impression, not a result; the benchmark method is update 7.

## Testing

TDD, fast tests only, no network (the SDKs are replaced by the fakes in `tests/fakes.py`). Question building for
each set (ids, count on v2 and on a vision variant, `composed` identical to `jev_composed.QUESTIONS`), each rule on
hand-made answers (ties, the two-step risk order, the reader's threshold and planning), `truth_of` against the
senses for all three id kinds, both player classes (valid, invalid, provider error, info), the LLM schema and prompt,
the registry and `PAID`, `brier_all`, the page panel (JS tests, escaped text). A free probe asserts each rule's
ceiling with perfect answers on a few seeds.

## Non-goals

No change to `jev`, `jev_composed`, `llm`, `briefing.py`, the fly, the game or the step record's shape. No retuning
of any wording on tournament seeds. No tournament.
