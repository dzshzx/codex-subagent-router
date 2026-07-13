# Codex 0.144.3 installed-binary hook evidence

Date verified: 2026-07-13

## Scope

This record verifies Codex CLI `0.144.3` as installed (standalone
`x86_64-unknown-linux-musl` release; `codex --version` reports
`codex-cli 0.144.3`) against this repository at package version `0.1.2`,
including the V1/V2 spawn-shape capability seam, the guarded installation
transaction, and the installer-generated configuration path. It is evidence
for the compatibility table, not a runtime version pin.

Source-level facts for the matching tag are recorded separately in
[`codex-0.144.3-multiagent-spawn-contract.md`](codex-0.144.3-multiagent-spawn-contract.md).
This file records what the shipped binary actually did.

## Key finding: the released binary drifts from the `rust-v0.144.3` tag

The tag source describes a stable V1 `spawn_agent` under namespace
`multi_agent_v1` (optional `message`/`items`, boolean `fork_context`, no
`task_name`) and a hook-name normalization that reports the canonical
`spawn_agent` for both generations.

The installed `0.144.3` binary did not match either claim:

- The `PreToolUse` payload `tool_name` was `collaborationspawn_agent`, the
  same flattened name observed on installed `0.144.1`.
- With default features (`codex features list`: `multi_agent` stable `true`,
  `multi_agent_v2` under development `false`), the default spawn handler
  enforced the V2-shaped contract: a V1-shaped call failed inside Codex with
  `failed to parse function arguments: missing field 'task_name'`, and the
  natural model-issued call used `task_name` and `fork_turns`.

Reading the release tag alone is therefore not release evidence; the
installed-binary probe remains the release gate. The validator's exact
allowlist (`spawn_agent`, `Agent`, `agentsspawn_agent`,
`collaborationspawn_agent`) plus the shape-based V1/V2 seam covers both the
shipped binary and the tag-source contract: a V1-shaped call that policy
allows is still rejected by the binary's own parser without creating a child,
so the fail direction is safe in both worlds.

## Probe environment

The methodology matches the 0.144.1 record: a new temporary `CODEX_HOME` per
home, an authentication snapshot copied without displaying its contents and
deleted afterwards, empty temporary working directories, and
`--ephemeral --ignore-rules --skip-git-repo-check
--dangerously-bypass-hook-trust` for fresh non-persisted sessions. Trust was
bypassed only inside the disposable homes. The managed configuration was
generated exclusively by this package's console scripts
(`codex-subagent-router install`) with the repository virtual environment's
absolute launcher path; no production Codex configuration was read or
modified.

## Probe record

| Probe | Observed result |
|---|---|
| Installer plan → install → status | `install` created `config.toml`, `hooks.json`, and the private receipt in the temporary home; `status` reported `installed` with no details. |
| Root `SessionStart(startup)` | `hook: SessionStart Completed`; the model observed the injected guidance sentinel and replied `SESSIONSTART_OK`. |
| Deny before child creation | A V1-shaped spawn requesting `gpt-5.6-sol / ultra` was blocked with `Tool call blocked by PreToolUse hook: child reasoning effort 'ultra' is prohibited. Tool: collaborationspawn_agent`; the event stream contained no subagent-start activity. |
| Raw `PreToolUse` payload capture | In a separate home with a stdin-teeing hook, the payload reported `tool_name: collaborationspawn_agent`; the natural model-issued call shape was `{task_name, message, fork_turns="none"}`; top-level payload keys matched the published `PreToolUse` schema. |
| V1-shaped valid call on the shipped binary | Allowed by this router's V1 contract, then rejected by the binary's own argument parser (`missing field 'task_name'`); no child was created. |
| Managed role + routed spawn | A spawn with `task_name`, `agent_type=reviewer`, `gpt-5.6-terra / medium`, `fork_turns="none"` ran; the child returned exactly `You are the reviewer for one bounded, read-only diff axis.`, the first sentence of the injected contract. |
| Full-history fork denial | `fork_turns="all"` with explicit routing was denied with `fork_turns must be 'none' or a positive integer string`. |
| Hook failure fail-open | Routing `SessionStart` into the `subagent-start` adapter produced `hook: SessionStart Failed` while the root turn continued and answered normally. |
| Rollback | `rollback` removed the created `config.toml`, `hooks.json`, and receipt; `status` reported `not-installed`. |

## Model behavior without guidance

In the capture home, which had no `SessionStart` guidance hook, the natural
model-issued spawn omitted `model`, `reasoning_effort`, and `agent_type`.
Under the installed configuration such a call is denied with an explicit
missing-fields reason, and the root guidance instructs explicit routing; the
two mechanisms together are what make parents route children explicitly.

## Environmental noise

One probe session hung for several minutes before producing any hook event
and was killed and re-run successfully; a separate run logged a transient
`failed to refresh available models: timeout waiting for child process to
exit` error without affecting the session result. Both match this machine's
known intermittent proxy behavior and do not bear on the contract
conclusions.

## Evidence limits

- These probes demonstrate the installed environment on one POSIX machine,
  not a universal product guarantee.
- The `--enable multi_agent_v2` registration path of this binary was not
  probed; the shape seam does not depend on it, and the allowlist already
  covers both the observed and the tag-source tool names.
- Hook trust approval remains a manual Codex decision; the dangerous bypass
  was used only inside disposable homes.
- Codex command-hook failures remain fail-open; the router is a policy
  guardrail, not a security or spending boundary.
