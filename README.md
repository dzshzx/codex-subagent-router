# Codex Subagent Router

[![CI](https://github.com/dzshzx/codex-subagent-router/actions/workflows/ci.yml/badge.svg)](https://github.com/dzshzx/codex-subagent-router/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/codex-subagent-router)](https://pypi.org/project/codex-subagent-router/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

`codex-subagent-router` is an independent Python project for developing and
validating model, effort, role, and context-routing policy for Codex subagents.

The repository currently provides the policy seam; strict JSON value
types for the `PreToolUse`, `SessionStart`, and `SubagentStart` hook boundaries;
and deny-only validation for routed `spawn_agent` calls. Root-session routing
guidance, managed subagent role-context handlers, and executable JSON command
adapters are also available. Explicit user-level installation, owned
Hook-launcher updates, cross-layer diagnosis, safe uninstall, and their
command-line entry points are implemented. The generated installation lifecycle
and the explicit V2 configuration each have recorded isolated Codex CLI evidence; see
[Codex compatibility](#codex-compatibility) for the exact scope and the
remaining real-backend boundary.

## Technology

- Python 3.11 or newer
- `uv` dependency and environment management
- Pytest behavior tests
- Ruff linting and formatting
- Strict mypy type checking
- `src/` package layout
- Pure hook handlers behind command and installation adapters
- Description-only managed roles and recoverable user-configuration transactions
- POSIX-only verified installation lifecycle (POSIX file modes and
  `shlex` quoting); Windows is unverified
- Test suite gated on Python 3.11 (declared minimum) and the current
  development Python

## Codex compatibility

Runtime code does not pin, compare, or branch on the Codex CLI version. A
version listed here is a completed compatibility probe, not a runtime lock, a
minimum version, or a claim about unlisted releases.

| Codex CLI | Verified surfaces | Evidence |
|---|---|---|
| `0.144.1` | Historical pre-V2-default package probe: strict hook protocol, generated user installation, and fresh-session role/Hook discovery | [`docs/research/codex-0.144.1-hook-evidence.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/research/codex-0.144.1-hook-evidence.md) |
| `0.144.3` | Historical pre-V2-default package probe: root guidance, deny-before-creation, role context, generated installation lifecycle, and both spawn shapes against the shipped stable toolset | [`docs/research/codex-0.144.3-hook-evidence.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/research/codex-0.144.3-hook-evidence.md) |
| `0.144.4` | Hook-managed lifecycle plus the explicitly configured V2 loopback contract, including visible routing metadata and the `agents` namespace; real-backend V2 remains unverified | [`docs/research/codex-0.144.4-hook-evidence.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/research/codex-0.144.4-hook-evidence.md) |

The `0.144.1` and `0.144.3` rows preserve historical evidence for the V1
compatibility seam; they do not verify the current V2-default generated
configuration. A current deployment should use the `0.144.4` V2 settings below
and retain its stated provider boundary.

Router-managed roles use one definition mode: description-only inline role
declarations plus the generated Hooks. Standalone custom-agent files are an
alternative mode, not an additional source for the same role. Do not declare
`researcher`, `reviewer`, `architecture_explorer`, or `interface_designer` in
any active user or project `agents` directory while using this router. The
installer recursively rejects those names under the explicit user Codex home;
project-layer collisions remain unsupported, but `doctor` can diagnose one
explicit project's `.codex/agents` tree without modifying it.

The `0.144.3` probe used package version `0.1.2`. Version `0.1.3` changed only
branch-agnostic documentation links. Version `0.1.4` retains the same generated
Hook configuration and runtime contracts while rejecting relative explicit
launcher paths earlier at the CLI boundary. These packaging and preflight
changes do not extend the Codex-version compatibility claim beyond the recorded
probe. Version `0.1.5` adds user-level update, doctor, and uninstall lifecycle
surfaces without changing the generated Hook protocol or expanding the recorded
Codex-version compatibility claim.

The installed `0.144.3` release binary drifts from its source tag: it still
reports the flattened `collaborationspawn_agent` hook tool name and its
default stable spawn handler enforces the V2-shaped input contract. Release
decisions therefore rest on installed-binary probes, never on tag source
reading alone.

Codex ships two multi-agent tool generations. In `0.144.4`, the session uses
the selected model's `multi_agent_version` metadata before falling back to the
feature default. The bundled catalog assigns V2 to `gpt-5.6-sol` and
`gpt-5.6-terra`, the only model families in this router's policy, so generated
installations explicitly enable V2. They also set
`hide_spawn_agent_metadata = false` so the Hook can validate role/model/effort,
and `tool_namespace = "agents"` to keep the spawn tool on the verified matcher
seam. The validator retains V1 input-shape support for compatibility, but V1 is
not the generated installation priority. See
[ADR-0005](docs/adr/0005-enable-multiagent-v2-for-gpt-5-6.md).

Unlisted Codex versions are unverified. The protocol boundary is deliberately
strict, while Codex command-hook failures are fail-open; an upstream schema or
tool-name change can therefore disable routing enforcement instead of safely
falling back. Do not declare another version verified until its official
schemas and source behavior have been compared and its isolated root-start,
spawn-denial, managed-child, generated-installation, status, and rollback
probes pass. Keep each version's evidence as a separate record rather than
replacing old links with an unpinned `latest` reference.

## Guided routing policy

The route table is the allowlist and ordering guidance for an explicit parent
decision. Root startup context tells the parent which role, model, effort, and
fork shape to select; the `PreToolUse` hook validates that explicit selection
and only denies invalid calls. It never chooses, fills, or rewrites spawn
parameters automatically.

Five named profiles cover routine work in ascending capability order:

| Profile | Model | Effort | Use for |
|---|---|---|---|
| `scout` | `gpt-5.6-terra` | `medium` | Broad reads, enumeration, and mechanical extraction. |
| `worker` | `gpt-5.6-sol` | `low` | Routine bounded execution with fast turnaround. |
| `analyst` | `gpt-5.6-terra` | `high` | Wide reading, digestion, and first drafts on the budget model. |
| `builder` | `gpt-5.6-sol` | `medium` | Standard implementation and multi-step changes. |
| `judge` | `gpt-5.6-sol` | `high` | Critical review, adjudication, and hard debugging. |

Two named profiles provide conditional escalation in ascending capability
order:

| Profile | Model | Effort | Use for |
|---|---|---|---|
| `escalation_xhigh` | `gpt-5.6-sol` | `xhigh` | Escalation when judge-level work needs deeper reasoning. |
| `escalation_max` | `gpt-5.6-sol` | `max` | Maximum effort; requires a stated concrete reason. |

## Generated skill document and usage report

Two derived surfaces make daily routing lighter without adding a second
policy source:

```bash
codex-subagent-router render-skill --out ~/.agents/skills/codex-subagent-routing/SKILL.md
codex-subagent-router usage-report --sessions-dir "$CODEX_HOME/sessions"
```

`render-skill` renders the routing policy, managed role descriptions, spawn
contract, delegation signals, a child task packet template, and a result
contract into one agent-skill markdown document. The output is a generated
artifact: regenerate it after policy changes instead of editing it.

`usage-report` scans an explicit sessions directory for rollout files,
extracts every spawn tool call (route fields are recorded in plaintext), and
replays each call through the deny-only validator. The machine-readable
output reports the route distribution and the violation rate — the data for
deciding how much enforcement a deployment actually needs.

## Public API

```python
import sys

from codex_subagent_router import (
    PreToolUseInput,
    SessionStartInput,
    SubagentStartInput,
    conditional_routes,
    encode_hook_output,
    handle_pre_tool_use_document,
    handle_session_start_document,
    handle_subagent_start_document,
    parse_hook_input,
    role_contracts,
    routine_routes,
    session_start_context,
    subagent_start_context,
    validate_child_effort,
    validate_pre_tool_use,
)

routine = routine_routes()
conditional = conditional_routes()
effort = validate_child_effort("high")

hook_input = parse_hook_input(sys.stdin.read())
if isinstance(hook_input, PreToolUseInput):
    denial = validate_pre_tool_use(hook_input)
    if denial is not None:
        denial_json = encode_hook_output(denial)
elif isinstance(hook_input, SessionStartInput):
    context = session_start_context(hook_input)
elif isinstance(hook_input, SubagentStartInput):
    context = subagent_start_context(hook_input)

managed_roles = role_contracts()
```

`parse_hook_input` accepts one JSON document and returns a typed
`PreToolUseInput`, `SessionStartInput`, or `SubagentStartInput`. It rejects
unknown fields, missing or wrongly typed fields, duplicate keys, unsupported
event and permission values, non-JSON numeric constants, and numeric overflow.
`encode_hook_output` only emits the project-owned deny, root-session guidance,
or subagent-context output shapes, whose string fields are validated when their
value objects are constructed.

`validate_pre_tool_use` ignores non-spawn tool calls. MultiAgent V1 and V2 use
the same validator capability seam, so for verified spawn tool
names the validator selects the contract from the input shape: a `task_name`
or `fork_turns` field selects the V2 contract, and any other object is
validated as a V1 spawn. Both variants must route explicitly with
`agent_type`, `model`, and `reasoning_effort` validated against the policy
seam. V2 spawns additionally require `message`, `task_name`, and
`fork_turns="none"` or a positive integer string; V1 spawns require exactly
one of `message` or `items` and must leave `fork_context` false or omitted.
The validator returns either a deny value or `None` and never rewrites tool
input.

`session_start_context` emits routing guidance only for a root `startup`; the
text is derived from the executable route and role sources. `subagent_start_context`
injects a fixed developer contract for `researcher`, `reviewer`,
`architecture_explorer`, or `interface_designer`. Built-in and other unmanaged
roles are left unchanged.

The three `handle_*_document` adapters compose parsing, the matching pure
handler, and output encoding. They return an empty string when Codex should
receive no hook output and raise `ProtocolViolation` for malformed or
wrong-event documents. The thin command boundary is executable as:

```bash
python -m codex_subagent_router.commands pre-tool-use
python -m codex_subagent_router.commands session-start
python -m codex_subagent_router.commands subagent-start
```

Each command reads one JSON document from stdin. Success exits `0`; protocol
errors are written to stderr and exit `1`; command usage errors exit `2`.

## User installation

### Prerequisites

Use a POSIX environment with Python 3.11 or newer. Install and authenticate the
Codex CLI before installing this package, then confirm its version and login:

```bash
codex --version
codex login status
```

The compatibility table records completed probes, not a runtime version pin.
If the installed Codex version is not listed, complete the compatibility gate
in [CONTRIBUTING.md](CONTRIBUTING.md#codex-compatibility-verification) before
describing the deployment as verified. The installer enables MultiAgent V2 for
the GPT-5.6 Sol/Terra policy used here; do not remove or override those settings
without re-verifying the Hook-visible spawn contract.

### Persistent package installation

Install the package as a persistent tool so both console scripts remain on
`PATH` across shells:

```bash
uv tool install codex-subagent-router

command -v codex-subagent-router
command -v codex-subagent-router-hook
```

Pin the package version in the `uv tool install` requirement when a deployment
must reproduce one specific release. Do not use a one-shot `uvx` invocation or
a temporary virtual environment: the installer writes the absolute Hook
launcher path into `hooks.json`, and removing that environment would silently
leave Codex pointing at a missing command. `status` reports a launcher that
later becomes non-executable.

### Plan, install, and verify

Define the target Codex home explicitly. The following commands manage the
default user-level Codex home:

```bash
CODEX_HOME="$HOME/.codex"

codex-subagent-router plan --codex-home "$CODEX_HOME"
```

`plan` is read-only. Inspect its `config_action`, `hooks_action`, additions, and
`conflicts` before continuing. It reports the conflicts modeled by the
installer, including an incomplete transaction journal, a held operation lock,
an unhealthy or diverging existing installation, incompatible role or Hook
configuration, unsafe file targets, and a launcher that is not executable.
It cannot predict permission, storage, or concurrent filesystem failures that
occur after the plan was produced; `install` repeats the checks while holding
the operation lock and fails closed if snapshots have changed.

The plan also recursively inspects active `*.toml` files under the explicit
`$CODEX_HOME/agents` tree. Every discovered path appears in
`standalone_agent_files_to_preserve`; these files remain user-owned and are
never added to the installation receipt. A file whose declared `name` is not
one of the four router-managed roles is left byte-for-byte and mode-for-mode
unchanged. Invalid or unsafe files fail closed because the installer cannot
prove that they are compatible.

A standalone file declaring `researcher`, `reviewer`,
`architecture_explorer`, or `interface_designer` conflicts with the
Hook-managed definition and blocks both `plan` and `install`. The installer
does not automatically rename, disable, adopt, or back up that file. Change its
declared `name`, or move it out of the active `agents` tree, then rerun `plan`.
Changing only the filename does not resolve the conflict because Codex role
identity comes from the TOML `name` field. If this is a temporary manual
change, reverse it manually after rollback when you want the standalone role
active again.

This preflight covers the explicit user Codex home only. A user-level installer
cannot enumerate every project's `.codex/agents` tree; a project-level
standalone file with a managed name remains unsupported. Run `doctor` for each
project you intend to use, then remove or rename any reported collision.

If `codex-subagent-router-hook` cannot be resolved on `PATH`, `plan` and
`install` accept `--hook-executable PATH`. The value must be an absolute path to
a regular executable file in a persistent environment.

When `plan` exits `0` with an empty `conflicts` array, install and query status:

```bash
codex-subagent-router install --codex-home "$CODEX_HOME"
codex-subagent-router status --codex-home "$CODEX_HOME"
codex-subagent-router doctor --codex-home "$CODEX_HOME" --project-dir "$PWD"
```

`--codex-home` is always required. The CLI never falls back to `~/.codex`,
and a blank value is rejected instead of resolving to the current working
directory.

`status` is healthy only when its JSON contains `"state": "installed"` and an
empty `details` array. A completed status query exits `0` for every reported
state, including `not-installed`, `modified`, and `incomplete`; automation must
inspect `state` instead of treating exit `0` as proof of a healthy installation.

`doctor` combines installation health, user standalone-agent checks, Hook
launcher checks, and the selected project's `.codex/agents` layer. It is
read-only. It exits `0` only when its JSON contains `"healthy": true`; diagnosed
issues are returned as JSON with exit `1`. `--project-dir` defaults to the
current directory, but automation should pass it explicitly.

Successful operations, `doctor`, and modeled `plan` or `update --dry-run`
conflicts write machine-readable JSON to stdout. A plan with conflicts or an
unhealthy doctor report exits `1`. Usage errors exit `2` with text on stderr.
Failures raised before planning, and installation, update, rollback, or
uninstall violations, exit `1` with text on stderr; callers must not assume that
every nonzero result contains JSON.

The installer adds this V2 table and description-only declarations for the four
managed roles to `config.toml`, adds the three command-hook groups to
`hooks.json`, and writes a private receipt under
`codex-subagent-router/installation.json`:

```toml
[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

Existing bytes and file modes are captured before a change. Each replacement
is atomic, and a persisted journal makes an interrupted two-file transaction
recoverable. Configuration files and state paths that are symbolic links are
rejected. Compatible entries that already exist are verified but are not
claimed as installer-owned; partial or conflicting V2 settings and the
V2-incompatible `agents.max_threads` setting fail closed.

### Update the user-level Hook launcher

After upgrading or relocating the persistent package environment, plan the
user-level launcher update before applying it:

```bash
codex-subagent-router update --dry-run --codex-home "$CODEX_HOME"
codex-subagent-router update --codex-home "$CODEX_HOME"
```

The dry run is read-only and reports `hooks_action`,
`hook_events_to_update`, and `conflicts`. The first update implementation is
deliberately narrow: it only replaces the command path in Hook groups that the
installation receipt proves were created by this installer. It does not
modify `config.toml`, MultiAgent V2 settings, managed role declarations,
standalone agent files, Hook matchers, timeouts, or user-owned compatible Hook
groups. A broader Hook specification change requires an explicit future
migration instead of being silently adopted.

The old launcher may already be missing, provided the receipt and managed Hook
groups are otherwise healthy and the new launcher is an absolute regular
executable file. Unrelated Hooks added after installation are preserved. The
update keeps the first installation's original bytes and modes as the permanent
rollback baseline, so a later rollback still restores the state from before
the router was first installed.

An interrupted update leaves a recoverable journal. Running `rollback` first
restores the previous complete installed state; run `rollback` again only when
you also intend to remove the router-managed configuration.

### Review Hook trust and start a fresh session

After a successful install, start Codex and review the new user Hooks through
the Codex Hook trust prompt or Hook management UI. Confirm that the three groups
are `PreToolUse`, `SessionStart`, and `SubagentStart`, and that each command uses
the same persistent `codex-subagent-router-hook` path reported by `command -v`.
See the [Codex Hooks documentation](https://developers.openai.com/codex/hooks)
for the current product UI and trust behavior.

The installer deliberately does not read or write Hook trust state and does not
enable `--dangerously-bypass-hook-trust`. After approving the Hooks, completely
close the old Codex session and start a fresh one; Codex does not reliably
hot-reload ordinary user configuration files.

In the fresh session, submit this smoke-test request:

```text
Call spawn_agent once with exactly these routing parameters:

task_name: "router-smoke"
message: "Return exactly ROUTER_SMOKE"
fork_turns: "none"
agent_type: "reviewer"
model: "gpt-5.6-sol"
reasoning_effort: "ultra"

Do not change or omit any parameter.
```

The call must be denied before a child is created with the reason
`child reasoning effort 'ultra' is prohibited`. If a child starts, enforcement
is not active. Re-run `status`, confirm the launcher is executable, review Hook
trust again, and open another fresh session. Do not use the dangerous trust
bypass as a production fix.

Hook launch failures and timeouts are fail-open in Codex, so this router remains
a policy guardrail, not a security or spending-isolation boundary.

Configuration uninstall is explicit:

```bash
codex-subagent-router uninstall --codex-home "$CODEX_HOME"
```

`uninstall` is a user-facing alias for the same safe transaction exposed as
`rollback`; it does not create a second removal implementation. If the installed
files are unchanged, it restores their exact original
bytes and modes or removes files the installer created. If unrelated content
was added later, it removes only still-intact owned blocks and hook groups.
It refuses to proceed when owned content has been modified, when the receipt is
unhealthy, or while another installation operation holds the lock.

Neither command modifies `$CODEX_HOME/agents`. Standalone files that predate the
installation, or that are added later, keep their current paths, bytes, and
modes. Because manual renames or disables are not installer-owned, uninstall
does not reverse them.

Uninstall in this order: run `uninstall` first, then remove the package with its
package manager. The CLI and the hook launcher live in the package environment, so
removing the package first leaves managed hook groups pointing at a missing
launcher. If that happens, reinstall the same package version and uninstall,
or repair `hooks.json` manually.

The same transaction seam is available to Python callers. Both paths must be
explicit; importing the package never reads user configuration:

```python
from pathlib import Path

from codex_subagent_router import (
    doctor_user_config,
    install_user_config,
    plan_user_installation,
    plan_user_update,
    rollback_user_config,
    update_user_config,
)

codex_home = Path("/explicit/codex/home")
hook_command = ("/absolute/path/to/codex-subagent-router-hook",)
plan = plan_user_installation(codex_home, hook_command)
result = install_user_config(codex_home, hook_command)
update_plan = plan_user_update(codex_home, hook_command)
updated = update_user_config(codex_home, hook_command)
report = doctor_user_config(codex_home, Path("/explicit/project"))
removed = rollback_user_config(codex_home)
```

Policy rationale and protocol evidence are documented in
[`docs/routing-policy.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/routing-policy.md),
[`docs/role-contracts.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/role-contracts.md), and
[`docs/research/`](https://github.com/dzshzx/codex-subagent-router/tree/HEAD/docs/research/).

## Development

Create or update the development environment:

```bash
uv sync --dev
```

Run all checks:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv build
git diff --check
```

## Delivery stages

1. Stable routing policy and tests. **Complete.**
2. Codex hook input and output protocol types. **Complete.**
3. Deny-only `PreToolUse` validator. **Complete.**
4. `SessionStart` routing guidance and `SubagentStart` role contracts. **Complete.**
5. Isolated end-to-end hook probes. **Complete.**
6. User-level plan/install/update/status/doctor/uninstall lifecycle. **Complete.**
7. Named route profiles, generated skill document, and offline usage report. **Complete.**

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Tests and package imports must not read or modify user-level Codex configuration.
- Repository code must not contain machine-specific absolute paths.
- Runtime policy code must not add hidden fallbacks or duplicate policy sources.
- Runtime package code must not pin or branch on a Codex CLI version; versioned
  compatibility claims belong in reproducible evidence records.
