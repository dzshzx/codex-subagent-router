# Codex 0.144.4 installed-binary hook evidence

Date verified: 2026-07-15

Decision update: this record preserves the original stable-path release gate.
After verifying that session selection honors model `multi_agent_version`
metadata before the feature fallback, generated installations changed to the
explicit V2 configuration already exercised by this record's supplemental
loopback arm. `codex debug models --bundled` on the installed 0.144.4 binary
reported V2 for `gpt-5.6-sol` and `gpt-5.6-terra`, and V1 for
`gpt-5.6-luna`. See
[`ADR-0005`](../adr/0005-enable-multiagent-v2-for-gpt-5-6.md). The original
probe observations and their real-backend boundary remain unchanged.

The updated installer was also run against a fresh temporary `CODEX_HOME`.
`codex features list` parsed the generated configuration and reported
`multi_agent_v2` enabled; router `status` reported `installed`, and rollback
removed the temporary configuration. This was a local config-parse/lifecycle
check and made no provider request.

## Status and scope

This record combines the **source contract** of the official
[`rust-v0.144.4` release tag](https://github.com/openai/codex/releases/tag/rust-v0.144.4)
(`8c68d4c87dc54d38861f5114e920c3de2efa5876`) with isolated observations of
the shipped standalone `x86_64-unknown-linux-musl` executable. `codex
--version` reported `codex-cli 0.144.4`.

Every behavioral probe used a new `CODEX_HOME` under `/tmp`, a loopback
Responses provider with `requires_openai_auth = false`, and no copied
credentials. The probe harness did not read or copy production credentials or
configuration; the recoverable production-name remediation noted below was a
separate deployment action, not a probe input. The default feature list
reported `hooks` stable/enabled, `multi_agent` stable/enabled, and
`multi_agent_v2` under-development/disabled, agreeing with the tag declarations
in
[`features/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/features/src/lib.rs#L1035-L1046).

## Release decision: compatible for the Hook-managed stable path

Codex `0.144.4` can be added to the compatibility table with the explicit
surface **Hook-managed stable path**. Every required observation passed for
the supported deployment:

- description-only inline declarations for the four managed roles;
- `SessionStart`, `PreToolUse`, and `SubagentStart` hooks as the sole source
  of routing guidance, policy enforcement, and managed role contracts;
- no active standalone TOML anywhere below a user or project `agents`
  directory declaring a managed name.

The managed names `researcher`, `reviewer`, `architecture_explorer`, and
`interface_designer` are reserved across every active custom-agent layer.
Standalone custom roles and Hook-managed roles are alternative definition
modes; same-name composition is unsupported, not a deployment the release
gate promises to make work.

The standalone-only, same-name, and trusted-project probes below establish
that boundary. A standalone role fixes child compute and receives no
`SubagentStart`; a trusted project standalone can override the user inline
role. The missing event was confirmed with a catch-all matcher, whose capture
count did not increase, ruling out a matcher miss. These observations justify
fail-closed conflict handling rather than disqualifying the supported
Hook-managed path.

## Installed-binary probe record

### Installation lifecycle

The router installer successfully planned and installed into a disposable
home that already contained the loopback provider configuration. `status`
reported `installed` with no details. `rollback` restored the original
provider configuration exactly, removed the generated hooks and receipt, and
left `status` at `not-installed`.

In a separate drift arm, a same-name user standalone role was created after
installation. `status` then reported `modified`. Rollback still succeeded and
preserved the standalone file's bytes and mode exactly; the router neither
adopted nor mutated that file.

For the actual deployment preflight, the four existing same-name custom-agent
files were recoverably renamed to `*.toml.disabled`. The current installer
plan then reported `conflicts = []`, which is the expected clean state for
Hook-managed mode.

### Default stable path

The first Responses request advertised namespace `multi_agent_v1`, function
`spawn_agent`, and the V1 fields `message`, `items`, `fork_context`,
`agent_type`, `model`, `reasoning_effort`, and `service_tier`; it did not
advertise `task_name`. This matches the tag's
[`multi_agents_spec.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L47-L75)
rather than the V2-shaped behavior previously observed from installed
`0.144.3`.

| Probe | Installed `0.144.4` observation |
|---|---|
| Root startup | `SessionStart` received `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `source`, and `transcript_path`; the complete routing guidance was present in the root's first model request. |
| Raw spawn hook | `PreToolUse.tool_name` was `spawn_agent`. Its top-level keys were `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id`, `transcript_path`, and `turn_id`. |
| Deny before child | A `reviewer` request for `gpt-5.6-terra`, `ultra`, and `fork_context = false` was denied, and the mock received no child request. |
| Valid inline role | A `reviewer` request for `gpt-5.6-terra`, `medium`, and `fork_context = false` created a child whose first request used that model/effort and contained the managed reviewer contract. |
| Child start payload | `SubagentStart` received `agent_id`, `agent_type`, `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`, `transcript_path`, and `turn_id` before the child's first request. |
| Full-history fork | `fork_context = true` was denied by router policy. |

The raw keys match the tag-generated schemas cited below, and the deny arm
demonstrates that the router stopped execution before child creation on this
installed executable.

### V2 paths

With only `[features] multi_agent_v2 = true`, inline `[agents.reviewer]`
parsed and startup succeeded. However, the advertised namespace was
`collaboration`, and the spawn schema exposed only `task_name`, `message`, and
`fork_turns`. Because the default `hide_spawn_agent_metadata` behavior hid
`agent_type`, `model`, and `reasoning_effort`, every such call failed the
router's explicit-routing requirement. The denial named
`collaborationspawn_agent`.

Thus inline roles and V2 **coexist syntactically**, but default V2 is **not
routable** under this router's contract.

The disposable loopback V2 arm became routable only with both settings:

```toml
[features.multi_agent_v2]
enabled = true
hide_spawn_agent_metadata = false
tool_namespace = "agents"
```

That configuration advertised `task_name`, `message`, `fork_turns`,
`agent_type`, `model`, `reasoning_effort`, and `service_tier`. Raw
`PreToolUse.tool_name` was `agentsspawn_agent`. A valid reviewer call using
`gpt-5.6-terra`, `medium`, and `fork_turns = "none"` created a child that
preserved the requested compute and received the managed contract before its
first request. `ultra` was denied before child creation, and `fork_turns =
"all"` was denied by router policy.

This corrects an important source-only simplification: V2 route fields are
not unconditionally model-visible. Their visibility depends on
`hide_spawn_agent_metadata`; namespace capability and `tool_namespace`
separately determine the model- and hook-visible tool name.
This was a local mock-provider binary probe, not validation against a real
OpenAI backend, and V2 preview is not part of the default supported release
surface.

### Role discovery and precedence matrix

| Configuration arm | Installed observation | Router result |
|---|---|---|
| User inline only, stable | Requested `gpt-5.6-terra/medium` was preserved; `SubagentStart` injected the managed reviewer contract. | Supported Hook-managed path: pass |
| User inline, default V2 preview | Config parsed, but route metadata was hidden, so every call was denied for missing `agent_type`, `model`, and `reasoning_effort`. | Preview boundary: fail closed; not a stable-path prerequisite |
| User standalone only | The file had a different filename but declared `name = "reviewer"`, `developer_instructions = "STANDALONE_SENTINEL"`, model `gpt-5.6-sol`, and effort `high`. The tool description said its configuration could not be changed. A spawn asking for `gpt-5.6-terra/medium` created a `gpt-5.6-sol/high` child containing the standalone sentinel and no managed reviewer contract. A catch-all start matcher still captured no `SubagentStart`. | Alternative standalone definition mode; outside Hook-managed support |
| Same user layer: inline plus same-name standalone | Codex warned that the standalone definition was a duplicate and ignored it. The child used `gpt-5.6-terra/medium`, contained the managed contract, and did not contain the standalone sentinel. | Unsupported composition; user-home preflight/status must fail closed |
| Trusted project standalone above user inline | `.codex/config.toml` plus `.codex/agents/reviewer.toml` changed the tool description to the project standalone role. The child used its fixed `gpt-5.6-sol/high`, contained the project sentinel, lacked the managed contract, and emitted no `SubagentStart`. | Explicitly unsupported configuration; managed names are reserved in project layers too |

The project role took effect only when the project configuration layer existed
and was trusted. Without an established/trusted project layer, the project
agent did not participate in discovery. This agrees with the current official
[hooks trust model](https://developers.openai.com/codex/hooks), but the
standalone-child omission is an installed-binary observation not promised by
that documentation.

The support rule is therefore name-based across all active layers, not just
the user home: no user or project standalone file may declare one of the four
managed names. The installer can detect and report user-home collisions via
preflight/status. Project-layer collisions remain an operator/project
configuration responsibility and are explicitly unsupported.

### Trust and hook failure

In a fresh untrusted home without the bypass flag, the capture hook ran zero
times, the root request contained no routing guidance, and the turn continued.
Adding `--dangerously-bypass-hook-trust` activated the reviewed disposable
hooks.

For the failure arm, `SessionStart` was deliberately routed to the
`subagent-start` adapter. The wrapper recorded return code `1` and stderr
`expected SubagentStart input, got SessionStartInput`; the installed turn
still returned `FAIL_OPEN_DONE`. This directly verifies fail-open behavior
for an ordinary hook failure on the shipped executable.

## Hook wire contract in the release tag

The tag ships generated JSON Schemas for all three events used by the router:

- [`PreToolUse` input](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json)
  requires `cwd`, `hook_event_name`, `model`, `permission_mode`, `session_id`,
  `tool_input`, `tool_name`, `tool_use_id`, `transcript_path`, and `turn_id`;
  `agent_id` and `agent_type` are optional. Unknown top-level fields are
  rejected by this exact tag-generated schema.
- [`SessionStart` input](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/session-start.command.input.schema.json)
  requires the session metadata plus a source from `startup`, `resume`,
  `clear`, or `compact`.
- [`SubagentStart` input](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/subagent-start.command.input.schema.json)
  requires `agent_id`, `agent_type`, `cwd`, event name, model, permission
  mode, session id, transcript path, and turn id.

The corresponding
[`PreToolUse`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/pre-tool-use.command.output.schema.json),
[`SessionStart`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/session-start.command.output.schema.json),
and
[`SubagentStart`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/schema/generated/subagent-start.command.output.schema.json)
output schemas share `continue`, `stopReason`, `suppressOutput`, and
`systemMessage`. Event-specific output can add `additionalContext`;
`PreToolUse` can additionally return `permissionDecision` (`allow`, `deny`,
or `ask`), a reason, and an updated input, while retaining the legacy
approve/block decision form.

The current official [Codex Hooks documentation](https://developers.openai.com/codex/hooks)
warns that its linked main schemas can contain fields added after a release.
Consequently, the generated files above are the exact source schemas for
`0.144.4`; the live documentation is used only for the current behavioral
contract.

## Hook lifecycle, blocking, and failure semantics

The following are verified source facts for `rust-v0.144.4`:

1. `PreToolUse` runs before the registered tool handler, and a block returns
   before the handler is invoked. See
   [`core/src/tools/registry.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/registry.rs#L493-L535).
2. All matching command handlers run concurrently and are reordered only for
   deterministic reporting. `PreToolUse` is turn-scoped; `SessionStart` and
   `SubagentStart` are thread-scoped. See
   [`hooks/src/engine/dispatcher.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/engine/dispatcher.rs#L89-L153).
3. `SubagentStart` is selected for a thread-spawn startup and its pending start
   hooks run before the child's first sampling loop. See
   [`core/src/hook_runtime.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/hook_runtime.rs#L103-L145)
   and
   [`core/src/session/turn.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/turn.rs#L167-L190).
4. An explicit deny, or command exit status `2` with stderr, blocks a
   `PreToolUse` call. Spawn/timeout/write errors, non-blocking nonzero exits,
   and invalid output are recorded as failed hooks but do not themselves
   block the tool. See
   [`hooks/src/events/pre_tool_use.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/events/pre_tool_use.rs#L54-L141)
   and its
   [command-result handling](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/events/pre_tool_use.rs#L188-L285).
5. Only `SessionStart` honors `continue = false`; `SubagentStart` contributes
   context but does not stop the child through that field. Ordinary start-hook
   errors are reported as failures. See
   [`hooks/src/events/session_start.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/events/session_start.rs#L211-L310).

The current official hooks documentation independently describes matching
command hooks as concurrent, `PreToolUse` deny as blocking, and ordinary hook
failure as fail-open. It also states that project hook configuration is used
only after the project `.codex` layer is trusted.

Non-managed command hooks are trusted by an exact normalized definition hash.
Managed hooks are trusted by policy; a changed user/project definition is
classified as modified and is not activated. The dispatcher includes a hook
only when it is enabled and either trust is bypassed or its trust status is
managed/trusted. See
[`hooks/src/engine/discovery.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/engine/discovery.rs#L480-L620).
The installed CLI exposes `--dangerously-bypass-hook-trust`; it must be used,
if at all, only with reviewed hook files in an isolated probe home.

The installed stable-inline probes confirmed those ordering, payload, deny,
and fail-open behaviors. They also exposed an important boundary not apparent
from the generic lifecycle: children resolved from standalone roles emitted
no `SubagentStart` at all.

## Stable and V2 spawn contracts

The tag has two distinct advertised schemas:

| Source path | Advertised form | Arguments |
|---|---|---|
| Stable V1 | Namespace `multi_agent_v1`, function `spawn_agent` | `message` or `items`, `agent_type`, boolean `fork_context`, `model`, `reasoning_effort`, `service_tier`; no `task_name` |
| V2 | Function `spawn_agent` | required `task_name` and `message`; `fork_turns`; plus optional `agent_type`, `model`, `reasoning_effort`, and `service_tier` only when spawn metadata is not hidden; no V1 `items` |

The schemas and required-field lists are defined in
[`multi_agents_spec.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L47-L113),
with their complete property sets in the same file's
[`spawn` definitions](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L552-L635).
When `hide_spawn_agent_metadata` is active, the builder removes
`agent_type`, `model`, `reasoning_effort`, and `service_tier`; see
[`hide_spawn_agent_metadata_options`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L637-L642).
The V2 runtime parser requires `task_name` and `message`, rejects
`fork_context`, and accepts `fork_turns` as `none`, `all`, or a positive
integer string, defaulting to `all`; see
[`multi_agents_v2/spawn.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L178-L215).

### Hook-visible tool names

The canonical hook name for spawning is `spawn_agent`, with matcher alias
`Agent`, in
[`hook_names.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/hook_names.rs#L41-L50).
However, hook-name normalization special-cases only an absent namespace and
the V1 namespace `multi_agent_v1`; other namespaces are flattened into the
reported name. See
[`registry.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/registry.rs#L713-L724).

For V2, providers that support namespace tools receive a configured namespace.
The tag's default V2 namespace is `collaboration`, while the default provider
capability enables namespace tools. See
[`core/src/config/mod.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/mod.rs#L241-L253),
[`model-provider/src/provider.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/model-provider/src/provider.rs#L28-L47),
and the
[`spec_plan` wrapper](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/spec_plan.rs#L760-L815).

Therefore the tag source implies this hook-name matrix:

- stable V1: `spawn_agent`;
- V2 without namespace-tool support: `spawn_agent`;
- V2 with the default namespace: `collaborationspawn_agent`;
- V2 configured with namespace `agents`: `agentsspawn_agent`.

This is a source inference across the cited registration, capability, and
normalization code. The raw installed payloads confirmed `spawn_agent` for
stable V1, `collaborationspawn_agent` for default V2, and
`agentsspawn_agent` for V2 with namespace `agents`.

## Inline roles and standalone agent files

The current official [Codex Subagents documentation](https://developers.openai.com/codex/subagents)
leads with standalone files in personal `~/.codex/agents/` and project
`.codex/agents/` directories. Each file must define `name`, `description`, and
`developer_instructions`; optional fields include nickname candidates, model,
reasoning effort, sandbox mode, MCP servers, and skill configuration. The
declared `name`, not the filename, is the role identity. A custom definition
with a built-in name takes precedence over the built-in role.

The tag source also continues to parse legacy/inline `[agents.<role>]`
declarations. The config type shows inline role entries flattened below
`[agents]` in
[`config_toml.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/config/src/config_toml.rs#L681-L721).
There is no primary-source basis here to call that surface removed or
deprecated.

Discovery and precedence are explicit in
[`core/src/config/agent_roles.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L19-L115):

- configuration layers are visited from lowest to highest precedence;
- within one layer, inline declarations are loaded first, then that layer's
  `agents/` directory is scanned recursively;
- a same-name standalone file in that same layer is skipped as a duplicate,
  so the inline declaration wins the collision;
- a higher-precedence layer replaces the lower role after inheriting fields
  that it omitted.

Standalone files require a nonempty `name` and `developer_instructions` when
loaded without an inline declaration hint; file metadata is separated from
the remaining agent config in
[`agent_roles.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L220-L315).
Recursive discoveries are sorted, and the first sorted file wins a duplicate
standalone name, with a warning, in
[`agent_roles.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L474-L554).

This demonstrates why same-name coexistence is outside the product contract.
An installer-created inline managed role shadows a same-name standalone file
in the same user layer, while a higher-precedence project standalone can
override the user role. Standalone-resolved children also use fixed compute
and omit `SubagentStart`/managed context. The product therefore reserves the
four managed names in every active custom-agent layer and fails closed on the
user-home conflicts it can preflight.

The V2 feature conflict check rejects `agents.max_threads` when V2 is enabled,
but does not reject inline role declarations merely because V2 is enabled;
see
[`core/src/config/mod.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/mod.rs#L1410-L1428).
The installed config probes confirmed that inline declarations start under
V2. Default V2 remains unusable for this router because metadata hiding
removes required route fields, not because inline syntax is rejected.

## Local Responses API probe without production authentication

The upstream tests provide a first-party pattern for driving Codex through a
local mock Responses endpoint. Their minimal custom-provider configuration
sets a model, selects a provider, and gives that provider a `/v1` base URL,
`wire_api = "responses"`, zero request/stream retries, and WebSockets disabled:
[`app-server/tests/common/config.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/app-server/tests/common/config.rs#L6-L80).

Provider fields are defined in
[`model-provider-info/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/model-provider-info/src/lib.rs#L86-L141).
`requires_openai_auth` and `supports_websockets` default to false. With no
`env_key`, the provider does not require an API key, as shown by
[`api_key`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/model-provider-info/src/lib.rs#L280-L299).
This is the safe mechanism for probing the installed binary without copying
or displaying production auth material.

The upstream mock accepts `POST .../responses` in
[`core/tests/common/responses.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L1005-L1010)
and returns HTTP 200 with `Content-Type: text/event-stream`. Each event is
serialized as `event: <type>`, then `data: <JSON>`, then a blank line; see
the [SSE serializer](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L627-L640)
and [HTTP response builder](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L973-L977).

A minimal function-call turn is:

1. `response.created`;
2. `response.output_item.done` whose item has `type = "function_call"`, a
   `call_id`, optional `namespace`, function `name`, and JSON-string
   `arguments`;
3. `response.completed` with usage.

The exact constructors are
[`response.created` and `response.completed`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L648-L666)
and
[`function_call`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L844-L872).
The upstream two-response function-call sequence is at
[`responses.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/common/responses.rs#L1466-L1488),
and a complete parent-spawn, child-answer, parent-follow-up sequence is at
[`subagent_notifications.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/tests/suite/subagent_notifications.rs#L375-L447).

The probe mock inspected the tool specification in each first request and
answered with the namespace and argument schema actually advertised there.
That captured stable V1, default V2, and explicitly configured V2 without
assuming tag/binary equivalence.

## Safe disposable-home skeleton

The following preparation never consults the normal Codex home and does not
copy credentials:

```bash
umask 077
probe_root=$(mktemp -d "${TMPDIR:-/tmp}/codex-01444.XXXXXX")
trap 'rm -rf -- "$probe_root"' EXIT
export CODEX_HOME="$probe_root/home"
mkdir -p "$CODEX_HOME" "$probe_root/work"

codex --version
codex features list
```

After starting a reviewed local mock server on `127.0.0.1:$port`, write this
configuration only under the disposable `$CODEX_HOME`:

```toml
model = "gpt-5.6-terra"
model_provider = "probe"
approval_policy = "never"
sandbox_mode = "read-only"

[model_providers.probe]
name = "Local 0.144.4 probe"
base_url = "http://127.0.0.1:PORT/v1"
wire_api = "responses"
request_max_retries = 0
stream_max_retries = 0
supports_websockets = false
requires_openai_auth = false
```

The repository installer itself also accepts an explicit home, so the managed
configuration lifecycle can remain isolated:

```bash
hook_exe=$(realpath .venv/bin/codex-subagent-router-hook)
uv run codex-subagent-router plan \
  --codex-home "$CODEX_HOME" --hook-executable "$hook_exe"
uv run codex-subagent-router install \
  --codex-home "$CODEX_HOME" --hook-executable "$hook_exe"
uv run codex-subagent-router status --codex-home "$CODEX_HOME"

codex exec --ephemeral --ignore-rules --skip-git-repo-check \
  --dangerously-bypass-hook-trust --json -C "$probe_root/work" \
  'PARENT_PROBE_SENTINEL'

uv run codex-subagent-router rollback --codex-home "$CODEX_HOME"
```

Use the trust-bypass flag only for the positive lifecycle arm after reviewing
the generated files. A separate negative-control home must omit it and verify
that an untrusted non-managed hook is skipped. Every arm should use a newly
created home; do not point `CODEX_HOME`, `--codex-home`, or the mock server at
production state.

For the default-metadata V2 arm, append the following to the disposable config
and do not set `agents.max_threads`, because the tag explicitly rejects that
combination:

```toml
[features]
multi_agent_v2 = true
```

The loopback V2 preview arm instead uses the `[features.multi_agent_v2]` table
shown earlier. The completed role matrix used independent homes for inline only,
standalone only, same-name inline plus standalone, default V2 inline, and a
higher-layer trusted project standalone definition. Each mock recorded the
advertised tool schema and subsequent parent/child request bodies.

## Release-gate assessment for the supported surface

The installed executable supplied all required artifacts for the Hook-managed
stable path. The negative custom-agent arms define the excluded boundary:

| Probe | Outcome |
|---|---|
| Default feature/config startup | Pass: stable Hook-managed configuration started with the expected default feature state. |
| Advertised stable spawn schema | Pass: V1 namespace and argument shape were captured from the first Responses request. |
| Raw stable start/tool payloads | Pass: exact `SessionStart`, `PreToolUse`, and `SubagentStart` keys and `spawn_agent` name were captured. |
| Deny before child creation | Pass: `ultra` produced no child request. |
| Root start context | Pass: complete routing guidance preceded the first root request. |
| Managed inline child context | Pass: `SubagentStart` and the contract preceded the child's first request. |
| Valid routing and fork policy | Pass: valid stable inline routing preserved requested compute; full-history fork was denied. |
| Failure and trust | Pass: ordinary failure was fail-open; fresh untrusted hooks were skipped; reviewed bypassed hooks ran. |
| Installation lifecycle | Pass, including standalone drift reporting and non-owning rollback preservation. |
| V2 preview | Supplemental only: default metadata hiding failed closed; the explicitly configured loopback path passed. No real OpenAI backend claim is made. |
| Standalone role behavior | Boundary evidence: alternative definition mode, not supported in combination with managed names. |
| Cross-layer precedence | Boundary evidence: trusted project standalone declarations of managed names are explicitly unsupported. |

## Evidence boundary

Verified here: exact tag schemas and source behavior; installed stable/V2
schemas and raw hook names; deny timing; start-context ordering; trust and
fail-open behavior; role discovery/precedence; standalone fixed-compute and
missing-`SubagentStart` behavior; and the installer lifecycle in isolated
homes.

Within the stated boundary, `0.144.4` is verified for the Hook-managed stable
path and may be listed in the README with that surface named explicitly. This
record does not claim support for same-name standalone composition, project
standalone overrides of managed names, V2 preview by default, or a real
OpenAI-backend V2 path.
