"""What a request costs, per player: one table for the money the page asks the user to agree to
(bakeoff/session.py) and the cost the study charts (bakeoff/bench.py). Nothing here imports anything, so the
benchmark can read it without loading the live session."""

from __future__ import annotations

# USD per live request, measured in docs/COSTS.md (update 2a) and rounded up, because this number is what
# the page asks the user to agree to: it must never be lower than what a request really costs. A price per
# player, not per provider: the same model costs what its question set makes it read and write, and the
# map set is about eleven times the plain one's. The budget, not this table, enforces the ceiling.
# Jev's prices are estimates (its provider does not bill per request; COSTS.md explains the token basis).
# GLM Flash is free while its free tier lasts.
PRICE_USD = {"haiku_plain": 0.0006, "haiku_step1": 0.0010, "haiku_guided": 0.0009, "haiku_step2": 0.0016,
             "haiku_map": 0.0065, "jev_plain": 0.00004, "jev_step1": 0.00003, "jev_guided": 0.00004,
             "jev_step2": 0.00003, "jev_map": 0.00012,
             "glm_plain": 0.0, "glm_step1": 0.0, "glm_guided": 0.0, "glm_step2": 0.0, "glm_map": 0.0}

# Jev's provider bills the user nothing (decision 50): its price is an estimate, charted as one
ESTIMATED = frozenset(name for name in PRICE_USD if name.startswith("jev_"))
