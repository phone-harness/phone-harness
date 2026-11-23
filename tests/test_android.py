"""Android backend behaviour that needs no phone: the commands it would send."""
import os
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from phone_harness import android as android_mod  # noqa: E402
from phone_harness.android import Android, TreeUnavailable  # noqa: E402


class Recorded(Android):
    """An Android whose adb shell is a list."""

    def __init__(self, installed=(), fail_motionevent=False, dumps=()):
        super().__init__()
        self.sent, self.installed, self.fail_motionevent = [], list(installed), fail_motionevent
        self.dumps, self.dump_calls, self.shots = list(dumps), 0, 0
        self._bounds = {"x": 0, "y": 0, "w": 720, "h": 1280, "id": "fake"}
        self._resolved = True

    def _screen_bounds(self):
        return self._bounds

    def _screen_require(self):
        return self._bounds

    def _adb(self, *args, binary=False, timeout=60):
        if "uiautomator" in args:
            self.dump_calls += 1
            return self.dumps.pop(0) if self.dumps else b"ERROR: could not get idle state."
        if "screencap" in args:
            self.shots += 1
            return b"\x89PNG-fake"
        raise AssertionError(args)

    def _pixel_text(self, min_confidence=0.3):
        self.shots += 1
        return [{"text": "Device name", "confidence": 0.9, "source": "pixels",
                 "x": 160, "y": 570, "w": 220, "h": 40}]

    def _gate(self):
        pass

    def _sh(self, cmd, timeout=60):
        self.sent.append(cmd)
        if self.fail_motionevent and "motionevent" in cmd:
            raise RuntimeError("Error: Unknown command: motionevent")
        if cmd.startswith("pm list packages"):
            return "\n".join(f"package:{p}" for p in self.installed)
        if cmd.startswith("cmd package resolve-activity"):
            return f"priority=0\n{cmd.split()[-1]}/.Main"
        return ""


class Scroll(unittest.TestCase):
    def test_a_scroll_holds_still_before_lifting_so_it_cannot_fling(self):
        phone = Recorded()
        phone._input_scroll(360, 640, dy=-768, dx=0, steps=10)
        (cmd,) = phone.sent
        self.assertTrue(cmd.startswith("input motionevent DOWN 360 1024"), cmd)
        self.assertIn("sleep 0.2 && input motionevent UP 360 256", cmd)
        self.assertNotIn("input swipe", cmd)

    def test_it_goes_sideways_and_stays_on_the_glass(self):
        phone = Recorded()
        phone._input_scroll(360, 640, dy=0, dx=-2000)
        (cmd,) = phone.sent
        self.assertTrue(cmd.startswith("input motionevent DOWN 676 640"), cmd)   # 94% of 720
        self.assertTrue(cmd.endswith("UP 43 640"), cmd)                          # 6% of 720

    def test_an_old_android_falls_back_to_a_slow_swipe_and_remembers(self):
        phone = Recorded(fail_motionevent=True)
        phone._input_scroll(360, 640, dy=-400)
        phone._input_scroll(360, 640, dy=-400)
        swipes = [c for c in phone.sent if c.startswith("input swipe")]
        self.assertEqual(len(swipes), 2)
        self.assertGreaterEqual(int(swipes[0].split()[-1]), 600)
        self.assertEqual(sum("motionevent" in c for c in phone.sent), 1)         # asked once


TREE = (b'<?xml version="1.0"?><hierarchy><node text="Apps" content-desc="" resource-id="" '
        b'class="android.widget.TextView" clickable="true" bounds="[100,900][300,960]"/></hierarchy>')


class Tree(unittest.TestCase):
    def test_a_never_idle_screen_is_asked_once_then_read_from_pixels(self):
        phone = Recorded()
        with unittest.mock.patch.object(android_mod, "_VISION", True):
            rows = phone._screen_text()
        self.assertEqual(phone.dump_calls, 1)                     # not five
        self.assertEqual([r["source"] for r in rows], ["pixels"])
        self.assertEqual(rows[0]["text"], "Device name")
        with unittest.mock.patch.object(android_mod, "_VISION", True):
            phone._screen_text()                                  # within the busy window:
        self.assertEqual(phone.dump_calls, 1)                     # ...no second dump at all

    def test_without_vision_it_fails_at_once_with_a_plain_message(self):
        phone = Recorded()
        with unittest.mock.patch.object(android_mod, "_VISION", False):
            with self.assertRaises(TreeUnavailable) as cm:
                phone._screen_text()
        self.assertEqual(phone.dump_calls, 1)
        self.assertIn("screenshot()", str(cm.exception))
        self.assertNotIn("animates", str(cm.exception))

    def test_a_good_tree_is_preferred_and_clears_the_busy_window(self):
        phone = Recorded(dumps=[TREE])
        phone._tree_busy_until = 0.0
        rows = phone._screen_text()
        self.assertEqual([(r["text"], r["source"], r["x"], r["y"]) for r in rows],
                         [("Apps", "tree", 200, 930)])
        self.assertEqual(phone.shots, 0)

    def test_a_transient_failure_is_retried_briefly(self):
        phone = Recorded(dumps=[b"garbage", TREE])
        with unittest.mock.patch.object(android_mod.time, "sleep"):
            rows = phone._screen_text()
        self.assertEqual(phone.dump_calls, 2)
        self.assertEqual(rows[0]["text"], "Apps")


class Launch(unittest.TestCase):
    INSTALLED = ["com.android.chrome", "com.android.chrome.helper", "com.facebook.orca",
                 "com.facebook.katana", "com.zhiliaoapp.musically", "com.whatsapp"]

    def launched(self, name):
        phone = Recorded(self.INSTALLED)
        return phone._apps_launch(name), phone.sent[-1]

    def test_names_people_say(self):
        for name, pkg in [("TikTok", "com.zhiliaoapp.musically"), ("tik tok", "com.zhiliaoapp.musically"),
                          ("Facebook", "com.facebook.katana"), ("Messenger", "com.facebook.orca"),
                          ("chrome", "com.android.chrome"), ("WhatsApp", "com.whatsapp"),
                          ("com.whatsapp", "com.whatsapp")]:
            with self.subTest(name=name):
                got, last = self.launched(name)
                self.assertEqual(got, pkg)
                self.assertEqual(last, f"am start -W -n {pkg}/.Main")


class ResolvePrimary(unittest.TestCase):
    """A saved primary that is gone is a failure. Another paired phone is not a substitute."""

    def setUp(self):
        self._saved = os.environ.pop("ANDROID_SERIAL", None)

    def tearDown(self):
        os.environ.pop("ANDROID_SERIAL", None)
        if self._saved is not None:
            os.environ["ANDROID_SERIAL"] = self._saved

    def phone(self):
        phone = Android.__new__(Android)
        phone._resolved = False
        return phone

    def test_an_unreachable_primary_does_not_connect_another_phone(self):
        phone = self.phone()
        cfg = {"primary": "pixel", "phones": {"pixel": {"serial": "PRIMARY"}}}
        with unittest.mock.patch.object(android_mod, "_load", return_value=cfg), \
             unittest.mock.patch.object(android_mod, "_attached", return_value=[
                 ("USB1", "device", "usb"), ("10.0.0.8:5555", "device", "wifi")]), \
             unittest.mock.patch.object(android_mod, "_prop", return_value="OTHER"), \
             unittest.mock.patch.object(android_mod, "_mdns", return_value=[
                 {"serial": "OTHER", "addr": "10.0.0.8:5555"}]), \
             unittest.mock.patch.object(android_mod, "_run") as run, \
             unittest.mock.patch.object(android_mod, "_remember"), \
             unittest.mock.patch("phone_harness.cloud.attached", return_value=None):
            with self.assertRaises(android_mod.PrimaryUnreachable) as cm:
                phone._resolve()
        self.assertIn("unreachable", str(cm.exception))
        self.assertIn("pixel", str(cm.exception))
        run.assert_not_called()
        self.assertNotIn("ANDROID_SERIAL", os.environ)

    def test_the_primary_is_used_when_it_is_already_up(self):
        phone = self.phone()
        cfg = {"primary": "pixel", "phones": {"pixel": {"serial": "PRIMARY"}}}

        def prop(adb_id, name):
            if name == "ro.serialno":
                return "PRIMARY" if adb_id == "10.0.0.5:5555" else "OTHER"
            return "Pixel"

        with unittest.mock.patch.object(android_mod, "_load", return_value=cfg), \
             unittest.mock.patch.object(android_mod, "_attached", return_value=[
                 ("USB1", "device", "usb"), ("10.0.0.5:5555", "device", "wifi")]), \
             unittest.mock.patch.object(android_mod, "_prop", side_effect=prop), \
             unittest.mock.patch.object(android_mod, "_mdns") as mdns, \
             unittest.mock.patch.object(android_mod, "_run") as run, \
             unittest.mock.patch.object(android_mod, "_remember"), \
             unittest.mock.patch("phone_harness.cloud.attached", return_value=None):
            chosen = phone._resolve()
        self.assertEqual(chosen, "10.0.0.5:5555")
        mdns.assert_not_called()
        run.assert_not_called()

    def test_mdns_connects_only_the_primary(self):
        phone = self.phone()
        cfg = {"primary": "pixel", "phones": {"pixel": {"serial": "PRIMARY"}}}
        ready = []

        def attached():
            return list(ready)

        def run(*args, **_kw):
            if args and args[0] == "connect":
                ready.append((args[1], "device", "wifi"))
                return "connected to " + args[1]
            return ""

        def prop(adb_id, name):
            return "PRIMARY" if name == "ro.serialno" else "Pixel"

        services = [
            {"serial": "OTHER", "addr": "10.0.0.6:5555"},
            {"serial": "PRIMARY", "addr": "10.0.0.5:5555"},
        ]
        with unittest.mock.patch.object(android_mod, "_load", return_value=cfg), \
             unittest.mock.patch.object(android_mod, "_attached", side_effect=attached), \
             unittest.mock.patch.object(android_mod, "_prop", side_effect=prop), \
             unittest.mock.patch.object(android_mod, "_mdns", return_value=services), \
             unittest.mock.patch.object(android_mod, "_run", side_effect=run) as run_mock, \
             unittest.mock.patch.object(android_mod, "_remember"), \
             unittest.mock.patch("phone_harness.cloud.attached", return_value=None):
            chosen = phone._resolve()
        self.assertEqual(chosen, "10.0.0.5:5555")
        connects = [c.args[1] for c in run_mock.call_args_list if c.args and c.args[0] == "connect"]
        self.assertEqual(connects, ["10.0.0.5:5555"])

    def test_usb_is_used_when_no_primary_is_configured(self):
        phone = self.phone()
        cfg = {"phones": {"pixel": {"serial": "AAA"}}}
        with unittest.mock.patch.object(android_mod, "_load", return_value=cfg), \
             unittest.mock.patch.object(android_mod, "_attached", return_value=[
                 ("USB1", "device", "usb")]), \
             unittest.mock.patch.object(android_mod, "_prop", return_value="AAA"), \
             unittest.mock.patch.object(android_mod, "_mdns") as mdns, \
             unittest.mock.patch.object(android_mod, "_run") as run, \
             unittest.mock.patch.object(android_mod, "_remember"), \
             unittest.mock.patch("phone_harness.cloud.attached", return_value=None):
            chosen = phone._resolve()
        self.assertEqual(chosen, "USB1")
        mdns.assert_not_called()
        run.assert_not_called()

    def test_session_state_does_not_hide_an_unreachable_primary(self):
        phone = self.phone()
        phone._resolve = unittest.mock.Mock(
            side_effect=android_mod.PrimaryUnreachable(
                "The primary Android phone 'pixel' is unreachable"))
        with self.assertRaises(android_mod.PrimaryUnreachable) as cm:
            phone._session_state()
        self.assertIn("unreachable", str(cm.exception))
        self.assertNotIn("no-adb", str(cm.exception))



DUMPSYS_NOTIF_SAMPLE = """
Notification Record List:
  NotificationRecord(0x7f8a123: pkg=com.google.android.apps.messaging user=UserHandle{0} id=101 tag=null: Notification(channel=sms pri=0))
    uid=10123 userId=0 pkg=com.google.android.apps.messaging
    key=0|com.google.android.apps.messaging|101|null|10123
    postTime=1732000000000
    flags=0x10
    extras={
      android.title=String (Google)
      android.text=String (Your verification code is 482910. Valid for 10 minutes.)
      android.subText=null
      android.template=String (android.app.Notification$BigTextStyle)
    }

  NotificationRecord(0x7f8a456: pkg=com.whatsapp user=UserHandle{0} id=202 tag=null: Notification(channel=messages pri=1))
    uid=10155 userId=0 pkg=com.whatsapp
    key=0|com.whatsapp|202|null|10155
    postTime=1732000005000
    extras={
      android.title=String (Alice)
      android.text=String (Hey, are you free tonight?)
    }

  NotificationRecord(0x7f8a789: pkg=com.android.systemui user=UserHandle{0} id=303 tag=null: Notification(channel=status pri=-1))
    uid=1000 userId=0 pkg=com.android.systemui
    key=0|com.android.systemui|303|null|1000
    postTime=1731999900000
    extras={
      android.title=String (USB debugging connected)
      android.text=String (Tap to turn off USB debugging)
    }
"""


class AndroidNotificationTests(unittest.TestCase):
    def test_parse_notifications_extracts_records(self):
        records = android_mod._parse_notifications(DUMPSYS_NOTIF_SAMPLE)
        self.assertEqual(len(records), 3)

        sms = records[0]
        self.assertEqual(sms["package"], "com.google.android.apps.messaging")
        self.assertEqual(sms["title"], "Google")
        self.assertEqual(sms["text"], "Your verification code is 482910. Valid for 10 minutes.")
        self.assertEqual(sms["time"], 1732000000000)
        self.assertEqual(sms["key"], "0|com.google.android.apps.messaging|101|null|10123")

        whatsapp = records[1]
        self.assertEqual(whatsapp["package"], "com.whatsapp")
        self.assertEqual(whatsapp["title"], "Alice")
        self.assertEqual(whatsapp["text"], "Hey, are you free tonight?")

    def test_parse_notifications_multiline_bigtext(self):
        dump = """
  NotificationRecord(0x111: pkg=com.bank user=UserHandle{0} id=1 tag=null: Notification())
    uid=101 key=0|com.bank|1|null|101 postTime=123456
    extras={
      android.title=String (Bank Alert)
      android.text=String (Code: 123)
      android.bigText=String (Line 1: Your login OTP is 987654.\nLine 2: Expires soon.)
    }
"""
        records = android_mod._parse_notifications(dump)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["title"], "Bank Alert")
        self.assertEqual(records[0]["text"], "Line 1: Your login OTP is 987654.\nLine 2: Expires soon.")

    def test_notification_list_op(self):
        phone = android_mod.Android(serial="fake-device")
        with unittest.mock.patch.object(phone, "_gate"), \
             unittest.mock.patch.object(phone, "_sh", return_value=DUMPSYS_NOTIF_SAMPLE):
            all_records = phone.send("notification.list")
            self.assertEqual(len(all_records), 3)
            self.assertEqual(all_records[0]["package"], "com.google.android.apps.messaging")

            limited = phone.send("notification.list", limit=1)
            self.assertEqual(len(limited), 1)
            self.assertEqual(limited[0]["package"], "com.google.android.apps.messaging")

    def test_wait_for_notification_extracts_otp(self):
        from phone_harness import helpers
        phone = android_mod.Android(serial="fake-device")
        with unittest.mock.patch.object(helpers, "phone", phone), \
             unittest.mock.patch.object(helpers, "send", lambda op, **kw: phone.send(op, **kw)), \
             unittest.mock.patch.object(phone, "_gate"), \
             unittest.mock.patch.object(phone, "_sh", return_value=DUMPSYS_NOTIF_SAMPLE):
            # Test extracting 6-digit OTP code using regex capture group
            otp = helpers.wait_for_notification(r"\b(\d{6})\b", timeout=1.0)
            self.assertEqual(otp, "482910")

            # Test matching whole notification dict
            notif = helpers.wait_for_notification("Alice", timeout=1.0)
            self.assertIsInstance(notif, dict)
            self.assertEqual(notif["title"], "Alice")

    def test_wait_for_notification_timeout(self):
        from phone_harness import helpers
        with unittest.mock.patch.object(helpers, "notifications", return_value=[]):
            with self.assertRaises(TimeoutError):
                helpers.wait_for_notification("Nonexistent", timeout=0.1, interval=0.05)


if __name__ == "__main__":
    unittest.main()
