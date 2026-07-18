# ADR-0002: Separate role identity from compute

- Status: Accepted
- Date: 2026-07-13
- Updated: 2026-07-18

## Context

Codex 0.144.1 applies per-spawn model and effort before applying a custom role.
A role backed by a config file reloads configuration layers and can erase those
per-spawn compute values. The project also needs the same role to operate at
different compute profiles without multiplying role files.

## Decision

Declare managed identities by name and description without a role `config_file`.
Inject their stable behavior through `SubagentStart`. Select model and reasoning
effort explicitly on each spawn from the routing policy.

The managed identities are:

- `researcher`
- `reviewer`

Codex's built-in `default`, `explorer`, and `worker` identities remain
platform-owned. Architecture scans and interface alternatives are task briefs
or methods applied to those identities until repeated usage demonstrates a
distinct persistent contract.

Role contracts contain behavior only. The executable compute ladder remains in
`policy.py`.

## Consequences

- One role can use different supported compute profiles without duplicated
  role-by-model files.
- Concurrent children can carry different role and compute combinations without
  sharing mutable configuration.
- Role contracts and compute routes have separate, narrow reasons to change.
- Installation must create description-only role declarations and hook-backed
  role context.
- A missing role-context hook is visible as missing behavior rather than an
  implicit fallback role file.

## Rejected alternatives

- Role config files risk overwriting per-spawn model and effort in the verified
  Codex version.
- A role-by-model matrix duplicates behavior and increases maintenance cost.
- A generic custom `explorer` would override the narrower built-in role.
- Architecture exploration and interface design currently vary by task brief,
  not by persistent identity.
- Custom worker, tester, and debugger identities duplicate the built-in worker
  or a method applied within a task.
- External SDK threads lose native subagent-tree and collaboration semantics.
- A local Codex patch would add ongoing upgrade and rollback risk.
