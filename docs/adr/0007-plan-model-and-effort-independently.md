# ADR-0007: Plan model and effort independently

- Status: Accepted
- Date: 2026-07-18

## Context

The previous policy represented routing as named `Profile` values that bound one
model to one reasoning effort. That made the parent choose from a static pair
table even though model capability and reasoning depth answer different task
questions.

Model choice depends on required capability, task type, risk, and scope. Effort
choice depends on reasoning depth, ambiguity, and verification needs. A simple
but ambiguous task may justify Luna/high, while a bounded operation needing Sol's
capability may justify Sol/low. A fixed pair allowlist cannot express those
decisions without growing into a second task taxonomy.

Python cannot reliably infer natural-language task semantics. The parent agent
already has that context and must remain responsible for the dynamic decision.

## Decision

Replace fixed profiles with one `RoutingPolicy` containing two independent
catalogs:

- model capability guidance for Luna, Terra, and Sol;
- reasoning-depth guidance for low, medium, high, xhigh, and max.

Expose two public entry points at the policy seam:

```python
routing_policy() -> RoutingPolicy
validate_routed_compute(model, reasoning_effort) -> RoutedCompute
```

Every listed model may be combined with every listed effort. The validator
checks membership independently, continues to prohibit `ultra`, and never
interprets, fills, falls back, or rewrites. The generated skill and SessionStart
guidance render the same two catalogs and decision rules.

Effort escalation cannot compensate for insufficient model capability. `xhigh`
and `max` require a concrete parent-supplied reason as guidance; the validator
cannot enforce prose that is absent from the spawn schema.

A real-backend Codex `0.144.4` probe confirmed that a V2 Sol parent can
explicitly create a Luna/low child with `fork_turns="none"`; see
[`codex-0.144.4-v2-luna-child-evidence.md`](../research/codex-0.144.4-v2-luna-child-evidence.md).

## Consequences

- Public `Profile`, `routine_routes()`, `conditional_routes()`, and
  `validate_child_effort()` are replaced in `0.1.7` by the new policy seam.
- Validator policy errors now distinguish unsupported model from unsupported
  reasoning effort; there is no unsupported-pair error.
- The parent gets task-aware flexibility such as Luna/high, Terra/xhigh, and
  Sol/low without adding combinations to a pair table.
- Usage reports can verify explicit supported values but cannot judge semantic
  task fit from route fields alone.
- Existing DeepSWE evidence remains historical support for some Terra/Sol
  trade-offs. It does not define the current independent catalogs or benchmark
  Luna quality, latency, or cost.
- Role identity and context inheritance remain independent of compute selection.

## Rejected alternatives

- A structured `TaskAssessment -> plan_routes()` engine: it would expose a broad
  interface and encode an incomplete duplicate of the parent agent's semantic
  judgment.
- Keeping legacy fixed profiles as compatibility projections: they would remain
  a misleading second routing surface.
- A model-effort compatibility matrix without runtime evidence requiring one:
  it would recreate fixed pairing under a different name.
