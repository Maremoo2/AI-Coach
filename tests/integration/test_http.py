import json
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path

from ai_coach.journal import Journal
from ai_coach.server import CoachHTTPServer
from tests.app_support import NOW, profile


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.journal = Journal(Path(self.temp.name) / "test.sqlite")
        self.server = CoachHTTPServer(("127.0.0.1", 0), self.journal, "app-test", "hq-test", lambda: NOW)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.temp.cleanup()

    def request(self, path, data=None, headers=None):
        base = {"Authorization": "Bearer app-test"}
        if data is not None:
            base["Content-Type"] = "application/json"
        base.update(headers or {})
        req = urllib.request.Request(self.url + path, headers=base, data=json.dumps(data).encode() if data is not None else None)
        try:
            response = urllib.request.urlopen(req)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read()
            return response.status, json.loads(raw) if response.headers.get_content_type() == "application/json" else raw.decode()

    def test_private_api_rejects_missing_token_cross_origin_and_host(self):
        for headers in ({"Authorization": ""}, {"Origin": "https://example.org"}, {"Host": "evil.example"}):
            self.assertEqual(self.request("/api/state", headers=headers)[0], 403)

    def test_browser_flow_onboard_propose_approve_and_read(self):
        self.assertEqual(self.request("/api/profile", {"expected_revision": 0, "value": profile()})[0], 200)
        status, proposal = self.request("/api/propose", {"expected_revision": 1})
        self.assertEqual(status, 200)
        decision = {"expected_revision": 2, "proposal_id": proposal["id"], "decision": "APPROVED"}
        self.assertEqual(self.request("/api/hq/decision", decision)[0], 403)
        self.assertEqual(self.request("/api/hq/decision", decision, {"X-HQ-Token": "hq-test"})[0], 200)
        self.assertEqual(self.request("/api/state")[1]["plan"]["authority"], "HQ")
        self.assertEqual(self.request("/api/hq/decision", decision, {"X-HQ-Token": "hq-test"})[0], 409)

    def test_static_assets_have_no_access_secrets(self):
        for path in ("/", "/app.js", "/style.css"):
            status, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertNotIn("app-test", body)
            self.assertNotIn("hq-test", body)

    def test_extra_fields_and_noninteger_revision_rejected(self):
        p = profile()
        p["authority"] = "HQ"
        self.assertEqual(self.request("/api/profile", {"expected_revision": 0, "value": p})[0], 400)
        self.assertEqual(self.request("/api/profile", {"expected_revision": True, "value": profile()})[0], 400)

    def test_web_chat_cannot_change_state(self):
        before = self.journal.read()
        status, reply = self.request("/api/chat", {"message": "Change my plan now"})
        self.assertEqual(status, 200)
        self.assertFalse(reply["plan_changed"])
        self.assertEqual(before, self.journal.read())
