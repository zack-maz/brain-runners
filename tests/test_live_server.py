"""The loopback server of `bakeoff live`, on an ephemeral port with a broadcast filled by hand.
The only connections are to 127.0.0.1, to the server under test."""

import http.client
import json
import re

import pytest

from bakeoff.live import Broadcast
from bakeoff.live_server import EVENTS_PATH, serve
from bakeoff.view import render_html

REPLAY = {"replay_version": 1, "runs": [{"run_id": "live"}], "players": [], "seeds": [1001], "tracks": {}, "episodes": []}


@pytest.fixture
def server():
    broadcast = Broadcast()
    httpd = serve(render_html(REPLAY, live=EVENTS_PATH), broadcast, port=0)
    yield httpd, broadcast
    broadcast.close()
    httpd.shutdown()
    httpd.server_close()


def get(httpd, path, host=None):
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("GET", path, headers={"Host": host} if host else {})
    response = connection.getresponse()
    body = response.read().decode()
    connection.close()
    return response, body


def test_the_live_page_is_the_player_with_an_empty_replay_and_the_stream_address():
    page = render_html(REPLAY, live=EVENTS_PATH)
    assert '<body data-live="/events">' in page
    assert "data-live" not in render_html(REPLAY)  # a replay file never looks for a server
    (data,) = re.findall(r'<script type="application/json" id="replay-data">(.*?)</script>', page, re.S)
    assert json.loads(data) == REPLAY
    with pytest.raises(ValueError, match="live must be a path"):
        render_html(REPLAY, live='"><script>')


def test_it_binds_to_loopback_only_and_serves_the_page(server):
    httpd, _ = server
    assert httpd.server_address[0] == "127.0.0.1"
    response, body = get(httpd, "/")
    assert response.status == 200 and response.getheader("Content-Type") == "text/html; charset=utf-8"
    assert '<body data-live="/events">' in body and response.getheader("Cache-Control") == "no-store"


def test_the_stream_sends_the_history_as_server_sent_events_and_ends_with_the_run(server):
    httpd, broadcast = server
    broadcast.emit("episode", {"episode": {"player": "fly"}, "track": {"seed": 1001}})
    broadcast.emit("frame", {"player": "fly", "seed": 1001, "frame": {"row": 0, "answers": {"text": "line\nbreak </script>"}}})
    broadcast.emit("end", {"status": "completed"})
    broadcast.close()
    response, body = get(httpd, EVENTS_PATH)
    assert response.status == 200 and response.getheader("Content-Type") == "text/event-stream"
    assert response.getheader("Access-Control-Allow-Origin") is None  # other origins cannot read the stream
    events = [block.split("\n") for block in body.strip().split("\n\n")]
    assert [lines[0] for lines in events] == ["event: episode", "event: frame", "event: end"]
    assert all(len(lines) == 2 and lines[1].startswith("data: ") for lines in events)  # one line each, whatever the log says
    assert json.loads(events[1][1][6:])["frame"]["answers"]["text"] == "line\nbreak </script>"


def test_the_port_can_be_bound_before_the_page_exists():
    httpd = serve(None, Broadcast(), port=0)
    try:
        assert get(httpd, "/")[0].status == 503
        httpd.page = "<p>ready</p>"
        assert get(httpd, "/")[1] == "<p>ready</p>"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_nothing_else_is_served(server):
    httpd, _ = server
    assert get(httpd, "/runs/")[0].status == 404
    assert get(httpd, "/../pyproject.toml")[0].status == 404
    assert get(httpd, "/", host="evil.example")[0].status == 403  # a rebound DNS name is not us
    assert get(httpd, "/", host=f"localhost:{httpd.server_address[1]}")[0].status == 200
    connection = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=5)
    connection.request("POST", "/", body="x")
    assert connection.getresponse().status == 501
    connection.close()
