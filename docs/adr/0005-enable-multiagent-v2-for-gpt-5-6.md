# ADR-0005: Enable MultiAgent V2 for GPT-5.6 routing

- Status: Accepted
- Date: 2026-07-15
- Update 2026-07-16: the real-backend gap noted below is closed for the
  pinned binary by
  [`codex-0.144.4-v2-real-backend-evidence.md`](../research/codex-0.144.4-v2-real-backend-evidence.md);
  the user-owned V2 table is also the Tier A entry path defined by
  [ADR-0006](0006-layer-advisory-guidance-over-optional-enforcement.md).

## Context

This router is built around `gpt-5.6-sol` and `gpt-5.6-terra`. Codex 0.144.4
does not select the multi-agent generation from the feature default alone. The
session first uses the selected model's `multi_agent_version` metadata and only
falls back to the feature flag when the model has no preference; see the pinned
[`session/mod.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/mod.rs#L3109-L3123).

The bundled 0.144.4 model catalog reports V2 for `gpt-5.6-sol` and
`gpt-5.6-terra`, and V1 for `gpt-5.6-luna`. Therefore treating the stable V1
feature default as the effective default for this project's GPT-5.6 routes is
incorrect.

The router requires every spawn to expose `agent_type`, `model`, and
`reasoning_effort`. Codex V2 hides those fields by default, and its default
namespace is not the stable hook-visible seam used by this project. The
0.144.4 loopback probe routed V2 only after making metadata visible and using
the `agents` namespace.

## Decision

The user installer enables V2 explicitly and installs this exact configuration:

```toml
[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

The installer owns this table when it is absent. If the exact required values
already exist, it preserves the user-owned table and only installs missing
managed identities. A partial table, a conflicting required value, or a
non-table path fails closed. Because Codex 0.144.4 rejects `agents.max_threads`
with V2, that combination also fails during planning. Status requires the same
V2 compatibility. If user-owned values later change, status reports `modified`,
while rollback preserves those values and removes only the intact router-owned
configuration. The V2 table itself is removed only when the installer added it.

V2 is the deployment priority. The validator retains its V1 input-shape support
as a compatibility seam for verified older behavior and upstream drift; V1 is
not the generated installation default.

## Consequences

- Generated installations match the model-selected generation used by the
  project's Sol/Terra route table.
- Explicit metadata remains available to `PreToolUse`, so deny-only model,
  effort, role, and fork validation continues to work.
- The `agents` namespace keeps the spawn tool on the hook matcher capability
  seam already accepted by the validator.
- Existing compatible V2 configuration remains user-owned and survives
  rollback byte for byte.
- Deployments still require Hook trust, a fresh session, and a compatibility
  probe when Codex changes its model catalog, schema, or tool naming.
- The pinned 0.144.4 V2 evidence uses a loopback provider; enabling V2 does not
  turn that observation into a cross-version or arbitrary-provider guarantee.

## Rejected alternatives

- Leaving V2 disabled assumes the feature fallback wins over model metadata,
  which is not how the pinned session selection works.
- Letting V2 hide routing metadata prevents the validator from observing the
  explicit route it must check.
- Keeping the default collaboration namespace reintroduces the namespace and
  hook-name ambiguity already exposed by the 0.144.4 probes.
- Removing V1 parsing would discard a cheap compatibility seam without making
  the V2 path safer.
