#!/usr/bin/env python3
"""Trainer HTTP collector for DEV-OCT-2026.

This is the server. Do not run racmorph/callback.py — that file POSTs
identity when a developer starts Python; it is not a collector.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 12331
DEFAULT_LOG = "training_callbacks.jsonl"

EVENTS = []
LOG = Path(DEFAULT_LOG)


def _load_existing(log_path):
    events = []
    if not log_path.is_file():
        return events
    with log_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


class Collector(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            body = json.dumps({"ok": True, "event_count": len(EVENTS)}).encode("utf-8")
            self._send(200, "application/json", body)
            return
        if path in ("/", "/trainer"):
            rows = []
            for i, ev in enumerate(EVENTS, 1):
                rows.append(
                    "<h2>Event %d</h2><pre>%s</pre>"
                    % (i, json.dumps(ev, indent=2, ensure_ascii=False))
                )
            html = (
                "<!doctype html><meta charset=utf-8>"
                "<title>Trainer collector</title>"
                "<h1>DEV-OCT-2026 collector</h1>"
                "<p>%d received (POST /api/callback). "
                "Identities only — no hostname/IP.</p>"
                % len(EVENTS)
                + "".join(rows)
            ).encode("utf-8")
            self._send(200, "text/html; charset=utf-8", html)
            return
        self.send_error(404)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        if path != "/api/callback":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            payload = {"_raw": raw.decode("utf-8", errors="replace")}
        EVENTS.append(payload)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print("received #%d %s" % (len(EVENTS), payload), flush=True)
        self._send(200, "application/json", b'{"ok":true}')

    def log_message(self, fmt, *args):
        return

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main(argv=None):
    global LOG, EVENTS

    parser = argparse.ArgumentParser(
        description="Trainer collector. Do not run racmorph/callback.py."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--log-file", default=DEFAULT_LOG)
    args = parser.parse_args(argv)

    LOG = Path(args.log_file)
    EVENTS[:] = _load_existing(LOG)

    print(
        "collector http://%s:%d/api/callback  (health /health, view /trainer)"
        % (args.host, args.port)
    )
    print("log %s  (%d existing events)" % (LOG, len(EVENTS)))
    print("do not run racmorph/callback.py — that is the client POST")
    ThreadingHTTPServer((args.host, args.port), Collector).serve_forever()


if __name__ == "__main__":
    main()
