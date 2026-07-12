# Contributing

## Code standards

- Support Python 3.11 and newer.
- Add runtime or development dependencies when they provide a concrete
  implementation or feedback benefit.
- Expose policy through the package public API; keep storage details private.
- Represent immutable policy data with frozen value objects and tuples.
- Validate external input at the protocol boundary and raise explicit errors.
- Keep one policy source of truth and derive protocol-specific output from it.
- Use descriptive domain names such as `Profile`, `PolicyViolation`, and
  `validate_child_effort`.
- Keep machine-specific paths and user configuration out of repository code.

## Tests

- Test observable behavior through public package interfaces.
- Use independent literals from the written policy as expected values.
- Add one focused test before implementing each new behavior.
- Avoid mocks for code owned by this repository.

Run all checks before committing:

```bash
uv run pytest
uv run ruff check .
uv run mypy
uv build
git diff --check
```
