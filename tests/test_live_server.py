"""The loopback server of `bakeoff live`, on an ephemeral port with a session of free players.
The only connections are to 127.0.0.1, to the server under test."""

import http.client
import json
import re
import socket
import struct
import threading
import time

import pytest

from bakeoff.game.rules import rules_for
from bakeoff.live import Broadcast, LiveRun
from bakeoff.live_server import EVENTS_PATH, TOKEN_HEADER, serve
from bakeoff.session import LiveSession
from bakeoff.view import render_html
from tests.fakes import slow_player

REPLAY = {"replay_version": 1, "runs": [{"run_id": "live"}], "players": [], "seeds": [1001], "tracks": {}, "episodes": []}
RULES = rules_for("v2").variant(max_rows=12)


@pytest.fixture
def server(tmp_path):
    session = LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", token="tok-123")
    httpd = serve(render_html(REPLAY, live=EVENTS_PATH, token=session.token), session, port=0)
    yield httpd, session
    if session.run is not None:
        session.run.stop()
    session.wait(30)
    httpd.shutdown()
    httpd.server_close()


def call(httpd, method, path, body=None, host=None, token="tok-123"):
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
    headers = {}
    if host:
        headers["Host"] = host
    if token is not None:
        headers[TOKEN_HEADER] = token
    connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    response = connection.getresponse()
    text = response.read().decode()
    connection.close()
    return response, text


def httpd_of(server):
    return server[0]


def get(httpd, path, host=None, token="tok-123"):
    return call(httpd, "GET", path, host=host, token=token)


def payload(httpd, method, path, body=None, token="tok-123"):
    response, text = call(httpd, method, path, body, token=token)
    return response.status, json.loads(text)


def test_the_live_page_is_the_player_with_an_empty_replay_the_stream_address_and_the_token():
    page = render_html(REPLAY, live=EVENTS_PATH, token="tok-123")
    assert '<body data-live="/events" data-token="tok-123">' in page
    assert "data-live" not in render_html(REPLAY)  # a replay file never looks for a server
    (data,) = re.findall(r'<script type="application/json" id="replay-data">(.*?)</script>', page, re.S)
    assert json.loads(data) == REPLAY
    with pytest.raises(ValueError, match="live must be a path"):
        render_html(REPLAY, live='"><script>')
    with pytest.raises(ValueError, match="token must be url-safe"):
        render_html(REPLAY, live=EVENTS_PATH, token='"><script>')


def test_it_binds_to_loopback_only_and_serves_the_page(server):
    httpd, _ = server
    assert httpd.server_address[0] == "127.0.0.1"
    response, body = get(httpd, "/")
    assert response.status == 200 and response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert '<body data-live="/events"' in body and response.getheader("Cache-Control") == "no-store"


def test_the_control_routes_need_the_token_but_the_page_itself_does_not(server):
    httpd, _ = server
    assert get(httpd, "/", token=None)[0].status == 200  # the page carries the token to the page
    assert get(httpd, "/state", token=None)[0].status == 403
    assert get(httpd, "/state", token="guessed")[0].status == 403
    assert call(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]}, token=None)[0].status == 403
    assert call(httpd, "POST", "/cancel", {}, token="guessed")[0].status == 403
    assert get(httpd, EVENTS_PATH, token=None)[0].status == 403
    assert get(httpd, "/state")[0].status == 200


def test_state_says_what_can_be_run(server):
    httpd, _ = server
    status, state = payload(httpd, "GET", "/state?seed=1001")
    assert status == 200 and state["status"] == "lobby" and state["seed"] == 1001
    assert state["game"]["version"] == "v2" and state["max_rows"] == 12
    assert {p["name"] for p in state["players"]} >= {"solver", "fly", "haiku_plain", "jev_step1"}
    assert [p["requests_left"] for p in state["players"] if p["name"] == "haiku_plain"] == [0]


def test_an_oversized_seed_answers_200_with_no_seed_not_a_crash(server):
    """str.isdigit() is true of a seed `int()` refuses (M2): a 4,300+ digit string is "digits" but
    int() raises past Python's conversion limit, uncaught before this fix. The regex caps it at 9 digits."""
    httpd, _ = server
    status, state = payload(httpd, "GET", f"/state?seed={'9' * 5000}")
    assert status == 200 and state["seed"] is None


def test_a_run_started_from_the_page_streams_its_frames_and_ends_in_the_lobby(server):
    httpd, session = server
    status, started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})
    # the snapshot is taken after the run began, and a 12-row run of two free players may already be
    # over by then: what the reply promises is the run, not that it is still going
    assert status == 200 and started["ok"] is True
    assert started["state"]["status"] in ("running", "finished")
    assert started["state"]["run"]["run_id"] == started["run_id"]
    assert started["state"]["run"]["replay"]["seeds"] == [1001]  # what the page resets itself to
    assert started["state"]["run"]["replay"]["runs"][0]["run_id"] == started["run_id"]
    session.wait(30)  # the whole run, so the history the stream replays is settled and the read cannot race
    response, body = get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")
    assert response.status == 200 and response.getheader("Content-Type") == "text/event-stream"
    assert response.getheader("Access-Control-Allow-Origin") is None  # other origins cannot read the stream
    kinds = [line[7:] for line in body.split("\n") if line.startswith("event: ")]
    assert kinds[0] == "episode" and kinds[-1] == "end" and "frame" in kinds
    assert payload(httpd, "GET", "/state")[1]["run"]["status"] == "completed"
    # and the stream of a finished run can still be replayed from its history, by name
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")[0].status == 200
    assert get(httpd, f"{EVENTS_PATH}?run=20200101-000000")[0].status == 404


def test_a_refusal_names_its_reason_and_starts_nothing(server):
    httpd, session = server
    status, refused = payload(httpd, "POST", "/run", {"seed": 7, "players": ["solver", "haiku_plain"]})
    assert status == 409 and refused["ok"] is False
    assert "seeds below 1000" in refused["error"] and session.run is None
    status, refused = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["nobody"]})
    assert status == 409 and "unknown player 'nobody'" in refused["error"]
    status, refused = payload(httpd, "POST", "/cancel", {})
    assert status == 409 and refused["error"] == "no run is going"
    assert not (session.out_root.exists() and any(session.out_root.iterdir()))


def test_cancel_stops_the_run_that_is_going(server, monkeypatch):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": [slow_player(monkeypatch)]})[1]
    status, stopped = payload(httpd, "POST", "/cancel", {})
    assert status == 200 and stopped["ok"] is True
    session.wait(30)
    meta = json.loads((session.out_root / started["run_id"] / "meta.json").read_text())
    assert meta["status"] == "interrupted"


def test_the_port_can_be_bound_before_the_page_exists(tmp_path):
    session = LiveSession(RULES, out_root=tmp_path / "runs", cache_dir=tmp_path / "cache", token="tok-123")
    httpd = serve(None, session, port=0)
    try:
        assert get(httpd, "/")[0].status == 503
        httpd.page = "<p>ready</p>"
        assert get(httpd, "/")[1] == "<p>ready</p>"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_stream_sends_the_history_as_server_sent_events_and_ends_with_the_run(server):
    httpd, session = server
    run = LiveRun([], 1001, out_root=session.out_root, rules=RULES, run_id="handmade", broadcast=Broadcast())
    session.finished.append(run)
    run.broadcast.emit("episode", {"episode": {"player": "fly"}, "track": {"seed": 1001}})
    run.broadcast.emit("frame", {"player": "fly", "seed": 1001, "frame": {"row": 0, "answers": {"text": "line\nbreak </script>"}}})
    run.broadcast.emit("end", {"status": "completed"})
    run.broadcast.close()
    response, body = get(httpd, f"{EVENTS_PATH}?run=handmade")
    assert response.status == 200
    events = [block.split("\n") for block in body.strip().split("\n\n")]
    assert [lines[0] for lines in events] == ["event: episode", "event: frame", "event: end"]
    assert all(len(lines) == 2 and lines[1].startswith("data: ") for lines in events)  # one line each, whatever the log says
    assert json.loads(events[1][1][6:])["frame"]["answers"]["text"] == "line\nbreak </script>"


def test_the_stream_takes_the_token_in_the_query_because_an_event_source_sends_no_headers(server):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]})[1]
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}&token=tok-123", token=None)[0].status == 200
    assert get(httpd, f"{EVENTS_PATH}?run={started['run_id']}&token=wrong", token=None)[0].status == 403


def test_the_query_token_is_taken_by_the_event_stream_alone(server):
    """An EventSource cannot send headers, so the stream takes `?token=`. Nothing else does: a token in
    a URL ends up in places a header does not."""
    assert get(httpd_of(server), "/state?token=tok-123", token=None)[0].status == 403
    assert call(httpd_of(server), "POST", "/run?token=tok-123",
                {"seed": 1001, "players": ["solver"]}, token=None)[0].status == 403


def test_nothing_else_is_served(server):
    httpd, _ = server
    assert get(httpd, "/runs/")[0].status == 404
    assert get(httpd, "/../pyproject.toml")[0].status == 404
    assert call(httpd, "POST", "/anything", {})[0].status == 404
    assert get(httpd, "/", host="evil.example")[0].status == 403  # a rebound DNS name is not us
    assert get(httpd, "/", host=f"localhost:{httpd.server_address[1]}")[0].status == 200
    assert call(httpd, "POST", "/run", host="evil.example", body={"seed": 1001, "players": ["solver"]})[0].status == 403
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("PUT", "/state", body="x")
    assert connection.getresponse().status == 501
    connection.close()


def test_a_request_that_is_not_json_is_a_refusal_not_a_crash(server):
    httpd, _ = server
    response, text = call(httpd, "POST", "/run", None)  # no body at all: a refusal naming what is missing
    assert response.status == 409 and "the track must be a whole number" in json.loads(text)["error"]
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("POST", "/run", body="not json", headers={TOKEN_HEADER: "tok-123"})
    response = connection.getresponse()
    assert response.status == 400 and "not JSON" in json.loads(response.read())["error"]
    connection.close()


def test_the_end_of_a_live_run_carries_the_benchmark_of_what_was_just_played(server):
    """The page has no numbers of its own: the server scores the run it just recorded and sends them
    with the end event, so the Analysis tab fills in without a reload (decision 36)."""
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})[1]
    session.wait(30)
    body = get(httpd, f"{EVENTS_PATH}?run={started['run_id']}")[1]
    blocks = [b.split("\n") for b in body.strip().split("\n\n")]
    end = json.loads(next(lines[1][6:] for lines in blocks if lines[0] == "event: end"))
    assert {p["player"] for p in end["bench"]["players"]} == {"solver", "random"}
    assert end["bench"]["players"][0]["seeds"] == 1  # one track: enough to score, never enough to rank
    assert all(p["ranked"] is False for p in end["bench"]["players"])


def test_what_was_recorded_is_served_behind_the_token(server):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver", "random"]})[1]
    session.wait(30)
    run_id = started["run_id"]
    status, results = payload(httpd, "GET", f"/results?run={run_id}")
    assert status == 200 and [p["player"] for p in results["players"]] == ["solver", "random"]
    status, replay = payload(httpd, "GET", f"/replay?run={run_id}")
    assert status == 200 and replay["runs"][0]["run_id"] == run_id
    status, records = payload(httpd, "GET", "/records")
    assert status == 200 and [r["run_id"] for r in records["runs"]] == [run_id]
    status, charts = payload(httpd, "GET", "/charts")
    assert status == 200 and {p["player"] for p in charts["bench"]["players"]} == {"solver", "random"}
    assert charts["scope"] == "all" and payload(httpd, "GET", "/charts?scope=all")[1]["scope"] == "all"
    status, held_out = payload(httpd, "GET", "/charts?scope=held_out")  # track 1001 is not a held-out one
    assert status == 200 and held_out["scope"] == "held_out" and held_out["bench"] is None
    assert payload(httpd, "GET", "/charts?scope=practice")[0] == 400
    status, writeup = payload(httpd, "GET", "/writeup")
    assert status == 200 and writeup["draft"] is True and "<article" in writeup["html"]
    for path in (f"/results?run={run_id}", f"/replay?run={run_id}", "/records", "/charts", "/writeup"):
        assert get(httpd, path, token=None)[0].status == 403
        assert get(httpd, path, token="wrong")[0].status == 403


def test_a_run_that_is_not_a_recorded_run_directory_is_not_found(server):
    httpd, _ = server
    for path in ("/results", "/results?run=", "/results?run=..%2F..%2Fpyproject.toml", "/replay?run=../cache",
                 "/replay?run=20990101-000000"):
        assert get(httpd, path)[0].status == 404, path


def test_a_run_directory_that_cannot_be_read_is_an_error_that_says_why(server):
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]})[1]
    session.wait(30)
    log = session.run_dir_of(started["run_id"]) / "solver.jsonl"
    log.write_text("not json\n" + log.read_text())  # broken before its last line: not a truncated tail
    status, body = payload(httpd, "GET", f"/results?run={started['run_id']}")
    assert status == 500 and body["ok"] is False and "cannot read that run" in body["error"]


def test_a_keyless_record_answers_with_a_500_and_a_reason_not_a_dropped_connection(server):
    """A record that parses but is not one of ours raises something other than OSError or ValueError deep
    inside results_of (I3): the page must still get a reasoned 500, never a closed socket."""
    httpd, session = server
    started = payload(httpd, "POST", "/run", {"seed": 1001, "players": ["solver"]})[1]
    session.wait(30)
    log = session.run_dir_of(started["run_id"]) / "solver.jsonl"
    log.write_text(json.dumps({"player": "solver", "seed": 1001}) + "\n")  # parses; no "row"
    status, body = payload(httpd, "GET", f"/results?run={started['run_id']}")
    assert status == 500 and body["ok"] is False and "cannot read that run" in body["error"]


def test_a_page_that_hangs_up_before_its_answer_is_dropped_quietly(server, capsys, monkeypatch):
    """A reload while the charts are being worked out: the answer has nowhere to go, and the terminal is not
    filled with tracebacks for it (nor with a 500 sent down the same closed connection)."""
    httpd, session = server
    asked, release = threading.Event(), threading.Event()

    def slow_charts(scope=None):
        asked.set()
        release.wait(5)
        return {"bench": None, "why": "x"}

    monkeypatch.setattr(session, "charts", slow_charts)
    sock = socket.create_connection(("127.0.0.1", httpd.server_address[1]), timeout=5)
    port = httpd.server_address[1]
    sock.sendall(f"GET /charts HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n{TOKEN_HEADER}: tok-123\r\n\r\n".encode())
    assert asked.wait(5)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))  # close with a reset
    sock.close()
    release.set()
    for _ in range(250):  # until the handler thread has written, failed and finished
        if not any("process_request" in t.name for t in threading.enumerate()):
            break
        time.sleep(0.02)
    assert "Traceback" not in capsys.readouterr().err
    assert get(httpd, "/state")[0].status == 200  # and it keeps serving
