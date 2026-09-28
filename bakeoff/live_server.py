"""The server of `bakeoff live`: loopback only, standard library only. It serves the player page, the
control channel the page drives the session with, and the event stream (Server-Sent Events), and
nothing else: no files, no other method, no other host.

Every request but the page itself carries the session's token, minted at startup and embedded in the
page, so no page in this browser but ours can drive the run (another tab, or a site that knows the port,
has no way to read the token). It is not a defence against a program on this machine: anything that may
read `GET /` may read the token out of the page, as anything that may read the run directory may read
the run.

| route | what it does |
| --- | --- |
| `GET /`            | the page |
| `GET /state`       | what can be run: players, prices, budgets, the seed rule, and what is happening now |
| `POST /run`        | `{seed, players}`: start a run, or refuse and name the reason |
| `POST /cancel`     | stop the run that is going |
| `GET /events`      | the frames of a run, Server-Sent Events (`?run=<run_id>`) |
| `GET /results`     | the results of a recorded run (`?run=<run_id>`), for the results screen |
| `GET /records`     | the past runs, for the records screen |
| `GET /charts`      | the study's numbers over every recorded track, for the charts screen |
| `GET /replay`      | the replay of a recorded run (`?run=<run_id>`), for Records' Watch |
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bakeoff.session import LiveSession, LobbyError

EVENTS_PATH = "/events"
HOST = "127.0.0.1"
TOKEN_HEADER = "X-Bakeoff-Token"
MAX_BODY = 64 * 1024  # a lobby request is a few hundred bytes; anything larger is not ours
# a `?seed=` worth trying to parse: str.isdigit() is also true of non-ASCII digits and of strings past
# int()'s own conversion limit, either of which used to reach int() uncaught
SEED = re.compile(r"[0-9]{1,9}")


def serve(page: str | None, session: LiveSession, port: int = 8000) -> ThreadingHTTPServer:
    """Starts serving in a daemon thread and returns the server (`shutdown()` stops it). Port 0 picks a
    free one. The port is bound before anything is written to disk, so the page may come later: set
    `server.page`; until then `/` answers 503."""

    class Handler(BaseHTTPRequestHandler):
        # ---- the checks every request goes through ------------------------------------------
        def _ours(self) -> bool:
            names = {f"{HOST}:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}"}
            if self.headers.get("Host") in names:
                return True
            self.send_error(403)  # a page elsewhere that points a DNS name at us gets nothing
            return False

        def _token(self) -> bool:
            """The token is in the header, and in `token=` for the event stream alone, because an
            EventSource sends no headers. A wrong one is 403. The query form is kept to the stream so
            the token stays out of the places a URL ends up."""
            sent = self.headers.get(TOKEN_HEADER)
            if sent is None and self._route == EVENTS_PATH:
                sent = self._query().get("token")
            if sent == self.server.session.token:
                return True
            self.send_error(403)
            return False

        def _query(self) -> dict:
            _, _, query = self.path.partition("?")
            out = {}
            for part in query.split("&"):
                key, _, value = part.partition("=")
                if key:
                    out[key] = value
            return out

        @property
        def _route(self) -> str:
            return self.path.partition("?")[0]

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                raise ValueError("the request is too large")
            try:
                return json.loads(self.rfile.read(length) or b"{}")
            except ValueError as e:
                raise ValueError(f"the request is not JSON: {e}") from e

        def _json(self, payload: dict, status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        # ---- the routes ----------------------------------------------------------------------
        def do_GET(self):  # noqa: N802 (the base class names it)
            if not self._ours():
                return
            if self._route == "/":
                self._page()
            elif self._route == "/state":
                if self._token():
                    seed = self._query().get("seed")
                    self._json(self.server.session.state(int(seed) if seed and SEED.fullmatch(seed) else None))
            elif self._route == EVENTS_PATH:
                if self._token():
                    self._events()
            elif self._route in ("/results", "/records", "/charts", "/replay"):
                if self._token():
                    self._recorded()
            else:
                self.send_error(404)

        def do_POST(self):  # noqa: N802
            if not self._ours():
                return
            if self._route not in ("/run", "/cancel"):
                return self.send_error(404)
            if not self._token():
                return
            try:
                body = self._body()
                if self._route == "/cancel":
                    self.server.session.cancel()
                    return self._json({"ok": True, "state": self.server.session.state()})
                started = self.server.session.start(body.get("seed"), list(body.get("players") or []))
                # the state carries the run's empty replay, so the page has one way in whoever started it
                self._json({"ok": True, "run_id": started.run.run_id,
                            "state": self.server.session.state(started.run.seed)})
            except LobbyError as e:
                self._json({"ok": False, "error": str(e)}, status=409)  # a refusal, not a crash
            except (ValueError, TypeError) as e:
                self._json({"ok": False, "error": str(e)}, status=400)
            except OSError as e:  # the run directory could not be made: nothing was started
                self._json({"ok": False, "error": f"cannot start the run: {e}"}, status=500)

        def _recorded(self) -> None:
            """What was recorded: files only, nothing spent. A run that is not a recorded run is a 404; a run
            directory that cannot be read is a 500 that says why, so the page can say it too."""
            session = self.server.session
            try:
                if self._route == "/records":
                    return self._json(session.records())
                if self._route == "/charts":
                    return self._json(session.charts())
                wanted = self._query().get("run")
                out = session.results(wanted) if self._route == "/results" else session.replay(wanted)
            except (OSError, ValueError) as e:
                return self._json({"ok": False, "error": f"cannot read that run: {e}"}, status=500)
            except Exception as e:  # a record that parses but is not one of ours: still a reason, not a hangup
                return self._json({"ok": False, "error": f"cannot read that run: {e!r}"}, status=500)
            if out is None:
                return self.send_error(404)
            self._json(out)

        def _page(self) -> None:
            if self.server.page is None:
                return self.send_error(503)
            body = self.server.page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _events(self) -> None:
            """The frames of one run. `?run=<run_id>` picks it: the page opens a stream per run, so a
            stream never runs on into the next one. Without it, the run going now (or the last one)."""
            wanted = self._query().get("run")
            run = self.server.session.find(wanted)
            if run is None:
                return self.send_error(404)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                for event in run.broadcast.listen():
                    if event is None:
                        self.wfile.write(b": keep-alive\n\n")
                    else:
                        name, data = event  # json.dumps escapes every newline, so an event is always two lines
                        self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the page was closed

        def log_message(self, format, *args):  # noqa: A002
            pass  # the terminal belongs to the run's own output

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    httpd.page = page
    httpd.session = session
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
