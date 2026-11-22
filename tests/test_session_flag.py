"""`--session SID` and `--session=SID` are the same flag.

The pin decides which cloud phone a script drives: `_take_session` lifts it off
argv and puts it in PHONE_HARNESS_SESSION, and cloud.attached() reads it from
there so a script cannot fall through to whatever phone is attached. Missing
the `=` spelling meant the pin never arrived, so the script ran against another
phone, and the raw sid was also left in the argv sent as telemetry.

    python -m unittest tests.test_session_flag
"""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SRC = str(Path(__file__).resolve().parents[1] / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from phone_harness import run  # noqa: E402


class BothSpellings(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("PHONE_HARNESS_SESSION", None)

    def test_the_equals_spelling_pins_the_session_and_leaves_no_argv_behind(self):
        self.assertEqual(run._take_session(["--session=SID-1"]), [])
        self.assertEqual(os.environ.get("PHONE_HARNESS_SESSION"), "SID-1")

    def test_the_equals_spelling_still_pins_ahead_of_a_command(self):
        self.assertEqual(run._take_session(["--session=SID-1", "cloud", "ls"]), ["cloud", "ls"])
        self.assertEqual(os.environ.get("PHONE_HARNESS_SESSION"), "SID-1")

    def test_an_empty_sid_is_not_a_pin(self):
        self.assertEqual(run._take_session(["--session=", "cloud", "ls"]), ["cloud", "ls"])
        self.assertIsNone(os.environ.get("PHONE_HARNESS_SESSION"))

    def test_the_space_spelling_is_unchanged(self):
        self.assertEqual(run._take_session(["--session", "SID-1", "cloud", "ls"]), ["cloud", "ls"])
        self.assertEqual(os.environ.get("PHONE_HARNESS_SESSION"), "SID-1")


class Telemetry(unittest.TestCase):
    """The pin is the event's session_id, so its sid is never sent as argv."""

    def test_neither_spelling_leaves_the_sid_in_the_recorded_command_line(self):
        for args in (["--session", "sid1", "cloud", "start", "ios"],
                     ["--session=sid1", "cloud", "start", "ios"]):
            with self.subTest(args=args):
                argv = run._telemetry_argv(list(args))
                self.assertEqual(argv, ["cloud", "start", "ios"])
                self.assertEqual(run._telemetry_command(argv), "cloud")

    def test_the_equals_spelling_of_a_script_is_still_a_script(self):
        for args in (["--session", "sid1"], ["--session=sid1"]):
            with self.subTest(args=args):
                self.assertEqual(run._telemetry_command(run._telemetry_argv(list(args))), "script")


if __name__ == "__main__":
    unittest.main()
