"""Which app the doctor tells you to grant permissions to (#17)."""
import os
import plistlib
import subprocess
import tempfile
import unittest
from unittest import mock

from phone_harness import admin


def _fake_ps(chain):
    """chain: {pid: (ppid, comm)}. Returns a subprocess.run stand-in."""
    def run(args, **kwargs):
        pid = int(args[-1])
        ppid, comm = chain.get(pid, (1, "launchd"))
        return subprocess.CompletedProcess(args, 0, stdout=f"{ppid} {comm}\n")
    return run


CLAUDE_DESKTOP = {
    500: (400, "/bin/zsh"),
    400: (300, "/Users/u/Library/Application Support/Claude/claude-code/2.1.0/"
               "claude.app/Contents/MacOS/claude"),
    300: (1, "/Applications/Claude.app/Contents/MacOS/Claude"),
}

TERMINAL = {
    500: (400, "-zsh"),
    400: (300, "login"),
    300: (1, "/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal"),
}

VSCODE = {
    500: (400, "/bin/zsh"),
    400: (300, "/Applications/Visual Studio Code.app/Contents/Frameworks/"
               "Code Helper (Plugin).app/Contents/MacOS/Code Helper (Plugin)"),
    300: (1, "/Applications/Visual Studio Code.app/Contents/MacOS/Electron"),
}


class HostAppTest(unittest.TestCase):
    def apps(self, chain):
        with mock.patch.object(admin.os, "getppid", return_value=500), \
                mock.patch.object(admin.subprocess, "run", _fake_ps(chain)):
            return admin._host_apps()

    def test_nested_agent_app_is_named_as_fallback(self):
        apps = self.apps(CLAUDE_DESKTOP)
        self.assertEqual([n for n, _ in apps], ["claude", "Claude"])
        hint = admin._host_app(apps)
        self.assertTrue(hint.startswith('"Claude"'), hint)
        self.assertIn('also turn on "claude"', hint)

    def test_plain_terminal_is_named_alone(self):
        apps = self.apps(TERMINAL)
        self.assertEqual(admin._host_app(apps), '"Terminal"')

    def test_helpers_inside_one_app_collapse_to_that_app(self):
        apps = self.apps(VSCODE)
        self.assertEqual(admin._host_app(apps), '"Visual Studio Code"')

    def test_no_app_falls_back_to_description(self):
        self.assertIn("your terminal or agent app", admin._host_app([]))

    def test_reset_hint_uses_bundle_id_when_readable(self):
        with tempfile.TemporaryDirectory() as d:
            bundle = os.path.join(d, "claude.app")
            os.makedirs(os.path.join(bundle, "Contents"))
            with open(os.path.join(bundle, "Contents", "Info.plist"), "wb") as f:
                plistlib.dump({"CFBundleIdentifier": "com.anthropic.claude-code"}, f)
            hint = admin._reset_hint("ScreenCapture", [("claude", bundle)])
        self.assertIn("`tccutil reset ScreenCapture com.anthropic.claude-code`", hint)
        self.assertIn("− button", hint)

    def test_reset_hint_without_bundle_id_shows_placeholder(self):
        hint = admin._reset_hint("Accessibility", [("x", "/nonexistent/x.app")])
        self.assertIn("`tccutil reset Accessibility <bundle-id>`", hint)


if __name__ == "__main__":
    unittest.main()
