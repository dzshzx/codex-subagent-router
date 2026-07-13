# Changelog

## 0.1.2 — 2026-07-13

First publicly released version.

### Added

- Spawn-shape capability seam: the `PreToolUse` validator accepts both the
  stable MultiAgent V1 input shape (`message`/`items`, `fork_context`) and
  the MultiAgent V2 shape (`task_name`, `fork_turns`), selected from the
  tool input itself, with one shared model/effort policy source.
- `plan` reports every condition that would make `install` refuse — leftover
  transaction journal, held operation lock, unhealthy or diverging existing
  installation, and a non-executable hook launcher — as explicit conflicts.
- `status` reports a managed hook launcher that is no longer an executable
  file without blocking rollback.
- MIT license, PEP 561 `py.typed` marker, complete packaging metadata, and
  project URLs.
- CI gate on Python 3.11 and 3.14; tag-triggered publishing through TestPyPI
  to PyPI with trusted publishing.

### Fixed

- Installation, crash recovery, and rollback now fail closed on concurrent
  external edits: every user-file replacement is a guarded compare-and-commit
  against the exact planned snapshot, a failed transaction restores only its
  own replacements, and concurrent modifications are preserved together with
  the recovery journal.
- A blank `--codex-home` is rejected instead of resolving to the current
  working directory.

### Evidence

- Isolated installed-binary probes of Codex CLI `0.144.3` verified the
  generated installation path end to end and documented that the release
  binary drifts from its source tag
  (`docs/research/codex-0.144.3-hook-evidence.md`).

## 0.1.1 and earlier

Internal, unpublished development versions; see the git history.
