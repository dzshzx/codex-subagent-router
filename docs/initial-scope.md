# Initial repository scope

Date: 2026-07-13

## Objective

Create an independent, versioned Python repository for developing and validating
Codex subagent routing hooks. The repository owns reusable routing code; user-level
Codex configuration remains an installation concern.

## Initial deliverable

- A standard `src/` Python package named `codex_subagent_router`.
- A single public policy seam that exposes the supported automatic routes and
  validates child reasoning effort.
- Five routine profiles:
  - `gpt-5.6-terra / medium`
  - `gpt-5.6-sol / low`
  - `gpt-5.6-terra / high`
  - `gpt-5.6-sol / medium`
  - `gpt-5.6-sol / high`
- Two conditional escalation profiles:
  - `gpt-5.6-sol / xhigh`
  - `gpt-5.6-sol / max`
- Standard-library unit tests that exercise the public policy seam.
- Packaging metadata and contributor commands sufficient to run the checks from
  a fresh checkout with Python 3.11 or newer.

## Boundaries

- The initial repository establishes policy and test infrastructure.
- Hook protocol handlers, role templates, installers, and release automation are
  subsequent deliverables.
- Production Codex configuration is unchanged by repository setup or tests.

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Tests must not read or modify `~/.codex`.
- Repository code must not contain machine-specific absolute paths.
- The initial package must not require third-party runtime or test dependencies.

## Acceptance criteria

1. The repository is initialized on branch `main`.
2. The package imports from `src/`.
3. The public policy seam returns exactly five routine routes and two conditional
   routes in the documented order.
4. The public policy seam accepts supported non-`ultra` efforts and rejects
   `ultra` and unknown effort names.
5. The full standard-library test suite passes.
6. The implementation is committed and reviewed against this scope.
