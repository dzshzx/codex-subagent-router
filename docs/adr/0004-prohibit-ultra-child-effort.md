# ADR-0004: Prohibit `ultra` child effort

- Status: Accepted
- Date: 2026-07-15

## Context

Codex accepts `ultra` as a reasoning-effort wire value, but the router must
decide whether it is meaningful for a child that has already been delegated a
bounded task. In the official `rust-v0.144.4` source, Codex maps an Ultra request
to the `max` wire effort and independently selects proactive multi-agent mode:
see [`client.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/client.rs#L165-L177)
and [`multi_agents.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/multi_agents.rs#L45-L58).
Ultra therefore carries orchestration semantics rather than merely selecting a
larger child reasoning budget.

A [community analysis](https://linux.do/t/topic/2578075) further describes
`ultra` as the `max` reasoning budget plus an orchestration prompt. Its specific
prompt and reported juice value are not an official compatibility contract and
are not relied on here. They are consistent with the two official source
behaviors above and with the project's installed-binary observations.

## Decision

Reject `ultra` whenever it is requested as child reasoning effort. The
`PreToolUse` validator remains deny-only: it returns the dedicated policy reason
and never rewrites `ultra` to `max` or another profile. `max` remains the highest
conditional child effort in the routing policy.

This is a project policy, not a claim that Codex considers the wire value
invalid. A delegated child should execute its assigned role; giving it an
orchestration-amplifying mode blurs parent/child ownership and invites nested
fan-out inside the child's budget.

## Consequences

- The policy seam must continue to distinguish prohibited child `ultra` from
  unknown effort names.
- A future Codex release changing Ultra's documented semantics does not silently
  relax this rule. Reconsideration requires explicit policy and probe evidence.
- Denial is observable before child creation when the command hook runs; it is
  still a fail-open hook guardrail rather than a security boundary.

## Rejected alternatives

- Silently rewriting `ultra` to `max` would hide caller error and violate the
  router's deny-only contract.
- Treating `ultra` as a routine high-effort child profile would couple bounded
  task execution to another orchestration layer.
