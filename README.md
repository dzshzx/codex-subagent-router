# Codex Subagent Router

`codex-subagent-router` is an independent Python project for developing and
validating model, effort, role, and context-routing policy for Codex subagents.

The repository currently provides the stable policy seam and strict JSON value
types for the `PreToolUse` and `SubagentStart` hook boundaries. Hook handlers and
installation tooling are subsequent deliverables.

## Technology

- Python 3.11 or newer
- `uv` dependency and environment management
- Pytest behavior tests
- Ruff linting and formatting
- Strict mypy type checking
- `src/` package layout
- JSON command adapters for Codex hooks in the next implementation stage
- Markdown role contracts and TOML installation metadata in later stages

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
    PreToolUseDenyOutput,
    conditional_routes,
    encode_hook_output,
    parse_hook_input,
    routine_routes,
    validate_child_effort,
)

routine = routine_routes()
conditional = conditional_routes()
effort = validate_child_effort("high")

hook_input = parse_hook_input(sys.stdin.read())
denial_json = encode_hook_output(
    PreToolUseDenyOutput(reason="explicit policy reason")
)
```

`parse_hook_input` accepts one JSON document and returns a typed
`PreToolUseInput` or `SubagentStartInput`. It rejects unknown fields, missing or
wrongly typed fields, duplicate keys, unsupported event and permission values,
non-JSON numeric constants, and numeric overflow. `encode_hook_output` only emits
the project-owned deny or subagent-context output shapes, whose string fields are
validated when their value objects are constructed.

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
3. Deny-only `PreToolUse` validator.
4. `SessionStart` routing guidance and `SubagentStart` role contracts.
5. Isolated end-to-end hook probes.
6. User-level installation and rollback tooling.

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Tests and package imports must not read or modify user-level Codex configuration.
- Repository code must not contain machine-specific absolute paths.
- Runtime policy code must not add hidden fallbacks or duplicate policy sources.
