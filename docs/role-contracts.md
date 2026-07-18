# Subagent identity roster

## Purpose

Subagent identity expresses a stable kind of work. Model and reasoning effort are
selected independently for each spawn through the routing policy.
`src/codex_subagent_router/roles.py` is the single executable source for the
ordered contracts and `SubagentStart` developer context. This document explains
that source and must not introduce alternative runtime wording or compute
choices.

## Identity roster

| Identity | Owner | Use when | Router contract |
|---|---|---|---|
| `default` | Codex | General delegated analysis or independent alternatives | none |
| `explorer` | Codex | A specific, well-scoped codebase question | none |
| `worker` | Codex | Bounded production changes with explicit file ownership | none |
| `researcher` | Router | Evidence-led investigation of external primary sources | managed |
| `reviewer` | Router | Independent read-only assessment of one supplied review axis | managed |

Only `researcher` and `reviewer` are router-managed identities. Built-in Codex
identities remain outside this managed set and must not be overridden. The
platform rows are descriptive compatibility facts; the router neither renders
nor installs them.

`subagent_start_context()` selects contracts by exact `agent_type`. It returns
no output for built-in or other unmanaged identities; it never substitutes a
default managed identity. `role_contracts()` exposes the frozen declarations
for later description-only installation metadata.

## `researcher`

The researcher investigates external documentation, specifications, APIs,
upstream source, and necessary local evidence.

Contract:

- Prefer primary and authoritative sources.
- Distinguish verified facts, source-based inferences, and open questions.
- Cite material claims near the claim.
- Write only the specifically requested research artifact when the task requires
  a repository deliverable.
- Do not make unrelated project changes.

Completion means the requested question is answered with enough evidence for a
later implementation or decision.

## `reviewer`

The reviewer performs an independent, read-only review of a bounded diff against
one axis supplied in the spawn brief.

Contract:

- Respect the fixed point, diff scope, standards sources, and specification in
  the brief.
- Review exactly one axis, such as Standards or Spec.
- Report only actionable findings supported by file, hunk, standard, or spec
  evidence.
- Rank findings by severity and explain the observable impact.
- Do not edit files or broaden the review into implementation.

Standards and Spec use separate reviewer instances, not separate role names.
Their axis-specific prompts remain the source of their temporary difference.

## Platform identities and task briefs

Use Codex's built-in `default`, `explorer`, and `worker` identities without
redefining them. A targeted codebase question belongs to `explorer`; production
work belongs to `worker`; general analysis and independent interface
alternatives can use `default` with distinct task briefs.

Architecture exploration, interface design, testing, and debugging are methods
or task-specific scopes. They do not become managed identities unless repeated
usage demonstrates a stable behavior, authority, or output contract that cannot
be expressed by a platform identity plus a task brief.

## Prohibitions

- A role contract must not pin a model, effort, service tier, or fork mode.
- Do not redefine the platform `default`, `explorer`, or `worker` identities.
- Do not add role names for one-off prompt differences.
- Do not create `standards_reviewer` and `spec_reviewer` unless their persistent
  tools or behavior genuinely diverge and the duplicated prompt source is first
  removed.
- Do not create `architecture_explorer`, `interface_designer`, `tester`,
  `debugger`, or `investigator` without repeated evidence for a distinct
  persistent identity.
