"""Loopback-only personal coach application; authenticated JSON API."""
import argparse
import hmac
import json
import os
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlsplit

from jsonschema.exceptions import ValidationError

from .hq import HQAuthority
from .journal import ConflictError, Journal, utc_now
from .language import expand_reply
from .service import CoachService


class CoachHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, journal, app_token, hq_token, clock=utc_now):
        if address[0] != "127.0.0.1":
            raise ValueError("This personal app only binds to 127.0.0.1")
        self.journal = journal
        self.service = CoachService(journal, clock)
        self.hq = HQAuthority(journal, hq_token)
        self.app_token = app_token
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Never print request bodies, tokens or athlete data.

    def send(self, status, body, mime="application/json"):
        raw = json.dumps(body, ensure_ascii=False, allow_nan=False).encode() if mime == "application/json" else body
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(raw)

    def guard(self):
        port = self.server.server_address[1]
        expected = f"127.0.0.1:{port}"
        if self.headers.get("Host") != expected:
            raise PermissionError("Unexpected host")
        origin = self.headers.get("Origin")
        if origin and origin != "http://" + expected:
            raise PermissionError("Cross-origin request rejected")
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied, "Bearer " + self.server.app_token):
            raise PermissionError("Open the private launch link to connect")

    def do_GET(self):
        path = urlsplit(self.path).path
        static = {"/": ("index.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/style.css": ("style.css", "text/css")}
        if path in static:
            name, mime = static[path]
            return self.send(200, files("ai_coach").joinpath("web", name).read_bytes(), mime)
        try:
            self.guard()
            if path == "/api/state":
                return self.send(200, self.server.service.snapshot())
            if path == "/api/health":
                return self.send(200, self.server.service.health())
            if path == "/api/export":
                return self.send(200, {"schema_version": "coach-journal-1.0", "events": self.server.journal.read()})
            self.send(404, {"error": "Not found"})
        except PermissionError as error:
            self.send(403, {"error": str(error)})
        except (ValueError, sqlite3.Error):
            self.send(500, {"error": "Integrity check failed; inspect the local database before continuing"})

    def do_POST(self):
        try:
            self.guard()
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 2_000_000 or self.headers.get_content_type() != "application/json":
                return self.send(400, {"error": "Expected JSON body, maximum 2 MB"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected JSON object")
            path = urlsplit(self.path).path
            revision = data.get("expected_revision")
            if path != "/api/chat" and (type(revision) is not int or revision < 0):
                raise ValueError("expected_revision is required")
            if path in ("/api/profile", "/api/goal", "/api/checkin"):
                result = self.server.service.save(path.split("/")[-1], data["value"], revision)
            elif path == "/api/propose":
                result = self.server.service.propose(revision, data.get("week_start"))
            elif path == "/api/import":
                result = self.server.service.import_evidence(data["value"], revision)
            elif path == "/api/source-import":
                from .onboarding import import_snapshot
                result = import_snapshot(self.server.journal, data["value"], revision)
            elif path == "/api/hq/decision":
                result = self.server.hq.decide(data["proposal_id"], data["decision"], self.headers.get("X-HQ-Token"), revision, self.server.service.clock())
                result = {"revision": result["revision"]}
            elif path == "/api/hq/import":
                result = self.server.hq.import_plan(data["value"], self.headers.get("X-HQ-Token"), revision, self.server.service.clock())
                result = {"revision": result["revision"]}
            elif path == "/api/chat":
                grounded = self.server.service.chat(data["message"])
                result = expand_reply(data["message"], grounded["message"], consent=data.get("cloud_consent") is True)
            elif path == "/api/backup":
                result = self.server.journal.backup(self.server.journal.path.parent / "backups")
            else:
                return self.send(404, {"error": "Not found"})
            self.send(200, result)
        except PermissionError as error:
            self.send(403, {"error": str(error)})
        except ConflictError as error:
            self.send(409, {"error": str(error)})
        except ValidationError as error:
            self.send(400, {"error": "Invalid field " + ".".join(str(p) for p in error.absolute_path)})
        except (ValueError, KeyError, TypeError) as error:
            self.send(400, {"error": str(error)})
        except sqlite3.Error:
            self.send(500, {"error": "Storage operation failed"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--demo", action="store_true", help="Use a separate synthetic demonstration database")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--open", action="store_true", help="Open the private local browser link")
    args = parser.parse_args()
    database = args.db or Path.home() / ".ai-coach" / ("demo.sqlite" if args.demo else "coach.sqlite")
    app_token = secrets.token_urlsafe(32)
    hq_token = os.environ.get("AI_COACH_HQ_TOKEN") or secrets.token_urlsafe(32)
    journal = Journal(database)
    if args.demo:
        from .demo import seed_demo
        seed_demo(journal, hq_token, utc_now)
    server = CoachHTTPServer(("127.0.0.1", args.port), journal, app_token, hq_token)
    url = f"http://127.0.0.1:{server.server_address[1]}/#token={app_token}"
    print("AI Coach v1 — local personal application", flush=True)
    print("Open: " + url, flush=True)
    print("HQ approval code (keep private): " + hq_token, flush=True)
    print("Stop with Ctrl+C. No external training-service sync is active.", flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
