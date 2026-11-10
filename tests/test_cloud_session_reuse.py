"""Selecting a running cloud session must not cause the next start to rent another.

Real temporary state and CLI handlers, with API/ADB boundaries mocked. No phone,
network, browser or cloud credentials are needed, including on Windows.
"""
import copy
import io
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SRC = str(Path(__file__).resolve().parents[1] / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from phone_harness import cloud, config


class CloudSessionReuse(unittest.TestCase):
    def keep_context(self, manager):
        result = manager.__enter__()
        self.addCleanup(manager.__exit__, None, None, None)
        return result

    def setUp(self):
        home = tempfile.TemporaryDirectory()
        self.addCleanup(home.cleanup)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("PHONE_HARNESS_") and k != "ANDROID_SERIAL"}
        env.update(PHONE_HARNESS_HOME=home.name, PHONE_HARNESS_TELEMETRY="0",
                   PHONE_HARNESS_NO_UPDATE_CHECK="1")
        self.keep_context(patch.dict(os.environ, env, clear=True))
        self.keep_context(redirect_stdout(io.StringIO()))
        self.keep_context(patch("urllib.request.urlopen", side_effect=AssertionError("unexpected network")))
        self.keep_context(patch.object(cloud, "_adb_present"))
        self.keep_context(patch.object(cloud, "ensure_connected"))
        self.keep_context(patch.object(cloud, "_open_browser", side_effect=AssertionError("unexpected browser")))
        self.keep_context(patch.object(cloud, "_reported_dead", {}))
        self.keep_context(patch.object(cloud, "_reported_fallback", None))
        self.sessions = {}
        self.creations = []
        self.catalog = [{"id": "iphone-1", "label": "Office iPhone",
                         "platform": "ios", "kind": "device"}]
        self.keep_context(patch.object(cloud, "_api", side_effect=self.api))

    def api(self, method, path, body=None, **kwargs):
        if method == "GET" and path == "/me":
            return {"available": copy.deepcopy(self.catalog)}
        if method == "GET" and path == "/sessions":
            return copy.deepcopy(list(self.sessions.values()))
        if method == "GET" and path.startswith("/sessions/"):
            return copy.deepcopy(self.sessions[path.rsplit("/", 1)[1]])
        if method == "POST" and path == "/sessions":
            self.creations.append(copy.deepcopy(body))
            sid = f"session-{len(self.creations)}"
            session = {"id": sid, "state": "ready", "expires_at": time.time() + 900,
                       "platform": body.get("platform", "android"),
                       "kind": body.get("kind", "emulator")}
            if session["platform"] == "ios":
                session["device_id"] = body["device_id"]
                session["control"] = {"url": "https://example.invalid/control", "token": "old-token"}
            else:
                session["adb"] = {"host": "example.invalid", "port": 5555, "code": "fake"}
            self.sessions[sid] = session
            return copy.deepcopy(session)
        raise AssertionError((method, path))

    def start(self, *args):
        self.assertEqual(cloud.cli(["start", *args, "--no-watch"]), 0)
        return cloud._load_state()["session"]["sid"]

    def use(self, sid):
        self.assertEqual(cloud.cli(["use", sid]), 0)

    def test_bare_start_reuses_session_after_use(self):
        sid = self.start()
        self.use(sid)
        self.assertEqual(self.start(), sid)
        self.assertEqual(len(self.creations), 1)

    def test_named_start_reuses_session_after_use(self):
        sid = self.start("Office iPhone")
        self.use(sid)
        self.assertEqual(self.start("iphone-1"), sid)
        self.assertEqual(len(self.creations), 1)

    def test_switch_back_preserves_each_sessions_selector(self):
        android = self.start()
        iphone = self.start("iphone-1")
        self.use(android)
        self.assertEqual(self.start(), android)
        self.use(iphone)
        self.assertEqual(self.start("iphone-1"), iphone)
        self.assertEqual(len(self.creations), 2)

    def test_use_refreshes_server_fields_while_preserving_selector(self):
        sid = self.start("iphone-1")
        refreshed = self.sessions[sid]
        refreshed["control"] = {"url": "https://example.invalid/rotated", "token": "new-token"}
        refreshed["expires_at"] += 300
        self.use(sid)
        state = cloud._load_state()
        record = state["session"]
        self.assertEqual(record["link"]["token"], "new-token")
        self.assertEqual(record["link"]["url"], refreshed["control"]["url"])
        self.assertEqual(record["expires_at"], refreshed["expires_at"])
        self.assertEqual(state["sessions"][sid], record)
        self.assertEqual(record["selector"], "id:iphone-1")

    def test_explicit_new_selector_wins(self):
        sid = self.start("iphone-1")
        cloud._attach(copy.deepcopy(self.sessions[sid]), selector="label:renamed")
        self.assertEqual(cloud._load_state()["session"]["selector"], "label:renamed")

    def test_unknown_session_does_not_inherit_another_sessions_selector(self):
        sid = self.start()
        unknown = copy.deepcopy(self.sessions[sid])
        unknown["id"] = "external-session"
        self.sessions[unknown["id"]] = unknown
        self.use(unknown["id"])
        state = cloud._load_state()
        self.assertIsNone(state["session"]["selector"])
        self.assertEqual(state["sessions"][sid]["selector"], "unnamed")

    def test_legacy_single_attached_record_keeps_selector(self):
        sid = self.start()
        state = cloud._load_state()
        state.pop("sessions")
        config._write(cloud._state_path(), state)
        self.use(sid)
        self.assertEqual(self.start(), sid)
        self.assertEqual(len(self.creations), 1)


if __name__ == "__main__":
    unittest.main()
