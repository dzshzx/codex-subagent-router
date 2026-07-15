# Codex CLI multi-agent `spawn_agent` 契约调研（tag `rust-v0.144.3`）

> 数据源：`openai/codex` 仓库 `rust-v0.144.3` tag 的原始源码，经 `gh api ... -H "Accept: application/vnd.github.raw"` 抓取。
> 所有行号均指向该 tag 下对应文件的原始内容。字段名 / 代码标识符保持英文原文。

## 0. 最关键结论（给 validator 的一句话）

在 `rust-v0.144.3` 中，**V1 与 V2 的 `spawn_agent` 在 PreToolUse hook payload 里的 `tool_name` 字段都等于字面量 `"spawn_agent"`**（并携带 `matcher_aliases = ["Agent"]`）。0.144.1 探针观察到的 `collaborationspawn_agent` 已不再出现——0.144.3 新增了针对 `spawn_agent` 的 hook 名称专用映射，把它归一化成规范名 `spawn_agent`。因此 validator 只能凭 `tool_input` 的形状（是否有 `task_name`、用 `fork_turns` 还是 `fork_context`）区分 V1/V2，不能凭 `tool_name` 区分。

---

## 1. 稳定 V1 `spawn_agent` 输入 schema

### 1.1 实际反序列化结构体（真正的解析契约）

`codex-rs/core/src/tools/handlers/multi_agents/spawn.rs`，L231-241：

```rust
#[derive(Debug, Deserialize)]
struct SpawnAgentArgs {
    message: Option<String>,
    items: Option<Vec<UserInput>>,
    agent_type: Option<String>,
    model: Option<String>,
    reasoning_effort: Option<ReasoningEffort>,
    service_tier: Option<String>,
    #[serde(default)]
    fork_context: bool,
}
```

| 字段 | JSON 类型 | 必填/可选 | 默认值 | 备注 |
|---|---|---|---|---|
| `message` | string | 可选 | 无 | 与 `items` 二选一（运行期校验） |
| `items` | array（`UserInput` 元素） | 可选 | 无 | 与 `message` 二选一 |
| `agent_type` | string | 可选 | 缺省用 role `"default"` | = role 名 |
| `model` | string | 可选 | 继承父 model | 需在可用 model 列表内 |
| `reasoning_effort` | string | 可选 | 继承父 effort | 见 §5 |
| `service_tier` | string | 可选 | 继承父 tier | 需被 model 支持 |
| `fork_context` | boolean | 可选 | `false`（`#[serde(default)]`） | true 表示全量 fork 父历史 |

注意：V1 结构体**没有** `#[serde(deny_unknown_fields)]`——多余字段被静默忽略（与 V2 相反）。

`message`/`items` 的互斥与非空由 `parse_collab_input` 在运行期强制（`codex-rs/core/src/tools/handlers/multi_agents_common.rs` L121-152）：两者都给 → 报错 `Provide either message or items, but not both`；都不给 → `Provide one of: message or items`；空 message → `Empty message can't be sent to an agent`；空 items → `Items can't be empty`。

### 1.2 对模型广告的 JSON schema（tool spec）

`codex-rs/core/src/tools/handlers/multi_agents_spec.rs`：
- `create_spawn_agent_tool_v1`（L47-76）把工具包成 `ToolSpec::Namespace(ResponsesApiNamespace { name: "multi_agent_v1", ... })`，内含一个 `Function { name: "spawn_agent" }`。
- `parameters: JsonSchema::object(properties, /*required*/ None, Some(false.into()))`（L72）——**广告 schema 的 required 为空**，`additionalProperties: false`。
- 属性来自 `spawn_agent_common_properties_v1`（L552-593）：`message`、`items`、`agent_type`、`fork_context`（boolean）、`model`、`reasoning_effort`、`service_tier`。

---

## 2. V2 `spawn_agent` 输入 schema

### 2.1 实际反序列化结构体

`codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs`，L178-189：

```rust
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SpawnAgentArgs {
    message: String,
    task_name: String,
    agent_type: Option<String>,
    model: Option<String>,
    reasoning_effort: Option<ReasoningEffort>,
    service_tier: Option<String>,
    fork_turns: Option<String>,
    fork_context: Option<bool>,
}
```

| 字段 | JSON 类型 | 必填/可选 | 默认值 | 备注 |
|---|---|---|---|---|
| `message` | string | **必填** | 无 | 非 Option，缺失即解析失败 |
| `task_name` | string | **必填** | 无 | 新 agent 的 task 名，小写字母/数字/下划线 |
| `agent_type` | string | 可选 | role `"default"` | 同 V1 |
| `model` | string | 可选 | 继承父 model | |
| `reasoning_effort` | string | 可选 | 继承父 effort | |
| `service_tier` | string | 可选 | 继承父 tier | |
| `fork_turns` | string | 可选 | 缺省/空 → `"all"` | 见下 |
| `fork_context` | boolean | 可选 | 无 | **出现即报错**（V2 不支持，见下） |

- 关键差异确认：`task_name` = **必填 `String`**（不是 Option）；`fork_turns` = **可选 `String`**（不是 bool/int）。
- V2 结构体带 `#[serde(deny_unknown_fields)]`（L179）——多余字段直接解析失败。

### 2.2 `fork_turns` / `fork_context` 语义（`fork_mode`，L192-226）

```rust
if self.fork_context.is_some() {
    return Err(... "fork_context is not supported in MultiAgentV2; use fork_turns instead" ...);
}
let fork_turns = self.fork_turns.as_deref().map(str::trim)
    .filter(|s| !s.is_empty()).unwrap_or("all");
if fork_turns.eq_ignore_ascii_case("none") { return Ok(None); }          // 不 fork
if fork_turns.eq_ignore_ascii_case("all")  { return Ok(Some(FullHistory)); }
let n = fork_turns.parse::<usize>().map_err(|_| ... )?;                  // 其他 → 整数
if n == 0 { return Err(... "fork_turns must be `none`, `all`, or a positive integer string" ...); }
Ok(Some(LastNTurns(n)))
```

- 只要出现 `fork_context`（不论 true/false）→ 报错 `fork_context is not supported in MultiAgentV2; use fork_turns instead`。
- `fork_turns` 缺省或空串 → `"all"` → `FullHistory`（默认把父全量历史 fork 进去）。
- `"none"` → 不 fork；`"all"` → 全量；正整数字符串（如 `"3"`）→ 最近 N 轮；`0` 或非整数 → 报错。

### 2.3 对模型广告的 JSON schema

`multi_agents_spec.rs`：
- `create_spawn_agent_tool_v2`（L78-113）是 `ToolSpec::Function(ResponsesApiTool { name: "spawn_agent" })`——**普通 Function，无 namespace**。
- `required: Some(vec!["task_name", "message"])`（L106），`additionalProperties: false`。
- 属性来自 `spawn_agent_common_properties_v2`（L595-635，含 `message`/`agent_type`/`fork_turns`/`model`/`reasoning_effort`/`service_tier`）+ 在 L87-93 插入 `task_name`。
- V2 无 `items` 字段；`message` 走 `.with_encrypted()`。

---

## 3. 注册的工具名 & PreToolUse hook payload 的 `tool_name`

### 3.1 各自注册的 `ToolName`

- V1：`ToolName::namespaced(MULTI_AGENT_V1_NAMESPACE, "spawn_agent")`（`multi_agents/spawn.rs` L25-27），其中 `MULTI_AGENT_V1_NAMESPACE = "multi_agent_v1"`（`multi_agents_spec.rs` L11）。
- V2：`ToolName::plain("spawn_agent")`（`multi_agents_v2/spawn.rs` L27-29）。

`ToolName` 结构（`codex-rs/protocol/src/tool_name.rs` L8-38）有独立的 `name` 与 `namespace: Option<String>` 两字段，文档注释称其"preserving the namespace split when the model provides one"。Responses API 原生支持 namespace 工具类型（`codex-rs/tools/src/responses_api.rs` L47 `#[serde(rename = "namespace")]`），因此 V1 调用回来时 `namespace` 天然是 `Some("multi_agent_v1")`，不是靠字符串切分。

### 3.2 hook payload 的 `tool_name` 如何构成（核心）

链路：`registry.rs` 生成 `PreToolUsePayload` → `hook_runtime.rs::run_pre_tool_use_hooks` 把它写进 payload。

1. `run_pre_tool_use_hooks`（`codex-rs/core/src/hook_runtime.rs` L163-183）：
   ```rust
   tool_name: tool_name.name().to_string(),
   matcher_aliases: tool_name.matcher_aliases().to_vec(),
   ```
   其中 `tool_name: &HookToolName`（不是 protocol 的 `ToolName`）。
2. `function_hook_tool_name`（`codex-rs/core/src/tools/registry.rs` L713-724）：
   ```rust
   if invocation.tool_name.name == "spawn_agent"
       && matches!(invocation.tool_name.namespace.as_deref(),
                   None | Some(MULTI_AGENT_V1_NAMESPACE)) {
       return HookToolName::spawn_agent();
   }
   HookToolName::new(flat_tool_name(&invocation.tool_name).into_owned())
   ```
   → V2（namespace `None`）与 V1（namespace `"multi_agent_v1"`）**都命中**该分支。
3. `HookToolName::spawn_agent()`（`codex-rs/core/src/tools/hook_names.rs`）：`name = "spawn_agent"`，`matcher_aliases = vec!["Agent"]`。
4. 调用点 `registry.rs` L495-501：`run_pre_tool_use_hooks(..., &pre_tool_use_payload.tool_name, &pre_tool_use_payload.tool_input)`，即上面 `HookToolName` 直通。

**单元测试直接锁定该契约**（`codex-rs/core/src/tools/registry_tests.rs` L251-289，`spawn_agent_function_tools_use_agent_matcher_alias`）：对 `ToolName::plain("spawn_agent")`（V2）和 `ToolName::namespaced(MULTI_AGENT_V1_NAMESPACE, "spawn_agent")`（V1）分别取 `pre_tool_use_payload`，断言两者的 `tool_name` 都等于 `HookToolName::spawn_agent()`。

### 3.3 结论 & 与 0.144.1 的差异

- **V1 与 V2 的 hook `tool_name` 相同，均为 `"spawn_agent"`；`matcher_aliases = ["Agent"]`。**
- 0.144.1 观察到的 `collaborationspawn_agent` 来自 `flat_tool_name`（`codex-rs/core/src/tools/mod.rs` L39-49）：namespace 与 name **直接拼接、无分隔符**；同样 `ToolName::Display`（`tool_name.rs` L40-46）也是 `{namespace}{name}`。0.144.1 当时的 namespace 是 `collaboration` 且**没有** `HookToolName::spawn_agent()` 专用映射，于是 hook 名回退成拼接值 `collaborationspawn_agent`。
- 0.144.3 有两处变化叠加：(a) V1 namespace 常量改为 `multi_agent_v1`；(b) 新增 §3.2 的专用映射把 `spawn_agent` 归一化为规范名。因此 0.144.3 的实际 payload 值是 `spawn_agent`。
  - （未直接核验）0.144.1 中 namespace 字面量确为 `"collaboration"`：此点为据观察值反推，本次未拉取 0.144.1 tag 源码逐字确认；0.144.3 侧则已逐行核验。

---

## 4. Feature flags：`multi_agent` 与 `multi_agent_v2`

`codex-rs/features/src/lib.rs`：

| feature key | Feature id | stage | default_enabled | 行号 |
|---|---|---|---|---|
| `multi_agent` | `Feature::Collab` | `Stage::Stable` | `true` | L1035-1040 |
| `multi_agent_v2` | `Feature::MultiAgentV2` | `Stage::UnderDevelopment` | `false` | L1041-1046 |
| `multi_agent_mode` | `Feature::MultiAgentMode` | `Stage::Removed` | `false` | L1047-1052 |

### 4.1 版本派生（feature → 版本枚举）

`codex-rs/core/src/config/mod.rs` L1412-1419：

```rust
pub(crate) fn multi_agent_version_from_features(&self) -> MultiAgentVersion {
    if self.features.enabled(Feature::MultiAgentV2) {
        MultiAgentVersion::V2
    } else if self.features.enabled(Feature::Collab) {
        MultiAgentVersion::V1
    } else {
        MultiAgentVersion::Disabled
    }
}
```

- 默认（v2=false, Collab=true）→ **V1**。
- `multi_agent_v2` 优先级高于 `multi_agent`：一旦 v2 开启即为 V2，无视 `multi_agent`。

### 4.2 是否二选一互斥 → 是

`codex-rs/core/src/tools/spec_plan.rs`，`add_collaboration_tools`（L762-845）：

```rust
if collab_tools_enabled(turn_context) {
    if multi_agent_v2_enabled(turn_context) {
        // 只注册 V2 handlers：SpawnAgentHandlerV2 / SendMessageHandlerV2 /
        // FollowupTaskHandlerV2 / WaitAgentHandlerV2 / InterruptAgentHandler / ListAgentsHandlerV2
    } else {
        // 只注册 V1 handlers：SpawnAgentHandler / SendInputHandler /
        // ResumeAgentHandler / WaitAgentHandler / CloseAgentHandler
    }
}
```

- `multi_agent_v2_enabled`（L339-341）= `turn_context.multi_agent_version == V2`。
- 这是 `if/else`：**开启 multi_agent_v2 时只注册 V2 工具，V1 `spawn_agent` 不再注册**；反之亦然。同一 turn 内 V1/V2 工具集互斥，永不并存。
- `collab_tools_enabled`（L343-352）：`Disabled` → false（完全不注册 collab 工具）；`V1` → true（除非超出 spawn 深度上限）；`V2` → true。

---

## 5. model / reasoning_effort / service_tier / fork / agent_type 的合法取值与校验位置

全部校验函数在 `codex-rs/core/src/tools/handlers/multi_agents_common.rs`（V1、V2 spawn handler 共用）。

- **model**：`apply_requested_spawn_agent_model_overrides`（L234-283）→ `find_spawn_agent_model_name`（L340-358）。请求的 model 必须存在于可用 model 列表，否则 `Unknown model \`{m}\` for spawn_agent. Available models: {...}`。
- **reasoning_effort**：
  - 解析边界：`ReasoningEffort`（`codex-rs/protocol/src/openai_models.rs` L40-52 枚举 + L120-140 `FromStr`）。合法 wire 值：`none / minimal / low / medium / high / xhigh / max / ultra`；空串 → 报错 `reasoning_effort must not be empty`；其他任意非空串 → `Custom(String)`（解析层不拒绝）。
  - 语义校验：`validate_spawn_agent_reasoning_effort`（common.rs L360-380）。effort 必须在目标 model 的 `supported_reasoning_levels` 内，否则 `Reasoning effort \`{e}\` is not supported for model \`{m}\`. Supported reasoning efforts: {...}`。
  - 注意：`ultra` 是 Codex 官方合法枚举变体，**Codex 侧不专门拒绝 ultra**；本 router 仓库对 child effort `ultra` 的拒绝是 router 自身策略，与 Codex 无关。
- **service_tier**：`apply_spawn_agent_service_tier`（common.rs L285-338）。若请求的 tier 不被 model 支持（`model_info.supports_service_tier`）→ `Service tier \`{t}\` is not supported for model \`{m}\`. Supported service tiers: {...}`。候选优先级：config → requested → parent，取第一个被 model 支持者。
- **fork 覆盖冲突**：`reject_full_fork_spawn_overrides`（common.rs L193-204）。当"全量 fork + 任一 `agent_type`/`model`/`reasoning_effort`"同时出现时报错：`Full-history forked agents inherit the parent agent type, model, and reasoning effort; omit agent_type, model, and reasoning_effort, or spawn without a full-history fork.`
  - V1 触发条件：`args.fork_context == true`（`multi_agents/spawn.rs` L94）。
  - V2 触发条件：`fork_mode == Some(FullHistory)`（`multi_agents_v2/spawn.rs` L67）。
- **agent_type（两版语义一致）**：两版都把 `agent_type` 去空白、过滤空串后作为 `role_name`（`multi_agents/spawn.rs` L58-62；`multi_agents_v2/spawn.rs` L55-59），传入 `apply_role_to_config`（`codex-rs/core/src/agent/role.rs` L38-53）：
  - 缺省 → `DEFAULT_ROLE_NAME = "default"`（role.rs L29）。
  - 解析不到该 role → 报错 `unknown agent_type '{role_name}'`。
  - 命中则把该 role 的配置层（`config_file`）叠加到 child config 上。
  - 全量 fork 时 `agent_type` 必须省略（否则被 §5 的 fork 冲突校验拒绝）。

---

## 6. Codex Hooks 公开文档对 PreToolUse 的承诺（https://developers.openai.com/codex/hooks）

### 6.1 PreToolUse 输入 payload 字段（一手 schema）

`codex-rs/hooks/schema/generated/pre-tool-use.command.input.schema.json`（draft-07，`additionalProperties: false`）：

- **required**：`cwd`、`hook_event_name`（const `"PreToolUse"`）、`model`、`permission_mode`、`session_id`、`tool_input`、`tool_name`、`tool_use_id`、`transcript_path`（nullable string）、`turn_id`。
- **可选**：`agent_id`、`agent_type`（仅子代理上下文出现）。
- `tool_input`: `true`（任意 JSON）；`tool_name`: string；`permission_mode` 枚举：`default / acceptEdits / plan / dontAsk / bypassPermissions`。
- 文档补充：`tool_name` 是"Canonical hook tool name"，如 `Bash`、`apply_patch`、MCP 名 `mcp__fs__read`；`matcher` 作用于 `tool_name` 及 matcher aliases（`apply_patch` 也匹配 `Edit`/`Write`，但 payload 里仍报 `tool_name: "apply_patch"`）。

### 6.2 deny 输出（三种等价写法）

首选（hook-specific 形状）：
```json
{ "hookSpecificOutput": { "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook." } }
```
兼容的旧块形状：`{ "decision": "block", "reason": "..." }`。
也可用 **exit code 2** + 把原因写到 **stderr**。

其他输出：
- 不阻断地注入模型可见上下文：`hookSpecificOutput.additionalContext`。
- 不阻断地改写调用：`permissionDecision: "allow"` + `updatedInput`（Bash/apply_patch 的 `updatedInput` 必须含字符串 `command`；MCP 则是替换参数对象；`updatedInput` 只能与 `allow` 一起用）。

### 6.3 失败 / fail-open 行为

- `Exit 0` 且无输出 = 成功，Codex 继续。stdout 上的纯文本被忽略。
- PreToolUse 与 PermissionRequest 支持 `systemMessage`，但 `continue`、`stopReason`、`suppressOutput` **尚不支持**；以及 `permissionDecision: "ask"`、旧 `decision: "approve"`。文档原文："If a PreToolUse hook returns one of those unsupported fields, Codex marks that hook run as failed, reports the error, and continues the tool call." → 即**不支持的输出 = 该 hook run 标记失败并放行工具调用（fail-open）**。
- PreToolUse 定位为"guardrail rather than a complete enforcement boundary"，因为 Codex 常能改走另一条支持路径完成等效动作；且当前只拦截简单 shell、`apply_patch` 编辑与 MCP 调用，不拦截 `unified_exec` 的富交互路径、`WebSearch` 等。
- hook 超时：`timeout` 单位秒，省略则默认 600 秒（通用 hook 配置，非 PreToolUse 专属）。

---

## 附：验证方式与残留风险

- 验证方式：逐文件抓取 `rust-v0.144.3` 原始源码并核对具体行号；hook `tool_name` 结论另有单元测试 `spawn_agent_function_tools_use_agent_matcher_alias`（registry_tests.rs L251-289）直接锁定。
- 残留风险 / 未逐字核验项：
  1. 0.144.1 中 V1 namespace 字面量为 `"collaboration"` 属据现象反推（本次未拉取 0.144.1 tag）。
  2. 抓取过程中 GitHub 代理多次间歇 EOF；关键文件均已重试拉全并核对行号，未见截断内容进入结论。
