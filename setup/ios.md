# Personal iPhone (iPhone Mirroring)

Drives the user's own iPhone through the Mac's iPhone Mirroring window.

## Needs

- A Mac on macOS 15 (Sequoia) or later, with the iPhone Mirroring app.
  Apple's own requirements apply: an iOS 18+ iPhone signed in to the same
  Apple ID, nearby, locked, with Bluetooth and Wi-Fi on.
- Python 3.10+ and the Mac-only dependencies, which the normal install pulls.
- Two macOS permissions for **the app that runs Python** (the terminal, or
  the agent's own app if it runs commands itself), in System Settings >
  Privacy & Security:
  - **Accessibility**: taps and typing. Takes effect at once.
  - **Screen Recording**: seeing the phone. Takes effect after that app
    restarts.
  macOS asks about the outermost app, not Python itself. Some agent hosts
  run commands inside a nested, separately signed app (Claude Desktop runs
  Claude Code's own `claude` app), and macOS can treat that nested app as its
  own subject; if turning on the outer app does not work, turn on the nested
  one too. `phone-harness doctor ios` names both when a permission is
  missing.

```bash
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
```

## Steps only the user can do

1. Open iPhone Mirroring once and finish pairing (needs the phone in hand).
2. Grant the two permissions above, then restart the app that runs Python.

## Check

`phone-harness doctor ios`. It checks each step in order and names the first
one that is missing. If it passes but taps or capture do nothing, look for a
macOS permission prompt on the Mac.

If a permission is on but still fails, macOS may hold a stale "denied" record
for that app. Flipping the switch does not clear it, and macOS will not prompt
again. Select the app in the list, remove it with the − button and add it
again, or reset it by bundle ID (the doctor prints the exact command):

```bash
tccutil reset ScreenCapture com.example.app   # or: tccutil reset Accessibility …
```

Not on a Mac, or no iPhone nearby? Use a [cloud phone](cloud.md).
