# Codex Subagent Router

`codex-subagent-router` is an independent Python project for developing and
validating model, effort, role, and context-routing policy for Codex subagents.

The repository currently provides the stable policy seam. Hook protocol adapters
and installation tooling are subsequent deliverables.

## Technology

- Python 3.11 or newer
- Standard-library policy and tests
- `src/` package layout
- JSON command adapters for Codex hooks in the next implementation stage
- Markdown role contracts and TOML installation metadata in later stages

## Automatic routing policy

Five routes cover routine work:

| Route | Model | Effort | Intent |
|---|---|---|---|
| `bounded-economy` | `gpt-5.6-terra` | `medium` | Batch work with clear boundaries and quickly verifiable results |
| `bounded-fast-quality` | `gpt-5.6-sol` | `low` | Interactive bounded work that needs stronger first-pass reliability |
| `routine` | `gpt-5.6-terra` | `high` | Routine coding, research, and review |
| `deep` | `gpt-5.6-sol` | `medium` | Cross-file work with multiple dependencies or sustained reasoning |
| `critical` | `gpt-5.6-sol` | `high` | High-impact, high-error-cost, or long-horizon work |

Two routes provide conditional escalation:

| Route | Model | Effort | Intent |
|---|---|---|---|
| `escalate` | `gpt-5.6-sol` | `xhigh` | Critical work that needs higher reliability or has concrete failure evidence |
| `ceiling` | `gpt-5.6-sol` | `max` | Work explicitly requiring the highest observed reliability |

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

Run the complete zero-dependency test suite:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Compile every Python source file:

```bash
python3 -m compileall -q src tests
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
