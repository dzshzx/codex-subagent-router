# V2 兼容性情报 intake：linux.do 2578075

来源：《【拯救 5.6 Sol（1）】开箱即用、快速高效、减少上下文腐烂的 Codex 子代理实践》
（https://linux.do/t/topic/2578075 ，MotorwaySouth，2026-07-13 发帖，2026-07-14 更新，
含 126 楼回复中楼主的补充）。2026-07-15 对照本项目源码与既有研究完成 intake。

性质：外部实践帖的兼容性对照。帖中所有「默认值」「上游行为」均为楼主转述或引用，
落地前一律以 installed-binary 探针为准（项目既定方针，见 memory 与
docs/research/codex-0.144.3-hook-evidence.md 的先例）。

帖子引用的上游材料（探针/研究可直接复用）：

- openai/codex#31864 — `collaboration.spawn_agent` 是 5.6 后端保留工具名
- openai/codex#20077 — V2 spawn 缺省 fork_turns 落 full-history、`all` 强制继承
- openai/codex#18394 — wait_agent timeout 可配置、超时 ≠ 子代理终止
- https://developers.openai.com/codex/subagents — `agents/*.toml` 官方字段
- codex-rs/models-manager/models.json — per-model `multi_agent_version` 映射（Sol/Terra→v2，Luna→v1）

已被既有研究覆盖、不建票的点：

- 正整数 `fork_turns` 是否强制继承父路由 — 已核实不继承，`none` 与正整数
  允许 per-spawn 显式路由，仅 `all` 强制继承
  （docs/research/codex-0.144.1-hook-evidence.md:136-138，引官方 spawn.rs）。
- 「安装后需新 session、不假设热加载」「用户后续修改 fail closed」— 帖 96/127/119
  楼与本项目既有硬性约束互相印证，无行动。

## Issues

| # | 票 | Status |
|---|---|---|
| 01 | hide_spawn_agent_metadata 运行前提未校验 | needs-triage |
| 02 | tool_namespace 保留名冲突未校验 | needs-triage |
| 03 | [agents.<role>] 与显式 multi_agent_v2 共存性未验证 | ready-for-agent |
| 04 | 评估 luna/low 作为探索型负载低档 | ready-for-human |
| 05 | ADR 记录禁 ultra 的机制层理据 | ready-for-agent |
| 06 | 派发后行为纪律不纳入 hook guidance | wontfix |

2026-07-15 本机 `0.144.4` 证据已追加到 issue 01–03。完整版本 release gate
与 installer 的 standalone-agent 漏检分别由
`release-readiness/issues/10-01444-probe.md` 和
`release-readiness/issues/11-standalone-agent-conflict-preflight.md` 追踪。
