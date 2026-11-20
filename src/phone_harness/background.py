"""Background backend — drive iPhone Mirroring WITHOUT bringing it to the front.

The default (mirror.py) backend must make the iPhone Mirroring window frontmost
before every action: it captures with `screencapture` and injects with
`CGEventPost`, both of which target the focused app, so automation steals your
screen for its whole run.

This backend removes that. Two pieces, both proven to work with the window
unfocused and another app frontmost:

  EYES  - CGWindowListCreateImage captures a specific window by id even when it
          is not the active app (and even when occluded).

  HANDS - the input path macOS actually gates on is the app being *active*, not
          merely its window being key. A normal CGEvent can't cross that. But
          the window server accepts a synthesized event record delivered
          straight to a process via SkyLight's SLPSPostEventRecordTo (the same
          mechanism yabai uses to focus windows without raising them). Written
          with a real location, it lands a positioned tap/drag in iPhone
          Mirroring while your frontmost app never changes.

The event-record layout is yabai's (window_manager_make_key_window): a 0xf8
buffer, length at 0x04, CGSEventType at 0x08 (1=down, 2=up, 6=dragged),
location at 0x10 and windowLocation at 0x20 as CGPoints, window id at 0x3c.
yabai blanks the location to signal "focus"; we write the real point to make
it a click. Every write stays inside the buffer, so a wrong value is a no-op,
never a crash.

Select with PHONE_HARNESS_BACKGROUND=1. Coordinates use the same global
screen-point convention as the mirror backend and screen(), so every helper on
top (tap_text, swipe, scroll_collect) works unchanged — just without focus.

Keyboard (type_text/press) makes the app AppKit-active with an activate
record, never the front process, so the user's own typing stays in their app.
"""
import ctypes, ctypes.util, os, struct, subprocess, tempfile, time
from contextlib import contextmanager
from pathlib import Path

import objc
import Quartz
from AppKit import NSRunningApplication

from . import mirror

APP_NAME = "iPhone Mirroring"
BUNDLE_ID = "com.apple.ScreenContinuity"
TMP = Path(tempfile.gettempdir()) / "phone-harness"
TMP.mkdir(exist_ok=True)

# --- SkyLight private API ---
_sky = ctypes.CDLL("/System/Library/PrivateFrameworks/SkyLight.framework/SkyLight")
_appserv = ctypes.CDLL(ctypes.util.find_library("ApplicationServices"))


class _PSN(ctypes.Structure):
    _fields_ = [("hi", ctypes.c_uint32), ("lo", ctypes.c_uint32)]


_appserv.GetProcessForPID.argtypes = [ctypes.c_int, ctypes.POINTER(_PSN)]
_appserv.GetProcessForPID.restype = ctypes.c_int
_sky.SLPSPostEventRecordTo.argtypes = [ctypes.POINTER(_PSN), ctypes.c_void_p]
_sky.SLEventGetEventRecord.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
_sky.SLEventGetEventRecord.restype = ctypes.c_int

# CGSEventType values (share the CGEventType numbering)
_LMOUSE_DOWN, _LMOUSE_UP, _LMOUSE_DRAGGED = 1, 2, 6


# --- window / app state (reused from mirror; none of these activate) ---

def find_window():
    """The phone window, on the active Space or not.

    SkyLight event records are addressed to a process and a window id, so this
    backend reaches the window wherever it is. mirror.py keeps the on-screen
    default because it posts CGEvents at global screen coordinates, which land
    on whatever is actually in front.

    Inheriting mirror's default is why a terminal on a different Space from the
    phone made the harness report a disconnected phone (#8) — the window was
    there the whole time, just not on the Space being asked about.
    """
    return mirror.find_window(on_screen=False)


running_app = mirror.running_app
window_ax_content = mirror.window_ax_content
window_ax_buttons = mirror.window_ax_buttons
press_window_button = mirror.press_window_button
ax_observer_target = mirror.ax_observer_target
ax_session_hint = mirror.ax_session_hint
launch = mirror.launch
focus_probe = mirror.focus_probe
interruption = mirror.interruption
frontmost_window = mirror.frontmost_window


# Shared with the mirror backend. Nothing here needs focus, but screen_info()
# reports the value and a wrong answer sends people hunting for focus bugs
# that are not there.
is_frontmost = mirror.is_frontmost


def activate():
    """No-op: the whole point of this backend is never to take focus."""
    return None


# session.require shows the window once at the start of a task so the user
# can watch; that is the only time this backend raises it on purpose.
show = mirror.activate


def ensure_window(timeout=5.0):
    win = find_window()
    if win is None:
        if running_app() is None:
            raise RuntimeError(
                f"{APP_NAME} isn't running — open it and connect your phone.")
        raise RuntimeError(
            f"{APP_NAME} has no phone window — connect your phone, then retry.")
    return win


# --- capture (eyes), no focus ---

def capture(path=None, retries=2):
    """Capture the mirroring window as a PNG without activating it.

    Returns (path, window_bounds), matching mirror.capture()."""
    path = str(path or TMP / "background.png")
    last = None
    for _ in range(retries + 1):
        win = find_window() or ensure_window()
        img = Quartz.CGWindowListCreateImage(
            Quartz.CGRectNull, Quartz.kCGWindowListOptionIncludingWindow,
            win["id"],
            Quartz.kCGWindowImageBoundsIgnoreFraming
            | Quartz.kCGWindowImageNominalResolution)
        if img is not None and Quartz.CGImageGetWidth(img) > 0:
            url = Quartz.CFURLCreateWithFileSystemPath(
                None, path, Quartz.kCFURLPOSIXPathStyle, False)
            dest = Quartz.CGImageDestinationCreateWithURL(url, "public.png", 1, None)
            Quartz.CGImageDestinationAddImage(dest, img, None)
            if Quartz.CGImageDestinationFinalize(dest):
                return path, win
            last = "could not encode PNG"
        elif _screencapture(win, path):
            # CGWindowListCreateImage renders nothing for a window that is not
            # on the active Space. `screencapture -l` still reaches it, with
            # live frames rather than a stale backing store. It costs a
            # subprocess, so it stays the fallback. Its image is Retina where
            # the fast path is point-resolution; ocr.recognize derives the
            # scale from the window, so both work.
            return path, win
        else:
            last = "CGWindowListCreateImage returned nothing, screencapture failed"
        time.sleep(0.3)
    raise RuntimeError(f"background capture failed: {last}")


def _screencapture(win, path):
    """Window capture via the screencapture binary. True if it wrote a PNG."""
    if os.path.exists(path):
        os.remove(path)
    subprocess.run(["screencapture", "-x", "-o", "-l", str(win["id"]), path],
                   capture_output=True)
    return os.path.exists(path) and os.path.getsize(path) > 1000


# --- input (hands), no focus ---

def _deliver(pid, wid, buf, gx, gy, lx, ly):
    """Address an event record to the window and hand it to the process."""
    struct.pack_into("<I", buf, 0x3c, wid)          # target window id
    struct.pack_into("<dd", buf, 0x10, gx, gy)      # location (global points)
    struct.pack_into("<dd", buf, 0x20, lx, ly)      # windowLocation (local)
    psn = _PSN()
    _appserv.GetProcessForPID(pid, ctypes.byref(psn))
    _sky.SLPSPostEventRecordTo(ctypes.byref(psn), ctypes.byref(buf))


def _post(pid, wid, etype, gx, gy, lx, ly):
    """Deliver one synthesized mouse event record to the process by pid."""
    buf = (ctypes.c_uint8 * 0xf8)()
    buf[0x04] = 0xf8                       # record length
    buf[0x3a] = 0x10                       # yabai's required flag byte
    buf[0x08] = etype
    _deliver(pid, wid, buf, gx, gy, lx, ly)


def _ctx():
    win = find_window() or ensure_window()
    return running_app().processIdentifier(), win


def _emit(etype, gx, gy, pid, win):
    _post(pid, win["id"], etype, gx, gy, gx - win["x"], gy - win["y"])


def tap(x, y):
    pid, win = _ctx()
    _emit(_LMOUSE_DOWN, x, y, pid, win)
    time.sleep(0.05)
    _emit(_LMOUSE_UP, x, y, pid, win)


def long_press(x, y, duration=0.8):
    pid, win = _ctx()
    _emit(_LMOUSE_DOWN, x, y, pid, win)
    time.sleep(duration)
    _emit(_LMOUSE_UP, x, y, pid, win)


def drag(x1, y1, x2, y2, duration=0.35, steps=14):
    """Touch-drag (an iOS swipe), delivered with the window unfocused."""
    pid, win = _ctx()
    _emit(_LMOUSE_DOWN, x1, y1, pid, win)
    time.sleep(0.02)
    for i in range(1, steps + 1):
        t = i / steps
        _emit(_LMOUSE_DRAGGED, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, pid, win)
        time.sleep(duration / steps)
    _emit(_LMOUSE_UP, x2, y2, pid, win)


def scroll_wheel(dy, x, y, steps=6, dx=0):
    """Scroll with an event record, like a tap: no pointer, no focus.

    macOS routes a scroll event to the window under the REAL cursor, not to the
    active application and not to the event's own location field. That single
    fact explains everything that failed here:

      - the old flick (down 0.72h, drag, up 0.28h) never scrolled at all: iOS
        read it as a TAP at the touch-down point and opened whatever row sat
        there. Silent, and destructive on a Home Screen or a chat list.
      - a wheel event posted with CGEventPostToPid does nothing, with or
        without the continuous/scroll-phase fields a real trackpad sets:
        posting to a pid bypasses the hit-testing that routes scrolls.
      - a hand-built SkyLight scroll record (CGSEventType 22): nothing at any
        delta offset tried. The wheel deltas sit further in than the mouse
        fields, from 0x88 on macOS 26.6.
      - arrow keys, space and cmd+down over the working background key path:
        nothing; iOS lists don't scroll from those.
      - posting to the HID tap with only CGEventSetLocation set: nothing,
        because the cursor was elsewhere on screen.

    So don't guess the record layout: make a real scroll CGEvent and have
    SLEventGetEventRecord serialize it, then deliver it like the mouse records.
    That skips the cursor routing, so the pointer is never warped and the
    window is never raised.

    The record's location does not aim it. The phone scrolls whatever sits
    under ITS pointer, which stays where the last touch left it: after a tap on
    a tab bar, a scroll sent to the middle of the list moved nothing. A lone
    mouse-up at (x, y) moves that pointer without touching the screen. A
    mouse-moved record does not.
    """
    pid, win = _ctx()            # window must exist; raises with a clear message
    _emit(_LMOUSE_UP, x, y, pid, win)
    time.sleep(0.05)
    for _ in range(steps):
        ev = Quartz.CGEventCreateScrollWheelEvent(
            None, Quartz.kCGScrollEventUnitPixel, 2,
            int(dy / steps), int(dx / steps))
        buf = (ctypes.c_uint8 * 0xf8)()
        if _sky.SLEventGetEventRecord(objc.pyobjc_id(ev), ctypes.byref(buf), 0xf8):
            raise RuntimeError("could not serialize the scroll event")
        _deliver(pid, win["id"], buf, x, y, x - win["x"], y - win["y"])
        time.sleep(0.03)


# --- keyboard (background), via activate + make-key + CGEventPostToPid ---
#
# Keyboard is delivered differently from mouse: the keystroke goes to the key
# window's text responder. Making the app AppKit-active and the window key
# (yabai's focus record: a down/up pair with a blanked location) and then
# posting the key event to the process by pid lands the text while another app
# stays the front process — verified by typing into Spotlight.

def _activate(pid, wid):
    """Make iPhone Mirroring AppKit-active without making it the front process.

    The app only handles keys while it believes it is active. Setting the front
    process does that, and also sends everything the user types to the phone.
    The window server's own "application activated" record does it alone: the
    app runs applicationWillBecomeActive and takes keys posted by pid, while
    the user's app keeps the front process and their keyboard.
    """
    buf = (ctypes.c_uint8 * 0xf8)()
    buf[0x04] = 0xf8
    buf[0x08] = 0x0d                    # AppKit-defined event
    buf[0x8a] = 0x01                    # subtype: application activated
    _deliver(pid, wid, buf, 0, 0, 0, 0)


def _make_key(pid, wid):
    buf = (ctypes.c_uint8 * 0xf8)()
    buf[0x04] = 0xf8
    buf[0x3a] = 0x10
    struct.pack_into("<I", buf, 0x3c, wid)
    for i in range(0x10):
        buf[0x20 + i] = 0xff            # blanked location => "focus", not a click
    psn = _PSN()
    _appserv.GetProcessForPID(pid, ctypes.byref(psn))
    buf[0x08] = _LMOUSE_DOWN
    _sky.SLPSPostEventRecordTo(ctypes.byref(psn), ctypes.byref(buf))
    buf[0x08] = _LMOUSE_UP
    _sky.SLPSPostEventRecordTo(ctypes.byref(psn), ctypes.byref(buf))


def _key_edge(pid, wid, code, down, flags=0):
    _make_key(pid, wid)                 # keep the window key across the keystroke
    ev = Quartz.CGEventCreateKeyboardEvent(None, code, down)
    if flags:
        # Mac-side consumers only. iPhone Mirroring forwards raw HID keycodes
        # to iOS and drops the flag mask, so a modifier expressed as a flag
        # never reaches the phone — it has to be a key that is held.
        Quartz.CGEventSetFlags(ev, flags)
    Quartz.CGEventPostToPid(pid, ev)
    time.sleep(0.03)


def _key(pid, wid, code, flags=0):
    for down in (True, False):
        _key_edge(pid, wid, code, down, flags)


@contextmanager
def _holding(pid, wid, mods):
    """Hold real modifier keys down around the body. See mirror._holding."""
    acc = 0
    for m in mods:
        acc |= mirror._MODIFIERS[m]
        _key_edge(pid, wid, mirror._MOD_KEYCODES[m], True, acc)
    try:
        yield acc
    finally:
        # Unconditional: a latched modifier corrupts every later keystroke, and
        # the damage surfaces somewhere else entirely.
        for m in reversed(mods):
            # Clear the bit *before* posting the release. A key-up still
            # carrying its own flag reads as "still held", which latches shift
            # on and turns the rest of the string into 1,200 -> !<@)).
            acc &= ~mirror._MODIFIERS[m]
            _key_edge(pid, wid, mirror._MOD_KEYCODES[m], False, acc)


def press(combo):
    """press('return'), press('cmd+1'), press('cmd+3') — no focus change."""
    pid, win = _ctx()
    parts = combo.lower().split("+")
    key, mods = parts[-1], parts[:-1]
    if key not in mirror._KEYCODES:
        raise ValueError(f"unknown key {key!r}")
    for m in mods:
        if m not in mirror._MOD_KEYCODES:
            raise ValueError(f"unknown modifier {m!r}")
    _activate(pid, win["id"])
    with _holding(pid, win["id"], mods) as flags:
        _key(pid, win["id"], mirror._KEYCODES[key], flags)


def _type_keystrokes(text, delay=0.03):
    """Type via real keycodes, no focus change. Subject to iOS autocorrect,
    which rewrites words as they are typed."""
    pid, win = _ctx()
    _activate(pid, win["id"])
    for i, line in enumerate(text.split("\n")):
        if i:
            _key(pid, win["id"], mirror._KEYCODES["return"])
        for ch in line:
            code, shifted = mirror._keycode_for(ch)
            if code is None:
                raise ValueError(f"cannot type {ch!r} via keycodes")
            with _holding(pid, win["id"], ["shift"] if shifted else []) as flags:
                _key(pid, win["id"], code, flags)
            time.sleep(delay)


def type_text(text, delay=0.03, keystrokes=False):
    """Type into the focused iOS field, no focus change.

    Pastes by default so the text arrives exactly as written, past autocorrect
    and keyboard layout both. keystrokes=True sends real key events instead.
    """
    if keystrokes or not text:
        return _type_keystrokes(text, delay)
    mirror.paste_with(press, text)
