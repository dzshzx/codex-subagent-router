# Hook-managed routing 与 standalone custom agent TOML 评测

Date verified: 2026-07-15

## 结论先行

两种方案不是同一目标下的简单替代品。

- 对 [LINUX DO 帖子](https://linux.do/t/topic/2578075)所设定的目标——只有一种通用、只读、固定为 Luna/low、每次不继承历史的“探子”——standalone
  `~/.codex/agents/default.toml` 更直接。它能在一个代理文件里固定模型、推理强度、
  developer instructions、sandbox、MCP 和 skill 配置；没有必要为这一固定模板再引入三个
  Hook 生命周期、外部 Python launcher 和路由事务。
- 对本项目的目标——四个稳定角色复用同一套行为合同，但每次 spawn 按任务动态选择
  model/effort，拒绝 `ultra` 和 full-history fork，并在子代理创建前验证显式路由——现有
  Hook-managed 方案更合适。固定 compute 的 agent file 会把“角色身份”和“算力档位”重新
  绑在一起；若用角色×档位矩阵补救，又会复制合同和配置。
- 本项目面向的 `gpt-5.6-sol` 与 `gpt-5.6-terra` 在 0.144.4 bundled model catalog 中标记为
  MultiAgent V2；session 会先采用模型元数据，再以 feature flag 兜底。因此部署改为 V2
  优先，installer 直接设置 `enabled=true`、`hide_spawn_agent_metadata=false` 和
  `tool_namespace="agents"`。V1 parser 只保留为兼容 seam，不再作为生成配置的默认路径。
- 对一般 Codex 用户，默认应先选官方 standalone custom agent：它是当前官方文档主推的
  声明式扩展面，能力更完整、文件更少。只有在确实需要跨 spawn 动态策略、执行前校验、
  根线程路由指导或外部可测试策略代码时，才值得承担 Hook 的信任、兼容性和 fail-open 成本。
- 两种方案都不是强安全或强成本隔离边界。custom agent 的配置受父会话 live runtime
  override 影响；普通 command Hook 失败则会 fail open。本项目的 `PreToolUse` 是可观测的
  policy guardrail，不应被描述成不可绕过的 enforcement boundary。

## 证据等级与评测边界

本文把来源分成四层，结论不跨层升级：

1. **官方现行文档**：用于说明当前公开的 custom agent 与 Hook 产品能力。官方
   [Subagents 文档](https://developers.openai.com/codex/subagents)说明 custom agent 的目录、
   必填字段、可继承配置和 sandbox 行为；官方
   [Hooks 文档](https://developers.openai.com/codex/hooks)说明 Hook 的发现、信任、生命周期和
   输出语义。
2. **`rust-v0.144.4` 不可变 tag 源码、schema 与测试**：用于说明本项目兼容版本的精确实现，
   而不是把 `main` 分支行为倒推到旧版本。该 tag 的 release commit 是
   [`8c68d4c87dc54d38861f5114e920c3de2efa5876`](https://github.com/openai/codex/releases/tag/rust-v0.144.4)。
3. **本仓库 installed-binary 观察**：
   [`codex-0.144.4-hook-evidence.md`](codex-0.144.4-hook-evidence.md)记录隔离
   `CODEX_HOME`、loopback Responses provider 和已发布 musl 二进制的观察。它可以证明“这次
   二进制在该探针中怎样运行”，不能证明 OpenAI 真实后端、其他平台或未来版本也如此。
4. **帖子实践材料**：帖子是有价值的二手配置经验，但其速度、额度、模型目录和后端兼容
   叙述不是 OpenAI 承诺。本文只在官方文档、tag 源码或本地探针能独立支持时把它提升为事实。

特别边界：本仓库对 V2 的正向探针使用 loopback provider。它验证本地 CLI 构造的 schema、
Hook 可见名称、参数保留与子线程配置，不验证真实 OpenAI 后端是否接受自定义 namespace 或扩展
schema。V2 优先是依据目标模型的本地选择逻辑作出的安装决策，不把这份 loopback 观察升级为
跨版本、跨 provider 的兼容保证。

## 两个目标实际在解决不同问题

| 维度 | 帖子的 fixed scout | 本项目的 router |
|---|---|---|
| 持久角色 | 一个 `default` 通用只读探子 | `researcher`、`reviewer`、`architecture_explorer`、`interface_designer` 四个稳定角色 |
| compute | 固定 Luna/low | 每次 spawn 从五个 routine 和两个 conditional profile 显式选择 |
| 模型可见参数 | V2 中有意隐藏 `agent_type`、`model`、`reasoning_effort`、`service_tier` | 必须暴露并显式提交 role/model/effort，Hook 才能校验 |
| 上下文 | 固定 `fork_turns="none"` | V2 允许 `none` 或正整数；V1 要求 `fork_context=false`；均拒绝 full history |
| 行为来源 | `default.toml` 的 `developer_instructions` | `roles.py` 的行为合同，经 `SubagentStart` 注入 |
| 策略来源 | `AGENTS.md` 中的调度纪律 | `policy.py` 的版本化 allowlist + `SessionStart` 指导 + `PreToolUse` deny |
| 主要收益 | 低成本、低延迟、隔离读操作噪声 | 同一角色可按任务升级/降级 compute，并显式拒绝越界组合 |

因此，“帖子配置比 Hook 简单”在帖子目标下成立；“它能替代本项目策略”不成立。反过来，
“Hook 能表达更多策略”也不意味着固定探子用户应该采用 Hook。

## 帖子主要主张逐项核验

### 1. custom agent 能固定模型、effort 和行为：成立

官方文档要求 standalone 文件定义 `name`、`description`、`developer_instructions`，并允许
`model`、`model_reasoning_effort`、`sandbox_mode`、`mcp_servers`、`skills.config` 等普通
`config.toml` 键；遗漏的可选值从父会话继承。代理身份以文件内 `name` 为准，而不是文件名。
参见官方 [Custom agents 与 file schema](https://developers.openai.com/codex/subagents#custom-agents)。

`rust-v0.144.4` 将选中的 role file 作为 session-flag 高优先级配置层重新加载；若文件设置
model 或 effort，它们会覆盖 spawn 所请求的 compute。工具说明也会告诉模型这些设置不可更改。
参见 tag 源码
[`agent/role.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/role.rs#L32-L81)
和
[`spawn tool role description`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/role.rs#L250-L299)。
本仓库 installed-binary 探针也观察到 standalone `reviewer` 把请求的 Terra/medium 替换为
文件内 Sol/high；这是 0.144.4 二进制观察，不是跨版本承诺。

### 2. 更快、更省、上下文更干净：机制合理，但不能归因于 TOML 格式

帖子组合了三个独立变量：

1. **model/effort**：把重模型改成 Luna/low，直接改变每个子线程的计算预算；
2. **fork shape**：`fork_turns="none"` 不复制主线程历史，减少子线程输入并隔离中间噪声；
3. **调度纪律**：只外包宽而重的读取、并行独立任务、要求高密度证据、等待后收口、禁止子代理
   再派生。

TOML 只是持久化第一个变量和角色合同的载体。第二个变量来自 spawn 参数，第三个主要来自
`AGENTS.md`/skill/brief 的模型可见指导。官方文档支持“把噪声移出主线程、返回摘要、并行读重
任务”的一般价值，同时也明确每个子代理会做自己的模型与工具工作，因此相较单代理通常消耗
更多 token；并行写任务还会增加冲突和协调成本。参见官方
[Why use subagent workflows](https://developers.openai.com/codex/subagents#why-use-subagent-workflows)。

所以帖子的速度和额度体验可以作为该配置的实测线索，不能写成 custom agent TOML 的普遍性能
保证，也不能推出“子代理越多越省”。

### 3. `hide_spawn_agent_metadata=true` 适合单模板：成立，但与本项目相反

V2 schema builder 在该选项开启时移除 `agent_type`、`model`、`reasoning_effort`、
`service_tier`，只留下 V2 的 `task_name`、`message`、`fork_turns` 等字段。参见 tag 源码
[`multi_agents_spec.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L79-L113)
和
[`hide_spawn_agent_metadata_options`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L637-L642)。

这正适合帖子“只有 default 一种模板，禁止模型临时选型”的目标。对本项目则是硬冲突：validator
要求每个 routed spawn 显式提供 role/model/effort。0.144.4 installed-binary 的默认 V2 探针
因此全部被 router 拒绝；只有在 loopback arm 同时设置
`hide_spawn_agent_metadata=false` 和 `tool_namespace="agents"` 后才可路由。

### 4. “V1 就是 `[agents]`，V2 就是 `[features.multi_agent_v2]`”：过度简化

`[agents]` 同时承载全局线程设置和 inline role 声明，并不等同于 V1 wire protocol。现行官方
文档仍把 `agents.max_threads`、`max_depth` 等列为全局 subagent 设置。tag 源码确实拒绝“启用
V2 时同时设置 `agents.max_threads`”，但没有因此拒绝 inline role；参见
[`validate_multi_agent_v2_config`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/mod.rs#L1410-L1428)。
本仓库探针也确认 inline role 在 V2 下能解析，失败点是默认隐藏 routing metadata，而不是
`[agents.<role>]` 语法本身。

帖子所述 Sol/Terra/Luna 的模型目录映射与本机 0.144.4 bundled catalog 一致：
`gpt-5.6-sol`、`gpt-5.6-terra` 为 V2，`gpt-5.6-luna` 为 V1。关键修正是不能只看 feature
declaration：session 先读取 `model_info.multi_agent_version`，只有模型没有偏好时才回退到
feature flag，参见固定 tag 的
[`session/mod.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/mod.rs#L3109-L3123)。
`multi_agent` stable/enabled 与 `multi_agent_v2` under-development/disabled 仍是 feature
目录事实，但不是 Sol/Terra 的最终选择结果。因此本项目为目标模型显式打开 V2，并同时暴露
routing metadata、固定 `agents` namespace；帖子结论在此点应提升为本项目的部署前提。

### 5. Ultra 是高 effort 加多代理编排：核心方向有 tag 源码支持

0.144.4 源码把 Ultra 请求映射到 `max` wire effort，并另行选择 proactive multi-agent mode；
参见
[`client.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/client.rs#L165-L177)
和
[`session/multi_agents.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/multi_agents.rs#L45-L58)。
因此本项目拒绝 child `ultra` 是有依据的项目策略：已被派发边界明确任务的 child 不应再次携带
主动编排语义。但帖子给出的 juice 数字、具体提示词和性能体验仍不是官方兼容合同。

## compute、角色与上下文

### Standalone agent

- 若 role file 固定 model/effort，选中该角色的每次 spawn 都使用相同 compute；若遗漏字段，
  则从父会话继承。它擅长“角色即固定运行配置”。
- `developer_instructions` 是该角色的必填核心行为，和 compute、sandbox、MCP、skills 一起
  进入高优先级 session config layer。
- 若同一行为需要七个 compute 档位，必须修改文件、创建多个 role，或不在文件中固定 compute。
  前两者降低动态性并可能复制合同；第三种则失去帖子的“永远 Luna/low”保证。

### Hook-managed router

- inline role 只声明 name/description，不提供 `config_file`，因此不会以 role config reload
  覆盖 per-spawn compute。
- 父代理按 `policy.py` 为每次 spawn 显式选 role/model/effort/fork；`PreToolUse` 只校验并拒绝，
  不猜测、不补字段、不改写。
- 同一 `reviewer` 可在 Terra/medium、Sol/high 或 conditional Sol/max 上执行，而行为合同仍只有
  一份。
- full-history fork 和 `ultra` 是本项目主动禁止的 policy，不是 Codex 对所有用户的非法输入。

因此 standalone 的“锁定”是 fixed-scout 的优势，却是动态路由的限制；Hook 的“显式参数”是
动态策略的优势，却增加了 schema 和工具名耦合。

## 生命周期与角色 instructions

本项目使用三个互补时点：

1. `SessionStart(startup)` 在 root 第一次采样前加入完整路由指导；`resume`、`clear`、`compact`
   不输出本项目指导。
2. `PreToolUse(spawn_agent)` 在注册工具 handler 前运行。明确 `deny` 时会在 child 创建前返回，
   tag 路径见
   [`tools/registry.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/registry.rs#L493-L535)。
3. `SubagentStart(agent_type)` 在 child 第一次 sampling loop 前加入对应 role contract；tag 顺序见
   [`hook_runtime.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/hook_runtime.rs#L103-L145)
   和
   [`session/turn.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/session/turn.rs#L167-L190)。

官方 Hook 文档确认 `SessionStart`/`SubagentStart` 属于 thread/start scope，`PreToolUse` 属于
turn scope；`SubagentStart.additionalContext` 会成为 child 的额外 developer context，但
`continue:false` 不会阻止 child 启动。参见官方
[Hook runtime behavior](https://developers.openai.com/codex/hooks#runtime-behavior-to-keep-in-mind)
和
[`SubagentStart`](https://developers.openai.com/codex/hooks#subagentstart)。

standalone agent 不需要这些事件来加载自己的 instructions；它在 spawn 配置构造时应用 role
layer。重要的版本边界是：本仓库 0.144.4 二进制探针中，standalone-resolved child 没有发出
`SubagentStart`，即使 matcher 改为 catch-all 也没有捕获。由此本项目把 standalone 与
Hook-managed 同名角色定义为**替代模式**，而不是把两套 instructions 叠加。官方 Hook 文档没有
承诺“standalone child 永远不发该事件”，因此该结论只能用于 0.144.4 支持边界，未来版本必须
重测。

## V1/V2 与 hook-visible contract

`rust-v0.144.4` 有两个不同 spawn schema：

| 项目 | V1 | V2 |
|---|---|---|
| 核心参数 | `message`/`items`、`agent_type`、`fork_context`、`model`、`reasoning_effort`、`service_tier` | `task_name`、`message`、`fork_turns`；routing metadata 可被隐藏 |
| 默认 fork 表达 | boolean `fork_context` | `none`、`all` 或正整数字符串，省略时为 `all` |
| 0.144.4 feature 目录 | stable/enabled | under-development/disabled |
| 目标模型元数据 | Luna | Sol、Terra |
| 本项目状态 | 保留 validator 兼容 seam | 生成配置优先；显式启用、暴露 metadata、使用 `agents` namespace |

精确字段来自 tag 的
[`spawn schema builders`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_spec.rs#L47-L113)
和
[`V2 parser`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/tools/handlers/multi_agents_v2/spawn.rs#L178-L220)。

V2 还引入 namespace/tool-name 风险。0.144.4 默认 namespace 是 `collaboration`；非 V1 namespace
会被 flatten 到 Hook 可见名称，因此本仓库实测过 `collaborationspawn_agent` 与配置
`tool_namespace="agents"` 后的 `agentsspawn_agent`。默认稳定 V1 则是 `spawn_agent`。这是本地
CLI 与 tag registration/normalization 的事实，不表示真实后端接受任意 V2 schema。帖子后来
建议切换到 `agents` namespace，反映的正是这种版本/后端兼容风险；不能把社区 workaround 当
官方稳定接口。

对帖子固定 default 角色而言，V2 隐藏 routing metadata 是简化。对本项目，它会让 validator
缺少必要输入而 fail closed。因此 installer 必须直接写入三项完整 V2 配置；已有完全兼容的
user-owned 表原样保留，部分或冲突配置 fail closed。V2 成为目标部署路径，但 0.144.4 的
real-backend 证据边界仍保持不变。

## role discovery、层级与同名冲突

官方文档允许个人角色放在 `~/.codex/agents/`，项目角色放在 `.codex/agents/`。tag 源码按
config layer 从低到高加载；同一 layer 先加载 inline `[agents.<role>]`，再扫描 `agents/`
目录。相同 `name` 的 standalone 在同层被当作 duplicate 跳过；高优先级 layer 可替换低层角色，
同时继承它没有提供的 metadata。参见
[`agent_roles.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L19-L115)。
user-defined role 也先于同名 built-in 解析，参见
[`resolve_role_config`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/agent/role.rs#L119-L127)。

本仓库 0.144.4 探针具体观察到：

- 同一 user layer 同时有 inline 与同名 standalone 时，inline 胜出并有 duplicate warning；
- trusted project standalone `reviewer` 可覆盖 user inline `reviewer`；
- 覆盖后 child 使用项目文件的固定 compute/instructions，并没有 managed `SubagentStart` context。

所以 router 不是只检查一个文件就能安全“叠加” custom agent。它正确地在显式 user
`CODEX_HOME` 下递归拒绝四个保留名的 standalone 文件；但 user installer 无法枚举所有未来
项目，project-layer 冲突仍是 operator 责任。

Hook 层级语义又不同：官方文档说明多个来源的 matching hooks 全部加载，高优先级配置层不会
替换低优先级 hooks；同层 `hooks.json` 和 inline `[hooks]` 还会合并并警告。参见官方
[Where Codex looks for hooks](https://developers.openai.com/codex/hooks#where-codex-looks-for-hooks)。
因此 Hook 需要避免重复 handler、并发输出和同一事件多方修改，不应套用 role 的“高层覆盖低层”
直觉。

## trust、fail-open 与故障模式

### Hook-managed

非 managed command Hook 必须按精确 normalized definition hash 审核信任；新建或修改后在再次
trust 前会被跳过，project Hook 还要求项目 `.codex` layer 已信任。参见官方
[Review and trust hooks](https://developers.openai.com/codex/hooks#review-and-trust-hooks)。本项目
installer 有意不写 trust state，也不启用 `--dangerously-bypass-hook-trust`。

明确 deny 或 exit code 2 + stderr 可以阻止 `PreToolUse`；但进程启动失败、timeout、普通非零
退出、无效输出和 schema 漂移通常只记录 Hook failure，工具继续。精确 0.144.4 行为见
[`pre_tool_use.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/events/pre_tool_use.rs#L54-L141)
及
[`command result handling`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/hooks/src/events/pre_tool_use.rs#L188-L285)。
本仓库故意把 `SessionStart` 接到错误 adapter 的探针也观察到 wrapper exit 1 后 turn 继续。

典型故障包括：未 trust/被禁用、launcher 被删除或不可执行、Python 环境移动、matcher 漏掉新
tool name、上游 input schema 新增字段触发严格 parser、多个 hook 并发冲突。其危险之处不是总是
“启动失败”，而是路由指导、角色合同或 deny policy 可能静默缺席。因此每个 Codex 版本都需要
source/schema 对比和 installed-binary release gate。

### Standalone custom agent

standalone 没有单独的 command-hook hash trust 流程，但 project config layer 是否激活仍受项目
trust 影响。损坏、缺必填字段或 duplicate 的 role 会被忽略并产生 startup warning；应用 role
layer失败则 spawn 报“agent type is currently not available”。tag 的解析与 warning 路径见
[`agent_roles.rs`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L118-L162)
和
[`standalone schema parsing`](https://github.com/openai/codex/blob/rust-v0.144.4/codex-rs/core/src/config/agent_roles.rs#L218-L315)。

其主要故障不是 Hook fail-open，而是选择了错误层的同名 role、固定 compute 覆盖调用方意图、
未设置字段时意外继承父配置、MCP/skill 依赖缺失，或 live runtime override 改变文件默认值。
官方文档明确说 child 继承父 turn 的 live sandbox/approval override，即使 custom agent file 写了
不同默认值；参见
[Approvals and sandbox controls](https://developers.openai.com/codex/subagents#approvals-and-sandbox-controls)。

## sandbox、MCP、skills 与工具面

这是 standalone agent 的明显优势。官方把每个 standalone 文件当作 spawned session 的完整
config layer，因此可以按角色设置：

- `sandbox_mode`，例如把 explorer 固定为 read-only；
- 专用 `mcp_servers`，例如只给 docs researcher 开文档 MCP；
- `skills.config` 及其他受支持的 `config.toml` 项。

官方示例同时展示了 read-only reviewer 与专用 docs MCP researcher，参见
[Example custom agents](https://developers.openai.com/codex/subagents#example-custom-agents)。但 live
parent permission override 的优先级仍需注意。

本项目的 `SubagentStart` 输出只能增加 developer context，不能重建 child 的 sandbox、MCP 或
skills config。`PreToolUse` 也不能补足这一点：官方明确称其为 guardrail，而不是完整执行边界，
且当前只拦截部分 shell、`apply_patch` 和 MCP 路径，不覆盖 WebSearch 等所有工具。参见官方
[`PreToolUse`](https://developers.openai.com/codex/hooks#pretooluse)。若未来需要角色级工具最小化，
应优先评估不与 managed 名冲突的 standalone role，或改变本项目 definition mode；不要把
SubagentStart 文本误写成 sandbox。

## 安装、回滚与可移植性

### Standalone

固定探子的最小变更是一个 `agents/default.toml`；帖子完整工作流另需 `AGENTS.md` 和
`config.toml`。复制、审阅和手工备份都较直接。官方同时提醒 standalone 文件是完整 session
config layer，形式相对 dedicated manifest 更重，且可能随 authoring/sharing 能力成熟而演进；
参见官方 [Custom agents](https://developers.openai.com/codex/subagents#custom-agents)。官方文档没有
提供把多个用户文件作为一个事务安装或精确回滚的流程。

### 本项目 installer

router 必须同时管理 `config.toml` 的四个 description-only inline roles、`hooks.json` 的三个
event group、持久 Python launcher 和私有 receipt/journal。其优势是本仓库已实现：

- 显式 `--codex-home` 的只读 plan、install、status、rollback；
- operation lock、原始 bytes/mode、hash 与 journal；
- crash recovery、幂等重试、后续无关用户修改的保留；
- symlink/非普通文件、冲突 role/hook、坏 receipt/journal 时 fail closed；
- rollback 只删除 installer-owned 且仍完整的条目。

代价是当前仅验证 POSIX，launcher 路径是机器绝对路径，package/venv 被移动后 Hook 会失效；
用户还必须在新 session 中审核 Hook trust。它在“安全管理已有用户配置”上强于帖子里的手工覆盖，
但在跨机器复制和零依赖上弱于单个 agent TOML。若通过 plugin 或企业 managed hooks 分发，可改善
部署一致性，但那是另一种部署产品，不是当前 installer 已验证的能力。

## 分场景建议

| 场景 | 建议 | 原因 |
|---|---|---|
| 单一 cheap read-only scout，始终 Luna/low | standalone `default.toml` | 目标与固定 role config 完全一致；V2 可隐藏 metadata，配置最少 |
| 多个专业角色，每个角色有固定 compute/sandbox/MCP | 多个 standalone TOML | 官方原生表达能力完整，role file 就是 session config layer |
| 同一角色需按任务动态升降 model/effort | Hook-managed router | 角色合同与 compute 分离，避免 role×profile 文件矩阵 |
| 必须拒绝 child `ultra`、full-history 或未显式路由 | Hook-managed，但只视为 guardrail | `PreToolUse` 可在正常运行时创建前 deny；普通故障仍 fail open |
| 需要硬安全隔离或不可绕过成本上限 | 两者都不够 | 应使用 sandbox、approval/requirements、provider/account policy 等更强边界 |
| 团队只想快速采用官方可移植配置 | standalone 优先 | 少一个外部 runtime、Hook trust 和版本化 wire adapter |
| 需要可测试、版本化、可恢复的组织路由策略 | 本项目 installer + Hook | 策略、协议、安装状态和回滚可由代码与测试锁定 |

## 最终判断

### 对本项目目标

保留 Hook-managed 方案。其必要性不在于“Hook 比 TOML 高级”，而在于三个不可约简需求：

1. **per-spawn 动态 compute**：同一角色复用多个 profile；
2. **创建前 deny-only policy**：拒绝 `ultra`、full history、缺字段和不在 allowlist 的组合；
3. **角色与算力分离**：四个稳定行为合同不复制成角色×模型×effort 文件矩阵。

部署以 V2 为优先：installer 显式启用 V2、暴露 routing metadata 并使用 `agents` namespace；
V1 只保留为兼容 seam。与此同时维持证据边界：四个 managed 名在所有 active custom-agent
layer 中保留；project 冲突由 operator 负责；0.144.4 的 V2 正向运行证据仍是 loopback；Hook
enforcement 明示 fail open。

### 对通用 Codex 用户

优先从 standalone custom agent 开始。特别是帖子这种 fixed Luna-low scout，TOML 是更小、更
原生、更易复制的答案。不要把帖子的效果归功于 TOML 本身：真正决定速度、成本和上下文质量的
是 model/effort、fork shape 与调度纪律。只有当这些固定配置无法表达动态 policy，并且用户愿意
承担 trust、launcher、schema/tool-name 漂移和版本探针成本时，再采用 Hook-managed routing。
