# Routing policy

## Purpose

This document defines the positive routing rules consumed by protocol adapters
and parent-agent guidance. `policy.py` remains the single executable source of
truth for the ordered compute profiles and supported child efforts.

## Automatic compute ladder

Routine routes are ordered by increasing capability and resource use:

| Order | Model | Effort | Intended quality gate |
|---:|---|---|---:|
| 1 | `gpt-5.6-terra` | `medium` | 35% |
| 2 | `gpt-5.6-sol` | `low` | 45% |
| 3 | `gpt-5.6-terra` | `high` | 50% |
| 4 | `gpt-5.6-sol` | `medium` | 60% |
| 5 | `gpt-5.6-sol` | `high` | 65% |

Conditional escalation routes are also ordered by increasing capability and
resource use:

| Order | Model | Effort | Intended quality gate |
|---:|---|---|---:|
| 1 | `gpt-5.6-sol` | `xhigh` | 70% |
| 2 | `gpt-5.6-sol` | `max` | 72% |

The gates describe the versioned DeepSWE analysis in
[`docs/research/deepswe-v1.1-routing-evidence.md`](research/deepswe-v1.1-routing-evidence.md).
They are selection guidance, not promises about a particular task.

## Selection rules

1. Choose the lowest routine profile that is credible for the task's required
   quality and complexity.
2. Use `sol/xhigh` only when the routine ladder is insufficient and the extra
   quality justifies the measured time and cost increase.
3. Use `sol/max` only for an explicit highest-quality requirement or after a
   lower route has proved insufficient.
4. Submit model and effort explicitly on a route-managed spawn. A missing field
   is not permission for a hook to guess.
5. Keep role identity independent of compute. The same stable role may be
   spawned at different supported profiles.
6. Keep context selection explicit. `fork_turns="all"` intentionally inherits
   full parent configuration and cannot carry per-spawn role/model/effort
   overrides in Codex 0.144.1. Route-managed spawns therefore use `none` or a
   positive integer string.
7. A protocol adapter derives accepted effort values from the policy seam. It
   must not copy a second effort allowlist.

## Hook responsibilities

- The parent chooses `agent_type`, model, effort, and context based on the task.
- `PreToolUse` validates the explicit spawn against policy and denies invalid
  calls before child creation.
- `PreToolUse` does not silently rewrite a model, effort, role, or fork mode.
- `SessionStart` emits parent routing guidance only for root `startup`. The
  guidance is derived from the executable route and managed-role sources.
- `SubagentStart` injects the stable contract for the resolved role. It does not
  select or validate compute, and it emits no output for unmanaged roles.

## `PreToolUse` validator contract

The public validator accepts an already parsed `PreToolUseInput` and returns a
`PreToolUseDenyOutput` or `None`. It performs no I/O and does not mutate the hook
input.

The validator recognizes the matching-tag `spawn_agent` name and `Agent` alias,
plus the `agentsspawn_agent` and `collaborationspawn_agent` names observed in
installed 0.144.1 probes. Other tool names are ignored without inspecting their
inputs. Supporting another tool name requires new versioned evidence; substring
matching inside the handler is not a fallback.

For a recognized spawn, `tool_input` must be an object containing only:

- required `message`, `task_name`, `agent_type`, `model`,
  `reasoning_effort`, and `fork_turns` strings;
- optional non-empty `service_tier` string.

All required strings must be non-empty. The model/effort pair must equal one of
the profiles returned by the policy seam. `fork_turns` must be exactly `none` or
an ASCII positive integer string. Full-history `all` is denied because routed
spawns provide explicit role and compute.

This stage deliberately validates only that `agent_type` is explicit and
non-empty. It does not own a role allowlist: managed role selection and context
loading belong to the start-context stage, while Codex built-in or separately
installed roles remain valid inputs to the routing validator.

This separation is recorded in
[`ADR-0001`](adr/0001-use-pretooluse-and-subagentstart.md) and
[`ADR-0002`](adr/0002-separate-role-identity-from-compute.md).

## Prohibitions

- Child reasoning effort `ultra` is prohibited.
- Unknown effort values are rejected explicitly.
- `max` is not prohibited; it is a conditional escalation profile.
- No hidden fallback may replace a missing or invalid route.
- No hook may infer complexity from `task_name` and silently change compute.
- No second route table or effort allowlist may be introduced in a protocol
  adapter, handler, role contract, or installer.
- Hook validation must not be represented as a fail-closed security or cost
  boundary; Codex command-hook failures are fail-open in the verified version.
