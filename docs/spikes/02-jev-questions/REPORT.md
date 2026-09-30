# Spike 02: why does Jev die so early?

2026-09-20. Throwaway code (`ask.py`, `analyze.py`); port ideas, do not merge. Practice seed 1000 only.
Spent: 200 live Jev requests (the cap the user approved), 377,728 tokens, about 0.014 USD at the
estimated rate of `docs/COSTS.md`; 0 errors; median latency 142 ms; model `jev-1.13.0`. The answers are
in `results/answers.jsonl` and in the response cache, so `ask.py` replays for free.

## Question

On practice track 1000 Jev fell after 23 rows, the LLM after 199, same rules, same senses. Jev's log
showed near-perfect yes/no answers (Brier 0.001 and 0.002) and a Choice that went flat next to a gap. Is
the early death perception, or choosing the action?

## Method

The 200 states the LLM passed through on seed 1000 (run `20260920-102919`); 55 of them have at least
one action that lands on a gap. One request per state, nine questions in parallel (TypeSafe: questions
of one request cannot see one another's answers):

- `action`: the tournament's Choice, word for word;
- four **pointed** Nouls, one per action: "Would the action `left` land the runner on a gap, that is,
  does `ahead[0].gaps_relative` contain -1?";
- four **unpointed** Nouls: the rules, then "Would the action `left` land the runner on a gap?".

Scored offline against the senses (one step only: does the move land on a gap?). On the 20 states the
original Jev run had also seen, the Choice was the same every time (confidence within 0.12).

## Results

| policy on the 55 dangerous states | lands on a gap |
| --- | --- |
| the tournament Choice, argmax | 16 (29%) |
| always `stay` | 18 (33%) |
| Choice with a confidence gate (0.2, 0.3 or 0.5; below it `stay`) | 18 (33%) |
| safest action by the unpointed Nouls | 2 (4%) |
| safest action by the pointed Nouls | 0 (0%) |
| the LLM (these are its own states) | 1 (2%) |

- **The Choice carries no information about which actions are fatal.** In dangerous states it puts 0.30
  of its probability on the fatal actions; uniform guessing would put 0.31. It picks `stay` in 38 of 55
  and is about as safe as always staying. Its confidence does know something is up (0.27 in dangerous
  states, 0.60 elsewhere), but not what.
- **Perception is not the problem.** Pointed Nouls: 1 of 800 on the wrong side of 0.5, no false alarm,
  one real gap missed (a `jump` landing).
- **The step Jev cannot do alone is action -> tile.** Unpointed: `stay` 0 of 18 gaps missed, `left` 1 of
  18 (10 false alarms), `right` 4 of 17 (7 false alarms), `jump` **16 of 16 missed**: from the rules alone
  it never works out that a jump lands two rows ahead. The Choice needs four such mappings and a
  comparison in one answer.
- **A confidence gate does not help**: low confidence falls back to `stay`, and `stay` is itself the
  fatal move in 18 of the 55 dangerous states.
- Not replicated: on the original 24 frames a gap on the left seemed to pull probability towards `left`.
  Here, with only `left` fatal (12 states), Jev stepped into it once and away from it twice. The Choice is
  uninformed, not attracted.

## Reading

This matches TypeSafe's own guidance (docs.typesafe.ai, "How to build with TypeSafe"): "Ask the most
explicit, narrow, specific, atomic questions you can ... Broad questions hide several judgments behind one
answer", and "Use code when you can". Jev as a one-shot policy is off-label use; Jev as four narrow
judgments composed by code is the documented use, and on these states it is perfect.

## Caveats

One track; the states come from the LLM's trajectory, not from Jev's own; one step ahead only, so this
says nothing about planning or about rows survived; the pointed questions name the value to look up, so
what they measure is reading, and the "safest action" rule is ours, not Jev's.

## Options for the tournament (the user's decision; `docs/DECISIONS.md` decision 12 froze the prompts)

1. Keep the one-shot Choice and report it as what it is: off-label use, about as good as always staying.
2. Add a second Jev player built the documented way: four per-action Nouls in one request, code picks the
   safest action (ties in the solver's order). The rule and the pointed wording are ours and must be
   labelled as ours, like the fly's thresholds; settle them on practice seeds before the tournament. Cost
   per request not measured: the pointed Nouls carry no rules text, so it should not exceed today's 880
   tokens, but a player that survives longer makes more requests (at most 300 per track).
3. Both players side by side (`jev` and `jev_composed`), which shows the finding itself: the same model,
   used two ways.
