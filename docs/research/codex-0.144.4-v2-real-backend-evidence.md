# Codex 0.144.4 V2 real-backend routing evidence

Date verified: 2026-07-16

## Status and scope

This record closes the real-backend evidence gap left open by
[ADR-0005](../adr/0005-enable-multiagent-v2-for-gpt-5-6.md) and the
[installed-binary hook evidence](codex-0.144.4-hook-evidence.md), whose V2
positive arm used only a loopback provider. It documents one controlled
`codex exec` run of installed `codex-cli 0.144.4` against the **real OpenAI
backend** with ChatGPT OAuth authentication.

Claim boundary: one binary, one account, one date, two runs. This is not a
cross-version, cross-account, or contractual compatibility guarantee. Hooks
were intentionally **not** installed, so the probe isolates backend
acceptance of the explicit-metadata V2 spawn path from router behavior.

## Method

- Isolated `CODEX_HOME` under a session temp directory; the production
  `~/.codex` was never read or written by the probe run. The production
  `auth.json` was copied into the isolated home; its `last_refresh` was
  compared afterwards and was unchanged (no token rotation occurred).
- Isolated `config.toml`, exactly the installer-generated V2 shape plus one
  description-only inline role:

  ```toml
  model = "gpt-5.6-terra"
  approval_policy = "never"
  sandbox_mode = "read-only"

  [features.multi_agent_v2]
  enabled = true
  hide_spawn_agent_metadata = false
  tool_namespace = "agents"

  [agents.reviewer]
  description = "Read-only reviewer for bounded checks. Spawn with explicit model and reasoning_effort."
  ```

- Prompt: instructed the root to call `spawn_agent` exactly once with
  `task_name`, `agent_type = "reviewer"`, `model = "gpt-5.6-sol"`,
  `reasoning_effort = "low"`, `fork_turns = "none"`, and a sentinel message,
  then report the child reply verbatim. Root model `gpt-5.6-terra` and child
  model `gpt-5.6-sol` were deliberately different so inheritance could not be
  mistaken for routing.
- Evidence sources: `codex exec --json` event stream and the rollout files
  written under the isolated home's `sessions/` tree.

## Observations

### Run 1: CLI-side task name validation

With `task_name = "probe-child"`, the spawn failed before any child was
created: `codex_core::tools::router` logged `agent_name must use only
lowercase letters, digits, and underscores`, and the root reported the
failure. The turn itself completed against the real backend, which means the
extended V2 tool schema (with visible `agent_type`, `model`,
`reasoning_effort` under namespace `agents`) had already been accepted in the
request that produced the spawn call.

Consequence for this project: V2 `task_name` values must match
`[a-z0-9_]+`. Routing guidance and any task-packet template should state
this; hyphens are rejected by the installed CLI.

### Run 2: explicit routing honored end to end

With `task_name = "probe_child"`, the full path succeeded:

| Evidence | Observation |
|---|---|
| Root `turn_context` | `model = "gpt-5.6-terra"` |
| Spawn `function_call` in root rollout | `{"task_name":"probe_child","agent_type":"reviewer","model":"gpt-5.6-sol","reasoning_effort":"low","fork_turns":"none",...}` |
| Child `turn_context` | `model = "gpt-5.6-sol"`, `effort = "low"` |
| Child reply | `CHILD_SENTINEL_OK zebra`, reported verbatim by the root |
| Event stream | `collab_tool_call` `wait` completed; turn completed normally |

The requested child compute was applied exactly; the child did not inherit
the root model.

### Fork isolation and token shape

The child rollout contained only three developer messages and one user
message (the task packet) before its answer — no root conversation history,
confirming `fork_turns = "none"` against the real backend.

Token usage for the successful run:

| Thread | Input | Cached input | Output |
|---|---|---|---|
| Root turn (spawn + wait + report) | 53,701 | 41,216 | 107 |
| Child (sentinel task) | 18,264 | 0 | 11 |

The ~18k child input with an empty fork is the fixed per-child overhead
(system prompt, tool schemas, developer context) on this configuration; it is
the floor cost of one V2 child, useful as a baseline for routing economics.

### Storage detail relevant to offline analysis

In the rollout file, the spawn `message` argument is stored encrypted
(opaque token), while `task_name`, `agent_type`, `model`, and
`reasoning_effort` are stored in plaintext. An offline usage analyzer can
therefore recover route distributions from rollouts without access to
inter-agent message content.

## Implications

- The deployment configuration chosen by ADR-0005 is now backed by a
  real-backend observation on the pinned binary: the backend accepted the
  namespaced, metadata-visible V2 schema, and explicit per-spawn compute was
  honored on the child.
- The evidence boundary in ADR-0005 and the hook-evidence record can be
  narrowed accordingly for 0.144.4 as of this date; wording that no
  real-backend claim exists is superseded by this record for exactly this
  binary, configuration, and date.
- New constraint for guidance/validation surfaces: `task_name` must match
  `[a-z0-9_]+` on this binary.
