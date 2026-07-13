# ADR-0003: Use recoverable user-installation transactions

- Status: Accepted
- Date: 2026-07-13

## Context

The router is useful only when four description-only roles and three command
hook groups are present in the user's Codex configuration. Codex 0.144.1 loads
user roles from `$CODEX_HOME/config.toml` and command hooks from the adjacent
`hooks.json`. It provides no ordinary CLI command that safely installs both
files as one operation.

The files are user-owned and may already contain unrelated configuration. A
process can fail after replacing one file but before replacing the other. A
later whole-file restore could also erase edits made after installation. Hook
trust is separate user state and must not be silently granted by an installer.

## Decision

Expose a transaction API whose `codex_home` and hook command are explicit:

- `plan_user_installation`
- `install_user_config`
- `installation_status`
- `rollback_user_config`

Keep the console interface thin. Its `plan`, `install`, `status`, and `rollback`
commands require `--codex-home`; the install paths never infer the production
home. The package exposes separate `codex-subagent-router` and
`codex-subagent-router-hook` console scripts, and installed hook commands use an
absolute launcher path.

Derive role declarations from `roles.py` and event names, matchers, handlers,
and command names from `hook_specs.py`. The installer does not duplicate the
routing table or role descriptions as a second executable source.

Before changing files, write a private transaction journal containing original
bytes, modes, installed hashes, owned entries, and the complete compatible
configuration expected after installation. Replace each file atomically in its
own directory, then atomically write the installed receipt and remove the
journal. A directory lock serializes install and rollback operations. Reject
symbolic links and non-file configuration targets instead of replacing links or
following state paths.

The transaction is recoverable rather than falsely described as cross-file
atomic. If an installation reports a filesystem error in-process, restore both
files from the in-memory snapshots. If its persisted journal remains after an
interruption, status reports `incomplete` and rollback accepts only original or
installed file hashes.

Validate a receipt as one internally consistent record before trusting any
rollback field. Rebuild each installed document from its recorded original
snapshot and managed delta, then require the rebuilt hash and expected role or
hook structure to match the receipt. Also require the observed file mode to
match the mode the transaction preserved or created before allowing rollback.

Rollback is also journaled before its first mutation. It computes both complete
targets, then persists each pre-rollback hash, target bytes and mode, and result
action under a `rolling-back` state. A retry accepts only a pre-rollback or
already-applied target hash, reapplies both targets idempotently, and removes the
receipt and journal only after both files reach their targets.

Record ownership narrowly. Compatible roles or hook groups that predate the
receipt are expected and monitored but not removed by rollback. Entries added
by the installer are removed only while still intact. When an installed file is
otherwise unchanged, restore its exact original bytes and mode. When unrelated
content was added later, remove the owned TOML block and exact JSON groups
surgically. Refuse rollback if owned configuration is missing or modified.

Do not write Codex hook trust hashes and do not configure the dangerous trust
bypass. Report that hook review and a fresh session are required.

## Consequences

- Package import and tests remain isolated from `~/.codex`; every filesystem
  target is explicit and tests use temporary directories.
- Reinstallation is idempotent for the same launcher and refuses to replace the
  original rollback snapshot when requested configuration differs.
- Invalid TOML, invalid JSON, incompatible role names, conflicting managed
  matchers, unsafe paths, unhealthy receipts, and concurrent operations fail
  closed before configuration changes.
- Newly created configuration and state files use mode `0600`; existing file
  modes are preserved across installation, failure recovery, and rollback.
- A crash can leave a visible journal or lock that requires recovery or operator
  inspection, but cannot be mistaken for a complete installation.
- Hook review remains an explicit human trust decision, and ordinary file writes
  require a fresh Codex session for reliable discovery.
- Codex command-hook failures remain fail-open. Installation improves
  repeatability and rollback, not the security strength of the hook boundary.

## Rejected alternatives

- Replacing whole user files would discard unrelated configuration.
- Keeping only an unjournaled backup cannot distinguish an interrupted install
  from a complete one.
- Replaying the original whole file during every rollback would erase later
  user edits.
- Silently adopting existing entries as installer-owned would remove
  configuration the user created independently.
- Auto-writing hook trust state or enabling the dangerous bypass would remove a
  deliberate Codex safety decision.
- Repository-relative hook commands would fail when Codex runs them from an
  event working directory outside the checkout.
