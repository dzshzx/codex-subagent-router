# Codex Subagent Router

`codex-subagent-router` is an independent Python project for developing and
validating model, effort, role, and context-routing policy for Codex subagents.

The repository currently provides the stable policy seam. Hook protocol adapters
and installation tooling are subsequent deliverables.

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
from codex_subagent_router import (
    conditional_routes,
    routine_routes,
    validate_child_effort,
)

routine = routine_routes()
conditional = conditional_routes()
effort = validate_child_effort("high")
```

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

1. Stable routing policy and tests.
2. Codex hook input and output protocol types.
3. Deny-only `PreToolUse` validator.
4. `SessionStart` routing guidance and `SubagentStart` role contracts.
5. Isolated end-to-end hook probes.
6. User-level installation and rollback tooling.

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Tests and package imports must not read or modify user-level Codex configuration.
- Repository code must not contain machine-specific absolute paths.
- Runtime policy code must not add hidden fallbacks or duplicate policy sources.
