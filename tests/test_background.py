"""The background backend must not take the user's focus or pointer.

    python -m unittest tests.test_background
"""
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

WIN = {"id": 93, "x": 267.0, "y": 157.0, "w": 316.0, "h": 696.0}
# tap/scroll at (400, 500): window id, global point, point inside the window
ADDRESSED = (93, 400.0, 500.0, 133.0, 343.0)


@unittest.skipUnless(sys.platform == "darwin", "the background backend is macOS only")
class TestBackgroundInput(unittest.TestCase):
    def setUp(self):
        from phone_harness import background
        self.bg = background
        self.records = []        # every record handed to the window server
        self.front_calls = []    # every attempt to change the front process
        sky = SimpleNamespace(
            SLEventGetEventRecord=background._sky.SLEventGetEventRecord,
            SLPSPostEventRecordTo=lambda psn, buf: self.records.append(bytes(buf._obj)),
            _SLPSSetFrontProcessWithOptions=lambda *args: self.front_calls.append(args))
        for name, fake in (("_sky", sky), ("_ctx", lambda: (1, WIN))):
            patcher = mock.patch.object(background, name, fake)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_records(self, event_types):
        self.assertEqual([r[0x08] for r in self.records], event_types)
        for r in self.records:
            self.assertEqual(
                struct.unpack_from("<I", r, 0x3c) + struct.unpack_from("<dddd", r, 0x10),
                ADDRESSED)

    def test_tap_does_not_change_the_front_process(self):
        self.bg.tap(400.0, 500.0)
        self.assertEqual(self.front_calls, [])
        self.assert_records([1, 2])                 # mouse down, mouse up

    def test_key_press_activates_without_the_front_process(self):
        with mock.patch.object(self.bg.Quartz, "CGEventPostToPid") as post:
            self.bg.press("return")
        self.assertEqual(self.front_calls, [])
        self.assertEqual(post.call_count, 2)        # key down, key up
        # one "application activated" record, then a make-key pair per key edge
        self.assertEqual([r[0x08] for r in self.records], [0x0d, 1, 2, 1, 2])
        self.assertEqual(self.records[0][0x8a], 1)
        for r in self.records:
            self.assertEqual(struct.unpack_from("<I", r, 0x3c), (93,))

    def test_scroll_is_a_record_not_a_pointer_warp(self):
        with mock.patch.object(self.bg.Quartz, "CGWarpMouseCursorPosition") as warp, \
                mock.patch.object(self.bg.Quartz, "CGEventPost") as post, \
                mock.patch.object(self.bg.mirror, "activate") as activate:
            self.bg.scroll_wheel(-120, 400.0, 500.0, steps=6)
        warp.assert_not_called()
        post.assert_not_called()
        activate.assert_not_called()
        self.assertEqual(self.front_calls, [])
        self.assert_records([2] + [22] * 6)         # aim with a mouse up, then the wheel


if __name__ == "__main__":
    unittest.main()
