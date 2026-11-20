# Phone Harness for Grok Build

A [Grok Build](https://x.ai/build) plugin with two paths, the same shape as
Browser Use's Grok plugin: a hosted MCP server, and the real CLI through
Grok's shell. It does not register `phone_exec` and it does not add a
shell-exec MCP. `.mcp.json` is only the hosted HTTP server.

| Phone | Path |
| --- | --- |
| Cloud Android emulator or Cloud iPhone, MCP connected | Hosted MCP. Preferred. Metered Android is 5 cents a minute on that server. A Cloud iPhone is a flat subscription, and it is not the phone in someone's pocket. |
| Personal iPhone (iPhone Mirroring) | `phone-harness` in Grok's shell. The hosted MCP cannot see it. |
| Android on the desk (adb) | `phone-harness` in Grok's shell. The hosted MCP cannot see it. |
| Cloud phone, only after the user explicitly chooses the CLI | `phone-harness cloud` in Grok's shell. Not a silent fallback when MCP auth or a bash prompt fails. |

Do not switch an action onto a different phone or the other path because a
call failed. Ask mode prompts before bash. A deny stops that action.

## Install

Install [Grok Build](https://docs.x.ai/build/overview), then sign in with
`grok login`.

Once this plugin is in the [Grok Build plugin marketplace](https://x.ai/news/grok-plugin-marketplace):

```bash
grok plugin install phone-harness --trust
```

Or open `/marketplace` in Grok Build and install **phone-harness**.

From a checkout, before it is listed, install this directory. On Grok 1.0.77
this is the command that works:

```bash
grok plugin install ./integrations/grok-build --trust
```

`--trust` skips the confirmation prompt. Installing the directory does not
publish the plugin. Grok 1.0.77 rejects `--plugin-dir` on `grok` itself
(`unexpected argument '--plugin-dir'`). That option is only on
`grok agent --no-leader --plugin-dir <dir> stdio`, which loads the directory
for one process and is not the install command.

A cloud call on the MCP path needs Phone Harness Cloud sign-in. Grok runs
its MCP OAuth flow in the browser. Approve it with the account whose cloud
phones Grok should drive. Do not paste an API key into the chat.

A local phone needs the `phone-harness` command on the machine running Grok
(or `uvx --from phone-harness==0.3.3 phone-harness` when it is not installed).
A personal iPhone also needs macOS 15+, iPhone Mirroring, and Accessibility
and Screen Recording for the app that runs that command. A desk Android needs
adb. CLI cloud, if the user explicitly chooses it, uses `phone-harness cloud
login` instead of the MCP OAuth flow.

## Authentication

`.mcp.json` names one HTTP server and no headers, so the client uses OAuth
instead of a key baked into the plugin.

Live discovery on the hosted server (no credential sent):

- Protected resource: `https://mcp.phone-harness.com/.well-known/oauth-protected-resource/mcp`
- Resource: `https://mcp.phone-harness.com/mcp`
- Authorization server: `https://clerk.phone-harness.com`
- Scope advertised: `phone:drive`
- Bearer method: `Authorization` header

`phone:drive` lets that account list, start, stop, and drive its own Cloud
phones. It does not grant any other account's phones.

The authorization server publishes authorization-code with PKCE (`S256`),
refresh, and device-code grants, plus a registration endpoint. Which grant
Grok's client picks is up to that client. This plugin does not collect, store,
or forward a token itself.

An API key (`PHONE_HARNESS_API_KEY`, minted from a signed-in CLI with
`phone-harness cloud keys create`) is an optional substitute for OAuth when
nobody can finish a browser sign-in. Put it in the user's own MCP settings for
this server, not in this repository. The key is a bearer for the same cloud
account. Anyone who can use the key can drive that account's cloud phones.

## Network

The plugin ships no code. What talks to the network depends on the path.

Hosted MCP, because of `.mcp.json` and OAuth discovery:

| Host | Why |
| --- | --- |
| `mcp.phone-harness.com` | The hosted MCP (`/mcp`) and its protected-resource metadata. |
| `clerk.phone-harness.com` | MCP sign-in. Authorize, token, registration, and revocation endpoints. |
| `https://api.phone-harness.com` | Not called by the plugin. The hosted MCP calls it with the user's bearer. |
| `phone-harness.com` | Dashboard for a PIN, password, or 2FA handoff on the MCP path. The plugin does not fetch it. |

On that path a Cloud Android's adb session stays inside Phone Harness Cloud.
Grok's machine does not open an adb port.

CLI path, only after Grok's bash tool is allowed to run `phone-harness`:

| Host | Why |
| --- | --- |
| none for a mirrored iPhone | The CLI uses the local mirroring window. |
| the desk phone's adb address | USB or Wi-Fi debugging. Not a Phone Harness host. |
| `https://api.phone-harness.com` and `https://clerk.phone-harness.com` | Only if the user explicitly chose CLI cloud (`cloud login` and `cloud start`). |
| the cloud Android's adb host and port | Outbound TCP from the machine running the CLI. The unlock code is a secret. The skill tells the model not to print it. |

The plugin adds no telemetry. The CLI, when it runs, follows its own setting
and by default sends usage, including scripts and what they print, to PostHog
at `https://us.i.posthog.com`. `DO_NOT_TRACK=1` or `phone-harness config set
telemetry false` turns that off. Phone Harness Cloud still records cloud
sessions the account starts.

## Least privilege

- One remote MCP server. No `command`, no stdio, no args, no hooked shell.
  The CLI is not launched by `.mcp.json`. Grok's own bash tool runs it, and
  Ask mode prompts first.
- No hooks, no agents, no slash-command scripts, no LSP, no filesystem tools.
- The plugin does not register `phone_exec`. Hermes and OpenClaw do. Do not
  switch paths to imitate that tool.
- `phone_save_screenshot` writes a file on the machine running a local stdio
  server. Hosted mode does not register it, and this plugin does not run that
  server.
- No API key, refresh token, or OAuth client secret in the plugin files.
- OAuth scope is the one the server advertises (`phone:drive`), not a broader
  grant this plugin invents.
- The skill tells the model to ask before sending, posting, buying, deleting,
  or changing settings, and to stop rather than type a PIN, password, or 2FA
  code.

Cloud Android time costs money. The skill says to ask before starting one and
to stop it when the task is done.

## Skill

`skills/phone-harness/SKILL.md` is generated from the repo-root
[SKILL.md](../../SKILL.md). The root file remains the only copy of the helpers,
the consent rule, the scroll-versus-swipe distinction, and the personal-phone
versus cloud-phone rule. The generated skill puts the Grok routing preface in
front of that guide. Rebuild it after changing the root guide:

```bash
python3 integrations/grok-build/scripts/build-skill.py
```

The hosted tool names match [phone-harness/mcp](https://github.com/phone-harness/mcp)
`server.py` at `b0572ff90388c8e62e17fe08484a072eb594ccf6`. They were not read
back from a signed-in `tools/list` call. If that server adds or renames a hosted
tool, update `HOSTED_TOOLS` in `scripts/build-skill.py` and rebuild.

`phone_start_device`'s `minutes` defaults to 30 on that server. That is not
the CLI's 15-minute default. `phone_long_press_on_screen_at_coordinates` takes
milliseconds. `phone_swipe_on_screen`'s `distance` is pixels, not the CLI's
fraction.

## Marketplace

Submission is a pull request to [xai-org/plugin-marketplace](https://github.com/xai-org/plugin-marketplace)
that adds one remote entry pointing at this repo, subdirectory
`integrations/grok-build`, pinned to a full commit SHA. The prepared entry and
the steps that are still waiting live in [submission/](submission/). Do not
open that pull request until the maintainer named there approves it. This
directory does not submit itself.

## License

MIT. The license file is [LICENSE](../../LICENSE) at the repository root.
Use of Phone Harness Cloud is governed by Phone Harness's own terms at
https://phone-harness.com.
