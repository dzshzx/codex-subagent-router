# Role contracts

## Purpose

Role identity expresses a stable kind of work. Model and reasoning effort are
selected independently for each spawn through the routing policy.
`src/codex_subagent_router/roles.py` is the single executable source for the
ordered contracts and `SubagentStart` developer context. This document explains
that source and must not introduce alternative runtime wording or compute
choices.

The minimum managed role set is `researcher`, `reviewer`,
`architecture_explorer`, and `interface_designer`. Built-in Codex roles remain
outside this managed set and must not be overridden accidentally.

`subagent_start_context()` selects contracts by exact `agent_type`. It returns
no output for built-in or other unmanaged roles; it never substitutes a default
managed role. `role_contracts()` exposes the frozen declarations for later
description-only installation metadata.

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

## `architecture_explorer`

The architecture explorer performs a broad, read-only codebase scan for module
and interface friction.

Contract:

- Read relevant domain context and ADRs before judging the design.
- Trace responsibilities, seams, adapters, invariants, and dependency
  direction across modules.
- Identify deepening opportunities with concrete file evidence and downstream
  leverage.
- Return candidates and their trade-offs only.
- Do not produce the final report, design a replacement interface, or implement
  a refactor.

This role is intentionally distinct from Codex's built-in `explorer`, which is
for specific, well-scoped codebase questions.

## `interface_designer`

The interface designer generates one genuinely distinct module or API design
from a supplied technical brief.

Contract:

- State invariants, ordering, error modes, usage, and hidden implementation.
- Define dependency adapters and explain the design's trade-offs.
- Use project domain vocabulary and respect existing ADRs.
- Stay independent of parallel designs so the alternatives differ materially.
- Do not edit files or implement the design.

Multiple design alternatives use multiple instances of this role with different
brief constraints, not numbered role variants.

## Prohibitions

- A role contract must not pin a model, effort, service tier, or fork mode.
- Do not define a generic custom `explorer`; it would override the built-in role.
- Do not add role names for one-off prompt differences.
- Do not create `standards_reviewer` and `spec_reviewer` unless their persistent
  tools or behavior genuinely diverge and the duplicated prompt source is first
  removed.
- Do not create speculative `worker`, `tester`, or `investigator` roles without
  an actual workflow that spawns them.
