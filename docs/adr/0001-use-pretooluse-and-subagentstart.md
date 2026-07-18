# ADR-0001: Use `PreToolUse` and `SubagentStart`

- Status: Accepted
- Date: 2026-07-13

## Context

The router must validate native `spawn_agent` parameters before child creation
and must inject role-specific developer context before the child's first model
request. Codex 0.144.1 exposes these abilities at different lifecycle events.

## Decision

Use one `PreToolUse` handler for deny-only spawn policy validation and one
`SubagentStart` handler for role-context selection.

Use an additional `SessionStart` handler matched only to root `startup` as a
parent-facing guidance layer. It renders the current route and managed-role
sources rather than owning another route table. Calls for resume, clear, or
compact produce no output.

The parent remains responsible for choosing explicit role, model, effort, and
context. `PreToolUse` rejects invalid input and never silently rewrites it.
`SubagentStart` selects a fixed role contract from the resolved `agent_type` and
does not attempt compute validation.

Both handlers derive behavior from project-owned policy and role sources. Their
protocol boundary rejects unknown fields and wrong event discriminators.

## Consequences

- Invalid spawns can be stopped before a child exists when the hook runs
  successfully.
- Role context reaches the child's first request as developer context.
- Root startup receives an exact view of the current managed identities and
  compute ladder without duplicating their executable sources.
- Routing validation and role behavior do not race as concurrent input rewrites.
- `SubagentStart` failures allow a child to continue without injected context.
- Command-hook failures are fail-open, so the validator is a guardrail rather
  than an isolation boundary.
- Installation must use a matcher compatible with both official and observed
  names and repeat an isolated probe on Codex upgrades.

## Rejected alternatives

- `PreToolUse` alone cannot inject child-only role context.
- `SubagentStart` alone runs too late to block or change child compute.
- `PostToolUse` runs after spawn side effects.
- `SessionStart` is not the thread-spawn child start event.
- Multiple rewrite hooks have last-completion-wins replacement semantics.
- Legacy `notify` is asynchronous observation without blocking or context
  injection.
