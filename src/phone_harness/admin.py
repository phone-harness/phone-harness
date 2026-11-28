"""Diagnostics: `phone-harness --doctor` walks the ladder for the phone the
helpers would drive — the config default, or `--doctor ios|android`."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _check(label, ok, hint="", fatal=True):
    """Print a check; a fatal failure is remembered for the verdict."""
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {hint}" if not ok and hint else ""))
    if not ok and fatal:
        _failures.append(label)
    return ok


_failures = []


def run_doctor(platform=None):
    from . import config
    platform = (platform or config.get("platform")).lower()
    print(f"phone-harness doctor — {platform}"
          f"{'' if platform == config.get('platform') else '  (default is ' + config.get('platform') + ')'}\n")
    _failures.clear()
    if platform == "android":
        _doctor_android()
    else:
        _doctor_ios()
    ok = not _failures
    print("\nall clear" if ok else "\nfix the FAILs above, then re-run")
    if not ok:
        print(CLOUD_HINT)
    return 0 if ok else 1


CLOUD_HINT = ("\nNo working phone here? A cloud phone needs no hardware: "
              "`phone-harness cloud login`, `phone-harness cloud ls`, then "
              "`phone-harness cloud start PHONE` (a cloud iPhone needs no adb; "
              "a cloud Android needs adb). "
              "No install possible? Use the HTTPS API: "
              "https://github.com/phone-harness/phone-harness/blob/main/setup/api.md")


def _host_apps():
    """The .app bundles this process runs under, nearest first, as
    (name, bundle path) pairs with repeats dropped. Agent hosts can run
    commands inside a nested, separately signed .app (Claude Desktop runs
    claude-code's own claude.app), which macOS may treat as its own
    permission subject (#17)."""
    apps, pid = [], os.getppid()
    for _ in range(40):
        if pid <= 1:
            break
        try:
            out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=5).stdout.strip()
            ppid, comm = out.split(None, 1)
        except (OSError, ValueError, subprocess.SubprocessError):
            break
        if ".app/" in comm:
            bundle = comm.split(".app/")[0] + ".app"
            name = bundle[:-len(".app")].rsplit("/", 1)[-1]
            if not any(b == bundle for _, b in apps):
                apps.append((name, bundle))
        pid = int(ppid)
    return apps


def _bundle_id(bundle):
    """CFBundleIdentifier from a bundle's Info.plist, or None."""
    import plistlib
    try:
        with open(os.path.join(bundle, "Contents", "Info.plist"), "rb") as f:
            return plistlib.load(f).get("CFBundleIdentifier")
    except (OSError, ValueError, plistlib.InvalidFileException):
        return None


def _host_app(apps=None):
    """The app macOS asks about: the outermost .app this process runs under
    (a terminal, or an agent's own app). When a nested app sits between it
    and this command, that one is named too, because some hosts need the
    grant on the nested app instead (#17). Falls back to a description."""
    apps = _host_apps() if apps is None else apps
    if not apps:
        return "the app that runs this command (your terminal or agent app)"
    outer, nearest = apps[-1][0], apps[0][0]
    if nearest != outer:
        return (f'"{outer}" (if that alone does not work, also turn on '
                f'"{nearest}", the app inside it that runs this command)')
    return f'"{outer}"'


def _reset_hint(service, apps=None):
    """How to clear a stale 'denied' record, which makes macOS skip the
    permission prompt and keeps flipping the switch from helping (#17)."""
    apps = _host_apps() if apps is None else apps
    bid = _bundle_id(apps[-1][1]) if apps else None
    cmd = f"tccutil reset {service} {bid}" if bid else f"tccutil reset {service} <bundle-id>"
    return (f"; if it is already on and still fails, remove it with the "
            f"\u2212 button and add it again, or run `{cmd}`")


# --- iPhone: pyobjc -> permissions -> Mirroring -> capture -> OCR -----------

def _doctor_ios():
    try:
        import Quartz, Vision, AppKit  # noqa: F401
        _check("pyobjc frameworks (Quartz, Vision, AppKit)", True)
    except ImportError as e:
        _check("pyobjc frameworks", False,
               f"pip install pyobjc-framework-Quartz pyobjc-framework-Vision "
               f"pyobjc-framework-Cocoa ({e})")
        return

    from ApplicationServices import AXIsProcessTrusted
    apps = _host_apps()
    host = _host_app(apps)
    _check("Accessibility permission (taps & keystrokes)", AXIsProcessTrusted(),
           f"System Settings > Privacy & Security > Accessibility: turn on {host}"
           f"{_reset_hint('Accessibility', apps)}")

    import Quartz as Q
    _check("Screen Recording permission (seeing the phone)",
           bool(Q.CGPreflightScreenCaptureAccess()),
           f"System Settings > Privacy & Security > Screen Recording: turn on {host}, "
           f"then quit and reopen it{_reset_hint('ScreenCapture', apps)}")

    from . import mirror
    _check(f"{mirror.APP_NAME} installed", Path(mirror.APP_PATH).exists(),
           "requires macOS Sequoia+ with a paired iPhone")

    running = mirror.running_app() is not None
    _check(f"{mirror.APP_NAME} running", running,
           "will auto-launch on first use — not fatal", fatal=False)

    win = mirror.find_window()
    _check("mirroring window found", win is not None,
           "open iPhone Mirroring once manually to pair the phone")
    if not win:
        return

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        path = f.name
    try:
        # Never crash here: a missing Screen Recording grant is exactly what
        # this check exists to report.
        r = subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), path],
                           capture_output=True)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        good = r.returncode == 0 and size > 20_000
        _check(f"window capture works ({size} bytes)", good,
               "capture failed or is blank — Screen Recording permission "
               f"takes effect only after {host} is quit and reopened")
        if good:
            from . import ocr
            n = len(ocr.recognize(path, win))
            _check(f"Vision OCR works ({n} text boxes)", True)
    finally:
        if os.path.exists(path):
            os.unlink(path)

    from . import ios
    state = ios.IPhone().send("session.state")
    _check(f"session state: {state}", state == "ready",
           "an interstitial is up (iPhone in Use / Connect / Mac Locked) — "
           "clear it on the Mac; lock the iPhone if it says in use", fatal=False)


# --- Android: adb -> a phone -> authorised -> awake -> tree ------------------

_ADB_INSTALL = {"darwin": "brew install android-platform-tools",
                "win32": "winget install Google.PlatformTools"}.get(sys.platform, "apt install adb (or your distro's android-tools)")
_SCRCPY_INSTALL = {"darwin": "brew install scrcpy", "win32": "winget install Genymobile.scrcpy"}.get(sys.platform, "apt install scrcpy")


def _doctor_android():
    from . import config
    adb = str(config.get("android.adb"))
    if not shutil.which(adb):
        _check(f"adb found ({adb})", False,
               _ADB_INSTALL + ", or set android.adb to the binary")
        return
    _check(f"adb found ({shutil.which(adb)})", True)
    _check("scrcpy found (optional: live mirror during `android awake`)",
           bool(shutil.which("scrcpy")), _SCRCPY_INSTALL + " — not required", fatal=False)

    from . import android
    phone = android.Android()
    state = phone.send("session.state")
    hints = {
        "no-device": "plug in with USB debugging on and tap Allow, or "
                     "Wireless debugging + `phone-harness android pair CODE`",
        "unauthorized": "tap Allow on the phone's 'Allow USB debugging?' prompt",
        "offline": "unplug/replug, or toggle Wireless debugging off and on",
        "locked": "unlock the phone (`phone-harness android awake` keeps it so)",
        "no-adb": "adb did not answer",
    }
    _check(f"a phone is reachable and ready (state: {state})",
           state in ("ready", "locked"), hints.get(state, ""))
    if state == "locked":
        _check("phone unlocked", False, hints["locked"], fatal=False)
    if state not in ("ready",):
        return

    b = phone.send("screen.bounds")
    label = android._phone_label(b["id"]) if b else "?"
    _check(f"talking to {label} ({b['id']}), screen {b['w']}x{b['h']}", bool(b))
    try:
        n = len(phone.send("tree"))
        _check(f"accessibility tree readable ({n} nodes)", n > 0)
    except RuntimeError as e:
        _check("accessibility tree readable", False, str(e)[:120], fatal=False)
    reg = config.devices_of("android")
    _check(f"remembered phones: {', '.join(reg['phones']) or 'none'}; primary: "
           f"{reg['primary'] or 'none'}", True)
