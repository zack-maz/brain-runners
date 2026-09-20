# Phase 3: The Paid Players (Jev and the LLM) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Jev (`jev-latest`) and Claude Haiku 4.5 play Tunnel Run as thin clients behind one disk response cache and a hard request cap, and one capped practice track gives the first measured cost per request for each.

**Architecture:** `bakeoff/clients/core.py` is the only path to a provider: cache lookup, then the cap, then one live call with SDK retries switched off, so one spent request is exactly one HTTP request. `bakeoff/clients/jev.py` and `llm.py` are the two thin SDK wrappers; `bakeoff/players/paid.py` holds what the two players share (provider errors become a logged `error`, the cap is left to end the run) and `players/jev.py` / `players/llm.py` only hold their questions and how to read an answer. Keys are read inside the program by `bakeoff/clients/keys.py`. The runner gains the `preflight()` hook (moved in from the CLI) so a missing key or missing fly data is a usage error before a run directory exists.

**Tech Stack:** Python 3.13, `uv`, `pytest`; new runtime dependencies `typesafe-sdk` (0.7), `anthropic` (1.7, built on `httpx2`), `python-dotenv`.

**Spec:** `docs/superpowers/specs/2026-09-19-tunnel-run-design.md` (binding; sections "Players", "Architecture", "Step record", "Report", "Budget", "Testing"). Background: `docs/DECISIONS.md`.

**Branch:** `phase3-paid-players` (already created; never build on `main`).

## Global Constraints

- Python via `uv` only: `uv add`, `uv run pytest`, `uv run python -m ...`. Python 3.13. Never call `pip` or bare `python`.
- TDD: write the failing test, watch it fail, then implement. **No test touches the network**: the two SDKs are replaced by the fakes in `tests/fakes.py`. The only real requests in this phase are Task 8 and the opt-in `live` tests, and both need the user's go-ahead first.
- **A guard blocks every shell command that contains the text `.env`.** Never put it in a command: no `cat`, `ls`, `grep`, `git add` or commit message that names that file. Code and documents may mention it (write them with the file tools). Keys are read only by `bakeoff/clients/keys.py`; nothing prints, logs or stores a key value, not even in an error message.
- **Budget:** a paid player without `--max-requests` has a cap of 0 and can only replay the cache. SDK retries stay off (`RetryPolicy(max_retries=0)`, `max_retries=0`). Never raise a cap or rerun a paid command to "see if it works"; ask the user.
- **Seed hygiene:** no paid request on a seed below 1000 in this phase. Tournament seeds are below 1000 and must not shape the prompts. Phase 3 plays practice seed 1000 only.
- **Frozen fly:** do not touch the fly constants, `bakeoff/senses.py`, `bakeoff/game/`, `bakeoff/fly/` or `calibration/`. One fly process at a time still holds; nothing in this phase needs the fly. `uv run pytest` runs the fast tests only (about 5 s) and is the loop for every task.
- Model ids, verbatim from the spec: `jev-latest` and `claude-haiku-4-5-20251001`. Haiku 4.5 prices used for `cost_usd`: 1.00 USD per million input tokens, 5.00 USD per million output tokens.
- Every code block below was run in a prototype and passes as written (final state: 205 fast tests, 9 deselected). Both real SDKs were also driven through the new clients against mock HTTP transports: correct endpoints and bodies, one HTTP request per spent request, a 503 becomes a logged error. If a test fails, suspect a transcription slip before redesigning.
- Commit after every task with the message given. The controller pre-writes each message to a file, attribution trailers included; the implementer runs exactly `git commit -F <that file>`, never `-m`, and checks `git log -1 --format=%B` afterwards.

## Decisions this plan makes beyond the spec

1. **The cap is per paid player, not per run.** `--max-requests N` gives Jev and the LLM a `RequestBudget(N)` each: the providers bill separately and one must not starve the other. Worst case a run spends `N` requests per paid player; the CLI help says so. The default is 0 (replay only), so spending always takes an explicit flag.
2. **A request is spent before the call, and a failed request stays spent** (it may have been billed). Failed requests are not cached. `meta.json` records `requests: {player: {max, used}}`; the report's `requests` column counts successful live calls only.
3. **No SDK retries.** With retries on, one counted request could be three HTTP requests and the cap would not be hard. A provider failure becomes that step's `error`, the runner executes `stay`, and the existing circuit breaker (more than 5 consecutive errors) ends the run as `aborted`.
4. **What is caught and what is not.** Only provider failures (`typesafe_sdk.TypeSafeError`, `anthropic.APIError`) become `ProviderError` and then a logged `error`. `BudgetExhausted` ends the run as `budget_exhausted`. Any other exception is our bug and ends the run as `interrupted`.
5. **The fly keeps phase 2's decision 9** (a simulator failure is not a fallback: it would quietly change the fly's score). The second PR #2 review suggested the opposite; this plan declines it and Task 7 corrects the note under Open in `docs/DECISIONS.md`.
6. **`preflight()` moves from the CLI into `Runner.run`,** runs after the duplicate-name check and before `mkdir`, and turns `OSError` or `ValueError` from a player into `PreflightError` (a `ValueError`, which the CLI already reports as usage, exit 2). A paid player's preflight asks for its key only when it could go live (cap above 0 and no injected SDK), so a full replay from the cache needs no key.
7. **Both paid players are told the same rules in the same words** (`bakeoff/players/briefing.py`, `RULES`): Jev in the Choice's instructions, the LLM in its system prompt. The text is ours, written once before any paid request, and is part of the cache key, so an edited prompt can never be answered from a response to the old one. Jev's Choice criteria are the four action descriptions already in the senses.
8. **Cache key** = sha256 of `{provider, model, senses, questions}` as canonical JSON (the spec's list). For the LLM, `questions` is `{system, schema, max_tokens}`. Senses include `lane` and `rows_survived`, so hits come from re-runs and replays, not from similar-looking rows. Cache files keep the request beside the response; the cache directory `.cache/responses` is already git-ignored.
9. **The LLM answers through structured output** (`output_config.format`, a JSON schema whose `action` is an enum of the four actions), `max_tokens` 256, no thinking. Invalid means: not JSON, no string `action`, an unknown action, or a `stop_reason` other than `end_turn`.
10. **Jev is never gated.** The spec defines no confidence threshold, so `gated` stays false; the Choice's probabilities and both Nouls are logged in `answers`. The two Nouls are named `gap_ahead` and `left_safe`, the keys of the record's `ground_truth`, so the report can score them (Brier).
11. **Report additions:** `cache_hits`, `cost_usd` (live tokens times the price of the model recorded in `meta.json`; `-` when the price is unknown, never 0), `brier_gap_ahead`, `brier_left_safe`. Amounts under 0.1 print with four decimals.
12. `schema_version` stays 1: `meta.json` only gains keys (`models`, `requests`, two `args`, one `versions` entry).
13. **Run-ending exceptions move to `bakeoff/errors.py`** (re-exported by `bakeoff/runner.py`), because a client that imported them from the runner would import every player and, through the registry, itself.

## File Structure

| File | Responsibility | Task |
| --- | --- | --- |
| `bakeoff/errors.py` | `RunAborted`, `BudgetExhausted`, `PreflightError` | 1 |
| `bakeoff/runner.py`, `bakeoff/__main__.py`, `bakeoff/players/base.py`, `bakeoff/players/fly.py` | `preflight()` run by `Runner.run`; the CLI loop removed | 1 |
| `pyproject.toml`, `uv.lock` | New dependencies | 2 |
| `bakeoff/clients/__init__.py` | Empty package marker | 2 |
| `bakeoff/clients/keys.py` | `require_key(name)`: environment, else the git-ignored key file; never prints a value | 2 |
| `bakeoff/clients/core.py` | `cache_key`, `DiskCache`, `RequestBudget`, `Reply`, `cached_request`, `ProviderError`, `PaidClient` | 2 |
| `bakeoff/clients/jev.py` | `JevClient`: one `system_one` request | 3 |
| `bakeoff/players/briefing.py` | `RULES`, the shared briefing text | 3 |
| `bakeoff/players/paid.py` | `PaidPlayer`: the shared act / error / cache-hit logic | 3 |
| `bakeoff/players/jev.py` | `QUESTIONS` and `JevPlayer.read` | 3 |
| `tests/fakes.py` | `FakeTypeSafe`, `jev_reply` (Task 3); `FakeAnthropic`, `llm_reply` (Task 4) | 3, 4 |
| `bakeoff/clients/llm.py` | `LlmClient`: one Messages request with structured output | 4 |
| `bakeoff/players/llm.py` | `QUESTIONS` and `LlmPlayer.read` | 4 |
| `bakeoff/players/__init__.py`, `bakeoff/__main__.py`, `bakeoff/runner.py` | Registry and `PAID`; `--max-requests`, `--cache`; `meta.json` `models` and `requests` | 5 |
| `bakeoff/report.py` | `cache_hits`, `cost_usd`, two Brier columns | 6 |
| `tests/test_live.py`, `README.md`, `CLAUDE.md`, `docs/STEP_RECORD.md`, `docs/DECISIONS.md` | Opt-in live tests; documentation | 7 |
| `docs/COSTS.md` | First measured cost per request, from one capped track each | 8 |

---

### Task 1: Run-ending errors in their own module, `preflight()` inside `Runner.run`

**Files:**
- Create: `bakeoff/errors.py`
- Modify: `bakeoff/runner.py`, `bakeoff/__main__.py`, `bakeoff/players/base.py`, `bakeoff/players/fly.py`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: the optional `preflight()` method players may define (today only `FlyPlayer`, which raises `FileNotFoundError`).
- Produces: `bakeoff.errors.RunAborted` (`status = "aborted"`), `bakeoff.errors.BudgetExhausted(RunAborted)` (`status = "budget_exhausted"`), `bakeoff.errors.PreflightError(ValueError)`. `bakeoff.runner` still exports `RunAborted` and `BudgetExhausted`. `Runner.run` calls every player's `preflight()` before creating the run directory and raises `PreflightError(f"{player.name}: {error}")` for an `OSError` or `ValueError`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_runner.py`, add the `PreflightError` import:

```diff
@@ -5,6 +5,7 @@ import pytest
 
 from bakeoff.players import make_player
 from bakeoff.players.base import Decision
+from bakeoff.errors import PreflightError
 from bakeoff.runner import BudgetExhausted, RunAborted, Runner
 
 KEYS = {"run_id", "player", "seed", "row", "lane", "senses", "looming", "questions", "answers",
```

and append at the end of the file:

```python
class Unready(Scripted):
    def __init__(self, error, name="unready"):
        super().__init__(Decision("stay"), name=name)
        self.error = error

    def preflight(self): raise self.error


@pytest.mark.parametrize("error", [FileNotFoundError("fly data unusable"), PermissionError("cannot read"),
                                   ValueError("TYPESAFE_API_KEY is not set")])
def test_a_failing_preflight_raises_before_the_run_directory_is_created(tmp_path, error):
    with pytest.raises(PreflightError, match=f"unready: {error}"):
        Runner(tmp_path).run([make_player("solver"), Unready(error)], range(1), max_rows=20, run_id="p")
    assert list(tmp_path.iterdir()) == []


def test_preflight_error_is_a_value_error_so_the_cli_reports_it_as_usage():
    assert issubclass(PreflightError, ValueError)


def test_a_passing_preflight_lets_the_run_happen(tmp_path):
    class Ready(Scripted):
        checked = False

        def preflight(self): self.checked = True

    ready = Ready(Decision("stay"), name="ready")
    Runner(tmp_path).run([ready], range(1), max_rows=20, run_id="p2")
    assert ready.checked and (tmp_path / "p2" / "ready.jsonl").exists()


def test_a_bug_in_preflight_is_not_dressed_up_as_a_usage_error(tmp_path):
    with pytest.raises(RuntimeError, match="bug"):
        Runner(tmp_path).run([Unready(RuntimeError("bug"))], range(1), run_id="p3")
    assert list(tmp_path.iterdir()) == []


def test_run_ending_exceptions_live_in_errors_and_are_re_exported_by_the_runner():
    from bakeoff import errors, runner

    assert runner.RunAborted is errors.RunAborted and runner.BudgetExhausted is errors.BudgetExhausted
    assert errors.BudgetExhausted.status == "budget_exhausted" and errors.RunAborted.status == "aborted"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_runner.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.errors'`

- [ ] **Step 3: Implement**

Create `bakeoff/errors.py`:

```python
"""Exceptions that end a run. A module of their own, so a paid client can raise them without importing the runner."""

from __future__ import annotations


class RunAborted(Exception):
    status = "aborted"  # a subclass may set a more specific status


class BudgetExhausted(RunAborted):
    """Raised by a paid client when its hard request cap is reached."""

    status = "budget_exhausted"


class PreflightError(ValueError):
    """A player cannot start (fly data missing, key missing). Raised before the run directory exists."""
```

Make exactly these edits to `bakeoff/runner.py` (the two exception classes leave the file; `_preflight` is new; `run` calls it after the duplicate-name check):

```diff
--- a/bakeoff/runner.py
+++ b/bakeoff/runner.py
@@ -11,6 +11,7 @@ from importlib import metadata
 from pathlib import Path
 from typing import Callable, Sequence
 
+from bakeoff.errors import BudgetExhausted, PreflightError, RunAborted  # noqa: F401  (re-exported)
 from bakeoff.fly import data as fly_data
 from bakeoff.fly.reading import WINDOW_MS
 from bakeoff.game.engine import ACTIONS, Game
@@ -25,16 +26,6 @@ SCHEMA_VERSION = 1
 FALLBACK_ACTION = "stay"  # never the solver's move: a rescue would hide what we want to see
 
 
-class RunAborted(Exception):
-    status = "aborted"  # a subclass may set a more specific status
-
-
-class BudgetExhausted(RunAborted):
-    """Raised by a paid client when the hard request cap is reached (phase 3)."""
-
-    status = "budget_exhausted"
-
-
 def _version(package: str) -> str | None:
     try:
         return metadata.version(package)
@@ -76,6 +67,19 @@ def _close(player: Player) -> None:
         pass
 
 
+def _preflight(players: list[Player]) -> None:
+    """Players may define preflight(): a check that they can start at all. It runs before the run
+    directory exists, so a usage error (no fly data, no key) leaves nothing behind."""
+    for player in players:
+        check = getattr(player, "preflight", None)
+        if check is None:
+            continue
+        try:
+            check()
+        except (OSError, ValueError) as e:
+            raise PreflightError(f"{player.name}: {e}") from e
+
+
 class Runner:
     def __init__(self, out_root: Path | str = "runs", max_consecutive_errors: int = 5):
         self.out_root = Path(out_root)
@@ -128,6 +132,7 @@ class Runner:
         duplicates = sorted({n for n in names if names.count(n) > 1})
         if duplicates:  # two players would write the same <name>.jsonl
             raise ValueError(f"duplicate player names: {duplicates}")
+        _preflight(players)
         run_id = run_id or time.strftime("%Y%m%d-%H%M%S")
         run_dir = self.out_root / run_id
         run_dir.mkdir(parents=True, exist_ok=False)
```

Remove the preflight loop from `bakeoff/__main__.py`; its existing `except ValueError` branch already prints a `PreflightError` and returns 2:

```diff
--- a/bakeoff/__main__.py
+++ b/bakeoff/__main__.py
@@ -47,14 +47,6 @@ def main(argv: list[str] | None = None) -> int:
     except KeyError as e:
         print(e.args[0], file=sys.stderr)
         return 2
-    for player in players:
-        preflight = getattr(player, "preflight", None)
-        if preflight is not None:
-            try:
-                preflight()
-            except FileNotFoundError as e:
-                print(e, file=sys.stderr)
-                return 2
     runner = Runner(args.out)
     run_id = time.strftime("%Y%m%d-%H%M%S")
     run_dir = runner.out_root / run_id
```

Update the two comments that said the CLI does this:

```diff
--- a/bakeoff/players/base.py
+++ b/bakeoff/players/base.py
@@ -33,5 +33,6 @@ class Player(Protocol):
     def reset(self, game: Game, seed: int) -> None: ...
     def act(self, senses: dict) -> Decision: ...
     def observe(self, executed_action: str) -> None: ...
-    # Players may also define close() (release resources) and preflight() (a usage-error check
-    # run before the CLI creates the run directory); both optional, checked with getattr.
+    # Players may also define close() (release resources) and preflight() (a check that the player
+    # can start at all, run by Runner.run before it creates the run directory; raise OSError or
+    # ValueError); both optional, checked with getattr.
```

```diff
--- a/bakeoff/players/fly.py
+++ b/bakeoff/players/fly.py
@@ -63,7 +63,7 @@ class FlyPlayer:
         self.gain_hz, self.falloff = gain_hz, falloff
 
     def preflight(self) -> None:
-        """Called by the CLI before the run directory exists: a fly without its data is a usage error."""
+        """Called by Runner.run before the run directory exists: a fly without its data is a usage error."""
         if self._brain_factory is _real_brain:
             from bakeoff.fly import data  # light: no brian2 import until a fly actually plays
 
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: `155 passed, 7 deselected`. `tests/test_cli.py::test_missing_fly_data_is_a_usage_error_before_the_run_directory_exists` still passes unchanged: the message now starts with `fly: `.

- [ ] **Step 5: Commit**

```bash
git add bakeoff/errors.py bakeoff/runner.py bakeoff/__main__.py bakeoff/players/base.py bakeoff/players/fly.py tests/test_runner.py
git commit -F <message file>   # feat: preflight runs inside Runner.run; run-ending errors get their own module
```

---

### Task 2: Dependencies, key loading, cache and request cap

**Files:**
- Modify: `pyproject.toml`, `uv.lock` (through `uv add`)
- Create: `bakeoff/clients/__init__.py` (empty), `bakeoff/clients/keys.py`, `bakeoff/clients/core.py`
- Test: `tests/test_clients_keys.py`, `tests/test_clients_core.py`

**Interfaces:**
- Consumes: `bakeoff.errors.BudgetExhausted` (Task 1).
- Produces:
  - `bakeoff.clients.keys.require_key(name: str, env_file: Path | str | None = None) -> str`; raises `ValueError(f"{name} is not set: ...")`.
  - `bakeoff.clients.core`: `DEFAULT_CACHE_DIR` (`Path(".cache") / "responses"`), `ProviderError(Exception)`, `cache_key(provider, model, senses, questions) -> str`, `DiskCache(root)` with `get(provider, key) -> dict | None` and `put(provider, key, request, payload)`, `RequestBudget(max_requests)` with `max_requests`, `used`, `spend()`, `Reply(payload: dict, latency_ms: float | None, cache_hit: bool)`, `cached_request(cache, budget, provider, model, senses, questions, live) -> Reply`.
  - `PaidClient(cache, budget, model=None, sdk=None)`: class attributes `provider`, `key_name`, `default_model`; attributes `cache`, `budget`, `model`, `_sdk`, `_owns_sdk`; methods `preflight()`, `ask(senses, questions) -> Reply`, `close()`; a subclass implements `_live(senses, questions) -> dict`.

- [ ] **Step 1: Add the dependencies**

Run: `uv add typesafe-sdk anthropic python-dotenv`
Expected: `pyproject.toml` gains `anthropic>=1.7.0`, `python-dotenv>=1.2.3`, `typesafe-sdk>=0.7.0` (or newer); `uv run pytest -q` still prints `155 passed`.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_clients_keys.py` (the key file in these tests is a temporary file with another name; the real one is never touched):

```python
import pytest

from bakeoff.clients.keys import require_key

NAME = "BAKEOFF_TEST_KEY"


def test_the_environment_wins_over_the_file(tmp_path, monkeypatch):
    env_file = tmp_path / "keys"
    env_file.write_text(f"{NAME}=from-file\n")
    monkeypatch.setenv(NAME, "from-environment")
    assert require_key(NAME, env_file) == "from-environment"


def test_the_file_is_read_inside_the_program_without_touching_the_environment(tmp_path, monkeypatch):
    import os

    env_file = tmp_path / "keys"
    env_file.write_text(f"OTHER=x\n{NAME}= from-file \n")
    monkeypatch.delenv(NAME, raising=False)
    assert require_key(NAME, env_file) == "from-file"
    assert NAME not in os.environ


@pytest.mark.parametrize("content", ["", f"{NAME}=\n", f"{NAME}=   \n"])
def test_a_missing_or_empty_key_is_a_value_error_that_names_the_key_only(tmp_path, monkeypatch, content):
    env_file = tmp_path / "keys"
    env_file.write_text(content)
    monkeypatch.delenv(NAME, raising=False)
    with pytest.raises(ValueError, match=f"{NAME} is not set"):
        require_key(NAME, env_file)


def test_a_missing_file_is_the_same_error(tmp_path, monkeypatch):
    monkeypatch.delenv(NAME, raising=False)
    with pytest.raises(ValueError, match="is not set"):
        require_key(NAME, tmp_path / "absent")
```

Create `tests/test_clients_core.py`:

```python
import json

import pytest

from bakeoff.clients.core import (DiskCache, PaidClient, ProviderError, Reply, RequestBudget, cache_key,
                                  cached_request)
from bakeoff.errors import BudgetExhausted

SENSES = {"lane": 4, "lanes": 12, "rows_survived": 0, "ahead": [{"row": 1, "gaps_relative": [0]}]}
QUESTIONS = {"action": {"type": "choice"}}


def test_cache_key_covers_provider_model_senses_and_questions_and_ignores_dict_order():
    base = cache_key("jev", "jev-latest", SENSES, QUESTIONS)
    assert len(base) == 64
    assert cache_key("jev", "jev-latest", dict(reversed(SENSES.items())), QUESTIONS) == base
    assert cache_key("llm", "jev-latest", SENSES, QUESTIONS) != base
    assert cache_key("jev", "jev-2", SENSES, QUESTIONS) != base
    assert cache_key("jev", "jev-latest", {**SENSES, "lane": 5}, QUESTIONS) != base
    assert cache_key("jev", "jev-latest", SENSES, {"action": {"type": "noul"}}) != base


def test_disk_cache_round_trip_keeps_the_request_beside_the_response(tmp_path):
    cache = DiskCache(tmp_path)
    assert cache.get("jev", "ab" * 32) is None
    cache.put("jev", "ab" * 32, {"model": "jev-latest"}, {"answers": {}})
    assert cache.get("jev", "ab" * 32) == {"answers": {}}
    path = tmp_path / "jev" / "ab" / f"{'ab' * 32}.json"
    assert json.loads(path.read_text()) == {"request": {"model": "jev-latest"}, "payload": {"answers": {}}}
    assert [p.name for p in path.parent.iterdir()] == [path.name]  # no partial file left


def test_a_damaged_cache_file_is_a_miss(tmp_path):
    cache = DiskCache(tmp_path)
    cache.put("jev", "cd" * 32, {}, {"ok": True})
    (tmp_path / "jev" / "cd" / f"{'cd' * 32}.json").write_text('{"payl')
    assert cache.get("jev", "cd" * 32) is None


def test_budget_raises_at_the_cap_and_counts_what_was_spent():
    budget = RequestBudget(2)
    budget.spend()
    budget.spend()
    with pytest.raises(BudgetExhausted, match="request cap of 2 reached"):
        budget.spend()
    assert budget.used == 2 and budget.max_requests == 2


def test_a_budget_of_zero_allows_no_live_request_and_a_negative_one_is_refused():
    with pytest.raises(BudgetExhausted):
        RequestBudget(0).spend()
    with pytest.raises(ValueError):
        RequestBudget(-1)


def test_a_miss_spends_calls_live_and_stores_and_a_hit_does_none_of_that(tmp_path):
    cache, budget, calls = DiskCache(tmp_path), RequestBudget(5), []

    def live():
        calls.append(1)
        return {"answer": "stay"}

    first = cached_request(cache, budget, "jev", "jev-latest", SENSES, QUESTIONS, live)
    assert first.payload == {"answer": "stay"} and not first.cache_hit and first.latency_ms >= 0
    second = cached_request(cache, budget, "jev", "jev-latest", SENSES, QUESTIONS, live)
    assert second == Reply({"answer": "stay"}, latency_ms=None, cache_hit=True)
    assert len(calls) == 1 and budget.used == 1


def test_the_cap_stops_a_miss_before_the_live_call_but_never_a_hit(tmp_path):
    cache, calls = DiskCache(tmp_path), []
    cached_request(cache, RequestBudget(1), "jev", "m", SENSES, QUESTIONS, lambda: {"a": 1})
    broke = RequestBudget(0)
    assert cached_request(cache, broke, "jev", "m", SENSES, QUESTIONS, lambda: calls.append(1)).cache_hit
    with pytest.raises(BudgetExhausted):
        cached_request(cache, broke, "jev", "m", {**SENSES, "lane": 5}, QUESTIONS, lambda: calls.append(1))
    assert calls == []


def test_a_failed_request_is_spent_but_not_cached(tmp_path):
    cache, budget = DiskCache(tmp_path), RequestBudget(3)

    def failing():
        raise ProviderError("503")

    with pytest.raises(ProviderError):
        cached_request(cache, budget, "jev", "m", SENSES, QUESTIONS, failing)
    assert budget.used == 1
    assert not cached_request(cache, budget, "jev", "m", SENSES, QUESTIONS, lambda: {"a": 1}).cache_hit
    assert budget.used == 2


class Echo(PaidClient):
    provider, key_name, default_model = "echo", "ECHO_KEY", "echo-1"

    def _live(self, senses, questions):
        return {"lane": senses["lane"]}


def test_a_paid_client_asks_through_the_cache_and_the_cap(tmp_path):
    client = Echo(DiskCache(tmp_path), RequestBudget(1), sdk=object())
    assert client.model == "echo-1" and Echo(DiskCache(tmp_path), RequestBudget(1), model="echo-2").model == "echo-2"
    assert client.ask(SENSES, QUESTIONS).payload == {"lane": 4}
    assert client.ask(SENSES, QUESTIONS).cache_hit
    with pytest.raises(BudgetExhausted):
        client.ask({**SENSES, "lane": 5}, QUESTIONS)


def test_paid_client_preflight_wants_the_key_only_when_it_may_go_live_with_its_own_sdk(tmp_path, monkeypatch):
    monkeypatch.delenv("ECHO_KEY", raising=False)
    Echo(DiskCache(tmp_path), RequestBudget(0)).preflight()
    Echo(DiskCache(tmp_path), RequestBudget(3), sdk=object()).preflight()
    with pytest.raises(ValueError, match="ECHO_KEY is not set"):
        Echo(DiskCache(tmp_path), RequestBudget(3)).preflight()
    monkeypatch.setenv("ECHO_KEY", "k")
    Echo(DiskCache(tmp_path), RequestBudget(3)).preflight()
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_clients_keys.py tests/test_clients_core.py`
Expected: two collection errors, `ModuleNotFoundError: No module named 'bakeoff.clients'`

- [ ] **Step 4: Implement**

Create an empty `bakeoff/clients/__init__.py`.

Create `bakeoff/clients/keys.py`:

```python
"""API keys: from the environment, else from the git-ignored .env file at the repo root, read inside
the program. A key is returned to the caller and never printed, logged or put in an error message."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def require_key(name: str, env_file: Path | str | None = None) -> str:
    value = os.environ.get(name) or dotenv_values(env_file or ENV_FILE).get(name) or ""
    if not value.strip():
        raise ValueError(f"{name} is not set: add it to the .env file at the repo root (see .env.example)")
    return value.strip()
```

Create `bakeoff/clients/core.py`:

```python
"""What every paid request goes through: the disk cache first, then the hard cap, then the live call."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from bakeoff.clients.keys import require_key
from bakeoff.errors import BudgetExhausted

DEFAULT_CACHE_DIR = Path(".cache") / "responses"  # git-ignored


class ProviderError(Exception):
    """The provider failed (network, HTTP status, unreadable response). The player logs it as the
    step's `error` and the runner executes `stay`. Anything else that goes wrong is our bug and
    is left to end the run."""


def cache_key(provider: str, model: str, senses: dict, questions: dict) -> str:
    """sha256 of provider, model, senses and questions. `questions` is everything else that shapes
    the answer (Jev's questions; the LLM's system prompt and schema), so editing a prompt can never
    be answered from a response to the old one."""
    blob = json.dumps({"provider": provider, "model": model, "senses": senses, "questions": questions},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


class DiskCache:
    """One JSON file per response, <root>/<provider>/<first two hex digits>/<key>.json. The file
    keeps the request next to the response, so a cached answer can be audited by hand."""

    def __init__(self, root: Path | str = DEFAULT_CACHE_DIR):
        self.root = Path(root)

    def _path(self, provider: str, key: str) -> Path:
        return self.root / provider / key[:2] / f"{key}.json"

    def get(self, provider: str, key: str) -> dict | None:
        try:
            return json.loads(self._path(provider, key).read_text())["payload"]
        except (OSError, ValueError, KeyError, TypeError):
            return None  # absent or damaged: ask again

    def put(self, provider: str, key: str, request: dict, payload: dict) -> None:
        path = self._path(provider, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(f".{os.getpid()}.partial")
        partial.write_text(json.dumps({"request": request, "payload": payload}))
        os.replace(partial, path)  # a run killed mid-write never leaves half a response behind


class RequestBudget:
    """The hard cap on live requests. One per paid player per run."""

    def __init__(self, max_requests: int):
        if max_requests < 0:
            raise ValueError(f"max_requests must not be negative: {max_requests}")
        self.max_requests = max_requests
        self.used = 0

    def spend(self) -> None:
        if self.used >= self.max_requests:
            raise BudgetExhausted(f"request cap of {self.max_requests} reached")
        self.used += 1


@dataclass
class Reply:
    payload: dict
    latency_ms: float | None  # None on a cache hit: the report counts a latency as a paid request
    cache_hit: bool


def cached_request(cache: DiskCache, budget: RequestBudget, provider: str, model: str, senses: dict,
                   questions: dict, live: Callable[[], dict]) -> Reply:
    """`live` makes the one real request and returns a JSON-able payload, or raises ProviderError."""
    key = cache_key(provider, model, senses, questions)
    payload = cache.get(provider, key)
    if payload is not None:
        return Reply(payload, latency_ms=None, cache_hit=True)
    budget.spend()  # before the call: a request that fails may still have been billed
    start = time.perf_counter()
    payload = live()
    latency_ms = (time.perf_counter() - start) * 1000.0
    cache.put(provider, key, {"provider": provider, "model": model, "senses": senses, "questions": questions},
              payload)
    return Reply(payload, latency_ms=latency_ms, cache_hit=False)


class PaidClient:
    """Base of the two thin clients. A subclass sets `provider`, `key_name` and `default_model` and
    implements _live(). `sdk` is the provider's SDK client: tests inject a fake, a real one is built
    on the first live request, so a run answered entirely from the cache needs no key."""

    provider: str
    key_name: str
    default_model: str

    def __init__(self, cache: DiskCache, budget: RequestBudget, model: str | None = None, sdk=None):
        self.cache, self.budget, self.model = cache, budget, model or self.default_model
        self._sdk = sdk
        self._owns_sdk = sdk is None

    def preflight(self) -> None:
        if self._owns_sdk and self.budget.max_requests > 0:
            require_key(self.key_name)

    def ask(self, senses: dict, questions: dict) -> Reply:
        return cached_request(self.cache, self.budget, self.provider, self.model, senses, questions,
                              lambda: self._live(senses, questions))

    def _live(self, senses: dict, questions: dict) -> dict:
        raise NotImplementedError

    def close(self) -> None:
        sdk, self._sdk = self._sdk, None
        if sdk is not None and self._owns_sdk:
            sdk.close()
```

- [ ] **Step 5: Run all tests**

Run: `uv run pytest -q`
Expected: `171 passed, 7 deselected`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock bakeoff/clients tests/test_clients_keys.py tests/test_clients_core.py
git commit -F <message file>   # feat: response cache, hard request cap and key loading for paid players
```

---

### Task 3: Jev client and player

**Files:**
- Create: `bakeoff/clients/jev.py`, `bakeoff/players/briefing.py`, `bakeoff/players/paid.py`, `bakeoff/players/jev.py`, `tests/fakes.py`
- Test: `tests/test_jev.py`

**Interfaces:**
- Consumes: `PaidClient`, `ProviderError`, `DiskCache`, `RequestBudget`, `require_key` (Task 2); `Decision` (`bakeoff/players/base.py`); `ACTIONS` (`bakeoff/game/engine.py`); `ACTION_DESCRIPTIONS` (`bakeoff/senses.py`). From `typesafe_sdk` 0.7: `TypeSafeClient(api_key=, retry=)`, `RetryPolicy(max_retries=0)`, `Choice(instructions=, criteria=)`, `Noul(instructions=)`, `client.system_one(state=, questions=, model=) -> SystemOneResponse` (`.model_dump()` gives `{"model", "usage": {"input_tokens", "output_tokens"}, "answers": {id: {"type": "choice", "choice", "confidence", "probabilities"} | {"type": "noul", "noul"}}}`), `TypeSafeError` (base of every SDK exception).
- Produces:
  - `bakeoff.players.briefing.RULES: str`.
  - `bakeoff.players.paid.PaidPlayer(cache=None, budget=None, model=None, sdk=None)`: attributes `budget`, `client`, `model`; methods `preflight`, `reset`, `act`, `observe`, `close`; a subclass sets `name`, `client_class`, `questions` and implements `read(payload) -> (action, invalid, answers)`.
  - `bakeoff.clients.jev.JevClient(PaidClient)`, `bakeoff.players.jev.QUESTIONS`, `bakeoff.players.jev.JevPlayer` (`name = "jev"`).
  - `tests.fakes.FakeTypeSafe(reply)` with `calls`, `closed`; `tests.fakes.jev_reply(action="stay", gap_ahead=0.1, left_safe=0.9) -> dict`.

- [ ] **Step 1: Write the fake SDK and the failing tests**

Create `tests/fakes.py`:

```python
"""Stand-ins for the two provider SDKs. No test touches the network."""

from __future__ import annotations


class FakeTypeSafe:
    """Looks like typesafe_sdk.TypeSafeClient. `reply` is a SystemOneResponse-shaped dict, or an exception to raise."""

    def __init__(self, reply):
        self.reply, self.calls, self.closed = reply, [], False

    def system_one(self, state, questions, model=None):
        from typesafe_sdk import SystemOneResponse

        self.calls.append({"state": state, "questions": questions, "model": model})
        if isinstance(self.reply, Exception):
            raise self.reply
        return SystemOneResponse.model_validate(self.reply)

    def close(self):
        self.closed = True


def jev_reply(action="stay", gap_ahead=0.1, left_safe=0.9):
    return {"model": "jev-latest", "usage": {"input_tokens": 400, "output_tokens": 3},
            "answers": {"action": {"type": "choice", "choice": action, "confidence": 0.7,
                                   "probabilities": {a: 0.7 if a == action else 0.1
                                                     for a in ("left", "right", "jump", "stay")}},
                        "gap_ahead": {"type": "noul", "noul": gap_ahead},
                        "left_safe": {"type": "noul", "noul": left_safe}}}
```

Create `tests/test_jev.py`:

```python
import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.clients.jev import JevClient
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players.jev import QUESTIONS, JevPlayer
from bakeoff.senses import compute_senses
from tests.fakes import FakeTypeSafe, jev_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeTypeSafe(reply)
    return JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_questions_are_a_choice_over_the_four_actions_and_two_nouls_named_like_the_ground_truth():
    assert set(QUESTIONS) == {"action", "gap_ahead", "left_safe"}
    assert QUESTIONS["action"]["type"] == "choice" and set(QUESTIONS["action"]["criteria"]) == set(ACTIONS)
    assert QUESTIONS["gap_ahead"]["type"] == QUESTIONS["left_safe"]["type"] == "noul"


def test_the_sdk_gets_the_senses_as_state_and_typed_questions(tmp_path):
    from typesafe_sdk import Choice, Noul

    jev, sdk = player(tmp_path, jev_reply())
    senses = senses_for()
    jev.act(senses)
    (call,) = sdk.calls
    assert call["state"] == senses and call["model"] == "jev-latest"
    assert isinstance(call["questions"]["action"], Choice) and isinstance(call["questions"]["gap_ahead"], Noul)
    assert dict(call["questions"]["action"].criteria) == QUESTIONS["action"]["criteria"]
    assert call["questions"]["left_safe"].instructions == QUESTIONS["left_safe"]["instructions"]


def test_a_live_decision_logs_the_choice_the_probabilities_the_nouls_and_the_usage(tmp_path):
    jev, _ = player(tmp_path, jev_reply("jump", gap_ahead=0.97))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "jump" and not decision.needs_fallback
    assert decision.questions == QUESTIONS
    assert decision.answers["action"]["probabilities"] == {"left": 0.1, "right": 0.1, "jump": 0.7, "stay": 0.1}
    assert decision.answers["gap_ahead"]["noul"] == 0.97
    assert decision.usage == {"input_tokens": 400, "output_tokens": 3}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "jev-latest"}


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    jev, sdk = player(tmp_path, jev_reply("left"))
    senses = senses_for()
    jev.act(senses)
    again = jev.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and jev.budget.used == 1
    fresh, fresh_sdk = player(tmp_path, jev_reply("right"), cap=0)  # a later run, no budget at all
    assert fresh.act(senses).chosen_action == "left" and fresh_sdk.calls == []


def test_a_provider_error_becomes_a_logged_error_not_an_exception(tmp_path):
    from typesafe_sdk import TypeSafeAPIConnectionError

    jev, _ = player(tmp_path, TypeSafeAPIConnectionError("connection refused"))
    decision = jev.act(senses_for())
    assert decision.chosen_action is None and decision.needs_fallback
    assert decision.error == "TypeSafeAPIConnectionError: connection refused"
    assert decision.questions == QUESTIONS and jev.budget.used == 1


def test_the_cap_ends_the_run_instead_of_becoming_a_fallback(tmp_path):
    jev, sdk = player(tmp_path, jev_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        jev.act(senses_for())
    assert sdk.calls == []


def test_a_bug_is_not_swallowed(tmp_path):
    jev, _ = player(tmp_path, RuntimeError("our bug"))
    with pytest.raises(RuntimeError, match="our bug"):
        jev.act(senses_for())


def test_an_unknown_or_missing_choice_is_invalid(tmp_path):
    jev, _ = player(tmp_path, jev_reply("fly"))
    decision = jev.act(senses_for())
    assert decision.chosen_action == "fly" and decision.invalid
    missing, _ = player(tmp_path / "other", {"model": "jev-latest", "usage": {}, "answers": {}})
    assert missing.act(senses_for()).invalid


def test_without_a_budget_the_player_can_only_replay(tmp_path):
    jev = JevPlayer(cache=DiskCache(tmp_path), sdk=FakeTypeSafe(jev_reply()))
    assert jev.budget.max_requests == 0 and jev.model == "jev-latest"


def test_preflight_needs_the_key_only_for_a_live_run_with_the_real_sdk(tmp_path, monkeypatch):
    import bakeoff.clients.core as core

    asked = []

    def no_key(name):
        asked.append(name)
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(0)).preflight()  # replay only
    JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5), sdk=FakeTypeSafe(jev_reply())).preflight()
    assert asked == []
    with pytest.raises(ValueError, match="TYPESAFE_API_KEY is not set"):
        JevPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5)).preflight()


def test_close_closes_only_an_sdk_the_client_built_itself(tmp_path):
    jev, sdk = player(tmp_path, jev_reply())
    jev.close()
    assert not sdk.closed
    client = JevClient(DiskCache(tmp_path), RequestBudget(1))
    client._sdk = owned = FakeTypeSafe(jev_reply())
    client.close()
    assert owned.closed and client._sdk is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_jev.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.clients.jev'`

- [ ] **Step 3: Implement**

Create `bakeoff/clients/jev.py`:

```python
"""Thin Jev client: one system_one request per decision, through the shared cache and cap."""

from __future__ import annotations

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import require_key


class JevClient(PaidClient):
    provider = "jev"
    key_name = "TYPESAFE_API_KEY"
    default_model = "jev-latest"

    def _live(self, senses: dict, questions: dict) -> dict:
        # imported here: listing players or replaying from the cache never loads the SDK
        from typesafe_sdk import Choice, Noul, RetryPolicy, TypeSafeClient, TypeSafeError

        if self._sdk is None:
            # no SDK retries: one spent request is one HTTP request, so the cap is exact
            self._sdk = TypeSafeClient(api_key=require_key(self.key_name), retry=RetryPolicy(max_retries=0))
        kinds = {"choice": Choice, "noul": Noul}
        built = {name: kinds[q["type"]](**{k: v for k, v in q.items() if k != "type"}) for name, q in questions.items()}
        try:
            response = self._sdk.system_one(state=senses, questions=built, model=self.model)
        except TypeSafeError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        return response.model_dump()  # {"model", "usage": {input_tokens, output_tokens}, "answers": {...}}
```

Create `bakeoff/players/briefing.py`:

```python
"""What the two paid players are told about the game: the same words for both. OURS, written once
before any paid request and never tuned on tournament seeds (the text is part of the cache key)."""

RULES = (
    "A runner moves through a tunnel made of a ring of lanes, one row per turn. `ahead` lists the next rows, "
    "nearest first: `row` 1 is the row the runner enters next. `gaps_relative` lists where the floor of that row "
    "is missing, as lane offsets from the runner's current lane: negative is to the runner's left, 0 is the "
    "runner's own lane, positive is to the right. Only offsets from -3 to 3 are visible. `left` and `right` move "
    "one lane sideways while entering row 1, so they land on offset -1 or 1 of row 1. `stay` lands on offset 0 of "
    "row 1. `jump` passes over row 1 and lands on offset 0 of row 2. Landing on a gap ends the run. The goal is "
    "to survive as many rows as possible."
)
```

Create `bakeoff/players/paid.py`:

```python
"""What the two paid players share: one cached, capped request per row; provider errors become a
logged `error` (the runner then executes `stay`); BudgetExhausted is left to end the run."""

from __future__ import annotations

from bakeoff.clients.core import DiskCache, PaidClient, ProviderError, RequestBudget
from bakeoff.game.engine import Game
from bakeoff.players.base import Decision


class PaidPlayer:
    name: str
    client_class: type[PaidClient]
    questions: dict  # plain JSON: logged in every record and part of the cache key

    def __init__(self, cache: DiskCache | None = None, budget: RequestBudget | None = None,
                 model: str | None = None, sdk=None):
        # Without a budget the cap is 0: the player can only replay the cache, never spend.
        self.budget = budget if budget is not None else RequestBudget(0)
        self.client = self.client_class(cache if cache is not None else DiskCache(), self.budget, model, sdk)
        self.model = self.client.model

    def preflight(self) -> None:
        """Called by Runner.run before the run directory exists: a live run without its key is a usage error."""
        self.client.preflight()

    def reset(self, game: Game, seed: int) -> None:
        pass

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        """The provider's payload -> (chosen action, invalid, answers to log)."""
        raise NotImplementedError

    def act(self, senses: dict) -> Decision:
        try:
            reply = self.client.ask(senses, self.questions)
        except ProviderError as e:
            return Decision(None, error=str(e), questions=self.questions)
        action, invalid, answers = self.read(reply.payload)
        return Decision(action, invalid=invalid, questions=self.questions, answers=answers,
                        latency_ms=reply.latency_ms, usage=reply.payload.get("usage"), cache_hit=reply.cache_hit,
                        info={"model": reply.payload.get("model")})

    def observe(self, executed_action: str) -> None:
        pass

    def close(self) -> None:
        self.client.close()
```

Create `bakeoff/players/jev.py`:

```python
"""Jev: one request per row. A Choice over the four actions decides; two speculative Nouls are
logged for calibration only (the engine knows the truth for free) and never influence the move."""

from __future__ import annotations

from bakeoff.clients.jev import JevClient
from bakeoff.game.engine import ACTIONS
from bakeoff.players.briefing import RULES
from bakeoff.players.paid import PaidPlayer
from bakeoff.senses import ACTION_DESCRIPTIONS

# The Noul ids are the keys of the record's `ground_truth`, so the report can score them.
QUESTIONS = {
    "action": {"type": "choice", "instructions": RULES + " Which action should the runner take now?",
               "criteria": dict(ACTION_DESCRIPTIONS)},
    "gap_ahead": {"type": "noul", "instructions": "Is there a gap directly ahead of the runner in the next row, "
                                                  "that is, does `ahead[0].gaps_relative` contain 0?"},
    "left_safe": {"type": "noul", "instructions": "Is the lane to the runner's left safe in the next row, "
                                                  "that is, is -1 absent from `ahead[0].gaps_relative`?"},
}


class JevPlayer(PaidPlayer):
    name = "jev"
    client_class = JevClient
    questions = QUESTIONS

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers = payload.get("answers") or {}
        action = (answers.get("action") or {}).get("choice")
        return action, action not in ACTIONS, answers
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: `182 passed, 7 deselected`

- [ ] **Step 5: Commit**

```bash
git add bakeoff/clients/jev.py bakeoff/players/briefing.py bakeoff/players/paid.py bakeoff/players/jev.py tests/fakes.py tests/test_jev.py
git commit -F <message file>   # feat: Jev player, one cached and capped request per row
```

---

### Task 4: LLM client and player

**Files:**
- Create: `bakeoff/clients/llm.py`, `bakeoff/players/llm.py`
- Modify: `tests/fakes.py` (append)
- Test: `tests/test_llm.py`

**Interfaces:**
- Consumes: `PaidClient`, `ProviderError`, `require_key` (Task 2); `PaidPlayer`, `RULES` (Task 3). From `anthropic` 1.7: `anthropic.Anthropic(api_key=, max_retries=0, timeout=)`, `client.messages.create(model=, max_tokens=, system=, messages=, output_config={"format": {"type": "json_schema", "schema": ...}})` returning a `Message` with `.model`, `.stop_reason`, `.content` (blocks with `.type` and `.text`), `.usage.input_tokens`, `.usage.output_tokens`; `anthropic.APIError` (base of every API exception). `anthropic` 1.x is built on `httpx2`, not `httpx`.
- Produces: `bakeoff.clients.llm.LlmClient(PaidClient)` whose payload is `{"model", "stop_reason", "text", "usage": {"input_tokens", "output_tokens"}}`; `bakeoff.players.llm.QUESTIONS` (`system`, `schema`, `max_tokens`); `bakeoff.players.llm.LlmPlayer` (`name = "llm"`); `tests.fakes.FakeAnthropic(reply)`, `tests.fakes.llm_reply(text='{"action": "stay"}', stop_reason="end_turn") -> dict`.

- [ ] **Step 1: Write the fake SDK and the failing tests**

Append to `tests/fakes.py`:

```python
class FakeAnthropic:
    """Looks like anthropic.Anthropic. `reply` is a Message-shaped dict, or an exception to raise."""

    def __init__(self, reply):
        self.reply, self.calls, self.closed = reply, [], False
        self.messages = self

    def create(self, **kwargs):
        import anthropic

        self.calls.append(kwargs)
        if isinstance(self.reply, Exception):
            raise self.reply
        return anthropic.types.Message.model_validate(self.reply)

    def close(self):
        self.closed = True


def llm_reply(text='{"action": "stay"}', stop_reason="end_turn"):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-4-5-20251001",
            "content": [{"type": "text", "text": text}], "stop_reason": stop_reason, "stop_sequence": None,
            "usage": {"input_tokens": 520, "output_tokens": 9}}
```

Create `tests/test_llm.py`:

```python
import json

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.errors import BudgetExhausted
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players import jev
from bakeoff.players.briefing import RULES
from bakeoff.players.llm import QUESTIONS, LlmPlayer
from bakeoff.senses import compute_senses
from tests.fakes import FakeAnthropic, llm_reply


def senses_for(seed=3):
    return compute_senses(Game(generate_track(seed, max_rows=40)))


def player(tmp_path, reply, cap=10):
    sdk = FakeAnthropic(reply)
    return LlmPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(cap), sdk=sdk), sdk


def test_both_paid_players_are_told_the_same_rules():
    assert QUESTIONS["system"].startswith(RULES) and jev.QUESTIONS["action"]["instructions"].startswith(RULES)


def test_the_request_is_haiku_with_the_senses_as_the_user_message_and_an_action_schema(tmp_path):
    llm, sdk = player(tmp_path, llm_reply())
    senses = senses_for()
    llm.act(senses)
    (call,) = sdk.calls
    assert call["model"] == "claude-haiku-4-5-20251001" and call["max_tokens"] == 256
    assert call["system"] == QUESTIONS["system"]
    assert call["messages"] == [{"role": "user", "content": json.dumps(senses)}]
    schema = call["output_config"]["format"]["schema"]
    assert call["output_config"]["format"]["type"] == "json_schema"
    assert schema["properties"]["action"]["enum"] == list(ACTIONS) and schema["additionalProperties"] is False


def test_a_live_decision_logs_the_answer_and_the_usage(tmp_path):
    llm, _ = player(tmp_path, llm_reply('{"action": "jump"}'))
    decision = llm.act(senses_for())
    assert decision.chosen_action == "jump" and not decision.needs_fallback
    assert decision.questions == QUESTIONS
    assert decision.answers == {"text": '{"action": "jump"}', "stop_reason": "end_turn"}
    assert decision.usage == {"input_tokens": 520, "output_tokens": 9}
    assert decision.latency_ms is not None and not decision.cache_hit
    assert decision.info == {"model": "claude-haiku-4-5-20251001"}


def test_the_same_senses_are_answered_from_the_cache_without_spending(tmp_path):
    llm, sdk = player(tmp_path, llm_reply('{"action": "left"}'))
    senses = senses_for()
    llm.act(senses)
    again = llm.act(senses)
    assert again.chosen_action == "left" and again.cache_hit and again.latency_ms is None
    assert len(sdk.calls) == 1 and llm.budget.used == 1


@pytest.mark.parametrize("reply, chosen", [
    (llm_reply("I would jump"), None),
    (llm_reply('{"move": "jump"}'), None),
    (llm_reply('{"action": 3}'), None),
    (llm_reply('["jump"]'), None),
    (llm_reply('{"action": "fly"}'), "fly"),
    (llm_reply('{"action": "jump"}', stop_reason="max_tokens"), "jump"),
    (llm_reply('{"action": "jump"}', stop_reason="refusal"), "jump"),
])
def test_anything_but_one_known_action_from_a_finished_turn_is_invalid(tmp_path, reply, chosen):
    llm, _ = player(tmp_path, reply)
    decision = llm.act(senses_for())
    assert decision.invalid and decision.needs_fallback and decision.chosen_action == chosen
    assert decision.answers["text"] == reply["content"][0]["text"]


def test_a_provider_error_becomes_a_logged_error_not_an_exception(tmp_path):
    import anthropic
    import httpx2

    error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
    llm, _ = player(tmp_path, error)
    decision = llm.act(senses_for())
    assert decision.chosen_action is None and decision.error.startswith("APIConnectionError: ")
    assert llm.budget.used == 1


def test_the_cap_ends_the_run_instead_of_becoming_a_fallback(tmp_path):
    llm, sdk = player(tmp_path, llm_reply(), cap=0)
    with pytest.raises(BudgetExhausted):
        llm.act(senses_for())
    assert sdk.calls == []


def test_preflight_names_the_anthropic_key(tmp_path, monkeypatch):
    import bakeoff.clients.core as core

    def no_key(name):
        raise ValueError(f"{name} is not set")

    monkeypatch.setattr(core, "require_key", no_key)
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY is not set"):
        LlmPlayer(cache=DiskCache(tmp_path), budget=RequestBudget(5)).preflight()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_llm.py`
Expected: collection error, `ModuleNotFoundError: No module named 'bakeoff.players.llm'`

- [ ] **Step 3: Implement**

Create `bakeoff/clients/llm.py`:

```python
"""Thin Anthropic client: one Messages request per decision, through the shared cache and cap."""

from __future__ import annotations

import json

from bakeoff.clients.core import PaidClient, ProviderError
from bakeoff.clients.keys import require_key

TIMEOUT_S = 60.0  # the SDK default is 10 minutes; a decision that slow is an error


class LlmClient(PaidClient):
    provider = "llm"
    key_name = "ANTHROPIC_API_KEY"
    default_model = "claude-haiku-4-5-20251001"

    def _live(self, senses: dict, questions: dict) -> dict:
        import anthropic  # imported here: listing players or replaying from the cache never loads the SDK

        if self._sdk is None:
            # no SDK retries: one spent request is one HTTP request, so the cap is exact
            self._sdk = anthropic.Anthropic(api_key=require_key(self.key_name), max_retries=0, timeout=TIMEOUT_S)
        try:
            message = self._sdk.messages.create(
                model=self.model, max_tokens=questions["max_tokens"], system=questions["system"],
                messages=[{"role": "user", "content": json.dumps(senses)}],
                output_config={"format": {"type": "json_schema", "schema": questions["schema"]}})
        except anthropic.APIError as e:
            raise ProviderError(f"{type(e).__name__}: {e}") from e
        text = "".join(block.text for block in message.content if block.type == "text")
        return {"model": message.model, "stop_reason": message.stop_reason, "text": text,
                "usage": {"input_tokens": message.usage.input_tokens, "output_tokens": message.usage.output_tokens}}
```

Create `bakeoff/players/llm.py`:

```python
"""The LLM: Claude Haiku 4.5 gets the same JSON senses and must answer with one action as
structured output. Anything else (cut off, refused, not JSON, no action) is logged as invalid."""

from __future__ import annotations

import json

from bakeoff.clients.llm import LlmClient
from bakeoff.game.engine import ACTIONS
from bakeoff.players.briefing import RULES
from bakeoff.players.paid import PaidPlayer

QUESTIONS = {
    "system": RULES + " The user message is the runner's current view as JSON. Answer with the action to take now.",
    "schema": {"type": "object", "properties": {"action": {"type": "string", "enum": list(ACTIONS)}},
               "required": ["action"], "additionalProperties": False},
    "max_tokens": 256,
}


class LlmPlayer(PaidPlayer):
    name = "llm"
    client_class = LlmClient
    questions = QUESTIONS

    def read(self, payload: dict) -> tuple[str | None, bool, dict]:
        answers = {"text": payload.get("text"), "stop_reason": payload.get("stop_reason")}
        try:
            action = json.loads(payload.get("text") or "")["action"]
        except (ValueError, KeyError, TypeError):
            return None, True, answers
        if not isinstance(action, str):
            return None, True, answers
        return action, payload.get("stop_reason") != "end_turn" or action not in ACTIONS, answers
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: `196 passed, 7 deselected`

- [ ] **Step 5: Commit**

```bash
git add bakeoff/clients/llm.py bakeoff/players/llm.py tests/fakes.py tests/test_llm.py
git commit -F <message file>   # feat: LLM player, Claude Haiku 4.5 answering with one action as structured output
```

---

### Task 5: CLI wiring, registry, and the cap on record in `meta.json`

**Files:**
- Modify: `bakeoff/players/__init__.py`, `bakeoff/__main__.py`, `bakeoff/runner.py`
- Test: `tests/test_cli.py`, `tests/test_players.py`

**Interfaces:**
- Consumes: `JevPlayer`, `LlmPlayer` (constructor keywords `cache=`, `budget=`; attributes `model`, `budget`), `DiskCache`, `RequestBudget`, `DEFAULT_CACHE_DIR`, `tests.fakes.FakeTypeSafe`, `tests.fakes.jev_reply`.
- Produces: `bakeoff.players.PAID = ("jev", "llm")`; registry entries `jev` and `llm`; CLI flags `--max-requests` (int, default 0, per paid player) and `--cache` (default `.cache/responses`); `meta.json` keys `models` (`{player: model id}`) and `requests` (`{player: {"max", "used"}}`, written at the start and again when the run ends); `args` gains `max_requests` and `cache`.

- [ ] **Step 1: Write the failing tests**

Make exactly these edits to `tests/test_cli.py` (one changed assertion, then new tests appended):

```diff
--- a/tests/test_cli.py
+++ b/tests/test_cli.py
@@ -13,7 +13,9 @@ def test_run_then_report(tmp_path, capsys):
     (run_dir,) = tmp_path.iterdir()
     meta = json.loads((run_dir / "meta.json").read_text())
     assert meta["status"] == "completed" and meta["seeds"] == [0, 1]
-    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30}
+    assert meta["args"] == {"players": "solver,random", "seeds": 2, "seed_start": 0, "max_rows": 30,
+                            "max_requests": 0, "cache": ".cache/responses"}
+    assert meta["models"] == {} and meta["requests"] == {}
 
     assert main(["report", str(run_dir)]) == 0
     assert "| solver |" in capsys.readouterr().out
@@ -93,3 +95,70 @@ def test_spaces_around_player_names_are_ignored(tmp_path, capsys):
     assert main(["run", "--players", "random, solver", "--seeds", "1", "--max-rows", "20", "--out", str(tmp_path)]) == 0
     out = capsys.readouterr().out
     assert "| random |" in out and "| solver |" in out
+
+
+def fake_paid(monkeypatch, action="stay"):
+    """Put a JevPlayer with a fake SDK in the registry; returns the list of SDKs the CLI built."""
+    from bakeoff.players.jev import JevPlayer
+    from tests.fakes import FakeTypeSafe, jev_reply
+
+    sdks = []
+
+    def factory(cache, budget):
+        sdks.append(FakeTypeSafe(jev_reply(action)))
+        return JevPlayer(cache=cache, budget=budget, sdk=sdks[-1])
+
+    monkeypatch.setitem(REGISTRY, "jev", factory)
+    return sdks
+
+
+def paid_args(tmp_path, *extra):
+    return ["run", "--players", "jev", "--seeds", "1", "--seed-start", "1000", "--max-rows", "12",
+            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache"), *extra]
+
+
+def test_without_max_requests_a_paid_player_cannot_spend_anything(tmp_path, capsys, monkeypatch):
+    sdks = fake_paid(monkeypatch)
+    assert main(paid_args(tmp_path)) == 1
+    assert "run budget_exhausted: request cap of 0 reached" in capsys.readouterr().err
+    assert sdks[0].calls == []
+    (run_dir,) = (tmp_path / "runs").iterdir()
+    meta = json.loads((run_dir / "meta.json").read_text())
+    assert meta["status"] == "budget_exhausted" and meta["requests"] == {"jev": {"max": 0, "used": 0}}
+    assert meta["models"] == {"jev": "jev-latest"}
+
+
+def test_the_cap_stops_the_run_and_the_next_run_continues_from_the_cache(tmp_path, capsys, monkeypatch):
+    sdks = fake_paid(monkeypatch, action="jump")  # always_jump survives the 12 rows of seed 1000
+    assert main(paid_args(tmp_path, "--max-requests", "2")) == 1
+    assert len(sdks[0].calls) == 2
+    time.sleep(1.1)  # run ids have one-second resolution
+    assert main(paid_args(tmp_path, "--max-requests", "50")) == 0
+    first, second = sorted((tmp_path / "runs").iterdir())
+    assert json.loads((first / "meta.json").read_text())["requests"] == {"jev": {"max": 2, "used": 2}}
+    steps = [json.loads(line) for line in (second / "jev.jsonl").read_text().splitlines()]
+    assert [s["cache_hit"] for s in steps[:2]] == [True, True] and not any(s["cache_hit"] for s in steps[2:])
+    meta = json.loads((second / "meta.json").read_text())
+    assert meta["status"] == "completed" and meta["requests"]["jev"]["used"] == len(steps) - 2
+    time.sleep(1.1)
+    assert main(paid_args(tmp_path)) == 0  # a full replay needs no budget at all
+    assert len(sdks[2].calls) == 0
+
+
+def test_a_missing_key_is_a_usage_error_before_the_run_directory_exists(tmp_path, capsys, monkeypatch):
+    import bakeoff.clients.core as core
+
+    def no_key(name):
+        raise ValueError(f"{name} is not set")
+
+    monkeypatch.setattr(core, "require_key", no_key)
+    args = ["run", "--players", "solver,llm", "--seeds", "1", "--max-requests", "3",
+            "--out", str(tmp_path / "runs"), "--cache", str(tmp_path / "cache")]
+    assert main(args) == 2
+    assert "llm: ANTHROPIC_API_KEY is not set" in capsys.readouterr().err
+    assert not (tmp_path / "runs").exists()
+
+
+def test_a_negative_cap_is_a_usage_error(tmp_path, capsys):
+    assert main(paid_args(tmp_path, "--max-requests", "-1")) == 2
+    assert "must not be negative" in capsys.readouterr().err
```

and to `tests/test_players.py`:

```diff
--- a/tests/test_players.py
+++ b/tests/test_players.py
@@ -2,7 +2,7 @@ import pytest
 
 from bakeoff.game.engine import ACTIONS, Game
 from bakeoff.game.track import generate_track
-from bakeoff.players import REGISTRY, make_player
+from bakeoff.players import PAID, REGISTRY, make_player
 from bakeoff.players.base import Decision
 from bakeoff.players.solver import solve, solve_depths
 from bakeoff.senses import compute_senses
@@ -29,8 +29,9 @@ def test_decision_defaults_and_fallback_rule():
 
 
 def test_factory_knows_the_baselines_and_rejects_unknown_names():
-    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly"}
-    assert all(make_player(name).name == name for name in REGISTRY)
+    assert set(REGISTRY) == {"random", "always_jump", "solver", "fly", "jev", "llm"}
+    assert set(PAID) == {"jev", "llm"}
+    assert all(make_player(name).name == name for name in REGISTRY)  # a paid player without a budget only replays
     with pytest.raises(KeyError, match="unknown player 'nope'"):
         make_player("nope")
 
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_cli.py tests/test_players.py`
Expected: `tests/test_players.py` fails to collect with `ImportError: cannot import name 'PAID'`; after that is fixed the new CLI tests fail with `SystemExit: 2` (`unrecognized arguments: --cache`).

- [ ] **Step 3: Implement**

`bakeoff/players/__init__.py`:

```diff
--- a/bakeoff/players/__init__.py
+++ b/bakeoff/players/__init__.py
@@ -5,11 +5,15 @@ from typing import Callable
 from bakeoff.players.always_jump import AlwaysJumpPlayer
 from bakeoff.players.base import Player
 from bakeoff.players.fly import FlyPlayer
+from bakeoff.players.jev import JevPlayer
+from bakeoff.players.llm import LlmPlayer
 from bakeoff.players.random_player import RandomPlayer
 from bakeoff.players.solver import SolverPlayer
 
 REGISTRY: dict[str, Callable[..., Player]] = {
-    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer}
+    "random": RandomPlayer, "always_jump": AlwaysJumpPlayer, "solver": SolverPlayer, "fly": FlyPlayer,
+    "jev": JevPlayer, "llm": LlmPlayer}
+PAID = ("jev", "llm")  # these take cache= and budget=; without a budget they can only replay the cache
 
 
 def make_player(name: str, **options) -> Player:
```

`bakeoff/__main__.py`:

```diff
--- a/bakeoff/__main__.py
+++ b/bakeoff/__main__.py
@@ -6,8 +6,9 @@ import argparse
 import sys
 import time
 
+from bakeoff.clients.core import DEFAULT_CACHE_DIR, DiskCache, RequestBudget
 from bakeoff.game.track import MAX_ROWS
-from bakeoff.players import REGISTRY, make_player
+from bakeoff.players import PAID, REGISTRY, make_player
 from bakeoff.report import format_table, load_meta, load_steps, summarize
 from bakeoff.runner import RunAborted, Runner
 
@@ -22,6 +23,10 @@ def _parser() -> argparse.ArgumentParser:
                      help="first seed; practice seeds must not overlap tournament seeds")
     run.add_argument("--max-rows", type=int, default=MAX_ROWS)
     run.add_argument("--out", default="runs")
+    run.add_argument("--max-requests", type=int, default=0,
+                     help="hard cap on live requests for EACH paid player (jev, llm); the default 0 only replays "
+                          "the cache. Worst case a run spends this many requests per paid player")
+    run.add_argument("--cache", default=str(DEFAULT_CACHE_DIR), help="response cache directory")
     report = sub.add_parser("report", help="summarize an existing run directory")
     report.add_argument("run_dir")
     return parser
@@ -42,17 +47,23 @@ def main(argv: list[str] | None = None) -> int:
             print(e, file=sys.stderr)
             return 2
         return 0
+    cache = DiskCache(args.cache)
     try:
-        players = [make_player(name.strip()) for name in args.players.split(",")]
+        # one budget per paid player: the providers bill separately, and one must not starve the other
+        players = [make_player(name, cache=cache, budget=RequestBudget(args.max_requests)) if name in PAID
+                   else make_player(name) for name in (n.strip() for n in args.players.split(","))]
     except KeyError as e:
         print(e.args[0], file=sys.stderr)
         return 2
+    except ValueError as e:
+        print(e, file=sys.stderr)
+        return 2
     runner = Runner(args.out)
     run_id = time.strftime("%Y%m%d-%H%M%S")
     run_dir = runner.out_root / run_id
     seeds = range(args.seed_start, args.seed_start + args.seeds)
     run_args = {"players": args.players, "seeds": args.seeds, "seed_start": args.seed_start,
-                "max_rows": args.max_rows}
+                "max_rows": args.max_rows, "max_requests": args.max_requests, "cache": args.cache}
     status = 0
     try:
         runner.run(players, seeds, max_rows=args.max_rows, run_id=run_id, args=run_args)
```

`bakeoff/runner.py`:

```diff
--- a/bakeoff/runner.py
+++ b/bakeoff/runner.py
@@ -80,6 +80,12 @@ def _preflight(players: list[Player]) -> None:
             raise PreflightError(f"{player.name}: {e}") from e
 
 
+def _requests(players: list[Player]) -> dict:
+    """Live requests spent against each paid player's cap (failed requests included)."""
+    return {p.name: {"max": p.budget.max_requests, "used": p.budget.used}
+            for p in players if getattr(p, "budget", None) is not None}
+
+
 class Runner:
     def __init__(self, out_root: Path | str = "runs", max_consecutive_errors: int = 5):
         self.out_root = Path(out_root)
@@ -147,8 +153,11 @@ class Runner:
             "fly": {"turn_threshold_hz": fly.TURN_THRESHOLD_HZ, "jump_threshold_hz": fly.JUMP_THRESHOLD_HZ,
                     "window_ms": WINDOW_MS, "provisional": not fly.CALIBRATED,
                     "model_commit": fly_data.MODEL_REPO_COMMIT, "annotations_commit": fly_data.ANNOTATIONS_COMMIT},
+            "models": {p.name: p.model for p in players if getattr(p, "model", None)},
+            "requests": _requests(players),
             "args": args or {}, "python": platform.python_version(),
-            "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic")},
+            "versions": {pkg: _version(pkg) for pkg in ("brian2", "cython", "numpy", "typesafe-sdk", "anthropic",
+                                                         "python-dotenv")},
         }
         meta_path.write_text(json.dumps(meta, indent=2))
         self._error_streak = 0
@@ -174,5 +183,6 @@ class Runner:
             meta["status"] = "completed"
         finally:
             meta["finished_at"] = _now()
+            meta["requests"] = _requests(players)
             meta_path.write_text(json.dumps(meta, indent=2))
         return run_dir
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: `200 passed, 7 deselected` (the new CLI tests sleep about 2 s in total, because run ids have one-second resolution)

- [ ] **Step 5: Commit**

```bash
git add bakeoff/players/__init__.py bakeoff/__main__.py bakeoff/runner.py tests/test_cli.py tests/test_players.py
git commit -F <message file>   # feat: jev and llm in the CLI behind --max-requests (default 0), cap and models in meta.json
```

---

### Task 6: Report: cache hits, cost and Noul calibration

**Files:**
- Modify: `bakeoff/report.py`
- Test: `tests/test_report.py`

**Interfaces:**
- Consumes: step records (`answers`, `ground_truth`, `usage`, `latency_ms`, `cache_hit`; read with `.get`, older records may lack keys) and `meta["models"]` (Task 5).
- Produces: `COLUMNS` gains `cache_hits` (after `requests`), `cost_usd` (after `output_tokens`), `brier_gap_ahead`, `brier_left_safe` (last); `bakeoff.report.PRICES_USD_PER_MTOK: dict[str, tuple[float, float]]` keyed by model id.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_report.py`:

```python
def test_cache_hits_are_counted_apart_from_requests():
    steps = [step(latency_ms=100.0), step(row=1, cache_hit=True), step(row=2, cache_hit=True, alive=False)]
    (row,) = summarize(steps)
    assert row["requests"] == 1 and row["cache_hits"] == 2


def test_cost_comes_from_live_tokens_and_the_price_of_the_model_in_meta():
    steps = [step(player="llm", latency_ms=100.0, usage={"input_tokens": 500_000, "output_tokens": 10_000}),
             step(player="llm", row=1, cache_hit=True, usage={"input_tokens": 9_000_000, "output_tokens": 0}),
             step(player="jev", latency_ms=50.0, usage={"input_tokens": 400, "output_tokens": 3}),
             step(player="solver")]
    meta = {"models": {"llm": "claude-haiku-4-5-20251001", "jev": "jev-latest"}}
    rows = {r["player"]: r for r in summarize(steps, meta)}
    assert rows["llm"]["cost_usd"] == pytest.approx(0.5 * 1.00 + 0.01 * 5.00)
    assert rows["jev"]["cost_usd"] is None  # price not known: never shown as free
    assert rows["solver"]["cost_usd"] is None
    assert {r["cost_usd"] for r in summarize(steps)} == {None}  # no meta, no model, no price


def test_brier_scores_the_logged_nouls_against_the_engine_truth():
    def noul_step(row, gap, left, truth_gap, truth_left, **extra):
        return step(row=row, answers={"action": {"choice": "stay"}, "gap_ahead": {"type": "noul", "noul": gap},
                                      "left_safe": {"type": "noul", "noul": left}},
                    ground_truth={"gap_ahead": truth_gap, "left_safe": truth_left}, **extra)

    steps = [noul_step(0, 0.9, 0.5, True, True), noul_step(1, 0.2, 0.5, False, False, cache_hit=True),
             step(row=2, answers=None, ground_truth={"gap_ahead": True, "left_safe": True}, alive=False)]
    (row,) = summarize(steps)
    assert row["brier_gap_ahead"] == pytest.approx((0.1 ** 2 + 0.2 ** 2) / 2)
    assert row["brier_left_safe"] == pytest.approx(0.25)


def test_brier_is_none_for_a_player_that_answers_no_nouls():
    (row,) = summarize([step(answers={"text": "{}"}, ground_truth={"gap_ahead": True, "left_safe": True})])
    assert row["brier_gap_ahead"] is None and row["brier_left_safe"] is None


def test_small_amounts_keep_four_decimals_in_the_table():
    steps = [step(player="llm", latency_ms=100.0, usage={"input_tokens": 5200, "output_tokens": 90}, alive=False)]
    table = format_table(summarize(steps, {"models": {"llm": "claude-haiku-4-5-20251001"}}))
    assert "| 0.0056 |" in table
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest -q tests/test_report.py`
Expected: the five new tests fail with `KeyError: 'cache_hits'`, `KeyError: 'cost_usd'`, `KeyError: 'brier_gap_ahead'` (twice) and an assertion on the table text.

- [ ] **Step 3: Implement**

Make exactly these edits to `bakeoff/report.py`:

```diff
--- a/bakeoff/report.py
+++ b/bakeoff/report.py
@@ -10,7 +10,12 @@ from pathlib import Path
 COLUMNS = ("player", "runs", "incomplete", "missing", "mean_rows", "median_rows", "finished",
            "ran_into_gap", "jumped_into_gap", "dodged_into_gap", "jump_share", "solver_agreement",
            "fallback_rate", "invalid_rate", "error_rate",
-           "requests", "mean_latency_ms", "input_tokens", "output_tokens")
+           "requests", "cache_hits", "mean_latency_ms", "input_tokens", "output_tokens", "cost_usd",
+           "brier_gap_ahead", "brier_left_safe")
+
+# USD per million tokens (input, output), by the model id in meta.json. Jev is absent until its
+# price is known (docs/COSTS.md): its cost then shows as "-", never as 0.
+PRICES_USD_PER_MTOK = {"claude-haiku-4-5-20251001": (1.00, 5.00)}
 
 
 def load_steps(run_dir: Path | str) -> list[dict]:
@@ -58,7 +63,26 @@ def _is_fallback(step: dict) -> bool:
     return bool(step["gated"] or step["invalid"] or step["error"] is not None or step["chosen_action"] is None)
 
 
-def _summarize_player(player: str, steps: list[dict]) -> dict:
+def _cost_usd(model: str | None, input_tokens: int, output_tokens: int) -> float | None:
+    if model not in PRICES_USD_PER_MTOK:
+        return None
+    per_input, per_output = PRICES_USD_PER_MTOK[model]
+    return (input_tokens * per_input + output_tokens * per_output) / 1_000_000
+
+
+def _brier(steps: list[dict], noul: str) -> float | None:
+    """Mean squared gap between a logged Noul probability and the engine's truth (0 is perfect,
+    0.25 is what always answering 0.5 scores). Cached answers count: a judgment is a judgment."""
+    errors = []
+    for s in steps:
+        answer = (s.get("answers") or {}).get(noul)
+        truth = (s.get("ground_truth") or {}).get(noul)
+        if isinstance(answer, dict) and isinstance(answer.get("noul"), (int, float)) and truth is not None:
+            errors.append((answer["noul"] - float(truth)) ** 2)
+    return _mean(errors)
+
+
+def _summarize_player(player: str, steps: list[dict], model: str | None = None) -> dict:
     runs = defaultdict(list)
     for s in steps:
         runs[s["seed"]].append(s)
@@ -70,6 +94,8 @@ def _summarize_player(player: str, steps: list[dict]) -> dict:
     comparable = [s for s in steps if s["chosen_action"] is not None]
     live = [s for s in steps if s["latency_ms"] is not None and not s["cache_hit"]]
     usage = [s["usage"] or {} for s in live]
+    input_tokens = sum(u.get("input_tokens") or 0 for u in usage)
+    output_tokens = sum(u.get("output_tokens") or 0 for u in usage)
 
     return {
         "player": player, "runs": len(complete), "incomplete": len(finals) - len(complete),
@@ -83,10 +109,11 @@ def _summarize_player(player: str, steps: list[dict]) -> dict:
         "invalid_rate": _ratio(sum(s["invalid"] for s in steps), len(steps)),
         "error_rate": _ratio(sum(s["error"] is not None for s in steps), len(steps)),
         "missing": None,  # filled in by summarize() when meta.json says which seeds were planned
-        "requests": len(live),
+        "requests": len(live), "cache_hits": sum(bool(s["cache_hit"]) for s in steps),
         "mean_latency_ms": _mean([s["latency_ms"] for s in live]),
-        "input_tokens": sum(u.get("input_tokens") or 0 for u in usage),
-        "output_tokens": sum(u.get("output_tokens") or 0 for u in usage),
+        "input_tokens": input_tokens, "output_tokens": output_tokens,
+        "cost_usd": _cost_usd(model, input_tokens, output_tokens) if live else None,
+        "brier_gap_ahead": _brier(steps, "gap_ahead"), "brier_left_safe": _brier(steps, "left_safe"),
     }
 
 
@@ -98,7 +125,7 @@ def summarize(steps: list[dict], meta: dict | None = None) -> list[dict]:
         groups.setdefault(player, [])  # a player that never started still gets a row
     rows = []
     for player, group in sorted(groups.items()):
-        row = _summarize_player(player, group)
+        row = _summarize_player(player, group, ((meta or {}).get("models") or {}).get(player))
         if meta is not None:
             row["missing"] = len(set(meta.get("seeds", ())) - {s["seed"] for s in group})
         rows.append(row)
@@ -109,7 +136,7 @@ def _fmt(value) -> str:
     if value is None:
         return "-"
     if isinstance(value, float):
-        return f"{value:.2f}"
+        return f"{value:.4f}" if 0 < abs(value) < 0.1 else f"{value:.2f}"  # a track costs cents
     return str(value)
 
 
```

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -q`
Expected: `205 passed, 7 deselected`

- [ ] **Step 5: Commit**

```bash
git add bakeoff/report.py tests/test_report.py
git commit -F <message file>   # feat: report shows cache hits, measured cost and Brier scores of Jev's Nouls
```

---

### Task 7: Opt-in live tests and documentation

**Files:**
- Create: `tests/test_live.py`
- Modify: `README.md`, `CLAUDE.md`, `docs/STEP_RECORD.md`, `docs/DECISIONS.md`

**Interfaces:**
- Consumes: `JevPlayer`, `LlmPlayer`, `require_key`, `DiskCache`, `RequestBudget`; the `live` marker already declared and deselected by default in `pyproject.toml` (`addopts = "-m 'not slow and not live'"`).
- Produces: `uv run pytest -m live -q` makes exactly one real request per provider (skipped when the key is absent). **This task does not run it.**

- [ ] **Step 1: Create `tests/test_live.py`**

```python
"""Opt-in: one real request per provider. Costs money. Run with `uv run pytest -m live -q`.
Each test has a budget of exactly one request and its own empty cache."""

import pytest

from bakeoff.clients.core import DiskCache, RequestBudget
from bakeoff.clients.keys import require_key
from bakeoff.game.engine import ACTIONS, Game
from bakeoff.game.track import generate_track
from bakeoff.players.jev import JevPlayer
from bakeoff.players.llm import LlmPlayer
from bakeoff.senses import compute_senses

pytestmark = pytest.mark.live
PRACTICE_SEED = 1000  # never a tournament seed


def one_decision(player_class, key_name, tmp_path):
    try:
        require_key(key_name)
    except ValueError as e:
        pytest.skip(str(e))
    player = player_class(cache=DiskCache(tmp_path), budget=RequestBudget(1))
    try:
        decision = player.act(compute_senses(Game(generate_track(PRACTICE_SEED))))
    finally:
        player.close()
    assert player.budget.used == 1
    assert decision.error is None, decision.error
    assert decision.chosen_action in ACTIONS and not decision.invalid
    assert decision.latency_ms > 0 and not decision.cache_hit
    assert decision.usage["input_tokens"] > 0
    return decision


def test_jev_answers_one_real_request(tmp_path):
    decision = one_decision(JevPlayer, "TYPESAFE_API_KEY", tmp_path)
    assert set(decision.answers) == {"action", "gap_ahead", "left_safe"}
    assert set(decision.answers["action"]["probabilities"]) == set(ACTIONS)
    assert 0.0 <= decision.answers["gap_ahead"]["noul"] <= 1.0


def test_the_llm_answers_one_real_request(tmp_path):
    decision = one_decision(LlmPlayer, "ANTHROPIC_API_KEY", tmp_path)
    assert decision.answers["stop_reason"] == "end_turn"
    assert decision.info["model"].startswith("claude-haiku-4-5")
```

- [ ] **Step 2: Check that a plain run never selects it**

Run: `uv run pytest -q`
Expected: `205 passed, 9 deselected` (7 slow, 2 live). Do **not** run `-m live` here: it spends money and belongs to Task 8.

- [ ] **Step 3: `README.md`**

Replace the status paragraph and the command block with:

```markdown
Status: phase 3 of 5 built. The untrained fly plays: on seeds 0–19 it survives 127 rows
on average (random 35, always-jump 48, solver 300; `calibration/RESULTS.md`). Jev and the LLM
(Claude Haiku 4.5) play behind a response cache and a hard request cap; first measured costs
are in `docs/COSTS.md`.

    uv run pytest                                    # fast tests, 5 s; `-m slow` runs the real brain (1 GB)
    uv run python -m scripts.fetch_fly_data          # once: 400 MB into data/
    uv run python -m bakeoff run --players fly,always_jump,random,solver --seeds 20
    uv run python -m bakeoff report runs/<run_id>

Paid players (`jev`, `llm`) need `TYPESAFE_API_KEY` / `ANTHROPIC_API_KEY` in a git-ignored `.env`
file at the repo root (template: `.env.example`). They spend nothing unless told to:

    uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300

`--max-requests` is a hard cap on live requests for **each** paid player in the run; the default 0
only replays `.cache/responses`. Every answer is cached, so a repeated run is free and a run stopped
by the cap (`status: budget_exhausted`) continues from the cache next time. `uv run pytest -m live`
makes one real request per provider.
```

- [ ] **Step 4: `docs/STEP_RECORD.md`**

In the step record table replace the `questions`, `answers`, `usage` and `info` rows with:

```markdown
| `questions` | object or null | what a paid player was asked, else null. Jev: `{action, gap_ahead, left_safe}`, each `{type: "choice" \| "noul", instructions, criteria?}`. LLM: `{system, schema, max_tokens}`; its user message is the `senses` as JSON |
| `answers` | object or null | Jev: `{action: {type, choice, confidence, probabilities: {left, right, jump, stay}}, gap_ahead: {type, noul}, left_safe: {type, noul}}`, `noul` being the probability of yes. LLM: `{text, stop_reason}`, `text` being the raw JSON it returned. Null after an `error` |
| `usage` | object or null | `{input_tokens, output_tokens}` for paid players, as reported by the provider (also on a cache hit: what the original request used) |
| `info` | object or null | player-specific extras: the fly's activity (below); `{model}` for paid players, the model id the provider reported |
```

After the "`info` of the fly" section add:

```markdown
### Paid players

One request per row. `latency_ms` is set only for a live request; `cache_hit: true` means the answer
came from `.cache/responses` and cost nothing. A provider failure sets `error` (`"<ExceptionName>:
<message>"`), leaves `answers` null and executes `stay`. The LLM is `invalid` when its text is not
JSON with a string `action`, the action is unknown, or `stop_reason` is not `end_turn`; Jev is
`invalid` when its choice is missing or unknown. Jev is never `gated`. The two Nouls never influence
the move: they are scored against `ground_truth` (same key names) in the report.
```

In the `meta.json` table add these rows after `fly`, and extend the `versions` row:

```markdown
| `models` | object | `{player: model id}` for paid players in the run, e.g. `{"jev": "jev-latest", "llm": "claude-haiku-4-5-20251001"}` |
| `requests` | object | `{player: {max, used}}` for paid players: the `--max-requests` cap and the live requests spent against it, failed ones included. Written when the run ends |
```

```markdown
| `versions` | object | `brian2`, `cython`, `numpy`, `typesafe-sdk`, `anthropic`, `python-dotenv` versions or null |
```

and after the "Added in phase 2" paragraph add:

```markdown
Added in phase 3 without a version bump (additions only): `models`, `requests`, `args.max_requests`,
`args.cache` and the `python-dotenv` entry of `versions`. Readers must treat them as optional.
```

- [ ] **Step 5: `docs/DECISIONS.md`**

Add after decision 10:

```markdown
11. **Paid players (phase 3):** one request per row through a disk cache (sha256 of provider, model,
    senses, questions) and a hard cap per paid player (`--max-requests`, default 0 = replay only).
    SDK retries are off so the cap is exact; a provider failure is a logged error and a `stay`.
    Jev and the LLM are told the same rules in the same words (`bakeoff/players/briefing.py`, ours,
    written before any paid request). No paid request on a seed below 1000 before the tournament.
```

In the Open list, replace the item that starts "Left from the second PR #2 review" with:

```markdown
- Left from the second PR #2 review: the fly data is hashed twice per CLI run (preflight, then
  `Brain`); `SurrogateBrain` raises a bare `KeyError` on a surface file missing a pin field. Done in
  phase 3: `preflight()` runs inside `Runner.run`. Declined: turning a brain exception into a `stay`
  fallback; phase 2 decided a simulator failure must end the run, because a silent `stay` would
  change the fly's score.
```

Replace the "Next step" section body with:

```markdown
Phases 1 to 3 are built. Run the first capped track for each paid player (phase 3 plan, Task 8,
needs the user's go-ahead), then write the phase 4 plan (replay viewer).
```

- [ ] **Step 6: `CLAUDE.md`**

In "Status" replace the last two sentences ("First scoreboard in ... then build it.") with:

```markdown
First scoreboard in `calibration/RESULTS.md`. Phase 3 built (plan:
`docs/superpowers/plans/2026-09-20-phase3-paid-players.md`): `jev` and `llm` players behind
`bakeoff/clients/core.py` (disk cache, hard cap per paid player, no SDK retries). Next: the first
capped track (Task 8 of that plan, needs the user's go-ahead), then the phase 4 plan.
```

and add to "How we work here":

```markdown
- Paid players spend nothing without `--max-requests` (default 0 replays `.cache/responses`). Never
  raise a cap, rerun a paid command or run `pytest -m live` without the user's go-ahead. No paid
  request on a seed below 1000 before the tournament.
```

- [ ] **Step 7: Commit**

```bash
git add tests/test_live.py README.md CLAUDE.md docs/STEP_RECORD.md docs/DECISIONS.md
git commit -F <message file>   # docs: paid players in README, step record and decisions; opt-in live tests
```

---

### Task 8: First capped track and first cost numbers (spends money: controller and user only)

Not for an implementer subagent. The controller runs it with the user present, one command at a time, and stops at the first surprise. Worst case: 2 + 300 + 300 live requests.

**Files:**
- Create: `docs/COSTS.md`
- Modify: `docs/DECISIONS.md`, and `bakeoff/report.py` with `tests/test_report.py` only if Jev turns out to be priced per token

**Interfaces:**
- Consumes: the CLI (Task 5), the report (Task 6), the live tests (Task 7), both keys in the git-ignored key file (the user puts them there; nobody prints them).

- [ ] **Step 1: Ask the user for the go-ahead**

Say what will be spent: 2 requests for the live tests, then at most 300 Jev requests and at most 300 Haiku requests (a 300-row track of about 550 input tokens and 10 output tokens per row is about 0.18 USD for Haiku; Jev's price is what this task finds out). Ask the user to confirm both keys are in place and to note the TypeSafe console's usage or balance **before** the run. Do not continue without a yes.

- [ ] **Step 2: One real request per provider**

Run: `uv run pytest -m live -q -rs`
Expected: `2 passed, 212 deselected`. A skip means a key is missing; a failure shows the provider's error text. Stop and report either.

- [ ] **Step 3: Jev plays practice seed 1000, alone**

Run: `uv run python -m bakeoff run --players jev --seeds 1 --seed-start 1000 --max-requests 300`
Expected: exit 0 and `status: completed` (Jev died or finished within the cap), with `requests` at most 300 in the table. `status: budget_exhausted` cannot happen on one 300-row track; `status: aborted` means more than 5 provider errors in a row: stop and report the `error` text from the last line of `runs/<run_id>/jev.jsonl`.

- [ ] **Step 4: The LLM plays the same track, alone**

Run: `uv run python -m bakeoff run --players llm --seeds 1 --seed-start 1000 --max-requests 300`
Expected: as in Step 3, and a `cost_usd` value in the table.

- [ ] **Step 5: Check the replay is free**

Run: `uv run python -m bakeoff run --players jev,llm --seeds 1 --seed-start 1000`
Expected: exit 0, `requests` 0 and `cache_hits` equal to the rows played for both players, the same `mean_rows` as Steps 3 and 4.

- [ ] **Step 6: Write `docs/COSTS.md`**

Ask the user what the TypeSafe console shows now, and compute Jev's cost per request as the difference divided by the `requests.jev.used` of Step 3's `meta.json` (plus 1 for the live test). Fill this file from the two report tables and that number; every cell is a measured value, and a value that could not be measured is written as `not measured` with the reason:

```markdown
# First measured costs (phase 3)

One track each, practice seed 1000, run alone, SDK retries off. Run ids: `<jev run id>`, `<llm run id>`.

| player | model | rows survived | live requests | mean latency ms | input tokens | output tokens | cost USD | USD per request |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| jev | jev-latest | | | | | | | |
| llm | claude-haiku-4-5-20251001 | | | | | | | |

Jev's cost comes from the TypeSafe console (before and after the run); the LLM's from its tokens at
1.00 / 5.00 USD per million input / output tokens.

## Projection for the tournament

20 seeds, one request per row survived, at most 300 rows: cost <= 20 x 300 x USD per request.
At the rows survived above: about 20 x rows x USD per request. Replays and re-runs are free (cache).

| player | worst case USD | at the measured rows USD |
| --- | --- | --- |
| jev | | |
| llm | | |

## What else the track showed

Solver agreement, invalid and error rates for both, Jev's Brier scores for `gap_ahead` and
`left_safe` (0 is perfect, 0.25 is what always answering 0.5 scores). One track: an impression,
not a result.
```

- [ ] **Step 7: If Jev is billed per token, teach the report its price**

Only if the console prices Jev per token. Add the test to `tests/test_report.py` with the two measured prices in place of `IN` and `OUT`, watch it fail, then add the entry:

```python
def test_jev_cost_uses_its_measured_price():
    from bakeoff.report import PRICES_USD_PER_MTOK

    assert PRICES_USD_PER_MTOK["jev-latest"] == (IN, OUT)
    steps = [step(player="jev", latency_ms=50.0, usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000})]
    (row,) = summarize(steps, {"models": {"jev": "jev-latest"}})
    assert row["cost_usd"] == pytest.approx(IN + OUT)
```

```python
PRICES_USD_PER_MTOK = {"claude-haiku-4-5-20251001": (1.00, 5.00), "jev-latest": (IN, OUT)}
```

and change `test_cost_comes_from_live_tokens_and_the_price_of_the_model_in_meta` so its Jev row expects `pytest.approx((400 * IN + 3 * OUT) / 1_000_000)` instead of `None`. If Jev is billed per request, leave the report alone: its `cost_usd` stays `-` and `docs/COSTS.md` carries the number.

- [ ] **Step 8: Record the outcome and commit**

In `docs/DECISIONS.md`, replace the Open item "Jev pricing and latency ..." with a decision 12 that states the measured USD per request and mean latency for both players and points to `docs/COSTS.md`; set "Next step" to the phase 4 plan. In `CLAUDE.md`, replace "Next: the first capped track ..." with "First costs in `docs/COSTS.md`. Next: write the phase 4 plan (replay viewer)." and drop "Jev's price is still unknown." from the budget bullet.

```bash
uv run pytest -q
git add docs/COSTS.md docs/DECISIONS.md CLAUDE.md bakeoff/report.py tests/test_report.py
git commit -F <message file>   # docs: first measured cost per request for Jev and the LLM
```

Runs and the cache stay git-ignored; the run ids in `docs/COSTS.md` are the paper trail.

---

## Self-review against the spec

- **Players 4 and 5** (one request per row; Choice over four actions with their descriptions; two speculative Nouls with engine ground truth; Haiku with the same JSON senses and structured output; unparseable or unknown answer is `invalid`): Tasks 3 and 4.
- **Fallback rule** (paid player errors, is gated or invalid: `stay`, never the solver): unchanged runner rule; Tasks 3 and 4 produce the `error` and `invalid` that trigger it.
- **`bakeoff/clients/`** (thin clients, shared disk cache keyed by sha256 of provider, model, senses, questions; hard `--max-requests`; keys loaded inside the program): Tasks 2 to 5.
- **`RunAborted` subclass for the cap, guarded `close()`, factory with options, run arguments in `meta.json`**: existing; Task 5 passes `cache=` and `budget=` through `make_player` and records the cap.
- **`meta.json` model ids**: Task 5 (`models`). **Report: requests, tokens, latency, measured cost per run, Noul calibration (Brier)**: Task 6.
- **Testing: fakes, no network, one opt-in `live` test per provider**: Tasks 3, 4 and 7.
- **Budget: phase 3 starts with a single capped track; cache makes re-runs free**: Task 8, Steps 3 to 5.
- Not in this phase: the viewer (phase 4), the tournament (phase 5), and the remaining items under Open in `docs/DECISIONS.md`.
