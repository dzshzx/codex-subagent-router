# Contributing

## Code standards

- Support Python 3.11 and newer.
- Add runtime or development dependencies when they provide a concrete
  implementation or feedback benefit.
- Expose policy through the package public API; keep storage details private.
- Represent immutable policy data with frozen value objects and tuples.
- Validate external input at the protocol boundary and raise explicit errors.
- Keep one policy source of truth and derive protocol-specific output from it.
- Keep runtime package code independent of the Codex CLI version. Record
  version-specific upstream facts in immutable, versioned evidence rather than
  scattering version comparisons or `latest` links through executable code.
- Use descriptive domain names such as `Profile`, `PolicyViolation`, and
  `validate_child_effort`.
- Keep machine-specific paths and user configuration out of repository code.

## Tests

- Test observable behavior through public package interfaces.
- Use independent literals from the written policy as expected values.
- Add one focused test before implementing each new behavior.
- Avoid mocks for code owned by this repository.

## Codex compatibility verification

Do not describe a Codex release as verified merely because the package imports
or its installer completes. For each newly verified release:

1. Compare the official hook schemas, hook lifecycle, spawn input, tool-name
   matching, role precedence, trust behavior, and failure behavior with the
   currently supported contract.
2. Run isolated root `SessionStart`, invalid-spawn denial, managed
   `SubagentStart`, generated installation, status, and rollback probes in a
   temporary explicit `CODEX_HOME`.
3. Add a new version-specific record under `docs/research/` with immutable
   upstream source links and the observed results. Preserve earlier records.
4. Add the release to the README compatibility table only after those checks
   pass. A table entry records tested evidence; it must not introduce a runtime
   version branch.

If an upstream protocol change needs more than the current strict contract,
design a protocol-capability seam instead of adding scattered version checks.

Run all checks before committing:

```bash
uv run pytest
uv run ruff check .
uv run mypy
uv build
git diff --check
```
