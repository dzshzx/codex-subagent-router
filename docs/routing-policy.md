# Routing policy

## Purpose

This document defines the supported route options and validation contract.
`policy.py` remains the single executable source of truth for independent child
model and reasoning-effort choices.

## Compute contract

Python does not infer natural-language task semantics. Identity, model, and
effort remain independent fields. The same catalogs apply to all five
identities.

| Model | Description |
|---|---|
| `gpt-5.6-luna` | Lightweight model |
| `gpt-5.6-terra` | General-purpose model |
| `gpt-5.6-sol` | Highest-capability model |

| Effort | Description |
|---|---|
| `low` | Low reasoning depth |
| `medium` | Medium reasoning depth |
| `high` | High reasoning depth |
| `xhigh` | Extra-high reasoning depth |
| `max` | Maximum reasoning depth |

Every listed model may be combined with every listed effort. The catalogs state
runtime-supported choices and option descriptions, not pre-bound profiles. The
older quality-gate analysis remains recorded in
[`deepswe-v1.1-routing-evidence.md`](research/deepswe-v1.1-routing-evidence.md)
as historical evidence, not as a second current route table.

## Hook responsibilities

- The parent supplies `agent_type`, model, effort, and context.
- `PreToolUse` validates the explicit model and effort independently and denies
  unsupported values before child creation.
- `PreToolUse` does not interpret task semantics or silently rewrite model,
  effort, role, or fork mode.
- `SessionStart` emits parent routing guidance only for root `startup`; the text
  is derived from the executable policy and managed-identity sources.
- `SubagentStart` injects the stable contract for the resolved role. It does not
  select or validate compute, and it emits no output for unmanaged identities.

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
present; managed identity selection belongs to the start-context stage.

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- `xhigh` and `max` have no extra justification requirement.
- Unknown model and effort values are rejected explicitly.
- No hidden fallback may replace a missing or invalid decision.
- No Hook may infer complexity from `task_name` and silently change compute.
- No second model catalog, effort catalog, or pair allowlist may be introduced.
- Hook validation must not be represented as a fail-closed security or cost
  boundary; Codex command-hook failures are fail-open in the verified version.
