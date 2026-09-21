"""The server of `bakeoff live`: loopback only, standard library only. It serves the player page and
the event stream (Server-Sent Events) and nothing else: no files, no other method, no other host."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bakeoff.live import Broadcast

EVENTS_PATH = "/events"
HOST = "127.0.0.1"


def serve(page: str | None, broadcast: Broadcast, port: int = 8000) -> ThreadingHTTPServer:
    """Starts serving in a daemon thread and returns the server (`shutdown()` stops it). Port 0 picks a
    free one. The port is bound before anything is written to disk, so the page may come later: set
    `server.page`; until then `/` answers 503."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (the base class names it)
            names = {f"{HOST}:{self.server.server_address[1]}", f"localhost:{self.server.server_address[1]}"}
            if self.headers.get("Host") not in names:
                return self.send_error(403)  # a page elsewhere that points a DNS name at us gets nothing
            if self.path == "/" and self.server.page is None:
                self.send_error(503)
            elif self.path == "/":
                body = self.server.page.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif self.path == EVENTS_PATH:
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    for event in broadcast.listen():
                        if event is None:
                            self.wfile.write(b": keep-alive\n\n")
                        else:
                            name, data = event  # json.dumps escapes every newline, so an event is always two lines
                            self.wfile.write(f"event: {name}\ndata: {json.dumps(data)}\n\n".encode("utf-8"))
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass  # the page was closed
            else:
                self.send_error(404)

        def log_message(self, format, *args):  # noqa: A002
            pass  # the terminal belongs to the run's own output

    httpd = ThreadingHTTPServer((HOST, port), Handler)
    httpd.daemon_threads = True
    httpd.page = page
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd
