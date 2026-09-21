"""The lockstep loop of `bakeoff live`, with scripted players. No network, no fly brain."""

import json

import pytest

from bakeoff.errors import BudgetExhausted
from bakeoff.live import Broadcast, LiveRun
from bakeoff.players import make_player
from bakeoff.players.base import Decision
from bakeoff.replay import build_replay
from bakeoff.report import load_steps


class Scripted:
    """Always the same move; optionally stops like a paid player whose cap is reached."""

    def __init__(self, name, action, cap=None, error=None):
        self.name, self.action, self.cap, self.error, self.asked, self.closed = name, action, cap, error, 0, False

    def reset(self, game, seed): pass

    def act(self, senses):
        if self.cap is not None and self.asked >= self.cap:
            raise BudgetExhausted(f"request cap of {self.cap} reached")
        self.asked += 1
        if self.error:
            return Decision(None, error=self.error, questions={"q": 1})
        return Decision(self.action, questions={"q": 1})

    def observe(self, executed_action): pass

    def close(self): self.closed = True


def events_of(live):
    return list(e for e in live.broadcast.listen(poll_seconds=0.01) if e is not None)


def run_live(tmp_path, players, max_rows=40, seed=1001):
    live = LiveRun(players, seed, out_root=tmp_path, max_rows=max_rows, run_id="live", args={"port": 0})
    live.run()
    return live, events_of(live)


def test_everyone_plays_the_same_track_in_lockstep_and_a_jumper_skips_a_row(tmp_path):
    live, events = run_live(tmp_path, [make_player("solver"), Scripted("jumper", "jump"), Scripted("stayer", "stay")])
    frames = [(data["frame"]["row"], data["player"]) for name, data in events if name == "frame"]
    assert [row for row, _ in frames] == sorted(row for row, _ in frames)  # nobody decides row 5 before everybody decided row 4
    assert [row for row, player in frames if player == "jumper"][:4] == [0, 2, 4, 6]  # in the air over the odd rows
    assert [player for row, player in frames if row == 0] == ["solver", "jumper", "stayer"]  # the order given
    tracks = [data["track"] for name, data in events if name == "episode"]
    assert len(tracks) == 3 and tracks[0] == tracks[1] == tracks[2] and tracks[0]["seed"] == 1001


def test_the_stream_is_the_replay_in_the_replays_own_shapes(tmp_path):
    live, events = run_live(tmp_path, [make_player("solver"), Scripted("stayer", "stay")])
    replay = build_replay([live.run_dir])  # what `bakeoff view` would show afterwards
    for episode in replay["episodes"]:
        name = episode["player"]
        (header,) = [d for n, d in events if n == "episode" and d["episode"]["player"] == name]
        sent = [d for n, d in events if n == "frame" and d["player"] == name]
        assert [d["frame"] for d in sent] == episode["frames"]
        assert sent[-1]["summary"] == {k: episode[k] for k in ("complete", "finished", "death_cause", "rows_survived")}
        assert header["episode"]["questions"] == episode["questions"] and header["episode"]["max_rows"] == 40
        assert header["track"] == replay["tracks"]["1001"]
        assert set(header["episode"]) == set(episode) - {"frames"}
    assert events[0][0] == "episode" and events[1][0] == "frame"  # a runner is announced, then it moves
    name, end = events[-1]
    assert name == "end" and end == {"status": "completed", "runs": replay["runs"], "scoreboard": replay["scoreboard"]}
    json.dumps(events)


def test_the_directory_is_a_normal_completed_run(tmp_path):
    live, _ = run_live(tmp_path, [make_player("solver"), Scripted("stayer", "stay")])
    meta = json.loads((live.run_dir / "meta.json").read_text())
    assert meta["status"] == "completed" and meta["finished_at"] and meta["players"] == ["solver", "stayer"]
    assert meta["seeds"] == [1001] and meta["args"] == {"port": 0} and meta["game"]["max_rows"] == 40
    steps = load_steps(live.run_dir)
    finals = {p: [s for s in steps if s["player"] == p][-1] for p in ("solver", "stayer")}
    assert finals["solver"]["finished"] and finals["solver"]["rows_survived"] == 40
    assert not finals["stayer"]["alive"] and finals["stayer"]["death_cause"] == "ran_into_gap"
    assert all(p.closed for p in live.players if hasattr(p, "closed"))


def test_a_cap_stops_everyone_and_leaves_a_valid_incomplete_run(tmp_path):
    capped = Scripted("paid", "stay", cap=3)
    live, events = run_live(tmp_path, [make_player("solver"), capped])
    assert live.status == "budget_exhausted" and live.error == "request cap of 3 reached"
    assert [name for name, _ in events[-2:]] == ["error", "end"]
    assert events[-2][1] == {"message": "request cap of 3 reached"} and events[-1][1]["status"] == "budget_exhausted"
    assert json.loads((live.run_dir / "meta.json").read_text())["status"] == "budget_exhausted"
    replay = build_replay([live.run_dir])
    assert [(e["player"], e["complete"], len(e["frames"])) for e in replay["episodes"]] == [("solver", False, 4), ("paid", False, 3)]
    assert capped.closed


def test_a_provider_that_keeps_failing_aborts_the_run(tmp_path):
    live, events = run_live(tmp_path, [Scripted("paid", "stay", error="HTTPError: 503")])
    assert live.status == "aborted" and "6 consecutive player errors" in events[-2][1]["message"]


def test_ctrl_c_is_an_interrupted_run_not_a_crash(tmp_path):
    class Interrupting(Scripted):
        def act(self, senses):
            if self.asked == 2:
                raise KeyboardInterrupt
            return super().act(senses)

    live, events = run_live(tmp_path, [Interrupting("fly", "stay")])
    assert live.status == "interrupted" and events[-1][0] == "end" and events[-1][1]["status"] == "interrupted"
    assert len(load_steps(live.run_dir)) == 2


def test_our_own_bug_still_closes_the_run_and_is_raised(tmp_path):
    class Buggy(Scripted):
        def act(self, senses): raise RuntimeError("our bug")

    live = LiveRun([Buggy("b", "stay")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    with pytest.raises(RuntimeError, match="our bug"):
        live.run()
    assert json.loads((live.run_dir / "meta.json").read_text())["status"] == "interrupted" and live.broadcast.closed


def test_prepare_gives_the_page_an_empty_replay_that_names_the_run(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    replay = live.prepare()
    assert replay["episodes"] == [] and replay["seeds"] == [1001] and replay["scoreboard"]["rows"] == []
    (run,) = replay["runs"]
    assert run["run_id"] == "live" and run["status"] == "running" and run["game"]["lookahead"] == 6
    assert (live.run_dir / "meta.json").is_file()


def test_usage_errors_leave_no_directory(tmp_path):
    with pytest.raises(ValueError, match="duplicate player names"):
        LiveRun([make_player("solver"), make_player("solver")], 1001, out_root=tmp_path)

    class Unready(Scripted):
        def preflight(self): raise ValueError("TYPESAFE_API_KEY is not set")

    live = LiveRun([Unready("paid", "stay")], 1001, out_root=tmp_path, run_id="live")
    with pytest.raises(ValueError, match="paid: TYPESAFE_API_KEY is not set"):
        live.prepare()
    assert not (tmp_path / "live").exists()


def test_a_late_listener_gets_the_whole_history_and_a_quiet_one_gets_keep_alives():
    broadcast = Broadcast()
    broadcast.emit("frame", {"n": 1})
    listener = broadcast.listen(poll_seconds=0.01)
    assert next(listener) == ("frame", {"n": 1})
    assert next(listener) is None  # nothing new: time for a keep-alive
    broadcast.emit("end", {"status": "completed"})
    broadcast.close()
    assert list(listener) == [("end", {"status": "completed"})]
    assert list(broadcast.listen()) == [("frame", {"n": 1}), ("end", {"status": "completed"})]


def test_cancelling_before_the_run_began_leaves_an_interrupted_run_with_no_logs(tmp_path):
    live = LiveRun([make_player("solver")], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    live.prepare()
    live.cancel()
    meta = json.loads((live.run_dir / "meta.json").read_text())
    assert meta["status"] == "interrupted" and meta["finished_at"] and live.broadcast.closed
    assert list(live.run_dir.glob("*.jsonl")) == []


def test_an_event_is_a_snapshot_later_decisions_do_not_change_what_was_already_sent(tmp_path):
    class TwoQuestions(Scripted):
        def act(self, senses):
            decision = super().act(senses)
            decision.questions = {"q": self.asked}  # a new question set with every decision
            return decision

    live = LiveRun([TwoQuestions("paid", "stay", cap=3)], 1001, out_root=tmp_path, max_rows=20, run_id="live")
    listener = live.broadcast.listen(poll_seconds=0.01)
    seen = []
    original_emit = live.broadcast.emit

    def emit(name, data):  # what a listener that reads at once would have serialised
        original_emit(name, data)
        seen.append(json.dumps(next(listener)))

    live.broadcast.emit = emit
    live.run()
    first = json.loads(seen[0])
    assert first[0] == "episode" and first[1]["episode"]["questions"] == [{"q": 1}]
    assert json.dumps(list(live.broadcast.listen(poll_seconds=0.01))[0]) == seen[0]  # and history still says the same


def test_a_listener_that_has_gone_is_no_longer_counted():
    broadcast = Broadcast()
    listener = broadcast.listen(poll_seconds=0.01)
    assert broadcast.listeners == 0  # nobody listens until the first event is asked for
    next(listener)
    assert broadcast.listeners == 1
    listener.close()  # the page was closed
    assert broadcast.listeners == 0
    broadcast.close()
    assert list(broadcast.listen()) == [] and broadcast.listeners == 0
