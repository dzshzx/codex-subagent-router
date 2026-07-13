# Codex 0.144.1 hook evidence

Date verified: 2026-07-13

## Scope

This report records the versioned evidence used to choose the hook protocol and
role-routing seams in this repository. It describes Codex CLI `0.144.1`, tag
[`rust-v0.144.1`](https://github.com/openai/codex/releases/tag/rust-v0.144.1),
commit
[`44918ea`](https://github.com/openai/codex/commit/44918ea10c0f99151c6710411b4322c2f5c96bea).
It is evidence for project decisions, not a runtime dependency.

This file is a versioned historical record, not a package version pin. Future
Codex releases receive separate evidence files after the same schema, lifecycle,
installation, and isolated-session checks; this record and its immutable source
links are not rewritten to follow `latest`.

The current project policy supersedes one historical assumption from the source
research: child effort `max` is supported and child effort `ultra` alone is
prohibited.

## Verified lifecycle

The minimum native hook chain for routed subagents is:

1. `PreToolUse` runs before the `spawn_agent` handler. It can inspect the full
   spawn input and deny the call before a child exists.
2. The native spawn handler resolves the requested role, model, effort, service
   tier, and context fork.
3. `SubagentStart` runs in the child before its first model request. It can add
   developer context selected by the resolved `agent_type`.

`PreToolUse` is the only hook in this chain that can block creation or replace
tool input. `SubagentStart` cannot block or reconfigure the child. Conversely,
`PreToolUse` additional context belongs to the calling thread, while
`SubagentStart` additional context belongs to the child. The events are
complementary rather than interchangeable.

Primary sources:

- [Codex Hooks documentation](https://developers.openai.com/codex/hooks)
- [`PreToolUse` before tool dispatch](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/tools/registry.rs#L493-L565)
- [`SubagentStart` before the child request](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/session/turn.rs#L176-L195)
- [Child-first-request integration test](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/tests/suite/subagent_notifications.rs#L500-L614)

## Protocol facts

The generated schemas use `additionalProperties: false` for all event objects
and nested hook-specific output objects. The project protocol boundary can
therefore reject unknown fields without being stricter than the matching Codex
version.

### `PreToolUse` input

Required fields are:

- `session_id`
- `turn_id`
- `transcript_path`, which is a string or `null`
- `cwd`
- `hook_event_name`, exactly `PreToolUse`
- `model`
- `permission_mode`
- `tool_name`
- `tool_input`, which may be any JSON value
- `tool_use_id`

`agent_id` and `agent_type` are optional and identify the calling subagent when
the hook is running inside one. They do not identify the child being requested.
The requested child fields live inside `tool_input`.

[Official generated input schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json)

### `SubagentStart` input

It has the same required common fields except for tool-specific fields, and it
requires `agent_id` and `agent_type`. Its `model` is the active child model. It
does not expose the spawn `task_name`, message, effort, service tier, or fork
mode.

[Official generated input schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/subagent-start.command.input.schema.json)

### `SessionStart` input

Required fields are `session_id`, nullable `transcript_path`, `cwd`,
`hook_event_name`, `model`, `permission_mode`, and `source`. Unlike turn-scoped
and subagent-start inputs, it has no `turn_id`. The source is exactly one of
`startup`, `resume`, `clear`, or `compact`.

The corresponding hook-specific output uses `hookEventName: "SessionStart"`
and an optional string `additionalContext`.

- [Official generated input schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/session-start.command.input.schema.json)
- [Official generated output schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/session-start.command.output.schema.json)

### Outputs used by this project

A deny-only `PreToolUse` handler returns:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "<non-empty policy reason>"
  }
}
```

A `SubagentStart` role loader returns:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStart",
    "additionalContext": "<role contract>"
  }
}
```

The official wire schema also admits legacy decisions, `allow`, `ask`, input
replacement, and universal output fields. Those capabilities are not needed by
the current project stages and must not appear through hidden fallbacks.

- [Official `PreToolUse` output schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/pre-tool-use.command.output.schema.json)
- [Official `SubagentStart` output schema](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/schema/generated/subagent-start.command.output.schema.json)

## Spawn input facts

MultiAgent V2 accepts required `message` and `task_name`, plus optional
`agent_type`, `model`, `reasoning_effort`, `service_tier`, and `fork_turns`.
It rejects unknown fields. The compatibility field `fork_context` is parsed but
then explicitly rejected by the V2 handler.

`fork_turns="all"` is full-history inheritance and cannot be combined with an
explicit role, model, or effort. `none` and positive integer strings allow
per-spawn compute selection.

[Official V2 spawn argument implementation](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L141-L225)

## Matcher facts

The matching-tag source exposes canonical `spawn_agent` and alias `Agent`.
Isolated probes of the installed `0.144.1` binary observed two flattened
namespaced forms at different points in development: `agentsspawn_agent` and,
in the final executable-handler probe, `collaborationspawn_agent`. A deployment
matcher therefore needs a compatibility shape such as
`^(Agent|.*spawn_agent.*)$`, followed by an exact allowlist check inside the
handler. Every Codex upgrade must repeat this probe.

Multiple matching command hooks run concurrently. If more than one
`PreToolUse` hook returns a replacement input, the last one to complete wins and
replaces the entire object. This is another reason to keep routing validation in
one handler and to avoid independent rewrite hooks.

- [Hook names and aliases](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/tools/hook_names.rs#L40-L56)
- [Matcher implementation](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/src/events/common.rs#L100-L210)
- [`PreToolUse` aggregation](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/src/events/pre_tool_use.rs#L74-L160)

## Role and compute precedence

In Codex 0.144.1, a custom role with a `config_file` reloads the layered child
configuration after per-spawn model and effort have been applied. A
behavior-only role file can therefore erase those per-spawn values. A role
declaration without `config_file` is a no-op at the configuration layer, so the
per-spawn model and effort remain intact.

Isolated probes verified description-only roles combined with per-spawn compute
and `SubagentStart` developer context, including concurrent children with
different roles and compute profiles. This evidence supports separating stable
role identity from per-spawn compute.

- [Role application](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/agent/role.rs#L56-L81)
- [Optional role config file](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/config/src/config_toml.rs#L712-L721)

## Isolated probe record

The following probes ran with the installed Codex CLI `0.144.1` and a temporary,
isolated `CODEX_HOME`. They did not read or modify production Codex
configuration. Hook trust was bypassed only inside the disposable environment so
that the protocol behavior could be observed before designing installation.

### Executable command adapters

The final stage-5 probes ran on 2026-07-13 with:

- installed `codex-cli 0.144.1`;
- a new temporary `CODEX_HOME` containing a copied authentication snapshot,
  fresh `config.toml`, and fresh `hooks.json`;
- an empty temporary working directory;
- `--ephemeral`, `--ignore-rules`, `--skip-git-repo-check`, and
  `--dangerously-bypass-hook-trust`;
- the repository's `python -m codex_subagent_router.commands` adapters as the
  only configured command hooks.

The authentication snapshot was copied without displaying its contents. No
normal user configuration, hook configuration, rules, session history, or
project configuration was copied or modified. The temporary configuration
declared `reviewer` by description only and enabled the native hooks and
multi-agent features. The temporary home and working directory, including the
authentication snapshot, were removed after the evidence below was extracted.

| Probe | Observed result |
|---|---|
| Root `SessionStart(startup)` | The first model response was exactly `Child effort ultra is prohibited.`, a sentence present only in the injected routing guidance. |
| Deny before child creation | A complete `collaborationspawn_agent` call requesting `gpt-5.6-sol / ultra` was blocked with `child reasoning effort 'ultra' is prohibited`; no child-start or wait path followed. |
| Managed `SubagentStart` | A real `reviewer` child returned exactly `You are the reviewer for one bounded, read-only diff axis.`, the first sentence of its injected contract. |
| Unmanaged `SubagentStart` | A real built-in `worker` child returned `UNMANAGED`; the captured start input identified `agent_type: worker`, for which the adapter emits no output. |
| Hook failure visibility | Deliberately routing `SessionStart` into the wrong document adapter produced `hook: SessionStart Failed` in normal Codex CLI output while the root turn continued. The adapter's process test separately locks the specific stderr protocol diagnostic and exit code `1`. |

The first deny attempt exposed a compatibility defect: the validator did not
recognize `collaborationspawn_agent`, so an `ultra` child was initially allowed.
The captured `PreToolUse` input established the canonical installed-binary name;
a failing regression test was added before the allowlist was corrected. The
same probe then blocked the call before child creation. This is why the
installed-binary probe is a release gate rather than documentation-only
research.

Codex encrypts the `message` field before it reaches this `PreToolUse` hook. The
validator deliberately checks only that this required field is a non-empty
string; it does not need or attempt to inspect message contents.

### Generated user installation

The stage-6 release probe used the package console scripts rather than a
handwritten configuration. It ran `codex-subagent-router install` against a new
temporary `CODEX_HOME`, which generated all four description-only role entries,
all three hook groups, absolute launcher commands, ten-second timeouts, and the
private installation receipt. A separate CLI smoke path completed
`install -> status -> rollback` without touching the normal user home.

The exact retained Codex CLI `0.144.1` binary then started two fresh,
non-persisted sessions from empty temporary working directories. As in the
earlier adapter probes, the disposable home received only an authentication
snapshot whose contents were never displayed. Rules were ignored and hook trust
was bypassed only for these vetted temporary runs.

| Installed configuration probe | Observed result |
|---|---|
| Generated `SessionStart` group | Codex recorded `hook: SessionStart Completed`; the root returned `INSTALL_HOOK_OK` only after observing the installed routing-guidance sentinel. |
| Generated role and `SubagentStart` group | After invalid spawn attempts were correctly denied by `PreToolUse`, a valid managed `reviewer` child ran and returned `ROLE_INSTALL_OK` only after observing the installed reviewer contract. |

These probes verify fresh-session discovery through the actual installer output,
including description-only role loading and the installed absolute command
path. They do not grant production hook trust: normal users must still review
the new hooks and open a fresh session after installation.

### Description-only role and child context

The representative role declaration was:

```toml
[agents.declared_reviewer]
description = "Behavior is injected by a SubagentStart hook; compute is selected per spawn."
```

It had no `config_file` and no standalone agent file. A `SubagentStart` matcher
`^declared_reviewer$` emitted a static reviewer contract. The parent submitted:

```text
agent_type=declared_reviewer
model=gpt-5.6-luna
reasoning_effort=medium
fork_turns=none
```

The child rollout recorded all of the following:

- `source.subagent.thread_spawn.agent_role = declared_reviewer`
- `turn_context.model = gpt-5.6-luna`
- `turn_context.effort = medium`
- the static contract as a separate `developer` message in the first request
- the contract sentinel `STATIC_CONTRACT_HOOK_OK` as the child result

This directly checks the combination that source-level unit tests cover only in
separate pieces.

### Concurrent role isolation

Two children were started from one parent turn:

| Role | Requested compute | Observed result |
|---|---|---|
| `declared_reviewer` | `gpt-5.6-luna / low` | reviewer contract only; `STATIC_CONTRACT_HOOK_OK` |
| `declared_researcher` | `gpt-5.6-sol / xhigh` | researcher contract only; `STATIC_RESEARCHER_CONTRACT_OK` |

A second concurrent pair observed `declared_architecture_explorer` at
`gpt-5.6-sol / high` and `declared_interface_designer` at
`gpt-5.6-terra / high`, each with only its matching contract. These results show
that role context and per-spawn compute did not cross between concurrent child
threads.

### Configuration precedence

Three representative spawns isolated the role-layer ordering:

- built-in `default` with a per-spawn compute override retained the requested
  compute;
- a custom behavior role backed by a config file but without model fields
  reverted to the parent `gpt-5.6-sol / max` configuration;
- a custom role config pinned to `gpt-5.6-terra / high` resolved to that pinned
  compute.

The description-only role probe above retained its per-spawn compute. Together,
the observations match the 0.144.1 source order: apply requested compute, then
apply any role configuration layer.

### Spawn matcher discrepancy

With a matcher containing `.*spawn_agent.*`, the hook input reported the
installed tool name `agentsspawn_agent` and exposed the expected `agent_type`,
`model`, `reasoning_effort`, `fork_turns`, and `task_name` fields. Replacing the
matcher with the matching-tag alias-only `^Agent$` did not intercept an explicit
`declared_reviewer + gpt-5.6-sol/max` request; the child was created with that
compute. This is the evidence for the compatibility matcher recommendation, not
an assertion that the official canonical name has changed.

### Creation-time denial

With the broad matcher restored, a prototype deny-only handler allowed a
`gpt-5.6-luna/medium` spawn and denied an out-of-policy
`gpt-5.6-sol/max` spawn before child creation. A later allowlist probe denied
four representative invalid shapes—an unlisted model, missing effort,
full-history context combined with explicit compute, and `sol/ultra`—and no
child rollout was created for any denial.

That probe used an earlier xhigh-cap policy. Its `max` decision is superseded;
the current project permits `sol/max` and prohibits only child `ultra`. The
probe remains evidence for valid deny output and creation-time blocking, while
the current policy document is the authority for which inputs are denied.

## Failure boundary

Command launch failures, timeouts, non-blocking non-zero exits, invalid JSON,
and unsupported output normally record a failed hook run and continue the
original operation. A valid deny response or the documented exit-code-2 block
path can stop a specific tool call, but hook availability itself is fail-open.

Consequently, the deny-only handler is a policy guardrail, not a security or
spending isolation boundary. Managed hook distribution changes trust and
mutability, not this runtime failure behavior.

- [Command runner failure behavior](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/src/engine/command_runner.rs#L54-L132)
- [`PreToolUse` failure branches](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/hooks/src/events/pre_tool_use.rs#L192-L319)

## Evidence limits

- Exact wire claims are anchored to Codex 0.144.1 and must be re-verified on an
  upgrade.
- The installed-version probes demonstrate this environment, not a universal
  product guarantee.
- Normal hook trust approval remains a manual Codex UI decision; automated
  probes used the dangerous bypass only inside disposable homes.
- The configured ten-second timeout and Codex's fail-open timeout behavior are
  covered by generated-document tests and matching-version source evidence, not
  by deliberately stalling the production handler.
- Rollback behavior is verified on real temporary files through both public API
  and console-command tests; it is not a Codex runtime lifecycle event.
