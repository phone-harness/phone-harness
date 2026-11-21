"""`phone-harness skill` is printed on Windows CI, where stdout is cp1252."""
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from phone_harness.run import _skill_text, _write_utf8  # noqa: E402
from phone_harness.android import CLI_USAGE as ANDROID_USAGE  # noqa: E402
from phone_harness.cloud import CLI_USAGE as CLOUD_USAGE  # noqa: E402
from phone_harness.cloud import IPHONES_ONLY  # noqa: E402
from phone_harness.config import CLI_USAGE as CONFIG_USAGE
from phone_harness.run import USAGE  # noqa: E402


class SkillOutput(unittest.TestCase):
    def test_printed_docs_and_help_are_ascii(self):
        for text in (_skill_text(), USAGE, ANDROID_USAGE, CLOUD_USAGE, CONFIG_USAGE):
            text.encode("ascii")

    def test_skill_command_survives_cp1252_stdout(self):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "cp1252:strict"
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        env["PHONE_HARNESS_TELEMETRY"] = "0"
        env.pop("BROWSER", None)
        r = subprocess.run(
            [sys.executable, "-m", "phone_harness.run", "skill"],
            capture_output=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(b"phone-harness", r.stdout)
        r.stdout.decode("ascii")

    def test_write_utf8_uses_the_buffer_when_the_text_stream_refuses(self):
        class Stdout:
            encoding = "cp1252"

            def __init__(self):
                self.buffer = io.BytesIO()

            def reconfigure(self, **_kw):
                raise OSError("cannot reconfigure")

            def write(self, s):
                s.encode(self.encoding)

            def flush(self):
                pass

        out = Stdout()
        old = sys.stdout
        sys.stdout = out
        try:
            _write_utf8("a \u2192 b")
        finally:
            sys.stdout = old
        self.assertEqual(out.buffer.getvalue(), "a \u2192 b".encode("utf-8"))

    def test_skill_points_at_helpers_and_names_screen(self):
        text = _skill_text()
        self.assertIn("The main helpers are listed in [Helpers](#helpers).", text)
        self.assertIn("\n## Helpers\n", text)
        self.assertIn("`screen(min_confidence=0.3)`", text)
        self.assertIn("`screenshot(path=None)` - Capture the screen to a PNG, print its path, and return it.", text)
        self.assertIn("`screen_info()`", text)
        self.assertNotIn("ocr()", text)

    def test_skill_says_how_reserving_a_phone_works(self):
        """What an agent has to get right before it reserves or cancels for someone."""
        section = _skill_text().split("\n## Reserving a cloud phone\n", 1)[1].split("\n## ", 1)[0]
        text = " ".join(section.split())
        for rule in (
                "**Which phones.** " + IPHONES_ONLY,             # the sentence `cloud reserve` refuses an Android with
                "`--type` is `iphone`, or `iphone-esim` for one with an eSIM",
                "**Signed in first.**", "phone-harness cloud login", "PHONE_HARNESS_API_KEY",
                "phone-harness.com/get-a-phone",                       # with no account: the website
                "$20 per phone refundable deposit", "quote the command prints is authoritative",
                "do not quote them from memory",
                "**You never pay.**", "**Nothing is held until the deposit is paid.**",
                "**Queue order is paid time.**", "does not move one up",
                "one phone at the intro price when this customer has not had it yet, the rest at the standard price",
                "The refund is automatic, to the card that paid",
                "part handed over refunds only the phones still waiting",
                "became a credit on the first bill and is no longer refundable",
                "**The website has no list.**", "`cloud reservations` is the list",
                "Cancelling one does not free a place"):
            self.assertIn(rule, text)
        self.assertNotIn("`android`", text)                # not a --type

    def test_skill_says_how_to_wake_a_cloud_iphone_and_that_it_has_no_passcode(self):
        """An agent that meets a lock screen has to know one call gets past it, and not to ask for a code."""
        text = _skill_text()
        self.assertIn("- `wake()` - Wake a cloud iPhone that is asleep or on its lock screen. "
                      "No passcode is typed. Cloud iPhones only.", text)
        section = " ".join(text.split("\n## Cloud iPhone\n", 1)[1].split("\n## ", 1)[0].split())
        for rule in (
                "**Asleep or locked.**", "the StandBy clock", "a black `screenshot()` with no text",
                "`screenshot()` and `screen()` still work",          # looking is how it learns the phone is locked
                "Call `wake()` and run the step again",
                "It returns `{state, was, woke, through}`",
                "Getting past StandBy leaves the phone on its Home Screen",
                "set up with no passcode: never ask the user for one, and nothing here types one",
                "a passcode has been set on it; tell the user",
                "Check `supports('device.wake')` first",
                "| `device.wake` | | `{state, was, woke, through}`; `state` is `'ready'` when the phone takes input."):
            self.assertIn(rule, section)
        # The sentence the skill quotes is the one the client raises.
        from phone_harness.remote import LOCKED
        quoted = "the cloud iPhone is locked or asleep. Call wake()"
        self.assertTrue(LOCKED.startswith(quoted + " "), LOCKED)
        self.assertIn(f"`{quoted} ...`", section)

    def test_the_api_and_install_guides_say_the_same(self):
        root = Path(__file__).resolve().parents[1]
        api = " ".join((root / "setup" / "api.md").read_text().split())
        install = " ".join((root / "install.md").read_text().split())
        for rule in ('{"op":"device.wake","kw":{}}', '{"op":"url.open","kw":{"url":"https://example.com"}}',
                     "answer 409 (`The iPhone is locked. ...`)",
                     '`session.state` answers `"locked"` or `"standby"`', "Send `device.wake` and repeat the op",
                     "It answers `{state, was, woke, through}`",
                     "set up with no passcode", "an https link only, of at most 4096 characters",
                     "`$API/sessions/SID/op` with the API key", "answers a locked phone with 502 and no code"):
            self.assertIn(rule, api)
        self.assertIn("`wake()` wakes it and the step can run again", install)
        self.assertIn("set up with no passcode", install)

    def test_skill_says_how_to_turn_a_cloud_iphone_and_that_coordinates_go_stale(self):
        text = _skill_text()
        self.assertIn('- `rotate(to)` - Turn a cloud iPhone to `"portrait"`, `"landscape_left"` or '
                      '`"landscape_right"`. Cloud iPhones only.', text)
        section = " ".join(text.split("\n## Cloud iPhone\n", 1)[1].split("\n## ", 1)[0].split())
        for rule in (
                "**Which way up.**", "lies flat in a rack, so it does not turn by itself",
                '`rotate("landscape_left")`, `rotate("landscape_right")` and `rotate("portrait")`',
                "after a turn their size and every coordinate are new, so read the screen again before the next tap",
                '`screen_info()["window"]` is the size to go by',
                "`find_window()` can still report the size the session started with",
                "An app that supports only one way up stays that way",
                "`rotate()` returns `{device, orientation, turned, lock}`",
                # the lock is not a refusal: the turn deals with it, and says whether it is put back
                "If iOS's Portrait Orientation Lock is on, `rotate()` turns it off first",
                "goes through Settings: it takes about a minute and leaves the phone on its Home Screen",
                "open the app again afterwards",
                "The lock then stays off until a turn back to portrait, which puts it on again",
                "`lock` is `'off'` or `'on'` when the call changed the lock",
                "A turn that does not come back may still be going, and the error says so",
                "look at `screenshot()` before calling `rotate()` again",
                "A turn is refused on a phone at its lock screen (`wake()` first)",
                "Check `supports('device.rotate')` first",
                "| `device.rotate` | `to` | `{device, orientation, turned, lock}`."):
            self.assertIn(rule, section)
        for gone in ("raises `Portrait Orientation Lock is on`", "No helper turns the lock off", "stays upright"):
            self.assertNotIn(gone, section)
        root = Path(__file__).resolve().parents[1]
        api = " ".join((root / "setup" / "api.md").read_text().split())
        for rule in ('{"op":"device.rotate","kw":{"to":"landscape_left"}}', "portrait | landscape_left | landscape_right",
                     "after a turn read them again: the size and every coordinate are new",
                     "`screen.bounds` can still answer the size the session started with",
                     "It answers `{device, orientation, turned, lock}`",
                     "If iOS's Portrait Orientation Lock is on, the turn switches it off first",
                     "takes about a minute, so allow the request that long",
                     "If the request answers 502 first, the phone may still be turning",
                     "The lock then stays off until a turn back to portrait, which puts it on again",
                     "`device.wake`, `device.rotate` and `url.open`"):
            self.assertIn(rule, api)
        self.assertNotIn("orientation_locked", api)
        self.assertNotIn("(`Portrait Orientation Lock is on`)", api)

    def test_screenshot_prints_the_path_it_returns(self):
        import contextlib

        from phone_harness import helpers

        path = "/tmp/phone-harness-example.png"
        saved = helpers.send
        helpers.send = lambda op, **kw: (path, {"w": 1})
        self.addCleanup(setattr, helpers, "send", saved)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            returned = helpers.screenshot()
        self.assertEqual(returned, path)
        self.assertEqual(buf.getvalue().strip(), path)

    def test_screen_is_the_name_of_ocr(self):
        from phone_harness.helpers import ocr, screen
        self.assertIs(ocr, screen)
        self.assertEqual(screen.__defaults__, (0.3,))
