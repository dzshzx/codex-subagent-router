# Contributing

## Code standards

- Support Python 3.11 and newer.
- Keep runtime and unit-test code on the Python standard library unless a concrete
  requirement justifies a dependency.
- Expose policy through the package public API; keep storage details private.
- Represent immutable policy data with frozen value objects and tuples.
- Validate external input at the protocol boundary and raise explicit errors.
- Keep one policy source of truth and derive protocol-specific output from it.
- Use descriptive domain names such as `Route`, `PolicyViolation`, and
  `validate_child_effort`.
- Keep machine-specific paths and user configuration out of repository code.

## Tests

- Test observable behavior through public package interfaces.
- Use independent literals from the written policy as expected values.
- Add one focused test before implementing each new behavior.
- Avoid mocks for code owned by this repository.

Run all checks before committing:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
git diff --check
```
