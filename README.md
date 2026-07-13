# Codex Subagent Router

[![CI](https://github.com/dzshzx/codex-subagent-router/actions/workflows/ci.yml/badge.svg)](https://github.com/dzshzx/codex-subagent-router/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/codex-subagent-router)](https://pypi.org/project/codex-subagent-router/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

`codex-subagent-router` is an independent Python project for developing and
validating model, effort, role, and context-routing policy for Codex subagents.

The repository currently provides the stable policy seam; strict JSON value
types for the `PreToolUse`, `SessionStart`, and `SubagentStart` hook boundaries;
and deny-only validation for routed `spawn_agent` calls. Root-session routing
guidance, managed subagent role-context handlers, and executable JSON command
adapters are also available. Explicit user-level installation, status, safe
rollback, and their command-line entry points are implemented. The complete
generated configuration path has a recorded isolated Codex CLI verification;
see [Codex compatibility](#codex-compatibility) for its exact scope.

## Technology

- Python 3.11 or newer
- `uv` dependency and environment management
- Pytest behavior tests
- Ruff linting and formatting
- Strict mypy type checking
- `src/` package layout
- Pure hook handlers behind command and installation adapters
- Description-only managed roles and recoverable user-configuration transactions
- POSIX-only verified installation and rollback (POSIX file modes and
  `shlex` quoting); Windows is unverified
- Test suite gated on Python 3.11 (declared minimum) and the current
  development Python

## Codex compatibility

Runtime code does not pin, compare, or branch on the Codex CLI version. A
version listed here is a completed compatibility probe, not a runtime lock, a
minimum version, or a claim about unlisted releases.

| Codex CLI | Verified surfaces | Evidence |
|---|---|---|
| `0.144.1` | Strict hook protocol, command adapters, generated user installation, and fresh-session role/Hook discovery | [`docs/research/codex-0.144.1-hook-evidence.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/research/codex-0.144.1-hook-evidence.md) |
| `0.144.3` | Root guidance, deny-before-creation, managed role context, fail-open behavior, generated installation, status, rollback, and both spawn shapes of the capability seam against the shipped stable toolset | [`docs/research/codex-0.144.3-hook-evidence.md`](https://github.com/dzshzx/codex-subagent-router/blob/HEAD/docs/research/codex-0.144.3-hook-evidence.md) |

The `0.144.3` probe used package version `0.1.2`. Version `0.1.3` changed only
branch-agnostic documentation links. Version `0.1.4` retains the same generated
Hook configuration and runtime contracts while rejecting relative explicit
launcher paths earlier at the CLI boundary. These packaging and preflight
changes do not extend the Codex-version compatibility claim beyond the recorded
probe.

The installed `0.144.3` release binary drifts from its source tag: it still
reports the flattened `collaborationspawn_agent` hook tool name and its
default stable spawn handler enforces the V2-shaped input contract. Release
decisions therefore rest on installed-binary probes, never on tag source
reading alone.

Codex ships two multi-agent tool generations: stable `multi_agent`
(MultiAgent V1) is enabled by default, while `multi_agent_v2` is a separately
enabled, under-development preview. Both generations register the same
`spawn_agent` hook tool name, so the validator supports both input shapes
through one capability seam and normal spawns work on a default V1
installation without enabling the preview.

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

Five profiles cover routine work in ascending capability order:

| Model | Effort |
|---|---|
| `gpt-5.6-terra` | `medium` |
| `gpt-5.6-sol` | `low` |
| `gpt-5.6-terra` | `high` |
| `gpt-5.6-sol` | `medium` |
| `gpt-5.6-sol` | `high` |

Two profiles provide conditional escalation in ascending capability order:

| Model | Effort |
|---|---|
| `gpt-5.6-sol` | `xhigh` |
| `gpt-5.6-sol` | `max` |

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

`validate_pre_tool_use` ignores non-spawn tool calls. Stable MultiAgent V1 and
MultiAgent V2 register the same hook tool name, so for verified spawn tool
names the validator selects the contract from the input shape: a `task_name`
or `fork_turns` field selects the V2 contract, and any other object is
validated as a stable V1 spawn. Both variants must route explicitly with
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
describing the deployment as verified. Normal use relies on the stable
`multi_agent` feature and does not require enabling the `multi_agent_v2`
preview.

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

If `codex-subagent-router-hook` cannot be resolved on `PATH`, `plan` and
`install` accept `--hook-executable PATH`. The value must be an absolute path to
a regular executable file in a persistent environment.

When `plan` exits `0` with an empty `conflicts` array, install and query status:

```bash
codex-subagent-router install --codex-home "$CODEX_HOME"
codex-subagent-router status --codex-home "$CODEX_HOME"
```

`--codex-home` is always required. The CLI never falls back to `~/.codex`,
and a blank value is rejected instead of resolving to the current working
directory.

`status` is healthy only when its JSON contains `"state": "installed"` and an
empty `details` array. A completed status query exits `0` for every reported
state, including `not-installed`, `modified`, and `incomplete`; automation must
inspect `state` instead of treating exit `0` as proof of a healthy installation.

Successful operations and modeled `plan` conflicts write machine-readable JSON
to stdout. A plan with conflicts exits `1`. Usage errors exit `2` with text on
stderr. Failures raised before planning, and installation or rollback
violations, exit `1` with text on stderr; callers must not assume that every
nonzero result contains JSON.

The installer adds description-only declarations for the four managed roles to
`config.toml`, adds the three command-hook groups to `hooks.json`, and writes a
private receipt under `codex-subagent-router/installation.json`. Existing bytes
and file modes are captured before a change. Each replacement is atomic, and a
persisted journal makes an interrupted two-file transaction recoverable.
Configuration files and state paths that are symbolic links are rejected.
Compatible entries that already exist are verified but are not claimed as
installer-owned.

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

Rollback is explicit:

```bash
codex-subagent-router rollback --codex-home "$CODEX_HOME"
```

If the installed files are unchanged, rollback restores their exact original
bytes and modes or removes files the installer created. If unrelated content
was added later, rollback removes only still-intact owned blocks and hook groups.
It refuses to proceed when owned content has been modified, when the receipt is
unhealthy, or while another installation operation holds the lock.

Uninstall in this order: run `rollback` first, then remove the package. The
rollback CLI and the hook launcher live in the package environment, so
removing the package first leaves managed hook groups pointing at a missing
launcher. If that happens, reinstall the same package version and roll back,
or repair `hooks.json` manually.

The same transaction seam is available to Python callers. Both paths must be
explicit; importing the package never reads user configuration:

```python
from pathlib import Path

from codex_subagent_router import install_user_config, plan_user_installation

codex_home = Path("/explicit/codex/home")
hook_command = ("/absolute/path/to/codex-subagent-router-hook",)
plan = plan_user_installation(codex_home, hook_command)
result = install_user_config(codex_home, hook_command)
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
6. User-level installation and rollback tooling. **Complete.**

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Tests and package imports must not read or modify user-level Codex configuration.
- Repository code must not contain machine-specific absolute paths.
- Runtime policy code must not add hidden fallbacks or duplicate policy sources.
- Runtime package code must not pin or branch on a Codex CLI version; versioned
  compatibility claims belong in reproducible evidence records.
