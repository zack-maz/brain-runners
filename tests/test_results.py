"""The results screen's numbers (bakeoff/results.py), from real run directories played by free and scripted
players. No network, no fly brain."""

import json

from bakeoff.game.rules import V1
from bakeoff.live import LiveRun
from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.results import results_of
from bakeoff.session import PRICE_USD
from tests.test_replay import record


class Scripted:
    """Always the same move, as a paid player named `name` would log it (latency, no cache hit)."""

    def __init__(self, name, action):
        self.name, self.action = name, action

    def reset(self, game, seed): pass

    def act(self, senses):
        return Decision(self.action, questions={"q": 1}, latency_ms=100.0)

    def observe(self, executed_action): pass

    def close(self): pass


def play(tmp_path, players, seed=1001, run_id="r1"):
    live = LiveRun(players, seed, out_root=tmp_path, rules=V1, max_rows=40, run_id=run_id)
    live.run()
    return live.run_dir


def test_one_entry_per_player_in_the_runs_order_with_how_its_track_ended(tmp_path):
    out = results_of(play(tmp_path, [make_player("solver"), Scripted("stayer", "stay")]))
    assert out["run_id"] == "r1" and out["status"] == "completed" and out["seeds"] == [1001]
    assert out["game"] == {"version": "v1", "max_rows": 40}
    solver, stayer = out["players"]
    assert (solver["player"], stayer["player"]) == ("solver", "stayer")
    assert solver["tracks"] == [{"seed": 1001, "rows": 40, "complete": True, "finished": True, "death_cause": None,
                                 "trapped": False, "fatal": None}]
    (track,) = stayer["tracks"]
    assert track["complete"] and not track["finished"] and track["death_cause"] == "ran_into_gap"
    # the fatal move, named: the row it died on, what it did, and what would have gone furthest instead
    assert track["fatal"]["row"] == track["rows"] and track["fatal"]["move"] == "stay"
    assert track["fatal"]["safe"] and "stay" not in track["fatal"]["safe"]
    assert track["rows"] == stayer["mean_rows"] < 40
    assert stayer["fatal_wrong_moves"] == 1 and stayer["wrong_moves"] >= 1  # the solver would have lived
    assert solver["wrong_moves"] == 0
    json.dumps(out)


def test_cost_is_live_requests_at_the_pages_price_and_free_players_cost_nothing(tmp_path):
    out = results_of(play(tmp_path, [make_player("random"), Scripted("haiku_step1", "stay")]))
    random_, haiku = out["players"]
    assert (random_["paid"], random_["price_usd"], random_["cost_estimate_usd"]) == (False, 0.0, 0.0)
    assert haiku["paid"] and haiku["price_usd"] == PRICE_USD["haiku_step1"]
    assert haiku["requests"] > 0
    assert haiku["cost_estimate_usd"] == haiku["requests"] * PRICE_USD["haiku_step1"]
    assert haiku["s_per_row"] is not None  # 100 ms a live decision


def test_a_stopped_run_keeps_its_players_rows_and_is_not_a_death(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, rules=V1, max_rows=40, run_id="stopped")
    live.prepare()
    live.cancel()  # given up before the first decision
    out = results_of(live.run_dir)
    assert out["status"] == "interrupted"
    (solver,) = out["players"]
    assert solver["tracks"] == [] and solver["runs"] == 0 and solver["s_per_row"] is None


def test_cost_estimate_uses_what_meta_json_says_was_spent_over_what_was_answered(tmp_path):
    """M4: a `ProviderError` step spends a request but logs no latency, so `requests` (steps actually
    answered) undercounts what the budget really spent. meta.json's own `requests[player].used`, when
    present, is the one that must be billed."""
    run_dir = tmp_path / "spent"
    run_dir.mkdir()
    step = record(player="haiku_step1", seed=1000, row=0, finished=True, latency_ms=120.0, cache_hit=False)
    (run_dir / "haiku_step1.jsonl").write_text(json.dumps(step) + "\n")
    (run_dir / "meta.json").write_text(json.dumps({"run_id": "spent", "status": "completed",
                                                    "players": ["haiku_step1"], "seeds": [1000],
                                                    "requests": {"haiku_step1": {"used": 5}}}))
    (haiku,) = results_of(run_dir)["players"]
    assert haiku["requests"] == 1 and haiku["spent"] == 5  # one step answered; five were really spent
    assert haiku["cost_estimate_usd"] == 5 * PRICE_USD["haiku_step1"]


def test_a_death_where_every_move_falls_is_trapped(tmp_path):
    run_dir = tmp_path / "hand"
    run_dir.mkdir()
    base = {"player": "p", "seed": 1000, "chosen_action": "stay", "executed_action": "stay", "gated": False,
            "invalid": False, "error": None, "latency_ms": None, "usage": None, "cache_hit": False, "finished": False,
            "death_cause": None}
    steps = [{**base, "row": 0, "alive": True, "rows_survived": 0, "solver_depths": {"stay": 1, "left": 0, "right": 0,
                                                                                     "jump": 3}},
             {**base, "row": 1, "alive": False, "rows_survived": 1, "death_cause": "ran_into_gap",
              "solver_depths": {"stay": 0, "left": 0, "right": 0, "jump": 0}}]
    (run_dir / "p.jsonl").write_text("".join(json.dumps(s) + "\n" for s in steps))
    (player,) = results_of(run_dir)["players"]
    assert player["tracks"][0]["trapped"] is True and player["tracks"][0]["fatal"] is None
    assert player["fatal_wrong_moves"] == 0 and player["wrong_moves"] == 1  # the wrong move was row 0's stay
