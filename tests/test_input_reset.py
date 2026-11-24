"""The reset CLI and shared transport against a local control endpoint only."""
import contextlib
import io
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from phone_harness import transport
from phone_harness.remote import Remote
from phone_harness.run import _run


def remake(ok):
    return {"ok": ok, "reason": "manual", "detail": None if ok else "remake failed",
            "attempts": 2, "took_s": 0.4, "at": 1234.5, "surface_rematch": False,
            "rsd": {"ok": True}}


class InputReset(unittest.TestCase):
    def setUp(self):
        class Host(BaseHTTPRequestHandler):
            offered = ["input.reset", "device.wake", "session.state"]
            result = remake(True)
            status = 200
            error = {"error": "reset unavailable"}
            calls = []

            def log_message(self, *_):
                pass

            def reply(self, status, body):
                raw = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self.reply(200, {"ops": self.offered})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.calls.append((self.path, body))
                self.reply(self.status, {"result": self.result} if self.status == 200 else self.error)

        self.host = Host
        server = ThreadingHTTPServer(("127.0.0.1", 0), Host)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.remote = Remote(f"http://127.0.0.1:{server.server_port}", "fixture-control")

    def test_vocabulary_and_capability_follow_the_host(self):
        self.assertIn("input.reset", transport.OP_NAMES)
        self.assertIn("input.reset", self.remote.ops())
        self.host.offered = ["input.tap"]
        other = Remote(self.remote.url, "fixture-control")
        self.assertNotIn("input.reset", other.ops())
        with self.assertRaises(transport.Unsupported):
            other.send("input.reset")
        self.assertEqual(self.host.calls, [])

    def test_no_fallback_on_a_local_backend(self):
        with self.assertRaises(transport.Unsupported):
            transport.Backend().send("input.reset")

    def test_transport_preserves_success_and_failure_objects(self):
        for ok in (True, False):
            self.host.result = remake(ok)
            self.assertEqual(self.remote.send("input.reset"), self.host.result)
        self.assertEqual(self.host.calls, [("/op", {"op": "input.reset", "kw": {}})] * 2)

    def test_transport_rejects_operation_arguments(self):
        for kw in ({"x": 1}, {"y": 2}, {"duration": 1}, {"force": True}):
            with self.subTest(kw=kw), self.assertRaises(TypeError):
                self.remote.send("input.reset", **kw)
        self.assertEqual(self.host.calls, [])

    def test_refusal_never_probes_state_or_recommends_wake(self):
        self.host.status = 409
        for code in (None, "locked"):
            self.host.error = {"error": "reset unavailable", "code": code}
            with self.assertRaisesRegex(RuntimeError, "^reset unavailable$"):
                self.remote.send("input.reset")
        self.assertEqual(self.host.calls, [("/op", {"op": "input.reset", "kw": {}})] * 2)

    def test_cli_prints_the_result_and_uses_inner_ok_for_exit_status(self):
        for ok, status in ((True, 0), (False, 1)):
            self.host.result = remake(ok)
            out = io.StringIO()
            with patch("phone_harness.transport.connect", return_value=self.remote) as connect, \
                    patch.dict(os.environ), contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit_:
                _run(["--session", "s_fixture", "input-reset"])
            self.assertEqual(exit_.exception.code, status)
            self.assertEqual(json.loads(out.getvalue()), self.host.result)
            connect.assert_called_once_with()
        self.assertEqual(self.host.calls, [("/op", {"op": "input.reset", "kw": {}})] * 2)

    def test_cli_never_reports_malformed_results_as_recovered(self):
        for result in (None, True, {}, {"ok": 1}, {"ok": "false"}):
            self.host.result = result
            with patch("phone_harness.transport.connect", return_value=self.remote), \
                    contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as exit_:
                _run(["input-reset"])
            self.assertEqual(exit_.exception.code, 1)

    def test_cli_help_and_extra_arguments_do_not_connect(self):
        with patch("phone_harness.transport.connect") as connect:
            out = io.StringIO()
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as exit_:
                _run(["input-reset", "--help"])
            self.assertEqual(exit_.exception.code, 0)
            self.assertIn("touch/HID", out.getvalue())
            self.assertIn("ok is true", out.getvalue())
            for args in (["1", "2"], ["--x", "1"], ["--hold", "1"], ["--duration", "1"]):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
                    _run(["input-reset", *args])
                self.assertEqual(exit_.exception.code, 2)
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
