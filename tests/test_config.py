import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = str(Path(__file__).resolve().parents[1] / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from phone_harness import config, telemetry  # noqa: E402


class ConfigSetBooleanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config_dir = Path(self.tmp.name)
        self.config_file = self.config_dir / "config.json"
        patcher = patch.object(config, "config_dir", return_value=self.config_dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        env = patch.dict(os.environ)                       # CI sets PHONE_HARNESS_TELEMETRY=0
        env.start()
        self.addCleanup(env.stop)
        for name in ("PHONE_HARNESS_TELEMETRY", "DO_NOT_TRACK", "PH_CLIENT",
                     "HERMES_SESSION_ID", "HERMES_REAL_HOME", "HERMES_AGENT"):
            os.environ.pop(name, None)

    def test_set_telemetry_off_coerces_to_boolean_false(self):
        for off_val in ("off", "no", "false", "0"):
            with self.subTest(value=off_val):
                res = config.set("telemetry", off_val)
                self.assertIs(res, False)
                self.assertIs(config.get("telemetry"), False)
                self.assertFalse(telemetry.is_enabled())
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.assertIs(data["telemetry"], False)

    def test_set_telemetry_on_coerces_to_boolean_true(self):
        for on_val in ("on", "yes", "true", "1"):
            with self.subTest(value=on_val):
                res = config.set("telemetry", on_val)
                self.assertIs(res, True)
                self.assertIs(config.get("telemetry"), True)
                self.assertTrue(telemetry.is_enabled())
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self.assertIs(data["telemetry"], True)

    def test_lookup_coerces_stale_string_in_config_file(self):
        self.config_file.write_text(json.dumps({"telemetry": "off"}), encoding="utf-8")
        val, source = config.lookup("telemetry")
        self.assertIs(val, False)
        self.assertEqual(source, "file")
        self.assertFalse(telemetry.is_enabled())

    def test_cli_set_telemetry_prints_boolean(self):
        out = []
        with patch("builtins.print", side_effect=out.append):
            code = config.cli(["set", "telemetry", "off"])
        self.assertEqual(code, 0)
        self.assertEqual(out, ["telemetry = false"])
        self.assertIs(config.get("telemetry"), False)


class DotEnvFileEncodingTests(unittest.TestCase):
    """The `.env` files read at import, whatever wrote them (#217).

    Windows PowerShell 5.1's `>` and `Out-File` write UTF-16LE with a BOM, so
    the same file a user edits by hand and one a shell redirects look different
    on disk. Both are read; a file that decodes as neither is a warning."""

    VAR = "PH_TEST_DOTENV_VALUE"

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        self.repo, self.ws = root / "repo", root / "workspace"
        self.repo.mkdir()
        self.ws.mkdir()
        env = patch.dict(os.environ)                      # whatever a test sets here goes
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop(self.VAR, None)
        for patcher in (patch.object(config, "_REPO_ROOT", self.repo),
                        patch("phone_harness.workspace.agent_workspace",
                              return_value=self.ws)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def load(self, raw, where="workspace"):
        """Write `raw` to one `.env` and run the loader; return what it set."""
        directory = self.ws if where == "workspace" else self.repo
        (directory / ".env").write_bytes(raw)
        config._load_env_files()
        return os.environ.get(self.VAR)

    def test_utf8_without_a_bom(self):
        self.assertEqual(self.load(f"{self.VAR}=utf8\n".encode("utf-8")), "utf8")

    def test_utf8_with_a_bom(self):
        self.assertEqual(self.load(f"{self.VAR}=utf8-bom\n".encode("utf-8-sig")),
                         "utf8-bom")

    def test_utf16le_with_a_bom_as_powershell_writes_it(self):
        raw = f"{self.VAR}=utf16le\r\n".encode("utf-16-le")
        self.assertEqual(self.load(b"\xff\xfe" + raw), "utf16le")

    def test_utf16be_with_a_bom(self):
        raw = f"{self.VAR}=utf16be\r\n".encode("utf-16-be")
        self.assertEqual(self.load(b"\xfe\xff" + raw), "utf16be")

    def test_a_utf16_file_keeps_its_comments_and_quotes(self):
        raw = (f"# per-machine overrides\r\n{self.VAR}='quoted'\r\n"
               .encode("utf-16-le"))
        self.assertEqual(self.load(b"\xff\xfe" + raw), "quoted")

    def test_an_existing_environment_variable_still_wins(self):
        os.environ[self.VAR] = "from-the-environment"
        raw = b"\xff\xfe" + f"{self.VAR}=utf16le\n".encode("utf-16-le")
        self.assertEqual(self.load(raw), "from-the-environment")

    def test_the_repo_root_file_is_read_before_the_workspace_one(self):
        self.load(f"{self.VAR}=first\n".encode("utf-8"), where="repo")
        self.assertEqual(self.load(f"{self.VAR}=second\n".encode("utf-8")), "first")

    def test_no_env_file_at_all_is_not_an_error(self):
        config._load_env_files()
        self.assertIsNone(os.environ.get(self.VAR))

    def warning_from(self, raw, where="workspace"):
        """What the loader wrote to stderr about `raw`, which it should skip."""
        directory = self.ws if where == "workspace" else self.repo
        (directory / ".env").write_bytes(raw)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            config._load_env_files()
        self.assertIsNone(os.environ.get(self.VAR))
        return errors.getvalue()

    def test_a_truncated_file_is_a_warning_naming_it_and_the_encoding(self):
        raw = f"{self.VAR}=utf16le\r\n".encode("utf-16-le")[:-1]   # odd length
        message = self.warning_from(b"\xff\xfe" + raw)
        self.assertIn(str(self.ws / ".env"), message)
        self.assertIn("UTF-8", message)
        self.assertIn("UTF-16", message)

    def test_utf16_without_a_bom_is_a_warning_not_a_crash(self):
        # PowerShell always writes the BOM, but `iconv` and editors need not.
        message = self.warning_from(f"{self.VAR}=utf16le\r\n".encode("utf-16-le"))
        self.assertIn(str(self.ws / ".env"), message)

    def test_a_binary_file_is_skipped_and_the_other_one_still_reads(self):
        (self.repo / ".env").write_bytes(b"\x00\xff\x00\xfe not text at all")
        # Its warning is the assertion of the test above.
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.load(f"{self.VAR}=android\n".encode("utf-8")), "android")

    def test_the_reported_command_no_longer_crashes(self):
        """#217's reproduction: a redirected `.env`, then a CLI run in a new process."""
        home = self.ws.parent / "home"
        (self.ws / ".env").write_bytes(
            b"\xff\xfe" + "PHONE_HARNESS_ANDROID_POKE_EVERY=37\r\n".encode("utf-16-le"))
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home),
               "PYTHONPATH": SRC, "PHONE_HARNESS_HOME": str(home),
               "PH_AGENT_WORKSPACE": str(self.ws), "PHONE_HARNESS_TELEMETRY": "0",
               "PHONE_HARNESS_NO_UPDATE_CHECK": "1"}
        result = subprocess.run([sys.executable, "-m", "phone_harness.run",
                                 "config", "get", "android.poke_every"],
                                 capture_output=True, text=True, timeout=60, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "37")


if __name__ == "__main__":
    unittest.main()
