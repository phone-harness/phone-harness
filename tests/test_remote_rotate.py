"""Turning a cloud iPhone (PHO-337).

A cloud iPhone lies flat in a rack and cannot be stood up, so which way up its
screen is has to be asked for. The control host here is a stand-in; no cloud.
It answers a turn as phone-host does: {device, orientation, turned, lock}.

A phone with iOS's Portrait Orientation Lock on does not turn, so the host
turns the lock off before the turn (it used to refuse). That goes through
Settings and ends on the Home Screen, which on a small iPhone stays upright.
After a turn to a landscape the lock stays off; the next turn to portrait puts
it back on, when a turn was what switched it off.
"""
import json
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from phone_harness import transport  # noqa: E402
from phone_harness.remote import LOCKED, STILL_TURNING, Remote  # noqa: E402
from phone_harness.transport import Unsupported  # noqa: E402

TALL, WIDE = {"x": 0, "y": 0, "w": 750, "h": 1334, "id": "udid1"}, {"x": 0, "y": 0, "w": 1334, "h": 750, "id": "udid1"}


class Control(BaseHTTPRequestHandler):
    """A phone's control URL: /ops and /op, as phone-host serves them."""
    ops = ()
    orientation = "portrait"
    app_turns = True        # False: the app in front supports one way up and stays upright
    upright_lock = False    # iOS's Portrait Orientation Lock
    unlocked_by_a_turn = False   # the host's note that a turn switched the lock off
    gave_up = None          # set: what the gateway answers a turn it stopped waiting for
    locked = False          # the phone shows its lock screen
    at_home = False         # on the Home Screen, where changing the lock leaves the phone
    calls = []

    def log_message(self, *a):
        pass

    def _send(self, status, body):
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _handle(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n)) if n else {}
        if self.headers.get("Authorization") != "Bearer ct_1":
            return self._send(404, {"error": "not found"})
        if self.path == "/ops":
            return self._send(200, {"ops": sorted(Control.ops)})
        if self.path == "/op":
            Control.calls.append(body)
            op, kw = body["op"], body.get("kw") or {}
            if op not in Control.ops:
                return self._send(400, {"error": f"this phone cannot {op!r}", "unsupported": True})
            if op == "device.rotate" and Control.gave_up:
                return self._send(*Control.gave_up)
            if op == "device.rotate" and Control.locked:
                return self._send(409, {"error": "The iPhone is locked. Unlock it on the phone, then retry; "
                                                 "the host never enters a passcode."})
            if op == "device.rotate":
                if set(kw) != {"to"} or kw["to"] not in ("portrait", "landscape_left", "landscape_right"):
                    return self._send(400, {"error": "to must be portrait, landscape_left or landscape_right"})
                lock = None
                if Control.upright_lock and kw["to"] != Control.orientation:
                    # The lock is in the way: off first, and the host notes that it did.
                    Control.upright_lock, Control.unlocked_by_a_turn, lock = False, True, "off"
                if kw["to"] == "portrait" and Control.unlocked_by_a_turn:
                    # Back on at the next turn to portrait, only when that note is there.
                    Control.upright_lock, Control.unlocked_by_a_turn, lock = True, False, "on"
                if lock:
                    Control.at_home = True
                turned = 0 if kw["to"] == Control.orientation else 1
                Control.orientation = kw["to"]
                drawn = kw["to"] if Control.app_turns and not Control.at_home else "portrait"
                return self._send(200, {"result": {"device": kw["to"], "turned": turned, "orientation": drawn,
                                                   "lock": lock}})
            if op == "session.state":
                return self._send(200, {"result": "locked" if Control.locked else "ready"})
            if op == "input.slow":
                return self._send(502, {"error": "could not reach the phone"})
            if op == "screen.capture":
                wide = Control.orientation != "portrait" and Control.app_turns
                return self._send(200, {"result": {"png_b64": "", "bounds": WIDE if wide else TALL}})
            if op == "screen.bounds":
                return self._send(200, {"result": TALL})        # the size the session started with
            return self._send(200, {"result": True})
        return self._send(404, {"error": "not found"})

    do_GET = do_POST = _handle


class TurningACloudIphone(unittest.TestCase):
    def setUp(self):
        Control.ops = ("screen.bounds", "screen.capture", "session.state", "input.tap", "device.rotate", "device.wake")
        Control.orientation, Control.app_turns, Control.upright_lock, Control.calls = "portrait", True, False, []
        Control.at_home = Control.unlocked_by_a_turn = Control.locked = False
        Control.gave_up = None
        server = ThreadingHTTPServer(("127.0.0.1", 0), Control)
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        self.remote = Remote(f"http://127.0.0.1:{server.server_port}", "ct_1")

    def test_the_vocabulary_has_the_op_and_a_host_that_lists_it_supports_it(self):
        self.assertIn("device.rotate", transport.OP_NAMES)
        self.assertTrue(self.remote.supports("device.rotate"))
        self.assertIn("device.rotate", self.remote.ops())

    def test_each_way_up_is_one_op_and_the_two_landscapes_are_different_words(self):
        for to in ("landscape_left", "landscape_right", "portrait"):
            self.assertEqual(self.remote.send("device.rotate", to=to),
                             {"device": to, "orientation": to, "turned": 1, "lock": None})
        self.assertEqual(Control.calls, [{"op": "device.rotate", "kw": {"to": "landscape_left"}},
                                         {"op": "device.rotate", "kw": {"to": "landscape_right"}},
                                         {"op": "device.rotate", "kw": {"to": "portrait"}}])

    def test_a_capture_follows_the_turn_and_the_reported_size_may_not(self):
        """phone-host records the screen's size once, when the session becomes ready."""
        self.remote.send("device.rotate", to="landscape_left")
        self.assertEqual(self.remote._op("screen.capture")["bounds"]["w"], 1334)
        self.assertEqual(self.remote.send("screen.bounds")["w"], 750)

    def test_an_app_that_does_not_turn_leaves_the_screen_drawn_upright(self):
        Control.app_turns = False
        self.assertEqual(self.remote.send("device.rotate", to="landscape_left"),
                         {"device": "landscape_left", "orientation": "portrait", "turned": 1, "lock": None})

    def test_a_turn_to_a_landscape_turns_the_lock_off_and_leaves_it_off(self):
        """One call, no refusal: the answer says the lock was turned off, and the
        phone is on its Home Screen, which stays upright."""
        Control.upright_lock = True
        self.assertEqual(self.remote.send("device.rotate", to="landscape_left"),
                         {"device": "landscape_left", "orientation": "portrait", "turned": 1, "lock": "off"})
        self.assertFalse(Control.upright_lock)
        self.assertEqual([c["op"] for c in Control.calls], ["device.rotate"])
        # the lock is off now, so the next turn has nothing to say about it
        self.assertIsNone(self.remote.send("device.rotate", to="landscape_right")["lock"])

    def test_the_next_turn_to_portrait_puts_the_lock_back(self):
        Control.upright_lock = True
        self.assertEqual(self.remote.send("device.rotate", to="landscape_left")["lock"], "off")
        self.assertIsNone(self.remote.send("device.rotate", to="landscape_right")["lock"])
        self.assertEqual(self.remote.send("device.rotate", to="portrait")["lock"], "on")
        self.assertTrue(Control.upright_lock)
        self.assertIsNone(self.remote.send("device.rotate", to="portrait")["lock"])      # and only once

    def test_a_lock_somebody_else_turned_off_is_not_put_back(self):
        self.remote.send("device.rotate", to="landscape_left")
        self.assertIsNone(self.remote.send("device.rotate", to="portrait")["lock"])
        self.assertFalse(Control.upright_lock)

    def test_a_turn_is_waited_for_longer_than_any_other_op(self):
        """Changing the lock goes through Settings: about 46 s on the test phone, where a plain turn takes one or two."""
        waits = {}
        call = self.remote._call

        def record(method, path, body=None, timeout=60):
            if isinstance(body, dict) and "op" in body:
                waits[body["op"]] = timeout
            return call(method, path, body, timeout)
        self.remote._call = record
        self.remote.send("device.rotate", to="landscape_left")
        self.remote.send("input.tap", x=1, y=2)
        self.assertEqual(waits, {"device.rotate": 200, "input.tap": 60})

    def test_a_turn_that_does_not_come_back_says_it_may_still_be_going(self):
        """The gateway in front of the control URL waits 70 s for the host and then
        answers 502. The host carries on, so a second turn asked for at once would
        run under the first."""
        for gave_up in ((502, {"error": "could not reach the phone"}), (504, {"error": "gateway timeout"})):
            Control.gave_up = gave_up
            with self.subTest(status=gave_up[0]), self.assertRaises(RuntimeError) as raised:
                self.remote.send("device.rotate", to="landscape_left")
            self.assertEqual(str(raised.exception), f"{gave_up[1]['error']}. {STILL_TURNING}")
        self.assertIn("may still be going", STILL_TURNING)
        self.assertIn("look at screenshot() before calling rotate() again", STILL_TURNING)

    def test_a_refusal_is_not_taken_for_a_turn_still_going(self):
        Control.gave_up = (400, {"error": "to is one of: portrait, landscape_left, landscape_right"})
        with self.assertRaises(RuntimeError) as raised:
            self.remote.send("device.rotate", to="landscape_left")
        self.assertNotIn("may still be going", str(raised.exception))
        Control.gave_up, Control.locked = None, True
        with self.assertRaises(RuntimeError) as raised:
            self.remote.send("device.rotate", to="landscape_left")
        self.assertEqual(str(raised.exception), LOCKED)          # a phone at its lock screen: wake() first

    def test_another_op_that_does_not_come_back_says_nothing_about_a_turn(self):
        Control.ops = Control.ops + ("input.slow",)
        with self.assertRaises(RuntimeError) as raised:
            self.remote.send("input.slow")
        self.assertEqual(str(raised.exception), "could not reach the phone")

    def test_a_turn_this_client_stopped_waiting_for_says_so_too(self):
        def no_answer(method, path, body=None, timeout=60):
            raise RuntimeError("could not reach the cloud phone: timed out")
        self.remote.supports("device.rotate")           # the host's list is read before the wire goes quiet
        self.remote._call = no_answer
        with self.assertRaises(RuntimeError) as raised:
            self.remote.send("device.rotate", to="portrait")
        self.assertEqual(str(raised.exception), f"could not reach the cloud phone: timed out. {STILL_TURNING}")

    def test_a_session_that_is_gone_is_said_as_it_is(self):
        self.remote.supports("device.rotate")
        self.remote.token = "expired"                   # the stand-in answers 404 to a token it does not know
        with self.assertRaises(RuntimeError) as raised:
            self.remote.send("device.rotate", to="portrait")
        self.assertIn("session is gone", str(raised.exception))
        self.assertNotIn("may still be going", str(raised.exception))

    def test_a_host_that_cannot_turn_a_phone_is_unsupported_and_is_sent_nothing(self):
        Control.ops = ("screen.bounds", "input.tap", "device.wake", "session.state")
        self.assertFalse(self.remote.supports("device.rotate"))
        with self.assertRaises(Unsupported) as raised:
            self.remote.send("device.rotate", to="portrait")
        self.assertEqual(str(raised.exception), "this cloud phone cannot 'device.rotate'")
        self.assertEqual(Control.calls, [])


class TheRotateHelper(unittest.TestCase):
    class Phone:
        def __init__(self, ops):
            self.ops, self.sent = set(ops), []

        def supports(self, op):
            return op in self.ops

        def send(self, op, **kw):
            self.sent.append((op, kw))
            return {"device": kw.get("to"), "orientation": kw.get("to"), "turned": 1}

    def with_phone(self, ops):
        from phone_harness import helpers
        phone = self.Phone(ops)
        saved = helpers.phone
        helpers.phone = phone
        self.addCleanup(setattr, helpers, "phone", saved)
        return helpers, phone

    def test_rotate_sends_the_op_with_the_way_up(self):
        helpers, phone = self.with_phone({"device.rotate"})
        for to in ("portrait", "landscape_left", "landscape_right"):
            self.assertEqual(helpers.rotate(to), {"device": to, "orientation": to, "turned": 1})
        self.assertEqual(phone.sent, [("device.rotate", {"to": "portrait"}), ("device.rotate", {"to": "landscape_left"}),
                                      ("device.rotate", {"to": "landscape_right"})])

    def test_anything_else_is_refused_here_and_nothing_is_sent(self):
        helpers, phone = self.with_phone({"device.rotate"})
        for to in ("landscape", "upside_down", "left", "LANDSCAPE_LEFT", "landscape-left", "", None, 90, True):
            with self.subTest(to=to), self.assertRaises(ValueError) as raised:
                helpers.rotate(to)
            self.assertIn("'portrait', 'landscape_left' or 'landscape_right'", str(raised.exception))
        self.assertEqual(phone.sent, [])

    def test_a_phone_that_cannot_be_turned_says_cloud_iphones_only_and_sends_nothing(self):
        helpers, phone = self.with_phone({"nav.home", "input.tap"})
        with self.assertRaises(Unsupported) as raised:
            helpers.rotate("landscape_left")
        self.assertIn("cloud iPhones only", str(raised.exception))
        self.assertEqual(phone.sent, [])

    def test_no_local_backend_claims_to_turn_a_phone(self):
        from phone_harness.android import Android
        self.assertIsNone(getattr(Android, "_device_rotate", None))
        if sys.platform == "darwin":
            try:
                from phone_harness.ios import IPhone
            except ImportError:
                return
            self.assertIsNone(getattr(IPhone, "_device_rotate", None))


if __name__ == "__main__":
    unittest.main()
