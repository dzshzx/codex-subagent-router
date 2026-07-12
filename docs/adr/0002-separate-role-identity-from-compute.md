# ADR-0002: Separate role identity from compute

- Status: Accepted
- Date: 2026-07-13

## Context

Codex 0.144.1 applies per-spawn model and effort before applying a custom role.
A role backed by a config file reloads configuration layers and can erase those
per-spawn compute values. The project also needs the same role to operate at
different compute profiles without multiplying role files.

## Decision

Declare managed roles by name and description without a role `config_file`.
Inject their stable behavior through `SubagentStart`. Select model and reasoning
effort explicitly on each spawn from the routing policy.

The managed roles are:

- `researcher`
- `reviewer`
- `architecture_explorer`
- `interface_designer`

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
- External SDK threads lose native subagent-tree and collaboration semantics.
- A local Codex patch would add ongoing upgrade and rollback risk.
