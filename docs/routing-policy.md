# Routing policy

## Purpose

This document defines the positive routing rules consumed by protocol adapters
and parent-agent guidance. `policy.py` remains the single executable source of
truth for independent child model and reasoning-effort choices.

## Dynamic compute planning

The parent interprets each task. Python does not attempt to infer natural-language
task semantics. Model and reasoning effort are two independent decisions:

| Model | Capability guidance |
|---|---|
| `gpt-5.6-luna` | Simple, low-risk, self-contained lookup, enumeration, and mechanical extraction |
| `gpt-5.6-terra` | Routine bounded execution, focused code changes, cross-file reading, synthesis, and analysis |
| `gpt-5.6-sol` | Complex multi-step implementation, critical review, adjudication, hard debugging, and high-risk work |

| Effort | Reasoning-depth guidance | Concrete reason required |
|---|---|---|
| `low` | Straightforward work with a clear path, few steps, and cheap verification | no |
| `medium` | Routine multi-step work with a known approach and normal verification | no |
| `high` | Ambiguous, cross-cutting, risk-sensitive, or verification-heavy work | no |
| `xhigh` | Exceptionally hard reasoning after high is insufficient | yes |
| `max` | Explicit highest-quality work after lower effort is insufficient | yes |

Every listed model may be combined with every listed effort. The catalogs state
runtime-supported choices and planning guidance, not pre-bound profiles. The
older quality-gate analysis remains recorded in
[`deepswe-v1.1-routing-evidence.md`](research/deepswe-v1.1-routing-evidence.md)
as historical evidence, not as a second current route table.

## Selection rules

1. Choose model from task capability, risk, and type: Luna for simple low-risk
   self-contained work; Terra for routine execution and analysis; Sol for
   complex implementation, critical review, hard debugging, and high-risk work.
2. Choose `reasoning_effort` independently from reasoning depth, ambiguity, and
   verification needs.
3. A higher effort does not compensate for a model that lacks the required
   capability.
4. Use the lowest-capability model and lowest effort that remain credible for
   the task.
5. Use `xhigh` or `max` only when the task requires it, and state a concrete
   reason.
6. Submit model and effort explicitly on a route-managed spawn. A missing field
   is not permission for a Hook to guess.
7. Keep role identity independent of compute. The same stable role may be
   spawned with different task-appropriate compute.
8. Keep context selection explicit. Route-managed V2 spawns use
   `fork_turns="none"` or a positive integer string; V1 spawns leave
   `fork_context` false or omitted.

The decision is recorded in
[`ADR-0007`](adr/0007-plan-model-and-effort-independently.md).

## Hook responsibilities

- The parent chooses `agent_type`, model, effort, and context based on the task.
- `PreToolUse` validates the explicit model and effort independently and denies
  unsupported values before child creation.
- `PreToolUse` does not interpret task semantics or silently rewrite model,
  effort, role, or fork mode.
- `SessionStart` emits parent routing guidance only for root `startup`; the text
  is derived from the executable policy and managed-role sources.
- `SubagentStart` injects the stable contract for the resolved role. It does not
  select or validate compute, and it emits no output for unmanaged roles.

## `PreToolUse` validator contract

The public validator accepts an already parsed `PreToolUseInput` and returns a
`PreToolUseDenyOutput` or `None`. It performs no I/O and does not mutate the Hook
input.

The validator recognizes the matching-tag `spawn_agent` name and `Agent` alias,
plus the `agentsspawn_agent` and `collaborationspawn_agent` names observed in
installed probes. Other tool names are ignored without inspecting their inputs.

For a recognized spawn, `tool_input` must be an object. A `task_name` or
`fork_turns` field selects the V2 contract; otherwise the stable V1 contract
applies.

V2 contains only:

- required non-empty `message`, `task_name`, `model`, `reasoning_effort`, and
  `fork_turns` strings;
- optional non-empty `agent_type` and `service_tier` strings.

`fork_turns` must be exactly `none` or an ASCII positive integer string.

V1 contains only:

- required non-empty `model` and `reasoning_effort` strings;
- exactly one of a non-empty `message` string or a non-empty `items` array;
- optional non-empty `agent_type` and `service_tier` strings;
- optional boolean `fork_context`, which must be `false`.

In both shapes model and reasoning effort are checked independently against the
policy catalogs. `agent_type` is checked only for a non-empty string when
present; managed role selection belongs to the start-context stage.

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Unknown model and effort values are rejected explicitly.
- No hidden fallback may replace a missing or invalid decision.
- No Hook may infer complexity from `task_name` and silently change compute.
- No second model catalog, effort catalog, or pair allowlist may be introduced.
- Hook validation must not be represented as a fail-closed security or cost
  boundary; Codex command-hook failures are fail-open in the verified version.
