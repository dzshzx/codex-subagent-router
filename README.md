# Codex Subagent Router

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

## Codex compatibility

Runtime code does not pin, compare, or branch on the Codex CLI version. A
version listed here is a completed compatibility probe, not a runtime lock, a
minimum version, or a claim about unlisted releases.

| Codex CLI | Verified surfaces | Evidence |
|---|---|---|
| `0.144.1` | Strict hook protocol, command adapters, generated user installation, and fresh-session role/Hook discovery | [`docs/research/codex-0.144.1-hook-evidence.md`](docs/research/codex-0.144.1-hook-evidence.md) |

Unlisted Codex versions are unverified. The protocol boundary is deliberately
strict, while Codex command-hook failures are fail-open; an upstream schema or
tool-name change can therefore disable routing enforcement instead of safely
falling back. Do not declare another version verified until its official
schemas and source behavior have been compared and its isolated root-start,
spawn-denial, managed-child, generated-installation, status, and rollback
probes pass. Keep each version's evidence as a separate record rather than
replacing old links with an unpinned `latest` reference.

## Automatic routing policy

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

`validate_pre_tool_use` ignores non-spawn tool calls. For verified spawn tool
names, it requires the explicit V2 fields, validates the model/effort pair from
the policy seam, permits only `fork_turns="none"` or a positive integer string,
and returns either a deny value or `None`. It never rewrites tool input.

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

Install the package so both console scripts are on `PATH`, then inspect the
planned changes against an explicit Codex home:

```bash
codex-subagent-router plan --codex-home "$CODEX_HOME"
codex-subagent-router install --codex-home "$CODEX_HOME"
codex-subagent-router status --codex-home "$CODEX_HOME"
```

`--codex-home` is always required. The CLI never falls back to `~/.codex`.
`plan` and `install` locate `codex-subagent-router-hook` on `PATH`; an explicit
absolute launcher can instead be selected with `--hook-executable PATH`.
Machine-readable JSON is written to stdout. Usage errors exit `2`, installation
or planning conflicts exit `1`, and successful operations exit `0`.

The installer adds description-only declarations for the four managed roles to
`config.toml`, adds the three command-hook groups to `hooks.json`, and writes a
private receipt under `codex-subagent-router/installation.json`. Existing bytes
and file modes are captured before a change. Each replacement is atomic, and a
persisted journal makes an interrupted two-file transaction recoverable.
Configuration files and state paths that are symbolic links are rejected.
Compatible entries that already exist are verified but are not claimed as
installer-owned.

Codex does not reliably hot-reload ordinary user configuration files. After a
successful install, review and trust the new user hooks in Codex, then start a
fresh session. The installer deliberately does not write hook trust state and
does not enable `--dangerously-bypass-hook-trust`. Hook launch failures and
timeouts are fail-open in Codex, so this router remains a policy guardrail, not
a security or spending-isolation boundary.

Rollback is explicit:

```bash
codex-subagent-router rollback --codex-home "$CODEX_HOME"
```

If the installed files are unchanged, rollback restores their exact original
bytes and modes or removes files the installer created. If unrelated content
was added later, rollback removes only still-intact owned blocks and hook groups.
It refuses to proceed when owned content has been modified, when the receipt is
unhealthy, or while another installation operation holds the lock.

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
[`docs/routing-policy.md`](docs/routing-policy.md),
[`docs/role-contracts.md`](docs/role-contracts.md), and
[`docs/research/`](docs/research/).

## Development

Create or update the development environment:

```bash
uv sync --dev
```

Run all checks:

```bash
uv run pytest
uv run ruff check .
uv run mypy
uv build
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
