"""The Grok Build plugin in integrations/grok-build, checked without Grok or a phone.

The skill is generated from the repo-root SKILL.md. These tests rebuild it and
compare, and they check the manifest, the MCP config, and the limits the README
states. Catalog SHA checks live with the submission entry and run when that
file is present.

    python -m unittest tests.test_grok_build_plugin
"""
import importlib.util
import json
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "integrations" / "grok-build"
ENTRY = PLUGIN / "submission" / "marketplace-entry.json"

GENERIC_KEYWORDS = {
    "phone", "api", "cli", "android", "iphone", "ios", "deploy", "database",
    "mcp", "postgres", "cloud", "mobile", "device", "automation",
}


def load_builder():
    spec = importlib.util.spec_from_file_location(
        "phone_harness_grok_build_skill", PLUGIN / "scripts" / "build-skill.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest():
    return json.loads((PLUGIN / ".grok-plugin" / "plugin.json").read_text(encoding="utf-8"))


def mcp():
    return json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))


class Manifest(unittest.TestCase):
    def test_names_the_plugin_and_states_the_license(self):
        data = manifest()
        self.assertEqual(data["name"], "phone-harness")
        self.assertEqual(data["license"], "MIT")
        self.assertEqual(data["homepage"], "https://phone-harness.com")
        self.assertEqual(data["repository"], "https://github.com/phone-harness/phone-harness")
        self.assertEqual(data["author"]["name"], "Phone Harness")
        self.assertEqual(data["version"], "0.2.0")
        self.assertIn("CLI", data["description"])
        self.assertIn("Hosted MCP", data["description"])
        self.assertNotIn("not reachable", data["description"])

    def test_keywords_are_brand_scoped(self):
        words = manifest()["keywords"]
        self.assertEqual(words, [
            "phone harness",
            "phone-harness",
            "phone harness cloud",
            "phone-harness mcp",
        ])
        for word in words:
            self.assertNotIn(word.lower(), GENERIC_KEYWORDS)

    def test_does_not_declare_a_native_tool_contract(self):
        raw = (PLUGIN / ".grok-plugin" / "plugin.json").read_text(encoding="utf-8")
        self.assertNotIn("phone_exec", raw)
        self.assertNotIn("mcpServers", manifest())


class McpConfig(unittest.TestCase):
    def test_one_http_server_and_no_local_command(self):
        servers = mcp()["mcpServers"]
        self.assertEqual(list(servers), ["phone-harness"])
        server = servers["phone-harness"]
        self.assertEqual(server, {
            "type": "http",
            "url": "https://mcp.phone-harness.com/mcp",
        })
        self.assertNotIn("command", server)
        self.assertNotIn("args", server)
        self.assertNotIn("headers", server)
        self.assertNotIn("env", server)

    def test_ships_no_hooks_agents_or_lsp(self):
        self.assertFalse((PLUGIN / "hooks").exists())
        self.assertFalse((PLUGIN / "agents").exists())
        self.assertFalse((PLUGIN / "commands").exists())
        self.assertFalse((PLUGIN / ".lsp.json").exists())


class SkillSync(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load_builder()
        cls.guide = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        cls.skill = (PLUGIN / "skills" / "phone-harness" / "SKILL.md").read_text(encoding="utf-8")

    def test_committed_skill_matches_the_builder(self):
        self.assertEqual(self.skill, self.builder.render(self.guide))

    def test_frontmatter_uses_literal_true_and_a_short_description(self):
        front = self.skill.split("---\n", 2)[1]
        self.assertIn("name: phone-harness\n", front)
        self.assertIn("user-invocable: true\n", front)
        description = re.search(r'^description: "(.*)"$', front, re.M).group(1)
        self.assertLessEqual(len(description), 120)
        self.assertIn("Hosted MCP", description)
        self.assertIn("CLI", description)
        self.assertNotIn("Cloud phones only", description)

    def test_quotes_the_root_rules_it_depends_on(self):
        found = self.builder.excerpts(self.guide)
        for body in found.values():
            self.assertIn(body, self.skill)
            self.assertIn(body, self.guide)

    def test_the_cli_guide_is_appended_verbatim(self):
        body = self.builder.guide_body(self.guide)
        self.assertTrue(self.skill.endswith(body))
        preface = self.skill[: -len(body)]
        self.assertIn("## CLI guide\n", preface)
        self.assertNotIn("# phone-harness\n", preface)

    def test_lists_every_hosted_tool_and_not_the_stdio_one(self):
        for name in self.builder.HOSTED_TOOLS:
            self.assertIn(f"`{name}`", self.skill)
            self.assertIn(f"`phone-harness__{name}`", self.skill)
        self.assertEqual(len(self.builder.HOSTED_TOOLS), 14)
        self.assertNotIn("phone_save_screenshot", self.builder.HOSTED_TOOLS)
        block = self.skill.split("## MCP tools (preferred when connected)\n", 1)[1]
        block = block.split("## CLI in Grok's shell\n", 1)[0]
        bullets = [line.split("`")[1] for line in block.splitlines() if line.startswith("- `phone_")]
        self.assertEqual(bullets, list(self.builder.HOSTED_TOOLS))
        self.assertIn("local stdio MCP", block)

    def test_routes_mcp_and_cli_without_switching_phones(self):
        self.assertIn("MCP tools (preferred when connected)", self.skill)
        self.assertIn("CLI in Grok's shell", self.skill)
        self.assertIn("phone-harness <<'PY'", self.skill)
        self.assertIn("iPhone Mirroring", self.skill)
        self.assertIn("desk over adb", self.skill)
        self.assertIn("explicitly chooses", self.skill)
        self.assertIn("Do not switch", self.skill)
        self.assertIn(f"phone-harness=={self.builder.cli_version()}", self.skill)
        self.assertNotIn("no shell tool", self.skill)
        self.assertNotIn("Do not run `phone-harness`", self.skill)
        self.assertNotIn("provides_tools", self.skill)
        self.assertEqual(self.skill.count("phone_exec"), 1)
        self.assertIn("does not register a `phone_exec` tool", self.skill)

    def test_units_that_differ_from_the_cli_are_stated(self):
        self.assertIn("milliseconds", self.skill)
        self.assertIn("pixels", self.skill)
        self.assertIn("defaults to 30", self.skill)
        self.assertIn("5 cents per minute", self.skill)

    def test_mapped_helpers_still_exist_in_the_root_guide(self):
        names = set(self.builder.helper_names(self.guide))
        for helper in self.builder.CLI_HELPERS_NOT_ON_HOSTED_MCP:
            self.assertIn(helper, names)
        for tool, helper in self.builder.HELPER_FOR_TOOL.items():
            if helper.startswith("cloud "):
                continue
            self.assertIn(helper, names, tool)
        for extra in ("home", "back", "app_switcher"):
            self.assertIn(extra, names)


class Readme(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (PLUGIN / "README.md").read_text(encoding="utf-8")

    def test_install_auth_network_and_license(self):
        for phrase in (
            "grok plugin install phone-harness --trust",
            "grok plugin install ./integrations/grok-build --trust",
            "phone:drive",
            "https://mcp.phone-harness.com/mcp",
            "https://mcp.phone-harness.com/.well-known/oauth-protected-resource/mcp",
            "https://clerk.phone-harness.com",
            "https://api.phone-harness.com",
            "Least privilege",
            "MIT",
            "iPhone Mirroring",
            "desk",
            "does not register `phone_exec`",
            "Grok's shell",
            "Do not switch",
            "5 cents",
            "b0572ff90388c8e62e17fe08484a072eb594ccf6",
        ):
            self.assertIn(phrase, self.text, phrase)

    def test_does_not_tell_the_reader_to_pipe_an_installer(self):
        self.assertNotIn("curl | bash", self.text)
        self.assertNotIn("curl -fsSL", self.text)

    def test_does_not_offer_the_rejected_plugin_dir_flag(self):
        self.assertNotIn("grok --plugin-dir", self.text)
        self.assertIn("grok agent --no-leader --plugin-dir <dir> stdio", self.text)

    def test_root_readme_points_here(self):
        root = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("integrations/grok-build", root)
        self.assertIn("grok plugin install phone-harness --trust", root)


class Secrets(unittest.TestCase):
    def test_no_credential_material_in_the_plugin(self):
        for path in PLUGIN.rglob("*"):
            if not path.is_file():
                continue
            raw = path.read_bytes()
            for needle in (b"phc_", b"pck_", b"BEGIN ", b"AKIA"):
                self.assertNotIn(needle, raw, f"{needle!r} in {path.relative_to(ROOT)}")
            # "task-specific" contains the letters sk-; a real token does not sit inside a word.
            self.assertIsNone(
                re.search(br"(?<![A-Za-z])sk-[A-Za-z0-9]", raw),
                f"sk- token in {path.relative_to(ROOT)}",
            )


class Layout(unittest.TestCase):
    def test_only_expected_files(self):
        found = sorted(
            path.relative_to(PLUGIN).as_posix()
            for path in PLUGIN.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
        allowed = {
            ".grok-plugin/plugin.json",
            ".mcp.json",
            "README.md",
            "scripts/build-skill.py",
            "skills/phone-harness/SKILL.md",
            "submission/SUBMISSION.md",
            "submission/marketplace-entry.json",
        }
        # The submission draft is added once the plugin commit to pin exists.
        self.assertTrue(set(found) <= allowed, found)
        for required in allowed - {"submission/SUBMISSION.md", "submission/marketplace-entry.json"}:
            self.assertIn(required, found)


SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def catalog_errors(entry: dict) -> list[str]:
    """The url-source checks from xai-org/plugin-marketplace scripts/validate-catalog.py.

    Mirrors that script at marketplace commit 2d9db5ccc539f42be6e13f84eecc2cd7f76d67cf.
    """
    errors = []
    name = entry.get("name") or "<unnamed>"
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "url":
        return [f"plugin '{name}': expected a url source"]
    sha = source.get("sha")
    if not isinstance(sha, str) or not SHA_RE.match(sha):
        errors.append(
            f"plugin '{name}': sha {sha!r} is not a 40-character lowercase hex string"
        )
    path = source.get("path")
    if not isinstance(path, str) or not path.strip():
        errors.append(f"plugin '{name}': url source `path` must be a non-empty string")
    elif (
        path.startswith("/")
        or "\\" in path
        or any(part in ("..", "") for part in path.split("/"))
    ):
        errors.append(f"plugin '{name}': url source `path` {path!r} is not a relative subdirectory")
    url = source.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append(f"plugin '{name}': url must be https")
    return errors


class CatalogEntry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = json.loads(ENTRY.read_text(encoding="utf-8"))
        cls.sha = cls.entry["source"]["sha"]

    def test_matches_the_marketplace_url_source_rules(self):
        self.assertEqual(catalog_errors(self.entry), [])
        self.assertEqual(self.entry["name"], "phone-harness")
        self.assertEqual(self.entry["source"]["url"], "https://github.com/phone-harness/phone-harness.git")
        self.assertEqual(self.entry["source"]["path"], "integrations/grok-build")
        self.assertEqual(self.entry["category"], "development")
        self.assertIn("CLI", self.entry["description"])
        self.assertIn("MCP", self.entry["description"])
        self.assertNotIn("not reachable", self.entry["description"])
        self.assertTrue(self.entry["homepage"])

    def test_keywords_and_domains_stay_on_the_brand(self):
        for word in self.entry["keywords"]:
            self.assertNotIn(word.lower(), GENERIC_KEYWORDS)
            self.assertIn("phone", word.lower())
        for domain in self.entry["domains"]:
            self.assertTrue(
                domain == "phone-harness.com" or domain.endswith(".phone-harness.com"),
                domain,
            )
        self.assertIn("mcp.phone-harness.com", self.entry["domains"])
        self.assertNotIn("phone", self.entry["keywords"])

    def test_pin_is_a_reachable_commit_containing_this_plugin(self):
        kind = subprocess.run(
            ["git", "cat-file", "-t", self.sha], cwd=ROOT, capture_output=True, text=True, check=False)
        self.assertEqual(kind.stdout.strip(), "commit", kind.stderr)
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", self.sha, "HEAD"], cwd=ROOT, check=False)
        self.assertEqual(ancestor.returncode, 0)
        listed = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", self.sha],
            cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        for path in (
            "integrations/grok-build/.grok-plugin/plugin.json",
            "integrations/grok-build/.mcp.json",
            "integrations/grok-build/skills/phone-harness/SKILL.md",
            "integrations/grok-build/README.md",
        ):
            self.assertIn(path, listed)

    def test_plugin_payload_matches_the_pin(self):
        """Files Grok installs, other than the maintainer submission notes, match the pin."""
        for path in PLUGIN.rglob("*"):
            if not path.is_file() or "submission" in path.parts or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(ROOT).as_posix()
            pinned = subprocess.run(
                ["git", "show", f"{self.sha}:{rel}"],
                cwd=ROOT, capture_output=True, check=False)
            self.assertEqual(pinned.returncode, 0, rel)
            self.assertEqual(pinned.stdout, path.read_bytes(), rel)

    def test_submission_instructions_use_the_same_pin(self):
        text = (PLUGIN / "submission" / "SUBMISSION.md").read_text(encoding="utf-8")
        self.assertIn(self.sha, text)
        self.assertIn("integrations/grok-build", text)
        self.assertIn("Do not open", text)
        self.assertIn("xai-org/plugin-marketplace", text)
        self.assertNotIn("x.ai/bot/marketplace", text)


if __name__ == "__main__":
    unittest.main()
